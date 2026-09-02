"""知识库管理自测脚本：列表 / 权限 / 上传 / 全局可问 / 删除后不再引用

先启动服务器：.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000
再运行本脚本：.venv\\Scripts\\python.exe test_documents.py
（会真实调用通义千问：上传向量化 + 两次问答，需要 .env 里的 key，会等几秒）
"""

import os
import sys
import time

import requests

BASE = "http://127.0.0.1:8000"
failures = []

# 临时上传文件（跑完删除）
SOURCE_FILE = "_kb_test_source.txt"
SOURCE_CONTENT = """丰云科技公司介绍

丰云科技成立于 2015 年，总部位于深圳，是一家专注于工业质检机器人研发和销售的高新技术企业。公司核心产品为智能视觉质检机器人，采用深度学习算法对生产线上产品的外观缺陷进行自动检测。

2026 年上半年，丰云科技实现营业收入 4.2 亿元，同比增长 45%。其中视觉质检机器人贡献营收的 70%，其余来自软件授权与售后维保服务。公司毛利率约 52%，明显高于同行平均水平。

公司计划在下半年推出新一代在线质检一体化平台，把检测算法、数据看板和产线控制打通，为客户提供端到端的质量数字化解决方案。目前该平台已在三家汽车零部件工厂完成试点。

风险提示：公司主要客户集中在消费电子行业，若下游需求波动可能影响订单稳定性；此外视觉算法人才竞争激烈，存在人才流失与研发投入加大的风险。
"""


def check(name, ok, extra=""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name} {extra}")
    if not ok:
        failures.append(name)


def login(user, pwd):
    r = requests.post(f"{BASE}/api/auth/login", json={"username": user, "password": pwd})
    return r.json()["token"]


def main():
    for _ in range(30):
        try:
            if requests.get(f"{BASE}/api/health", timeout=2).status_code == 200:
                break
        except Exception:
            time.sleep(1)

    admin_tok = login("wly", "123456")
    h_admin = {"Authorization": f"Bearer {admin_tok}"}

    # 1. 启动自检已内置示例文档
    docs = requests.get(f"{BASE}/api/documents", headers=h_admin).json()
    check("启动已自动内置示例研报", len(docs) >= 1, f"(共 {len(docs)} 份)")

    # 2. 权限：普通用户访问知识库接口应被拒（403）
    uname = f"kbuser_{int(time.time())}"
    requests.post(f"{BASE}/api/auth/register", json={"username": uname, "password": "abc12345"})
    tok_u = login(uname, "abc12345")
    h_user = {"Authorization": f"Bearer {tok_u}"}
    r_u_list = requests.get(f"{BASE}/api/documents", headers=h_user)
    r_u_del = requests.delete(f"{BASE}/api/documents/{docs[0]['id']}", headers=h_user)
    check("普通用户列文档被拒(403)", r_u_list.status_code == 403)
    check("普通用户删文档被拒(403)", r_u_del.status_code == 403)

    # 3. 管理员上传新文档
    with open(SOURCE_FILE, "w", encoding="utf-8") as f:
        f.write(SOURCE_CONTENT)
    try:
        with open(SOURCE_FILE, "rb") as f:
            r = requests.post(
                f"{BASE}/api/documents/upload",
                headers=h_admin,
                files={"file": ("丰云科技介绍.txt", f, "text/plain")},
                data={"title": "丰云科技公司介绍（测试）"},
            )
    finally:
        os.remove(SOURCE_FILE)
    doc = r.json()
    check("上传成功且切了片段", r.status_code == 200 and doc["chunk_count"] > 0,
          f"(片段数: {doc.get('chunk_count')})")
    doc_id = doc["id"]

    # 4. 新文档可被问答引用（跨文档检索）
    r = requests.post(f"{BASE}/api/ask", json={"question": "丰云科技主要做什么？"},
                      headers=h_admin, timeout=90)
    ans = r.json()["answer"]
    check("新文档内容能被问答引用", r.status_code == 200 and "丰云" in ans,
          f"(答案片段: {ans[:40]}...)")

    # 5. 列表变成 2 份
    docs = requests.get(f"{BASE}/api/documents", headers=h_admin).json()
    check("列表显示 2 份文档", len(docs) == 2, f"(共 {len(docs)} 份)")

    # 6. 删除后列表回到 1 份，且问答不再引用它（只会如实说"资料中未提及"）
    r = requests.delete(f"{BASE}/api/documents/{doc_id}", headers=h_admin)
    check("删除文档成功", r.status_code == 200)
    docs = requests.get(f"{BASE}/api/documents", headers=h_admin).json()
    check("列表回到 1 份", len(docs) == 1)
    r = requests.post(f"{BASE}/api/ask", json={"question": "丰云科技主要做什么？"},
                      headers=h_admin, timeout=90)
    ans2 = r.json()["answer"]
    check("删除后不再引用已删文档", "未提及" in ans2,
          f"(答案片段: {ans2[:40]}...)")

    print("\n" + "=" * 40)
    if failures:
        print(f"共 {len(failures)} 项失败：{failures}")
        sys.exit(1)
    print("全部通过")


if __name__ == "__main__":
    main()
