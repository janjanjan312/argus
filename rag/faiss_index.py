from __future__ import annotations

import faiss
import numpy as np
from pathlib import Path


class FaissIndex:
    def __init__(self, dim: int = 768, index_path: str = "data/faiss.index"):
        self.dim = dim
        self.index_path = Path(index_path)
        self.index = faiss.IndexFlatIP(dim)

    def load(self):
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))

    def save(self):
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))

    def add(self, vectors: list[list[float]]):
        if not vectors:
            return
        arr = np.array(vectors).astype("float32")

        # normalize（用于 cosine similarity）
        faiss.normalize_L2(arr)

        self.index.add(arr)

    def search(self, query_vec: list[float], top_k: int = 5):
        if self.index.ntotal == 0:
            return [], []

        q = np.array([query_vec]).astype("float32")
        faiss.normalize_L2(q)

        scores, indices = self.index.search(q, top_k)
        return scores[0].tolist(), indices[0].tolist()