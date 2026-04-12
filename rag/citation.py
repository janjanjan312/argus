from __future__ import annotations

from typing import Any


def to_agent_payload(query: str, ticker: str | None, docs: list[dict[str, Any]]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for d in docs:
        meta = d.get("metadata", {})
        results.append(
            {
                "chunk_id": d.get("chunk_id"),
                "score": round(float(d.get("score", 0.0)), 4),
                "text": d.get("text", ""),
                "section_title": d.get("section_title", ""),
                "citation": {
                    "ticker": meta.get("ticker", ""),
                    "filing_type": meta.get("filing_type", ""),
                    "filing_date": meta.get("filing_date", ""),
                    "accession_no": meta.get("accession_no", ""),
                    "source_url": meta.get("source_url", ""),
                    "page_numbers": d.get("page_numbers", []),
                },
            }
        )
    return {"query": query, "ticker": ticker, "results": results}

