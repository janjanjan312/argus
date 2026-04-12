from sentence_transformers import CrossEncoder


class Reranker:
    def __init__(self):
        self.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-12-v2")

    def rerank(self, query: str, docs: list[dict]) -> list[dict]:
        if not docs:
            return docs

        pairs = [(query, d["text"]) for d in docs]
        scores = self.model.predict(pairs)

        for d, s in zip(docs, scores):
            d["score"] = float(s)

        return sorted(docs, key=lambda x: x["score"], reverse=True)