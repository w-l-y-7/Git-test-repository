"""
第 1 步：跑通最简单的 RAG（检索增强生成）

流程：读文档 → 切块 → 转成向量存库 → 检索 → 通义千问带资料回答

RAG 全称 Retrieval-Augmented Generation（检索增强生成）：
大模型本身不"知道"你的文档，所以先把文档切成小块存起来，
用户提问时先把最相关的小块"检索"出来，连同问题一起交给大模型，
让大模型"看着资料"回答，并标出引用来源。
"""

import os
from dotenv import load_dotenv

# 读取 .env 文件里的 API key（DASHSCOPE_API_KEY）
load_dotenv()

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models.tongyi import ChatTongyi

# ---------- 第 1 步：读文档 ----------
# 把 data 文件夹里的研报读进来
loader = TextLoader("data/研报示例.md", encoding="utf-8")
doc = loader.load()
print(f"① 文档读取完成，共 {len(doc[0].page_content)} 个字符")

# ---------- 第 2 步：把文档切成小块 ----------
# chunk_size=200：每块约 200 个字；chunk_overlap=50：相邻块重叠 50 个字，
# 避免一句话刚好被从中间切开，导致语义丢失
splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50)
chunks = splitter.split_documents(doc)
print(f"② 文档被切成 {len(chunks)} 块")

# ---------- 第 3 步：把每块文字转成"向量"存进向量库 ----------
# 向量 = 一串数字，代表这段话的"语义坐标"。
# 语义相近的话，向量距离就近。这就是后面能"按意思找"的基础。
embeddings = DashScopeEmbeddings(model="text-embedding-v3")
vectorstore = Chroma.from_documents(chunks, embeddings)
print(f"③ 已把 {len(chunks)} 块文字向量化并存入向量库")

# ---------- 第 4 步：检索 ----------
# 把用户的问题也转成向量，去库里找语义最接近的 3 块
question = "华辰智造 2026 年预计营收是多少？"
retrieved = vectorstore.similarity_search(question, k=3)
print("\n④ 检索到与问题最相关的片段：")
for i, d in enumerate(retrieved):
    print(f"   --- 片段 {i + 1} ---")
    print(f"   {d.page_content}")

# ---------- 第 5 步：通义千问带着资料回答 ----------
# 把检索到的片段拼成上下文，和问题一起发给大模型，
# 并明确要求"只根据资料回答、没有就直说"，防止它瞎编（幻觉）
llm = ChatTongyi(model="qwen-plus")
context = "\n\n".join(d.page_content for d in retrieved)
prompt = f"""你是一个金融知识库问答助手。
请只根据下面提供的【资料】回答问题。资料里没有的内容，明确说"资料中未提及"，不要编造。

【资料】
{context}

【问题】{question}

【回答】"""

answer = llm.invoke(prompt)
print("\n⑤ 通义千问的回答：")
print(answer.content)
