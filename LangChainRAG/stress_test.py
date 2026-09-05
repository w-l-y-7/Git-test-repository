"""100 人并发压测脚本：模拟 N 个用户同时走「登录 → 开会话 → 提问 → 拿回答」主链路

压测前请先把后端开成「离线模式」（不调通义千问，省钱不封号）：
    $env:MOCK_DASHSCOPE='1'; .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000

用法：
    .venv/Scripts/python.exe stress_test.py --users 100 --rounds 3     # 100 人各问 3 轮
    .venv/Scripts/python.exe stress_test.py --users 5 --rounds 2       # 先小并发冒烟
    .venv/Scripts/python.exe stress_test.py --cleanup                  # 清掉历史压测账号，重新建号

脚本只做两类请求：POST /api/auth/register、/api/auth/login（准备账号），
POST /api/ask（正式压测）。结束后打印报告，另存一份 CSV 供毕设画图。
"""

import argparse
import csv
import os
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

BASE = "http://127.0.0.1:8000"

# 压测账号统一前缀：脚本只认 stress_ 开头的账号，方便一键清理
USER_PREFIX = "stress_"
PASSWORD = "stress123"  # 压测号专用弱密码，≥6 位即可

# 问题池：从内置研报的角度出几个问题，轮流发，避免所有人问同一句
QUESTIONS = [
    "公司有什么风险？",
    "公司的主营业务是什么？",
    "公司的财务状况怎么样？",
    "行业竞争格局如何？",
    "公司未来有什么发展计划？",
    "公司的客户主要有哪些？",
    "公司毛利率是多少？",
    "公司应收账款情况如何？",
]

REQUEST_TIMEOUT = 30  # 每个问题最长等 30 秒（离线模式一般 1 秒内就回）

# 数据库文件路径（清理压测账号用），脚本就放在项目根目录
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "langchain_rag.db")


def clean_old_accounts():
    """删掉所有 stress_ 开头的压测账号（连它们的会话、消息一起），好重复压测"""
    if not os.path.exists(DB_PATH):
        print("没找到数据库文件，跳过清理")
        return
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        cur = conn.cursor()
        cur.execute(
            """DELETE FROM messages WHERE conversation_id IN
               (SELECT c.id FROM conversations c
                JOIN users u ON c.user_id = u.id
                WHERE u.username LIKE 'stress_%')"""
        )
        cur.execute(
            """DELETE FROM conversations
               WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'stress_%')"""
        )
        cur.execute("DELETE FROM users WHERE username LIKE 'stress_%'")
        conn.commit()
        conn.close()
        print("[清理] 已删除历史压测账号")
    except sqlite3.Error as exc:
        print(f"[清理] 跳过（{exc}），不影响本次压测")


def make_account(index: int) -> str:
    """注册第 index 个假人并登录，返回 token。账号已存在就改成直接登录"""
    username = f"{USER_PREFIX}{index:04d}"
    payload = {"username": username, "password": PASSWORD}

    r = requests.post(f"{BASE}/api/auth/register", json=payload, timeout=REQUEST_TIMEOUT)
    if r.status_code == 400:
        pass  # 用户已存在（上次压测留下的），走下面登录
    else:
        r.raise_for_status()

    r = requests.post(f"{BASE}/api/auth/login", json=payload, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()["token"]


def ensure_offline_mode(token: str) -> bool:
    """问一句看后端是不是离线模式：是则放心压（不花钱），否则提醒先开开关"""
    r = requests.post(
        f"{BASE}/api/ask",
        json={"question": "测试模式探针"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=REQUEST_TIMEOUT,
    )
    if r.status_code == 200 and "离线模式" in r.json().get("answer", ""):
        return True
    return False


def percentiles(sorted_latency_ms: list[float], points: tuple) -> dict[str, float]:
    """从已排序的耗时列表里取各分位数（越大代表越多请求比它慢）"""
    if not sorted_latency_ms:
        return {f"p{p}": 0.0 for p in points}
    out = {}
    n = len(sorted_latency_ms)
    for p in points:
        idx = min(n - 1, int(p / 100 * n))
        out[f"p{p}"] = sorted_latency_ms[idx]
    return out


def run_user(user_index: int, token: str, rounds: int, records: list[dict]) -> None:
    """一个假人的完整行为：开一个会话，连续问 rounds 轮。每轮记一条结果"""
    conversation_id = None  # 第一轮不带会话 id，让后端自动开新会话
    for r in range(1, rounds + 1):
        question = QUESTIONS[(user_index * rounds + r) % len(QUESTIONS)]
        body = {"question": question}
        if conversation_id is not None:
            body["conversation_id"] = conversation_id

        start = time.perf_counter()
        try:
            resp = requests.post(
                f"{BASE}/api/ask",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
                timeout=REQUEST_TIMEOUT,
            )
            ms = (time.perf_counter() - start) * 1000
            if resp.status_code == 200:
                conversation_id = resp.json().get("conversation_id", conversation_id)
                records.append({"user": user_index, "round": r, "ok": True,
                                "status": 200, "ms": ms, "detail": ""})
            else:
                records.append({"user": user_index, "round": r, "ok": False,
                                "status": resp.status_code, "ms": ms,
                                "detail": resp.text[:80]})
        except requests.Timeout:
            ms = (time.perf_counter() - start) * 1000
            records.append({"user": user_index, "round": r, "ok": False,
                            "status": "timeout", "ms": ms, "detail": "请求超时"})
        except requests.RequestException as exc:
            ms = (time.perf_counter() - start) * 1000
            records.append({"user": user_index, "round": r, "ok": False,
                            "status": "conn_err", "ms": ms, "detail": str(exc)[:80]})


def run_load(tokens: list[str], rounds: int) -> list[dict]:
    """让所有假人同时开工：users 个并发 × 每人数轮。返回每轮请求的明细"""
    records: list[dict] = []
    workers = len(tokens)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_user, i, tok, rounds, records)
                   for i, tok in enumerate(tokens)]
        for f in futures:
            f.result()  # 等所有人跑完
    return records


def print_report(records: list[dict], elapsed: float) -> None:
    """把每轮明细汇总成大白话报告"""
    total = len(records)
    ok = [r for r in records if r["ok"]]
    fail = [r for r in records if not r["ok"]]
    ok_ms = sorted(r["ms"] for r in ok)

    print("\n" + "=" * 50)
    print("压测报告")
    print("=" * 50)
    print(f"总请求数：{total}（成功 {len(ok)}，失败 {len(fail)}）")
    if total:
        print(f"成功率：{(len(ok) / total * 100):.1f}%")
        print(f"总耗时：{elapsed:.1f} 秒 | 平均吞吐：{total / elapsed:.1f} 请求/秒")
    if ok_ms:
        p = percentiles(ok_ms, (50, 90, 95, 99))
        avg = sum(ok_ms) / len(ok_ms)
        print(f"\n成功请求的响应时间：")
        print(f"  平均 {avg:.0f} ms | p50 {p['p50']:.0f} ms | "
              f"p90 {p['p90']:.0f} ms | p95 {p['p95']:.0f} ms | "
              f"p99 {p['p99']:.0f} ms | 最慢 {ok_ms[-1]:.0f} ms")
    if fail:
        print(f"\n失败 {len(fail)} 条，按类型统计：")
        from collections import Counter
        for reason, count in Counter(str(r["status"]) for r in fail).most_common():
            label = f"HTTP {reason}" if reason.isdigit() else reason
            print(f"  {label}: {count} 条")
        print("  解读提示：")
        print("  · 全失败时先看后端控制台报错（比如 Milvus 的 GOAWAY/too_many_pings、")
        print("    SQLite 的 database is locked），那才是真正卡住的点；")
        print("  · 全是 timeout 通常是服务端线程卡住/排队太久，而不是数据库本身拒绝。")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="LangChainRAG 并发压测")
    parser.add_argument("--users", type=int, default=100, help="模拟几个人（默认 100）")
    parser.add_argument("--rounds", type=int, default=3, help="每人连续问几轮（默认 3）")
    parser.add_argument("--cleanup", action="store_true",
                        help="跑之前先删掉历史压测账号，重新建号")
    args = parser.parse_args()

    # 0) 服务器在线吗
    try:
        requests.get(f"{BASE}/api/health", timeout=10)
    except requests.RequestException:
        print(f"连不上 {BASE}/api/health。请先启动后端再跑本脚本。")
        sys.exit(1)

    # 0.5) 清理旧压测数据（可选）
    if args.cleanup:
        clean_old_accounts()

    # 1) 准备账号（不计入压测成绩）：建号 + 登录拿 token
    print(f"[准备] 创建 {args.users} 个压测账号并登录…")
    setup_start = time.perf_counter()
    setup_workers = min(20, args.users)
    with ThreadPoolExecutor(max_workers=setup_workers) as pool:
        tokens = list(pool.map(make_account, range(args.users)))
    print(f"[准备] 账号就绪（花 {time.perf_counter() - setup_start:.1f} 秒）")

    # 2) 安全探针：不是离线模式就停下，别花冤枉钱
    if not ensure_offline_mode(tokens[0]):
        print("提醒：后端现在不是「离线模式」，会真实调用通义千问产生费用！")
        print("请先重启后端并设环境变量 MOCK_DASHSCOPE=1 再压测。")
        sys.exit(1)
    print("[确认] 后端处于离线模式，可以放心压测")

    # 3) 正式压测：100 人同时提问
    print(f"[压测] {args.users} 人并发，每人 {args.rounds} 轮，开始…")
    load_start = time.perf_counter()
    records = run_load(tokens, args.rounds)
    elapsed = time.perf_counter() - load_start

    # 4) 报告：控制台 + CSV
    print_report(records, elapsed)
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "langchain_rag_stress_report.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["user", "round", "ok", "status", "ms", "detail"])
        writer.writeheader()
        writer.writerows(records)
    print(f"明细已存：{csv_path}")


if __name__ == "__main__":
    main()
