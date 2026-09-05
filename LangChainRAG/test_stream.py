# -*- coding: utf-8 -*-
"""第 8 步新增：流式问答接口测试（/api/ask/stream，SSE）

需要：后端已启动且连上 MySQL（见 README 第 5 节），能联网调通义千问。
会真实调用大模型 + 往数据库写两条问答，属预期行为。
直接运行：python test_stream.py
"""
import json

import requests

BASE = "http://127.0.0.1:8000"
ADMIN = {"username": "wly", "password": "123456"}


def login():
    r = requests.post(f"{BASE}/api/auth/login", json=ADMIN)
    r.raise_for_status()
    return r.json()["token"]


def main():
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    question = "华辰智造主要做什么产品？"

    # 1) 先同步问一题拿到会话 id（流式会追加进同一个会话）
    r = requests.post(
        f"{BASE}/api/ask",
        json={"question": question, "conversation_id": None},
        headers=headers,
        timeout=180,
    )
    assert r.status_code == 200, f"同步问答失败: {r.text}"
    conversation_id = r.json()["conversation_id"]

    # 2) 流式提问：应收到若干 delta 帧 + 一个 done 事件
    deltas = 0
    done = None
    with requests.post(
        f"{BASE}/api/ask/stream",
        json={"question": question, "conversation_id": conversation_id},
        headers=headers,
        stream=True,
        timeout=180,
    ) as resp:
        assert resp.status_code == 200, f"流式请求失败: {resp.text}"
        assert resp.headers.get("content-type", "").startswith("text/event-stream"), \
            "响应类型应为 text/event-stream"
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data:"):
                continue
            evt = json.loads(raw[5:].strip())
            if evt["type"] == "delta":
                deltas += 1
            elif evt["type"] == "done":
                done = evt
            elif evt["type"] == "error":
                raise AssertionError(f"流式返回 error: {evt['detail']}")

    assert deltas >= 1, "至少应收到一段生成文字（delta 帧）"
    assert done is not None, "应收到 done 结束事件"
    assert done["conversation_id"] == conversation_id, "done 的会话 id 应对上"
    assert len(done["sources"]) > 0, "回答应带引用片段"

    # 3) 查该会话历史：同步 + 流式两次问答 = 4 条消息
    msgs = requests.get(
        f"{BASE}/api/conversations/{conversation_id}/messages", headers=headers
    ).json()
    user_msgs = [m for m in msgs if m["role"] == "user"]
    ai_msgs = [m for m in msgs if m["role"] == "assistant"]
    assert len(user_msgs) >= 2 and len(ai_msgs) >= 2, (
        f"同步+流式两次问答后应至少 4 条消息，实际 {len(msgs)} 条"
    )

    print(f"test_stream PASS：delta 帧 {deltas}，sources {len(done['sources'])}，会话共 {len(msgs)} 条消息")


if __name__ == "__main__":
    main()
    print("OK")
