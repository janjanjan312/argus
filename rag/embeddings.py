from __future__ import annotations

import os
from typing import Sequence
from sentence_transformers import SentenceTransformer


_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_texts(texts, *, model=None, batch_size=128):
    m = get_model()
    return m.encode(texts, normalize_embeddings=True).tolist()


def embed_query(text, *, model=None):
    return embed_texts([text])[0]


