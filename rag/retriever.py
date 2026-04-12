from __future__ import annotations

from typing import Any

from .citation import to_agent_payload
from .config import RagConfig
from .index_store import RagIndexStore
from .embeddings import embed_query
from .reranker import Reranker


# =========================
# Intent Detection（增强版）
# =========================
def detect_intent(query: str):
    q = query.lower()

    # 更全面的意图关键词
    intent_keywords = {
        "risk": ["risk", "uncertainty", "exposure", "threat", "hazard", "challenge"],
        "legal": ["legal", "lawsuit", "litigation", "compliance", "regulation", "liability"],
        "business": ["business", "operation", "model", "strategy", "market", "competition"],
        "financial": ["financial", "revenue", "income", "balance", "profit", "loss", "earnings"],
        "product": ["product", "service", "offering", "innovation", "technology"],
        "management": ["management", "leadership", "board", "executive", "governance"]
    }

    for intent, keywords in intent_keywords.items():
        if any(k in q for k in keywords):
            return intent

    return None


# =========================
# Query Rewrite（增强版）
# =========================
def rewrite_query(query: str, intent: str | None):
    if not intent:
        return query

    # 更具体的查询前缀
    prefix_map = {
        "risk": "Risk Factors and Potential Challenges:",
        "legal": "Legal Proceedings and Compliance Issues:",
        "business": "Business Operations and Market Strategy:",
        "financial": "Financial Performance and Results:",
        "product": "Products and Services Offered:",
        "management": "Management and Corporate Governance:"
    }

    return f"{prefix_map.get(intent, '')} {query}"


# =========================
# Query Expansion（新增）
# =========================
def expand_query(query: str):
    # 简单的查询扩展，增加相关术语
    expansions = {
        "revenue": ["sales", "income", "turnover"],
        "profit": ["earnings", "income", "gain"],
        "risk": ["uncertainty", "exposure", "threat"],
        "legal": ["lawsuit", "litigation", "compliance"],
        "business": ["operation", "company", "firm"]
    }

    expanded_terms = [query]
    for term, related in expansions.items():
        if term in query.lower():
            expanded_terms.extend(related)

    return " ".join(expanded_terms)


# =========================
# Utils
# =========================
def _minmax_norm(items: list[tuple[int, float]]) -> dict[int, float]:
    if not items:
        return {}

    vals = [s for _, s in items]
    lo, hi = min(vals), max(vals)

    if hi <= lo:
        return {i: 0.0 for i, _ in items}

    return {i: (s - lo) / (hi - lo) for i, s in items}


# =========================
# Retriever
# =========================
class HybridRetriever:
    def __init__(self, index_store: RagIndexStore, config: RagConfig | None = None) -> None:
        self.index = index_store
        self.config = config or RagConfig()
        self.reranker = Reranker()

    def _filter_doc(self, doc: dict[str, Any], filters: dict[str, Any] | None) -> bool:
        if not filters:
            return True

        meta = doc.get("metadata", {})

        if filters.get("ticker") and meta.get("ticker") != filters["ticker"]:
            return False

        if filters.get("filing_types") and meta.get("filing_type") not in filters["filing_types"]:
            return False

        return True

    # =========================
    # Core Hybrid Search（优化版）
    # =========================
    def hybrid_search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_n: int | None = None,
    ) -> list[dict[str, Any]]:

        if not self.index.docs:
            return []

        # 增强查询处理
        intent = detect_intent(query)
        expanded_query = expand_query(query)
        rewritten_query = rewrite_query(expanded_query, intent)

        top_n = top_n or self.config.top_n_candidates

        # =========================
        # Dense (FAISS)
        # =========================
        q_dense = embed_query(rewritten_query, model=self.config.embedding_model)

        faiss_scores, faiss_indices = self.index.faiss.search(
            q_dense, top_k=top_n
        )

        dense_scores = []
        for idx, score in zip(faiss_indices, faiss_scores):
            if idx < 0 or idx >= len(self.index.docs):
                continue

            doc = self.index.docs[idx]
            if not self._filter_doc(doc, filters):
                continue

            dense_scores.append((idx, score))

        # =========================
        # Sparse (BM25)
        # =========================
        sparse_scores = []
        for i, doc in enumerate(self.index.docs):
            text = (doc.get("text") or "").lower()

            # 更严格的过滤
            if "table of contents" in text:
                continue
            if len(text) < 150:  # 增加最小长度
                continue
            if not self._filter_doc(doc, filters):
                continue

            # 使用扩展后的查询
            sparse_scores.append((i, self.index.bm25(expanded_query, i)))

        # =========================
        # Normalize
        # =========================
        dense_norm = _minmax_norm(dense_scores)
        sparse_norm = _minmax_norm(sparse_scores)

        all_ids = set(dense_norm) | set(sparse_norm)

        # =========================
        # Final scoring（优化版）
        # =========================
        scored = []
        for i in all_ids:
            doc = self.index.docs[i]
            section = str(doc.get("section_title", "")).lower()
            text_length = len(doc.get("text", ""))

            # 🔥 基础分
            score = (
                self.config.dense_weight * dense_norm.get(i, 0.0)
                + self.config.sparse_weight * sparse_norm.get(i, 0.0)
            )

            # =========================
            # Section Soft Bias（增强）
            # =========================
            if intent:
                if intent in section:
                    score += 0.2   # 更强的加分
                else:
                    score -= 0.02   # 更轻微的惩罚

            # =========================
            # 内容质量加分
            # =========================
            # 长度适中的文档
            if 300 <= text_length <= 1500:
                score += 0.05
            # 包含关键章节
            if any(k in section for k in ["risk", "legal", "discussion", "financial", "business"]):
                score += 0.08
            # 排除低质量内容
            if "see also" in text.lower() or "reference" in text.lower():
                score -= 0.05

            scored.append((i, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        out: list[dict[str, Any]] = []
        for i, s in scored[:top_n]:
            d = dict(self.index.docs[i])
            d["score"] = s
            out.append(d)

        return out

    # =========================
    # Rerank（优化版）
    # =========================
    def rerank(self, query: str, docs: list[dict]) -> list[dict]:
        if not docs:
            return docs

        # 优化重排序，使用原始查询
        return self.reranker.rerank(query, docs)

    # =========================
    # Public API
    # =========================
    def retrieve_context(
        self,
        query: str,
        ticker: str | None = None,
        top_k: int = 5,
        filing_types: list[str] | None = None,
    ) -> dict[str, Any]:

        filters: dict[str, Any] = {}

        if ticker:
            filters["ticker"] = ticker

        if filing_types:
            filters["filing_types"] = filing_types

        # 🔥 召回更多候选
        cands = self.hybrid_search(
            query=query,
            filters=filters,
            top_n=self.config.top_n_candidates
        )

        # 🔥 全量 rerank（不要截断）
        reranked = self.rerank(query, cands)

        return to_agent_payload(
            query=query,
            ticker=ticker,
            docs=reranked[:top_k],
        )