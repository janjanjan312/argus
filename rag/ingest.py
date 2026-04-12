from __future__ import annotations

import argparse
import json
import shutil
import re
from pathlib import Path
from typing import List

from data_tools.filings import parse_filing
from .config import RagConfig
from .index_store import RagIndexStore


def reset_index(index_dir: Path):
    if index_dir.exists():
        shutil.rmtree(index_dir)
        print(f"[INFO] Index reset: {index_dir}")


def save_debug(chunks: List[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    preview = [
        {
            "chunk_id": c.get("chunk_id"),
            "section": c.get("section_title"),
            "text_preview": (c.get("text") or "")[:300],
        }
        for c in chunks
    ]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(preview, f, ensure_ascii=False, indent=2)

    print(f"[DEBUG] Saved chunks preview -> {path}")


#从文件名提取日期
def extract_date_from_filename(name: str) -> str:
    # 匹配 YYYYMMDD
    m = re.search(r"(20\d{6})", name)
    if m:
        d = m.group(1)
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"

    # fallback：只匹配年份（如 Tencent）
    m2 = re.search(r"(20\d{2})", name)
    if m2:
        return f"{m2.group(1)}-01-01"

    return ""


def ingest_directory(directory: str, chunk_size: int, chunk_overlap: int, rebuild: bool, debug: bool):
    root = Path(directory)

    config = RagConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    store = RagIndexStore(config)

    if rebuild:
        reset_index(Path(store.index_dir))

    store.load()

    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".html", ".htm", ".pdf"}:
            continue

        print(f"\n[INFO] Processing: {path.name}")

        ticker = path.name.split("_")[0].upper()

        name = path.name.lower()
        if "10-k" in name:
            filing_type = "10-K"
        elif "20-f" in name:
            filing_type = "20-F"
        elif "presentation" in name:
            filing_type = "EARNINGS_PRESENTATION"
        elif "announcement" in name:
            filing_type = "ANNOUNCEMENT"
        else:
            filing_type = "OTHER"

        metadata = {
            "company": ticker,
            "ticker": ticker,
            "filing_type": filing_type,
            "filing_date": extract_date_from_filename(path.name),
            "document_title": path.name,
            "accession_no": "",
            "source_url": "",
            "source": "LOCAL_FILE",
        }

        chunks = parse_filing(
            file_path=str(path),
            metadata=metadata,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        before = len(store.docs)
        store.upsert(chunks)
        after = len(store.docs)

        print(f"[INFO] Added {after - before} chunks")

        if debug:
            save_debug(chunks[:50], Path(f"debug/{ticker}_chunks.json"))

    store.save()

    print(f"\n[DONE] Total docs: {len(store.docs)}")


def main():
    parser = argparse.ArgumentParser("RAG Ingest")

    parser.add_argument("--dir", help="directory of filings")
    parser.add_argument("--chunk-size", type=int, default=600)
    parser.add_argument("--chunk-overlap", type=int, default=100)
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    if not args.dir:
        parser.error("--dir required")

    ingest_directory(
        directory=args.dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        rebuild=args.rebuild,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()