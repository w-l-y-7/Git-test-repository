"""FastAPI 入口：把 RAG 服务包成 HTTP 接口，浏览器就能通过网址来调用"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .auth_router import router as auth_router
from .conversations_router import router as conversations_router
from .conversations_router import save_turn
from .documents_router import router as documents_router
from .database import get_db, init_db
from .db_models import User
from .models import AskRequest, AskResponse, SourceItem
from .rag import ask
from .security import get_current_user

# 用 uvicorn 的日志器，错误会打到服务器控制台，方便排查问题
logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时自动建表、建管理员账号"""
    init_db()
    yield


# 创建应用实例，title 会显示在自动生成的接口文档里
app = FastAPI(title="金融知识库问答系统", lifespan=lifespan)

# 允许浏览器跨域访问（前端是另一个端口跑，需要这个才能互相通信）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段先全放开，上线前再收紧成具体网址
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册认证接口（/api/auth/...）、会话接口（/api/conversations/...）
# 和文档管理接口（/api/documents/...，仅管理员）
app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(documents_router)


@app.get("/api/health")
def health():
    """健康检查：浏览器先调这个，确认服务活着"""
    return {"status": "ok", "message": "服务运行中"}


@app.post("/api/ask", response_model=AskResponse)
def ask_question(
    req: AskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """问答接口：登录后使用；问答会存进会话里，下次登录还能找回来

    不带 conversation_id 时自动新建一个会话，返回的 conversation_id 就是新会话。
    """
    try:
        answer, sources = ask(req.question)
    except Exception:
        # 完整错误栈写到服务器日志（供排查），对外只返回一句人话
        logger.exception("问答接口处理出错")
        raise HTTPException(status_code=500, detail="服务器处理出错了，请稍后再试")

    conversation_id = save_turn(
        db, current_user.id, req.conversation_id, req.question, answer, sources
    )
    return AskResponse(
        question=req.question,
        answer=answer,
        sources=[SourceItem(content=s) for s in sources],
        conversation_id=conversation_id,
    )
