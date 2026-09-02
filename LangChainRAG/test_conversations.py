"""会话功能自测脚本：自动建会话 / 追问同一会话 / 历史找回 / 权限隔离 / 删除

先启动服务器：.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000
再运行本脚本：.venv\\Scripts\\python.exe test_conversations.py
（会真实调用通义千问回答问题，需要 .env 里的 key，会等几秒）
"""

import sys
import time

import requests

BASE = "http://127.0.0.1:8000"
failures = []


def check(name: str, ok: bool, extra: str = ""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name} {extra}")
    if not ok:
        failures.append(name)


def register_and_login(tag: str) -> tuple[str, str]:
    """注册一个随机新用户并登录，返回 (用户名, token)"""
    username = f"convuser_{tag}_{int(time.time())}"
    password = "abc12345"
    requests.post(f"{BASE}/api/auth/register", json={"username": username, "password": password})
    r = requests.post(f"{BASE}/api/auth/login", json={"username": username, "password": password})
    return username, r.json()["token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main():
    _, tok1 = register_and_login("a")
    _, tok2 = register_and_login("b")

    # 1. 提问时不带会话 id → 自动新建会话，并返回会话 id
    r = requests.post(
        f"{BASE}/api/ask",
        json={"question": "公司主要做什么产品？"},
        headers=auth(tok1),
    )
    data = r.json()
    auto_cid = data.get("conversation_id")
    check("不带会话提问自动建会话", r.status_code == 200 and auto_cid is not None,
          f"(会话 id: {auto_cid})")

    # 2. 该会话历史里有"一问一答"两条，回答带引用片段
    r = requests.get(f"{BASE}/api/conversations/{auto_cid}/messages", headers=auth(tok1))
    msgs = r.json()
    roles = [m["role"] for m in msgs]
    check("历史是一问一答两条", r.status_code == 200 and roles == ["user", "assistant"], f"({roles})")
    check("回答带着引用片段", bool(msgs) and len(msgs[-1]["sources"]) > 0)

    # 3. 继续往同一会话提问 → 历史变 4 条
    r = requests.post(
        f"{BASE}/api/ask",
        json={"question": "有什么风险？", "conversation_id": auto_cid},
        headers=auth(tok1),
    )
    check("带会话 id 提问成功", r.status_code == 200 and r.json()["conversation_id"] == auto_cid)
    r = requests.get(f"{BASE}/api/conversations/{auto_cid}/messages", headers=auth(tok1))
    check("历史追加到 4 条", r.status_code == 200 and len(r.json()) == 4)

    # 4. 会话列表能看到这个会话，标题取自第一个问题
    r = requests.get(f"{BASE}/api/conversations", headers=auth(tok1))
    titles = [c["title"] for c in r.json()]
    check("会话列表含新会话且标题=首问", any("产品" in t for t in titles), f"(标题: {titles[:3]})")

    # 5. 手动新建一个空会话
    r = requests.post(f"{BASE}/api/conversations", json={}, headers=auth(tok1))
    empty_cid = r.json().get("id")
    check("手动新建空会话", r.status_code == 200 and r.json()["title"] == "新会话",
          f"(会话 id: {empty_cid})")

    # 6. 权限隔离：user2 看不到、删不掉 user1 的会话
    r1 = requests.get(f"{BASE}/api/conversations/{auto_cid}/messages", headers=auth(tok2))
    r2 = requests.delete(f"{BASE}/api/conversations/{auto_cid}", headers=auth(tok2))
    check("别人的会话查不到", r1.status_code == 404)
    check("别人的会话删不掉", r2.status_code == 404)

    # 7. 不带 token 提问 → 401
    r = requests.post(f"{BASE}/api/ask", json={"question": "你好"})
    check("未登录提问被拦", r.status_code == 401)

    # 8. 删除自己的会话后，历史也跟着没了
    r = requests.delete(f"{BASE}/api/conversations/{auto_cid}", headers=auth(tok1))
    check("删除自己的会话成功", r.status_code == 200)
    r = requests.get(f"{BASE}/api/conversations/{auto_cid}/messages", headers=auth(tok1))
    check("删除后查历史返回不存在", r.status_code == 404)

    # 9. user1 的会话列表里：被删的没了，空会话还在
    r = requests.get(f"{BASE}/api/conversations", headers=auth(tok1))
    ids = [c["id"] for c in r.json()]
    check("列表里删的没了、空会话还在", auto_cid not in ids and empty_cid in ids)

    print("\n" + "=" * 40)
    if failures:
        print(f"共 {len(failures)} 项失败：{failures}")
        sys.exit(1)
    print("全部通过")


if __name__ == "__main__":
    main()
