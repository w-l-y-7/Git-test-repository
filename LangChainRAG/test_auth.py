"""认证功能自测脚本：注册 / 登录 / 查我 / 改密码 / 错误密码拦截

先启动服务器：.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000
再运行本脚本：.venv\\Scripts\\python.exe test_auth.py
"""

import sys
import time

import requests

BASE = "http://127.0.0.1:8000"
ADMIN_USER = "wly"
ADMIN_PASSWORD = "123456"
TEST_USER = f"testuser_{int(time.time())}"  # 每次跑用不同的名字，避免撞库
TEST_PASSWORD = "abc12345"

failures = []


def check(name: str, ok: bool, extra: str = ""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name} {extra}")
    if not ok:
        failures.append(name)


def main():
    # 1. 管理员登录
    r = requests.post(f"{BASE}/api/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASSWORD})
    data = r.json()
    check("管理员登录 wly/123456", r.status_code == 200 and data["user"]["role"] == "admin",
          f"(返回角色: {data.get('user', {}).get('role')})")
    admin_token = data.get("token", "")

    # 2. 用管理员 token 查 me
    r = requests.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    check("携带 token 查 me 是 wly", r.status_code == 200 and r.json()["username"] == ADMIN_USER)

    # 3. 注册新用户
    r = requests.post(f"{BASE}/api/auth/register", json={"username": TEST_USER, "password": TEST_PASSWORD})
    check("注册新用户", r.status_code == 200 and r.json()["role"] == "user", f"({TEST_USER})")

    # 4. 重复注册同名用户应被拦截
    r = requests.post(f"{BASE}/api/auth/register", json={"username": TEST_USER, "password": TEST_PASSWORD})
    check("重复注册被拦截", r.status_code == 400)

    # 5. 新用户登录，角色应是普通用户
    r = requests.post(f"{BASE}/api/auth/login", json={"username": TEST_USER, "password": TEST_PASSWORD})
    data = r.json()
    check("新用户登录", r.status_code == 200 and data["user"]["role"] == "user",
          f"(返回角色: {data.get('user', {}).get('role')})")
    user_token = data.get("token", "")

    # 6. 不带 token 访问 me 应被拦下（401）
    r = requests.get(f"{BASE}/api/auth/me")
    check("不带 token 被拦下", r.status_code == 401)

    # 7. 改密码：旧密码错误应被拦截
    r = requests.post(f"{BASE}/api/auth/change-password",
                      json={"old_password": "wrong-pw", "new_password": "newpw123"},
                      headers={"Authorization": f"Bearer {user_token}"})
    check("旧密码错误被拦截", r.status_code == 400)

    # 8. 改密码：正确旧密码
    r = requests.post(f"{BASE}/api/auth/change-password",
                      json={"old_password": TEST_PASSWORD, "new_password": "newpw123"},
                      headers={"Authorization": f"Bearer {user_token}"})
    check("正确旧密码改密成功", r.status_code == 200)

    # 9. 用新密码能登录、旧密码不能
    r_new = requests.post(f"{BASE}/api/auth/login", json={"username": TEST_USER, "password": "newpw123"})
    r_old = requests.post(f"{BASE}/api/auth/login", json={"username": TEST_USER, "password": TEST_PASSWORD})
    check("新密码可登录、旧密码失效", r_new.status_code == 200 and r_old.status_code == 401)

    # 10. 密码太短被拦截
    r = requests.post(f"{BASE}/api/auth/register", json={"username": f"{TEST_USER}_short", "password": "123"})
    check("密码过短被拦截", r.status_code == 400)

    print("\n" + "=" * 40)
    if failures:
        print(f"共 {len(failures)} 项失败：{failures}")
        sys.exit(1)
    print("全部通过")


if __name__ == "__main__":
    main()
