from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RagConfig:
    index_dir: Path = Path("data") / "rag_index"
    filings_dir: Path = Path("data") / "filings"

    chunk_size: int = 1000
    chunk_overlap: int = 150

    embedding_dim: int = 768
    embedding_model: str = "all-mpnet-base-v2"

    embed_batch_size: int = 128

    dense_weight: float = 0.7
    sparse_weight: float = 0.3

    top_n_candidates: int = 30