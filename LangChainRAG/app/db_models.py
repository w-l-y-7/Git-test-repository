"""数据表定义（ORM 模型）：把数据库表映射成 Python 类"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    """用户表：存账号信息"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))  # bcrypt 加密后的密码
    role: Mapped[str] = mapped_column(String(20), default="user")  # "user" 或 "admin"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Document(Base):
    """知识库文档表：记录每份已入库的文件（谁传的、多少片段）"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))  # 显示用的标题
    filename: Mapped[str] = mapped_column(String(255))  # 原始文件名
    stored_path: Mapped[str] = mapped_column(String(255), default="")  # 存在 uploads 里的相对文件名
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)  # 切成多少片段入库
    created_by: Mapped[str] = mapped_column(String(50))  # 上传人用户名（快照）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Conversation(Base):
    """会话表：一个用户可以有多个会话，彼此独立（就是侧边栏那个会话列表）"""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)  # 属于哪个用户
    title: Mapped[str] = mapped_column(String(100), default="新会话")  # 列表里显示的名字
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Message(Base):
    """消息表：一个会话里的所有问答记录，一问你一答算两条"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # "user" 提问 / "assistant" 回答
    content: Mapped[str] = mapped_column(Text)  # 消息内容（可能很长，用 Text 不限长）
    sources: Mapped[str] = mapped_column(Text, default="[]")  # 回答引用的片段，存成 JSON 字符串
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
