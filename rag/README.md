# RAG 系统使用指南

## 系统概述

本RAG（Retrieval-Augmented Generation）系统用于从公司 filings 文档中检索相关信息，为问答系统提供上下文支持。系统采用了混合检索策略（FAISS + BM25 + 重排序），并经过优化以提高检索效果。

## 目录结构

```
rag/
├── __init__.py          # 模块导出
├── citation.py          # 引用格式处理
├── config.py            # 配置文件
├── embeddings.py        # 嵌入模型
├── faiss_index.py       # FAISS索引
├── index_store.py       # 索引存储
├── ingest.py            # 文档摄入
├── interface.py         # 统一接口（检索、工具定义、命令行）
├── rag_query_eval.json  # 评估文件
├── reranker.py          # 重排序器
├── retriever.py         # 检索器
└── README.md            # 本使用指南
```

## 安装依赖

```bash
pip install sentence-transformers faiss-cpu
```

## 统一接口文件 interface.py

`interface.py` 是RAG系统的统一接口文件，整合了以下功能：

- `retrieve_context`：检索函数（支持自动摄入）
- `query_rag`：便捷检索函数
- `RagAPI`：RAG接口类
- `RAG_TOOL_DEFINITIONS`：MultiAgent工具定义
- `RAG_TOOL_MAP`：MultiAgent工具映射
- 命令行查询入口

## 使用方法

### 方法一：使用 query_rag（简洁编程接口）

**适用场景**：直接在代码中调用RAG功能。

```python
from rag import query_rag

result = query_rag(
    question="What are the main risk factors for Apple?",
    ticker="AAPL",
    top_k=5
)

print(result)
```

### 方法二：使用 RagAPI 类

```python
from rag import RagAPI

rag = RagAPI()
result = rag.query(
    question="What challenges does management mention for Microsoft?",
    ticker="MSFT",
    top_k=3,
    filing_types=["10-K"]
)

print(result)
```

### 方法三：使用 retrieve_context（适合MultiAgent系统）

**适用场景**：集成到Agent框架中，支持自动摄入功能。

```python
from rag import retrieve_context, RAG_TOOL_DEFINITIONS

# 直接调用
result = retrieve_context(
    query="What are NVIDIA's competitive risks?",
    ticker="NVDA",
    top_k=5,
    auto_ingest=False
)

# 作为工具定义使用
agent_tools = RAG_TOOL_DEFINITIONS
```

### MultiAgent系统集成

```python
from rag import RAG_TOOL_DEFINITIONS, RAG_TOOL_MAP

# 注册RAG工具到Agent系统
def register_rag_tools(agent):
    for tool_def in RAG_TOOL_DEFINITIONS:
        agent.register_tool(
            tool_def["function"]["name"],
            RAG_TOOL_MAP[tool_def["function"]["name"]],
            tool_def
        )
```

### 命令行使用

# 构建索引, 查询问题
```bash
python -m rag.ingest --dir data/filings

python -m rag.interface --query "What legal proceedings involve Apple?"
```

## 返回格式

```python
{
    "query": "查询问题",
    "ticker": "股票代码",
    "results": [
        {
            "chunk_id": "文档块ID",
            "score": 0.95,
            "text": "文档内容...",
            "section_title": "章节标题",
            "citation": {
                "ticker": "股票代码",
                "filing_type": "文件类型",
                "filing_date": "filing日期",
                "accession_no": "访问号",
                "source_url": "源URL",
                "page_numbers": [1, 2]
            }
        }
    ]
}
```

### 检索效果差怎么办？

1. 重新摄入文档：`python -m rag.ingest --dir data/filings/..`
2. 调整查询语句使其更具体
3. 使用ticker参数限制检索范围
4. 检查文档质量
```
