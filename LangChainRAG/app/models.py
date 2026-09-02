"""API 的请求/响应数据结构：定义"浏览器传什么进来、系统返回什么出去"的格式"""

from datetime import datetime

from pydantic import BaseModel


class AskRequest(BaseModel):
    """用户提问的请求格式：问题 + 会话 id（不传就自动新建一个会话）"""
    question: str
    conversation_id: int | None = None


class SourceItem(BaseModel):
    """一条引用片段：回答依据的原文内容"""
    content: str


class AskResponse(BaseModel):
    """系统回答的响应格式：问题、答案、引用的片段、这次落在哪个会话"""
    question: str
    answer: str
    sources: list[SourceItem]
    conversation_id: int


# ============ 认证（注册/登录/改密码） ============

class RegisterRequest(BaseModel):
    """注册请求：用户名 + 密码"""
    username: str
    password: str


class LoginRequest(BaseModel):
    """登录请求：用户名 + 密码"""
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    """改密码请求：要验证旧密码，再设新密码"""
    old_password: str
    new_password: str


class UserOut(BaseModel):
    """对外返回的用户信息（绝不含密码）"""
    id: int
    username: str
    role: str


class LoginResponse(BaseModel):
    """登录成功的响应：token + 用户信息"""
    token: str
    user: UserOut


class MessageOut(BaseModel):
    """通用提示信息"""
    message: str


# ============ 会话与历史（第 4 步新增） ============

class ConversationCreateRequest(BaseModel):
    """手动新建会话：标题可选，不填就是"新会话"（会在第一个问题时自动改好）"""
    title: str | None = None


class ConversationOut(BaseModel):
    """一个会话的信息（会话列表的一项）"""
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageOut(BaseModel):
    """会话里的一条消息：前端聊天窗口渲染用，assistant 消息带引用片段"""
    id: int
    role: str
    content: str
    sources: list[str]
    created_at: datetime


# ============ 知识库文档管理（第 6 步新增） ============

class DocumentOut(BaseModel):
    """一份已入库文档的信息（知识库管理列表用）"""
    id: int
    title: str
    filename: str
    chunk_count: int
    created_by: str
    created_at: datetime
