"""数据库连接层：负责连接、建表、启动时自动创建管理员

用 SQLAlchemy 统一管数据库，以后换 MySQL 只改 config.py 里的 DB_URL。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DB_URL

# 连接数据库（SQLite 是单个文件，check_same_thread=False 允许 FastAPI 多线程访问）
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

# SessionLocal 是"和数据库对话"的会话工厂，每次请求创建一个
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """所有数据表的公共基类（ORM 模型都继承它）"""
    pass


def get_db():
    """FastAPI 依赖：给每个请求一个数据库会话，用完自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """建所有表；如果管理员不存在就创建一个"""
    from . import db_models  # 先 import，让表注册进 Base

    Base.metadata.create_all(bind=engine)

    from .config import ADMIN_USERNAME, ADMIN_PASSWORD
    from .db_models import User
    from .security import hash_password

    with SessionLocal() as db:
        admin = db.query(User).filter(User.username == ADMIN_USERNAME).first()
        if admin is None:
            db.add(User(
                username=ADMIN_USERNAME,
                password_hash=hash_password(ADMIN_PASSWORD),
                role="admin",
            ))
            db.commit()
            print(f"[init] 已创建内置管理员：{ADMIN_USERNAME}")
        else:
            print(f"[init] 管理员已存在：{ADMIN_USERNAME}")

    # 保证知识库有内容：文档表为空就内置示例研报；向量库缓存被删就自动重建
    from .rag import ensure_kb_ready

    with SessionLocal() as db:
        ensure_kb_ready(db)
