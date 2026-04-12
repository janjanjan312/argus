from __future__ import annotations

import argparse
import json
from typing import Any, Callable

from .citation import to_agent_payload
from .config import RagConfig
from .index_store import RagIndexStore
from .retriever import HybridRetriever


def retrieve_context(
    query: str,
    ticker: str | None = None,
    top_k: int = 5,
    filing_types: list[str] | None = None,
    auto_ingest: bool = False,
) -> dict[str, Any]:
    """
    RAG检索入口函数

    Args:
        query: 查询问题
        ticker: 股票代码（可选）
        top_k: 返回结果数量
        filing_types: 文件类型列表（可选）
        auto_ingest: 是否自动摄入（可选）

    Returns:
        包含检索结果的字典
    """
    from data_tools.filings import download_filing, parse_filing

    store = RagIndexStore()
    store.load()

    if auto_ingest and ticker:
        form = "10-K"
        if filing_types and "20-F" in filing_types:
            form = "20-F"

        result = download_filing(ticker=ticker, form=form)
        chunks = parse_filing(result["file_path"], result["metadata"])

        store.upsert(chunks)
        store.save()

    retriever = HybridRetriever(store)

    return retriever.retrieve_context(
        query=query,
        ticker=ticker,
        top_k=top_k,
        filing_types=filing_types,
    )


class RagAPI:
    """RAG系统的简洁接口类"""

    def __init__(self):
        self.store = RagIndexStore()
        self.store.load()
        self.retriever = HybridRetriever(self.store)

    def query(
        self,
        question: str,
        ticker: str | None = None,
        top_k: int = 5,
        filing_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        检索与查询相关的文档

        Args:
            question: 查询问题
            ticker: 股票代码（可选）
            top_k: 返回的文档数量
            filing_types: 文件类型列表（可选）

        Returns:
            包含查询结果的字典
        """
        return self.retriever.retrieve_context(
            query=question,
            ticker=ticker,
            top_k=top_k,
            filing_types=filing_types,
        )


rag_api = RagAPI()


def query_rag(
    question: str,
    ticker: str | None = None,
    top_k: int = 5,
    filing_types: list[str] | None = None,
) -> dict[str, Any]:
    """
    便捷函数：直接查询RAG系统

    Args:
        question: 查询问题
        ticker: 股票代码（可选）
        top_k: 返回的文档数量
        filing_types: 文件类型列表（可选）

    Returns:
        包含查询结果的字典
    """
    return rag_api.query(
        question=question,
        ticker=ticker,
        top_k=top_k,
        filing_types=filing_types,
    )


RAG_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_context",
            "description": "从RAG系统（FAISS + BM25 + 重排序）检索证据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "查询问题"},
                    "ticker": {"type": "string", "description": "股票代码"},
                    "top_k": {"type": "integer", "description": "返回结果数量"},
                    "filing_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "文件类型列表，如10-K、20-F等",
                    },
                    "auto_ingest": {
                        "type": "boolean",
                        "description": "是否自动摄入新文档",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


RAG_TOOL_MAP: dict[str, Callable[..., Any]] = {
    "retrieve_context": retrieve_context,
}


def main() -> None:
    """命令行入口"""
    parser = argparse.ArgumentParser(description="查询本地RAG索引")
    parser.add_argument("--query", required=True, help="查询问题")
    parser.add_argument("--ticker", default=None, help="股票代码")
    parser.add_argument("--top-k", type=int, default=5, help="返回结果数量")
    parser.add_argument("--filing-types", nargs="*", default=None, help="文件类型")

    args = parser.parse_args()

    payload = retrieve_context(
        query=args.query,
        ticker=args.ticker,
        top_k=args.top_k,
        filing_types=args.filing_types,
    )

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
