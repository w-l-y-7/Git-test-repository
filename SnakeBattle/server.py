"""
贪吃蛇对战 —— 服务器

服务器说了算：它自己跑游戏逻辑，玩家只负责把按键发上来、把收到的画面画出来。
这样两台电脑看到的画面永远一致，不会各算各的算岔了。
"""

import asyncio
import json
import random
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).parent

COLS, ROWS = 40, 30      # 棋盘多少格
TICK_MS = 40             # 服务器心跳：每 40 毫秒推进一拍，一秒 25 拍
A_EVERY = 2              # 玩家 A 每 2 拍走一步 → 80 毫秒一格
B_EVERY = 3              # 玩家 B 每 3 拍走一步 → 120 毫秒一格
FOOD_COUNT = 2           # 棋盘上同时存在几个食物

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

app = FastAPI()


@app.get("/")
async def index():
    """把游戏页面发给浏览器。"""
    return FileResponse(BASE_DIR / "index.html")


class Snake:
    """一条蛇。body 是身体坐标列表，第 0 个是蛇头。"""

    def __init__(self, x, y, dx, dy):
        self.body = [(x, y), (x - dx, y - dy), (x - 2 * dx, y - 2 * dy)]
        self.dir = (dx, dy)
        self.pending = []        # 玩家按下的方向，排队等这一步走完再生效
        self.score = 0
        self.alive = True

    def turn(self, name):
        """收到玩家按键。掉头和重复方向直接忽略，最多缓存两步防止乱按丢键。"""
        d = DIRS.get(name)
        if d is None:
            return
        last = self.pending[-1] if self.pending else self.dir
        if d == (-last[0], -last[1]) or d == last:
            return
        if len(self.pending) >= 2:
            return
        self.pending.append(d)

    def next_head(self):
        return (self.body[0][0] + self.dir[0], self.body[0][1] + self.dir[1])


class Room:
    """一个房间 = 两个玩家 + 一局游戏。"""

    def __init__(self, code):
        self.code = code
        self.players = {}        # "a" / "b" → WebSocket
        self.task = None
        self.over = False
        self.tick = 0
        self.a = None
        self.b = None
        self.food = []

    # ---------- 开局 ----------
    def reset(self):
        self.tick = 0
        self.over = False
        self.food = []
        self.a = Snake(4, 10, 1, 0)              # 玩家 A 在左边，往右走
        self.b = Snake(COLS - 5, ROWS - 11, -1, 0)  # 玩家 B 在右边，往左走
        self.spawn_food()

    def spawn_food(self):
        """把食物撒在空格子里。"""
        taken = set(self.a.body) | set(self.b.body) | set(self.food)
        free = [
            (x, y)
            for y in range(ROWS)
            for x in range(COLS)
            if (x, y) not in taken
        ]
        while len(self.food) < FOOD_COUNT and free:
            self.food.append(free.pop(random.randrange(len(free))))

    # ---------- 推进一拍 ----------
    def step(self):
        """返回 True 表示这一步有蛇动了，需要把新画面对外广播。"""
        if self.over:
            return False

        self.tick += 1
        a_moves = self.tick % A_EVERY == 0 and self.a.alive
        b_moves = self.tick % B_EVERY == 0 and self.b.alive
        if not (a_moves or b_moves):
            return False

        if a_moves and self.a.pending:
            self.a.dir = self.a.pending.pop(0)
        if b_moves and self.b.pending:
            self.b.dir = self.b.pending.pop(0)

        # 先算出移动的蛇这一步的新头，再统一判定死伤。
        # 分开算的话，先处理的那条蛇会占到便宜。
        heads = {}
        if a_moves:
            heads["a"] = self.a.next_head()
        if b_moves:
            heads["b"] = self.b.next_head()

        dead = set()
        for who, head in heads.items():
            me = self.a if who == "a" else self.b
            other = self.b if who == "a" else self.a
            other_moving = b_moves if who == "a" else a_moves

            if not (0 <= head[0] < COLS and 0 <= head[1] < ROWS):
                dead.add(who)                      # 撞墙
                continue
            if head in me.body[:-1]:
                dead.add(who)                      # 撞自己（尾巴那格下一步就让位了）
                continue
            # 撞对方。对方这一步也在动的话，它尾巴那格同样会让位
            other_body = other.body[:-1] if other_moving else other.body
            if head in other_body:
                dead.add(who)
                continue
            # 两个头撞在一起，同归于尽
            if len(heads) == 2 and heads["a"] == heads["b"]:
                dead.add(who)

        # 判定完了再统一落子
        for who in ("a", "b"):
            if who not in heads:
                continue
            me = self.a if who == "a" else self.b
            if who in dead:
                me.alive = False
                continue

            head = heads[who]
            me.body.insert(0, head)
            if head in self.food:
                self.food.remove(head)
                me.score += 1
                self.spawn_food()
            else:
                me.body.pop()

        if not self.a.alive or not self.b.alive:
            self.over = True

        return True

    def winner(self):
        if self.a.alive and self.b.alive:
            return None
        if self.a.alive:
            return "a"
        if self.b.alive:
            return "b"
        return "draw"

    # ---------- 对外 ----------
    def snapshot(self):
        return {
            "type": "state",
            "a": {"body": self.a.body, "score": self.a.score, "alive": self.a.alive},
            "b": {"body": self.b.body, "score": self.b.score, "alive": self.b.alive},
            "food": self.food,
            "over": self.over,
            "winner": self.winner(),
        }

    async def broadcast(self, payload):
        text = json.dumps(payload)
        for ws in list(self.players.values()):
            try:
                await ws.send_text(text)
            except Exception:
                pass

    async def run(self):
        """房间的主循环：每 40 毫秒推进一拍，有变化就把新画面对外广播。"""
        try:
            while not self.over:
                await asyncio.sleep(TICK_MS / 1000)
                if self.step():
                    await self.broadcast(self.snapshot())
            await self.broadcast(self.snapshot())
        except asyncio.CancelledError:
            pass

    def start(self):
        if self.task:
            self.task.cancel()
        self.task = asyncio.create_task(self.run())


ROOMS = {}


def new_code():
    while True:
        code = f"{random.randint(0, 9999):04d}"
        if code not in ROOMS:
            return code


@app.websocket("/ws")
async def game_socket(ws: WebSocket):
    await ws.accept()
    room = None
    role = None

    try:
        while True:
            msg = json.loads(await ws.receive_text())
            kind = msg.get("type")

            if kind == "create":
                code = new_code()
                room = Room(code)
                ROOMS[code] = room
                role = "a"
                room.players["a"] = ws
                await ws.send_text(json.dumps(
                    {"type": "joined", "role": "a", "room": code, "waiting": True}
                ))

            elif kind == "join":
                code = str(msg.get("room", "")).strip()
                target = ROOMS.get(code)
                if target is None:
                    await ws.send_text(json.dumps(
                        {"type": "error", "msg": "没找到这个房间号"}
                    ))
                    continue
                if "b" in target.players:
                    await ws.send_text(json.dumps(
                        {"type": "error", "msg": "这个房间已经满了"}
                    ))
                    continue

                room, role = target, "b"
                room.players["b"] = ws
                await ws.send_text(json.dumps(
                    {"type": "joined", "role": "b", "room": code}
                ))
                room.reset()
                await room.broadcast({"type": "start"})
                room.start()

            elif kind == "dir":
                if room and role and not room.over:
                    snake = room.a if role == "a" else room.b
                    snake.turn(msg.get("d"))

            elif kind == "again":
                if room and room.over:
                    room.reset()
                    await room.broadcast({"type": "start"})
                    room.start()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"连接出错：{e}")
    finally:
        if room and role:
            room.players.pop(role, None)
            if room.task:
                room.task.cancel()
            ROOMS.pop(room.code, None)
            await room.broadcast({"type": "peer_left"})
