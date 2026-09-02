"""知识库文档接口：只有管理员能用 —— 查看已入库文档、上传新文档、删除文档

对应需求：知识库管理页面只对管理员开放。
"""

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .database import get_db
from .db_models import Document, User
from .models import DocumentOut, MessageOut
from .rag import add_document, remove_document
from .security import require_admin

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/documents", tags=["知识库管理"])

# 单次上传大小上限：10MB（防止有人传超大文件把向量化接口拖死）
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _doc_out(d: Document) -> DocumentOut:
    """数据库里的文档 → 对外返回结构"""
    return DocumentOut(
        id=d.id,
        title=d.title,
        filename=d.filename,
        chunk_count=d.chunk_count,
        created_by=d.created_by,
        created_at=d.created_at,
    )


@router.get("", response_model=list[DocumentOut])
def list_documents(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """已入库的文档列表（新的在前）"""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [_doc_out(d) for d in docs]


@router.post("/upload", response_model=DocumentOut)
def upload_document(
    title: str = Form(""),
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """上传文档：自动切块向量化入库，全库即可被问答引用

    支持 txt / md / pdf。文件名或表单里的 title 会成为列表里的标题。
    """
    data = file.file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件超过 10MB，请压缩后再传")

    try:
        doc = add_document(
            db,
            title=title,
            original_filename=file.filename or "未命名.txt",
            data=data,
            creator=admin.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("文档入库失败")
        raise HTTPException(status_code=500, detail="文档入库失败，请查看服务器日志")

    return _doc_out(doc)


@router.delete("/{doc_id}", response_model=MessageOut)
def delete_document(
    doc_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """删除文档：向量库片段 + 原件 + 记录一并清掉"""
    if not remove_document(db, doc_id):
        raise HTTPException(status_code=404, detail="文档不存在")
    return MessageOut(message="文档已删除")
