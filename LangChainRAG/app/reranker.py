"""检索精排：先按语义（余弦）粗筛出候选，再结合关键词 BM25 打分精排

为什么需要这一步：Milvus 只按"意思像不像"捞片段，会漏掉那些关键词完全命中、
但语义向量没对齐的片段。BM25 是经典的"关键词命中"打分器，把它和语义排名融合，
两者互补、命中更稳——这就是企业检索里"混合检索"的思路（这里先做轻量版）。

流程：语义粗筛 N 段 → 每段算两个分加权 → 取总分最高的 TOP_K 段喂给大模型。
"""

import logging

import jieba
from rank_bm25 import BM25Okapi

from .config import TOP_K

# jieba 第一次用要现场建词库，会卡一下还刷日志，干脆启动时就初始化好
jieba.setLogLevel(logging.WARNING)
jieba.initialize()

WEIGHT_BM25 = 0.5  # BM25 关键词命中分 占比
WEIGHT_RANK = 0.5  # 语义排名分 占比


def _tokens(text: str) -> list[str]:
    """中文分词：把一段话切成词（去掉空白），供 BM25 统计用"""
    return [t for t in jieba.cut(text) if t.strip()]


def _norm(values: list[float]) -> list[float]:
    """min-max 归一化到 [0,1]：最大值变 1、最小值变 0；全相等就原样返回"""
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return values
    return [(v - lo) / (hi - lo) for v in values]


def rerank(question: str, candidates: list[str]) -> list[str]:
    """把语义粗筛出的候选精排成 TOP_K 个返回

    candidates 已按语义相似度从高到低排好（来自 Milvus 的返回顺序）。
    问题或片段切不出有效词（如扫描件乱码）时无法打分，就直接用原顺序，不弄巧成拙。
    """
    if len(candidates) <= TOP_K:
        return candidates

    q_tokens = _tokens(question)
    doc_tokens = [_tokens(c) for c in candidates]
    if not q_tokens or not any(doc_tokens):
        return candidates[:TOP_K]

    bm25 = BM25Okapi(doc_tokens)
    bm25_scores = _norm(list(bm25.get_scores(q_tokens)))
    # 语义排名分：排第 1 名最高，越往后越低（1/(排名) 再归一化）
    rank_scores = _norm([1.0 / (i + 1) for i in range(len(candidates))])

    scored = [
        (i, WEIGHT_BM25 * bm25_scores[i] + WEIGHT_RANK * rank_scores[i])
        for i in range(len(candidates))
    ]
    scored.sort(key=lambda t: t[1], reverse=True)
    return [candidates[i] for i, _ in scored[:TOP_K]]
