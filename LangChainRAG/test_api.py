"""后端接口冒烟测试：确认服务活着 + 问答接口能返回答案和引用

问答现在需要登录（第 4 步起），所以先拿管理员账号登录换 token。

运行前需要先启动服务器：.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000
再另开一个终端运行本脚本：.venv\\Scripts\\python.exe test_api.py
"""

import requests

BASE = "http://127.0.0.1:8000"
ADMIN_USER = "wly"
ADMIN_PASSWORD = "123456"


def get_token() -> str:
    """管理员登录，返回 token"""
    r = requests.post(
        f"{BASE}/api/auth/login",
        json={"username": ADMIN_USER, "password": ADMIN_PASSWORD},
    )
    r.raise_for_status()
    return r.json()["token"]


def test_health():
    """健康检查：确认服务活着"""
    r = requests.get(f"{BASE}/api/health")
    if r.status_code != 200:
        print(f"健康检查失败：状态码 {r.status_code}，返回：{r.text[:200]}")
        return
    print("健康检查:", r.status_code, r.json())


def test_ask(question: str):
    """问答：发一个问题，打印答案和引用片段（会自动新建一个会话）"""
    r = requests.post(
        f"{BASE}/api/ask",
        json={"question": question},
        headers={"Authorization": f"Bearer {get_token()}"},
    )
    if r.status_code != 200:
        # 服务器没开、或后端报错时，先停下来提示，而不是直接崩
        print(f"问答请求失败：状态码 {r.status_code}，返回：{r.text[:200]}")
        return
    data = r.json()
    print("\n问题:", question)
    print("回答:", data["answer"])
    print(f"会话 id: {data['conversation_id']}")
    print(f"引用片段数: {len(data['sources'])}")
    for i, s in enumerate(data["sources"]):
        print(f"  片段{i + 1}: {s['content'][:50]}...")


if __name__ == "__main__":
    test_health()
    test_ask("公司有什么风险？")
