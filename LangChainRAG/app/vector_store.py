"""Milvus 向量库封装：建集合、写入、检索、按文档删除、统计

开发用 Milvus Lite（pymilvus 自带的本地引擎，数据落在 milvus_lite.db 单文件，
不需要 Docker）；以后切真实 Milvus 服务，只改 config.MILVUS_URI 一处即可。

这里不套 langchain 的向量库包装，而是自己定义集合结构：
  doc_id（哪个文档） + text（原文片段） + vector（向量）
并配 HNSW 余弦索引 —— 字段可控、按文档删除方便，也更接近企业部署的写法。
向量化仍走 langchain 的 DashScopeEmbeddings（保持 LangChain 框架要求）。
"""

import logging

from langchain_community.embeddings import DashScopeEmbeddings

from .config import EMBEDDING_MODEL, MILVUS_COLLECTION, MILVUS_URI

logger = logging.getLogger("uvicorn.error")

_client = None
_emb = None
_dim = None


def _embeddings() -> DashScopeEmbeddings:
    """创建一次向量化工具后复用（文字 → 向量）"""
    global _emb
    if _emb is None:
        _emb = DashScopeEmbeddings(model=EMBEDDING_MODEL)
    return _emb


def _dimension() -> int:
    """拿到模型实际输出的向量维度（text-embedding-v3 默认 1024）"""
    global _dim
    if _dim is None:
        _dim = len(_embeddings().embed_query("向量维度探针"))
    return _dim


def _ensure_collection(client) -> None:
    """集合不存在就建一个（带好字段和索引），存在就直接复用"""
    from pymilvus import DataType

    if client.has_collection(MILVUS_COLLECTION):
        return

    schema = client.create_schema(auto_id=True)
    schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
    schema.add_field("doc_id", DataType.INT64)  # 标记这段文字属于哪份文档
    schema.add_field("text", DataType.VARCHAR, max_length=65535)  # 原文片段
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=_dimension())

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="HNSW",  # 近似最近邻索引，速度快、召回好
        metric_type="COSINE",  # 用余弦相似度衡量语义远近
        params={"M": 16, "efConstruction": 200},
    )
    client.create_collection(
        collection_name=MILVUS_COLLECTION,
        schema=schema,
        index_params=index_params,
    )
    print(f"[milvus] 向量集合已创建：{MILVUS_COLLECTION}")


def get_client():
    """全局只建一个客户端连接，多线程请求复用它"""
    global _client
    if _client is None:
        from pymilvus import MilvusClient

        _client = MilvusClient(MILVUS_URI)
        _ensure_collection(_client)
    return _client


def add_texts(doc_id: int, texts: list[str]) -> int:
    """把一份文档的一组片段向量化写入集合，返回写入条数"""
    if not texts:
        return 0
    vectors = _embeddings().embed_documents(texts)
    data = [
        {"doc_id": doc_id, "text": text, "vector": vector}
        for text, vector in zip(texts, vectors)
    ]
    get_client().insert(collection_name=MILVUS_COLLECTION, data=data)
    return len(texts)


def search(question: str, k: int) -> list[str]:
    """把问题向量化，在全集合里找语义最接近的 k 段原文"""
    query_vec = _embeddings().embed_query(question)
    result = get_client().search(
        collection_name=MILVUS_COLLECTION,
        data=[query_vec],
        limit=k,
        output_fields=["text"],
    )
    hits = result[0] if result else []
    return [hit["entity"]["text"] for hit in hits]


def delete_by_doc(doc_id: int) -> None:
    """删除某文档的全部片段（doc_id 精确匹配）"""
    get_client().delete(
        collection_name=MILVUS_COLLECTION,
        filter=f"doc_id == {doc_id}",
    )


def row_count() -> int:
    """集合里现有多少片段；0 说明向量缓存空了，需要重建"""
    client = get_client()
    try:
        result = client.query(
            collection_name=MILVUS_COLLECTION,
            filter="id >= 0",
            output_fields=["count(*)"],
        )
        if result:
            return int(result[0].get("count(*)", 0))
    except Exception:
        pass
    try:
        stats = client.get_collection_stats(MILVUS_COLLECTION)
        return int(stats.get("row_count", 0))
    except Exception:
        return 0
