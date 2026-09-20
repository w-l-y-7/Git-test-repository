# -*- coding: utf-8 -*-
"""SnakeBattle/server.py 的单元测试。

只测游戏逻辑（蛇、房间推进、碰撞、吃食物、胜负），
WebSocket 连接部分不测（那是网络，不属于纯逻辑）。
"""
import unittest

import server
from server import (
    A_EVERY,
    B_EVERY,
    COLS,
    DIRS,
    FOOD_COUNT,
    ROOMS,
    ROWS,
    Room,
    Snake,
    new_code,
)


class TestSnakeBasics(unittest.TestCase):
    """一条蛇的基本行为。"""

    def test_init_pointing_right(self):
        s = Snake(4, 10, 1, 0)
        self.assertEqual(s.body, [(4, 10), (3, 10), (2, 10)])
        self.assertEqual(s.dir, (1, 0))
        self.assertEqual(s.score, 0)
        self.assertTrue(s.alive)
        self.assertEqual(s.pending, [])

    def test_init_pointing_left(self):
        # 边界：朝左时身体应往右排（在蛇头身后）
        s = Snake(COLS - 5, ROWS - 11, -1, 0)
        self.assertEqual(s.body[0], (COLS - 5, ROWS - 11))
        self.assertEqual(s.body[1], (COLS - 4, ROWS - 11))
        self.assertEqual(s.dir, (-1, 0))

    def test_next_head(self):
        s = Snake(4, 10, 1, 0)
        self.assertEqual(s.next_head(), (5, 10))
        s.dir = (0, -1)
        self.assertEqual(s.next_head(), (4, 9))

    def test_turn_accepts_valid_direction(self):
        s = Snake(4, 10, 1, 0)
        s.turn("up")
        self.assertEqual(s.pending, [(0, -1)])

    def test_turn_ignores_reverse(self):
        s = Snake(4, 10, 1, 0)
        s.turn("left")          # 正朝右，掉头左转应被忽略
        self.assertEqual(s.pending, [])

    def test_turn_ignores_same_direction(self):
        s = Snake(4, 10, 1, 0)
        s.turn("right")         # 和当前方向一样，忽略
        self.assertEqual(s.pending, [])

    def test_turn_ignores_unknown_direction(self):
        # 异常输入：不认识的按键名
        s = Snake(4, 10, 1, 0)
        s.turn("diagonal")
        s.turn(None)
        self.assertEqual(s.pending, [])

    def test_turn_reverse_of_last_pending_is_ignored(self):
        s = Snake(4, 10, 1, 0)
        s.turn("up")
        s.turn("down")          # 和"排队中最后一步"相反，忽略
        self.assertEqual(s.pending, [(0, -1)])

    def test_turn_caches_at_most_two(self):
        s = Snake(4, 10, 1, 0)
        s.turn("up")            # 排队 [up]
        s.turn("left")          # 排队 [up, left]
        s.turn("down")          # 已排满 2 步，忽略
        self.assertEqual(s.pending, [(0, -1), (-1, 0)])


class TestRoomSetup(unittest.TestCase):
    """开局状态。"""

    def setUp(self):
        self.room = Room("1234")
        self.room.reset()

    def test_reset_positions(self):
        self.assertEqual(self.room.a.body[0], (4, 10))
        self.assertEqual(self.room.a.dir, (1, 0))
        self.assertEqual(self.room.b.body[0], (COLS - 5, ROWS - 11))
        self.assertEqual(self.room.b.dir, (-1, 0))

    def test_reset_flags(self):
        self.assertEqual(self.room.tick, 0)
        self.assertFalse(self.room.over)
        self.assertIsNone(self.room.winner())

    def test_food_count_and_placement(self):
        self.assertEqual(len(self.room.food), FOOD_COUNT)
        taken = set(self.room.a.body) | set(self.room.b.body)
        for f in self.room.food:
            self.assertNotIn(f, taken)
            self.assertTrue(0 <= f[0] < COLS)
            self.assertTrue(0 <= f[1] < ROWS)
        self.assertEqual(len(set(self.room.food)), len(self.room.food))

    def test_spawn_food_fills_up(self):
        # 边界：食物被清空后重新撒，应补满到 FOOD_COUNT 个
        self.room.food = []
        self.room.spawn_food()
        self.assertEqual(len(self.room.food), FOOD_COUNT)


class TestRoomStep(unittest.TestCase):
    """每一拍的推进。"""

    def setUp(self):
        self.room = Room("1234")
        self.room.reset()
        self.room.food = []          # 去掉随机食物，让测试确定

    def test_no_move_on_quiet_tick(self):
        # tick=1 时 A(每2拍)和 B(每3拍)都不动
        self.assertFalse(self.room.step())
        self.assertEqual(self.room.tick, 1)

    def test_a_moves_on_even_tick_only(self):
        self.room.tick = 1           # 下一步 tick=2
        a_before = list(self.room.a.body)
        b_before = list(self.room.b.body)
        self.assertTrue(self.room.step())
        self.assertNotEqual(self.room.a.body, a_before)
        self.assertEqual(self.room.b.body, b_before)
        self.assertEqual(self.room.a.body[0], (5, 10))

    def test_b_moves_on_third_tick_only(self):
        self.room.tick = 2           # 下一步 tick=3
        a_before = list(self.room.a.body)
        b_before = list(self.room.b.body)
        self.assertTrue(self.room.step())
        self.assertEqual(self.room.a.body, a_before)
        self.assertNotEqual(self.room.b.body, b_before)

    def test_pending_direction_is_consumed(self):
        self.room.a.pending = [(0, -1)]     # 玩家按了上
        self.room.tick = 1                  # 下一步 A 动
        self.room.step()
        self.assertEqual(self.room.a.dir, (0, -1))
        self.assertEqual(self.room.a.pending, [])

    def test_step_when_over_does_nothing(self):
        self.room.over = True
        self.assertFalse(self.room.step())

    def test_body_length_constant_when_not_eating(self):
        self.room.tick = 1
        self.room.step()
        self.assertEqual(len(self.room.a.body), 3)


class TestCollisions(unittest.TestCase):
    """撞墙、撞自己、撞对方、同归于尽。"""

    def setUp(self):
        self.room = Room("1234")
        self.room.reset()
        self.room.food = []

    def test_wall_collision_kills_and_ends_game(self):
        self.room.a.body = [(COLS - 1, 5), (COLS - 2, 5), (COLS - 3, 5)]
        self.room.a.dir = (1, 0)             # 再走一步出界
        self.room.tick = A_EVERY - 1
        self.room.step()
        self.assertFalse(self.room.a.alive)
        self.assertTrue(self.room.over)
        self.assertEqual(self.room.winner(), "b")

    def test_self_collision_kills(self):
        # 下一步头 = (5,6)，正好撞在身体中段（不是尾巴，尾巴会让位）
        self.room.a.body = [(5, 5), (6, 5), (5, 6), (4, 6)]
        self.room.a.dir = (0, 1)
        self.room.tick = A_EVERY - 1
        self.room.step()
        self.assertFalse(self.room.a.alive)

    def test_moving_into_own_tail_is_allowed(self):
        # 尾巴这一格下一步会让位，所以撞尾巴不算死
        self.room.a.body = [(5, 5), (5, 6), (6, 6), (6, 5)]
        self.room.a.dir = (1, 0)             # 下一步 (6,5) 正好是尾巴
        self.room.tick = A_EVERY - 1
        self.room.step()
        self.assertTrue(self.room.a.alive)
        self.assertEqual(self.room.a.body[0], (6, 5))

    def test_head_on_collision_is_a_draw(self):
        self.room.a.body = [(10, 10), (9, 10), (8, 10)]
        self.room.a.dir = (1, 0)             # 下一步 (11,10)
        self.room.b.body = [(12, 10), (13, 10), (14, 10)]
        self.room.b.dir = (-1, 0)            # 下一步 (11,10)
        self.room.tick = A_EVERY * B_EVERY - 1     # 让两条蛇同时动
        self.room.step()
        self.assertFalse(self.room.a.alive)
        self.assertFalse(self.room.b.alive)
        self.assertTrue(self.room.over)
        self.assertEqual(self.room.winner(), "draw")

    def test_dead_snake_stops_moving(self):
        self.room.a.alive = False
        self.room.tick = A_EVERY - 1         # A 本该动的这一拍
        self.assertFalse(self.room.step())   # 死了就不动，也没有别的事件


class TestEating(unittest.TestCase):
    """吃食物加分、变长。"""

    def setUp(self):
        self.room = Room("1234")
        self.room.reset()

    def test_eat_increases_score_and_length(self):
        self.room.food = [(5, 10)]           # 正好放在 A 的下一步
        self.room.tick = A_EVERY - 1
        self.room.step()
        self.assertEqual(self.room.a.score, 1)
        self.assertEqual(len(self.room.a.body), 4)
        self.assertEqual(self.room.a.body[0], (5, 10))

    def test_eaten_food_is_refilled(self):
        self.room.food = [(5, 10)]
        self.room.tick = A_EVERY - 1
        self.room.step()
        # 吃掉一个后应立刻补满成 FOOD_COUNT 个
        self.assertEqual(len(self.room.food), FOOD_COUNT)
        self.assertNotIn((5, 10), self.room.food)


class TestWinnerAndSnapshot(unittest.TestCase):

    def setUp(self):
        self.room = Room("1234")
        self.room.reset()

    def test_winner_none_when_both_alive(self):
        self.assertIsNone(self.room.winner())

    def test_winner_a_when_b_dead(self):
        self.room.b.alive = False
        self.assertEqual(self.room.winner(), "a")

    def test_winner_b_when_a_dead(self):
        self.room.a.alive = False
        self.assertEqual(self.room.winner(), "b")

    def test_winner_draw_when_both_dead(self):
        self.room.a.alive = False
        self.room.b.alive = False
        self.assertEqual(self.room.winner(), "draw")

    def test_snapshot_shape(self):
        snap = self.room.snapshot()
        self.assertEqual(snap["type"], "state")
        self.assertEqual(set(snap["a"].keys()), {"body", "score", "alive"})
        self.assertEqual(set(snap["b"].keys()), {"body", "score", "alive"})
        self.assertIsNone(snap["winner"])
        self.assertFalse(snap["over"])


class TestModuleHelpers(unittest.TestCase):

    def test_dirs_mapping(self):
        self.assertEqual(DIRS["up"], (0, -1))
        self.assertEqual(DIRS["down"], (0, 1))
        self.assertEqual(DIRS["left"], (-1, 0))
        self.assertEqual(DIRS["right"], (1, 0))

    def test_new_code_format(self):
        code = new_code()
        self.assertEqual(len(code), 4)
        self.assertTrue(code.isdigit())
        self.assertNotIn(code, ROOMS)

    def test_new_code_avoids_used(self):
        # 边界：已占用的号码不应再被返回
        ROOMS["0000"] = object()
        try:
            self.assertNotEqual(new_code(), "0000")
        finally:
            ROOMS.pop("0000", None)


if __name__ == "__main__":
    unittest.main()
