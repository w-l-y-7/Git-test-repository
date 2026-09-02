"""RAG 服务：文档入库、检索、问答。这是系统的核心业务逻辑。

第 7 步起向量库用 Milvus（app/vector_store.py 封装，开发是 Milvus Lite）：
- 每份上传的文档切成片段后写入 Milvus 集合，每个片段带 doc_id 标签
- 删除文档 = 按 doc_id 把它的片段从集合里清掉
- 启动时文档表为空就内置示例研报；向量库空了就按保存的原件自动重建
"""

import os

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_text_splitters import RecursiveCharacterTextSplitter

from . import vector_store
from .config import (
    ALLOWED_EXTENSIONS,
    DATA_DIR,
    MODEL_NAME,
    TOP_K,
    UPLOAD_DIR,
)


# ============ 文本处理 ============

def _split_text(text: str) -> list[str]:
    """把长文本切成有重叠的小片段，保证大模型只看到相关的一小段"""
    splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50)
    return splitter.split_text(text)


def extract_text(data: bytes, ext: str) -> str:
    """把上传文件的字节解析成纯文本（支持 txt / md / pdf）"""
    if ext in (".txt", ".md"):
        # 中文文本常是 UTF-8，偶尔是 GBK；逐个试，兜底用替换符不崩
        for encoding in ("utf-8", "gb18030"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    if ext == ".pdf":
        from io import BytesIO

        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)

    raise ValueError(f"不支持的文件类型：{ext}")


# ============ 文档管理（增 / 删 / 自愈） ============

def add_document(db, *, title: str, original_filename: str, data: bytes, creator: str):
    """把一份文件切块向量化入库，返回数据库里的文档记录

    文件原件保存到 data/uploads 备查；失败时回滚数据库并清理残留文件。
    """
    from .db_models import Document

    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"不支持 {ext} 类型，仅支持 {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    text = extract_text(data, ext)
    if not text.strip():
        raise ValueError("没能从文件里提取出文字。若 PDF 是扫描件/图片，需先转成可复制的文字")

    doc = Document(
        title=(title or "").strip() or os.path.basename(original_filename),
        filename=os.path.basename(original_filename),
        stored_path="",
        chunk_count=0,
        created_by=creator,
    )
    db.add(doc)
    db.flush()  # 先拿 id，用来给文件名和片段打标

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    rel_path = f"{doc.id}_{doc.filename}"
    file_path = os.path.join(UPLOAD_DIR, rel_path)
    with open(file_path, "wb") as f:
        f.write(data)
    doc.stored_path = rel_path

    chunks = _split_text(text)
    try:
        vector_store.add_texts(doc.id, chunks)
    except Exception:
        db.rollback()
        try:
            os.remove(file_path)
        except OSError:
            pass
        raise

    doc.chunk_count = len(chunks)
    db.commit()
    db.refresh(doc)
    return doc


def remove_document(db, doc_id: int) -> bool:
    """按 id 删除文档：清向量库里的片段 + 删原件 + 删数据库记录"""
    from .db_models import Document

    doc = db.get(Document, doc_id)
    if doc is None:
        return False

    try:
        vector_store.delete_by_doc(doc.id)
    except Exception:
        pass  # 向量库可能被重建过，尽力删除即可，不阻塞

    if doc.stored_path:
        try:
            os.remove(os.path.join(UPLOAD_DIR, doc.stored_path))
        except OSError:
            pass

    db.delete(doc)
    db.commit()
    return True


def ensure_kb_ready(db):
    """应用启动时调用，保证知识库一定有内容可问

    1) 文档表为空 → 内置示例研报
    2) 文档表有记录但向量集合是空的（缓存被删过）→ 从保存的原件重建
    """
    from .db_models import Document

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if db.query(Document).count() == 0:
        sample_path = os.path.join(DATA_DIR, "研报示例.md")
        if os.path.exists(sample_path):
            with open(sample_path, "rb") as f:
                add_document(
                    db,
                    title="华辰智造 2026 中期研报（示例）",
                    original_filename="研报示例.md",
                    data=f.read(),
                    creator="system",
                )
            print("[kb] 已内置示例文档：华辰智造 2026 中期研报")

    try:
        if vector_store.row_count() > 0:
            return
        for doc in db.query(Document).all():
            if not doc.stored_path:
                continue
            file_path = os.path.join(UPLOAD_DIR, doc.stored_path)
            if not os.path.exists(file_path):
                continue
            with open(file_path, "rb") as f:
                raw = f.read()
            text = extract_text(raw, os.path.splitext(doc.filename)[1].lower())
            chunks = _split_text(text)
            if chunks:
                vector_store.add_texts(doc.id, chunks)
                doc.chunk_count = len(chunks)
        db.commit()
        print("[kb] 向量库缓存已自动重建")
    except Exception as exc:
        print(f"[kb] 向量库自检跳过（{exc}）")


# ============ 问答 ============

def ask(question: str) -> tuple[str, list[str]]:
    """核心问答流程：检索相关片段 → 通义千问基于资料回答

    返回 (答案文本, 引用的片段列表)
    """
    # 1) 在全知识库（所有文档）里检索与问题语义最接近的 TOP_K 段原文
    sources = vector_store.search(question, TOP_K)
    context = "\n\n".join(sources)

    # 2) 把资料 + 问题拼成提示词，交给大模型
    llm = ChatTongyi(model=MODEL_NAME)
    prompt = f"""你是"金融知识库问答助手"，由阿里云通义千问大模型（模型名 qwen-plus，DashScope 平台）驱动，运行在一个金融知识库问答系统里，回答会引用知识库原文作为依据。

回答规则：
1. 如果用户是在问系统本身（例如"你是什么模型""你是谁""谁开发的""怎么用"），或者只是打招呼闲聊，直接用上面的自我介绍如实回答即可。
2. 其余问题一律只依据下方【资料】回答，不得用知识库之外的猜测填充。资料里确实没有的内容，明确说"资料中未提及"，绝不编造。

【资料】
{context}

【问题】{question}

【回答】"""

    answer = llm.invoke(prompt).content
    return answer, sources
