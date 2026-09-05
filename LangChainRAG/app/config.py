"""全局配置：从 .env 读密钥，集中管理路径和模型名，改配置只动这个文件"""

import os
from dotenv import load_dotenv

# 项目根目录 = LangChainRAG（app 的上一级）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 读取根目录下的 .env（里面有 API key）
load_dotenv(os.path.join(BASE_DIR, ".env"))

# 通义千问 API key（从 .env 读，绝不写死在代码里）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

# JWT 签名密钥：用来给登录 token 签名，泄露 = 别人能伪造登录身份
SECRET_KEY = os.getenv("SECRET_KEY", "开发用临时密钥-上线前必须改")

# 登录 token 有效期（小时）：过期后要重新登录
TOKEN_EXPIRE_HOURS = 24

# 内置管理员账号：只有他之后能进知识库管理页
ADMIN_USERNAME = "wly"
ADMIN_PASSWORD = "123456"

# 模型名：qwen-plus 质量好，够用；嫌贵/嫌慢可换 qwen-turbo
MODEL_NAME = "qwen-plus"

# 向量化模型：阿里云 text-embedding-v3，和通义千问同一个 key
EMBEDDING_MODEL = "text-embedding-v3"

# 离线压测/演示开关：设环境变量 MOCK_DASHSCOPE=1 时，向量化和大模型都用本地假实现，
# 不调阿里云（免费、不占额度、不会限流）。默认关闭，行为跟原来完全一样。
MOCK_DASHSCOPE = os.getenv("MOCK_DASHSCOPE") == "1"

# 文档放 data 文件夹
DATA_DIR = os.path.join(BASE_DIR, "data")

# 向量数据库：Milvus。开发用 Milvus Lite（pymilvus 本地引擎，单文件，免 Docker）
# 以后在 Docker 里起了真 Milvus，只需把下面这行改成服务地址，其余代码不动：
#   MILVUS_URI = "http://localhost:19530"
MILVUS_URI = os.path.join(BASE_DIR, "milvus_lite.db")
MILVUS_COLLECTION = "finance_kb"

# 上传的原始文档存放在 data/uploads，便于追溯和向量库重建
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

# 上传允许的文件类型（限制后缀，防上传乱七八糟的文件）
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}

# ===== 数据库（第 8 步起用 MySQL，一条 docker compose up -d 就能起）=====
# 连接参数默认值和 docker-compose.yml 的开发账号一致，平时不用改；
# 正式部署把这些写进 .env 覆盖即可。
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "rag")
DB_PASSWORD = os.getenv("DB_PASSWORD", "rag_dev_pass")
DB_NAME = os.getenv("DB_NAME", "langchainrag")

# 想临时回到 SQLite（比如这台机器不想开 MySQL）：在 .env 里加一行
#   DB_URL=sqlite:///C:/你电脑上的路径/LangChainRAG/langchain_rag.db
# SQLAlchemy 屏蔽了不同数据库的差异，换库不用改业务代码。
DB_URL = os.getenv(
    "DB_URL",
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4",
)

# 问答时每次喂给大模型的最终片段数
TOP_K = 3

# 检索增强：先按语义粗筛更多候选，再精排取 TOP_K 个（见 app/reranker.py）
RETRIEVAL_CANDIDATES = 15
