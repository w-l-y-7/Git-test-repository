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

# 数据库：现在用 SQLite（一个文件，零安装）。
# 以后部署换 MySQL，只需把这一行改成
#   DB_URL = "mysql+pymysql://用户名:密码@localhost:3306/langchainrag"
# 其余代码不用动（SQLAlchemy 屏蔽了数据库差异）
DB_URL = f"sqlite:///{os.path.join(BASE_DIR, 'langchain_rag.db')}"

# 问答时每次检索几个相关片段喂给大模型
TOP_K = 3
