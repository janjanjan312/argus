from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .config import RagConfig
from .embeddings import embed_texts
from .faiss_index import FaissIndex


_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9\-\./]{1,}")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


class RagIndexStore:
    def __init__(self, config: RagConfig | None = None) -> None:
        self.config = config or RagConfig()

        self.docs: list[dict[str, Any]] = []
        self.inverted: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.df: dict[str, int] = {}
        self.avg_doc_len: float = 0.0

        # FAISS
        self.faiss = FaissIndex(dim=384)

    @property
    def _docs_path(self) -> Path:
        return self.config.index_dir / "docs.jsonl"

    # =========================
    # UPSERT（写入索引）
    # =========================
    def upsert(self, chunks: list[dict[str, Any]]) -> None:
        known = {d["chunk_id"] for d in self.docs}

        new_chunks = []
        for c in chunks:
            cid = c.get("chunk_id")
            txt = c.get("text", "")

            if not cid or not txt or cid in known:
                continue

            new_chunks.append(c)

        if not new_chunks:
            return

        # 🔥 embedding（只对新chunk）
        texts = [c.get("text", "") for c in new_chunks]
        embeddings = embed_texts(
            texts,
            model=self.config.embedding_model,
            batch_size=self.config.embed_batch_size,
        )

        # 写入 docs
        for c, emb in zip(new_chunks, embeddings):
            doc = {
                "chunk_id": c.get("chunk_id"),
                "text": c.get("text"),
                "metadata": c.get("metadata", {}),
                "section_title": c.get("section_title", "General"),
                "page_numbers": c.get("page_numbers", []),
                "tokens": tokenize(c.get("text", "")),
                "dense": emb,
            }
            self.docs.append(doc)

        # 🔥 写入 FAISS（顺序必须一致）
        self.faiss.add(embeddings)

        # 重建 BM25 索引
        self._rebuild_sparse()

    # =========================
    # BM25 索引构建
    # =========================
    def _rebuild_sparse(self) -> None:
        self.inverted.clear()
        self.df.clear()
        total_len = 0

        for i, d in enumerate(self.docs):
            toks = d.get("tokens", [])
            total_len += len(toks)

            tf = Counter(toks)

            for term, freq in tf.items():
                self.inverted[term].append((i, freq))

            for term in tf:
                self.df[term] = self.df.get(term, 0) + 1

        self.avg_doc_len = (total_len / len(self.docs)) if self.docs else 0.0

    # =========================
    # SAVE（持久化）
    # =========================
    def save(self) -> None:
        self.config.index_dir.mkdir(parents=True, exist_ok=True)

        # 保存 docs
        with self._docs_path.open("w", encoding="utf-8") as f:
            for d in self.docs:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")

        # 保存 FAISS
        self.faiss.save()

    # =========================
    # LOAD（加载索引）
    # =========================
    def load(self) -> None:
        self.docs = []

        # 加载 FAISS
        self.faiss.load()

        if not self._docs_path.exists():
            self._rebuild_sparse()
            return

        with self._docs_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                self.docs.append(json.loads(line))

        self._rebuild_sparse()

        # 🔥 一致性检查（非常关键）
        if self.faiss.index.ntotal != len(self.docs):
            raise ValueError(
                f"FAISS size ({self.faiss.index.ntotal}) != docs size ({len(self.docs)})"
            )

    # =========================
    # BM25 评分
    # =========================
    def bm25(self, query: str, doc_idx: int, k1: float = 1.2, b: float = 0.75) -> float:
        q_toks = tokenize(query)

        if not q_toks or not self.docs:
            return 0.0

        score = 0.0
        doc = self.docs[doc_idx]
        tf = Counter(doc.get("tokens", []))

        doc_len = len(doc.get("tokens", [])) or 1
        n_docs = len(self.docs)

        for term in q_toks:
            if term not in self.df:
                continue

            idf = math.log(
                1.0 + (n_docs - self.df[term] + 0.5) / (self.df[term] + 0.5)
            )

            f = tf.get(term, 0)

            denom = f + k1 * (1 - b + b * doc_len / (self.avg_doc_len or 1.0))

            if denom > 0:
                score += idf * (f * (k1 + 1.0) / denom)

        return score