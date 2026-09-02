"""会话接口：会话列表、新建、查历史、删除；问答的记录也由这里统一写入

对应需求：多用户多会话（每个人有自己独立的会话）+ 历史可找回。
所有接口都要登录，且只能碰自己名下的会话。
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .db_models import Conversation, Message, User
from .models import (
    ChatMessageOut,
    ConversationCreateRequest,
    ConversationOut,
    MessageOut,
)
from .security import get_current_user

router = APIRouter(prefix="/api/conversations", tags=["会话"])


def _now() -> datetime:
    """取当前 UTC 时间（数据库统一存 UTC，前端显示时再转本地）"""
    return datetime.now(timezone.utc)


def _conv_out(c: Conversation) -> ConversationOut:
    """数据库里的会话 → 对外返回结构"""
    return ConversationOut(
        id=c.id, title=c.title, created_at=c.created_at, updated_at=c.updated_at
    )


def _msg_out(m: Message) -> ChatMessageOut:
    """数据库里的消息 → 对外结构（sources 从 JSON 字符串还原成列表）"""
    try:
        sources = json.loads(m.sources) if m.sources else []
    except json.JSONDecodeError:
        sources = []
    return ChatMessageOut(
        id=m.id, role=m.role, content=m.content, sources=sources, created_at=m.created_at
    )


def _get_own_conversation(db: Session, conversation_id: int, user_id: int) -> Conversation:
    """按 id 找会话，同时确认它是当前用户的（别人的会话一律当不存在）"""
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conv


def save_turn(
    db: Session,
    user_id: int,
    conversation_id: int | None,
    question: str,
    answer: str,
    sources: list[str],
) -> int:
    """问答结束后调用：把"提问"和"回答"各存一条到会话里，返回会话 id

    conversation_id 为空就自动新建一个会话（拿第一个问题当标题），
    这样前端"不建会话直接提问"也能自动归到某个会话下面。
    """
    if conversation_id is None:
        conv = Conversation(user_id=user_id, title=question.strip()[:30] or "新会话")
        db.add(conv)
        db.flush()  # 先落库拿到新会话的 id
    else:
        conv = _get_own_conversation(db, conversation_id, user_id)
        if conv.title == "新会话":
            # 空会话第一次提问：用问题把标题改好，列表里更好认
            conv.title = question.strip()[:30] or "新会话"

    db.add(Message(conversation_id=conv.id, role="user", content=question, sources="[]"))
    db.add(
        Message(
            conversation_id=conv.id,
            role="assistant",
            content=answer,
            sources=json.dumps(sources, ensure_ascii=False),
        )
    )
    conv.updated_at = _now()
    db.commit()
    return conv.id


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的会话列表：按最近活动排序，新的在前"""
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [_conv_out(c) for c in convs]


@router.post("", response_model=ConversationOut)
def create_conversation(
    req: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """手动新建一个空会话（也可以不建，直接提问会自动建）"""
    conv = Conversation(user_id=current_user.id, title=(req.title or "").strip() or "新会话")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _conv_out(conv)


@router.get("/{conversation_id}/messages", response_model=list[ChatMessageOut])
def list_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """某个会话的全部聊天记录：一问你一答两条，按先后顺序返回"""
    _get_own_conversation(db, conversation_id, current_user.id)
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.asc())
        .all()
    )
    return [_msg_out(m) for m in msgs]


@router.delete("/{conversation_id}", response_model=MessageOut)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除一个会话（连它的聊天记录一起删）"""
    conv = _get_own_conversation(db, conversation_id, current_user.id)
    db.query(Message).filter(Message.conversation_id == conv.id).delete()
    db.delete(conv)
    db.commit()
    return MessageOut(message="会话已删除")
