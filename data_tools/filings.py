"""
PDF download and parsing for SEC EDGAR filings (10-K, 10-Q, 8-K).

Uses `edgartools` for downloading and `pdfplumber` for table extraction.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Optional

import pdfplumber
from edgar import Company, set_identity

from .schemas import DocumentChunk, FilingMetadata, TableData

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "filings"

set_identity("ARGUS Research argus@research.ai")


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_filing(
    ticker: str,
    form: str = "10-K",
    save_dir: Optional[str] = None,
) -> dict:
    """Download the latest SEC filing for *ticker* and return metadata.

    Parameters
    ----------
    ticker : str
        Stock ticker, e.g. ``"AAPL"``.
    form : str
        Filing type – ``"10-K"``, ``"10-Q"``, or ``"8-K"``.
    save_dir : str, optional
        Directory to save the filing.  Defaults to ``data/filings/``.

    Returns
    -------
    dict with keys: ``file_path``, ``metadata`` (FilingMetadata dict).
    """
    dest = Path(save_dir) if save_dir else DATA_DIR
    dest.mkdir(parents=True, exist_ok=True)

    company = Company(ticker)
    filings = company.get_filings(form=form)
    latest = filings.latest()

    filing_date = str(getattr(latest, "filing_date", ""))
    accession_no = str(getattr(latest, "accession_no", getattr(latest, "accession_number", "")))

    safe_date = filing_date.replace("-", "")
    filename = f"{ticker}_{form}_{safe_date}.html"
    file_path = dest / filename

    latest.save(str(file_path))

    metadata = FilingMetadata(
        company=getattr(company, "name", ticker),
        ticker=ticker,
        filing_type=form,
        filing_date=filing_date,
        document_title=f"{ticker} {form} filed {filing_date}",
        accession_no=accession_no,
        source_url=str(getattr(latest, "document_url", getattr(latest, "url", ""))),
        source="SEC_EDGAR",
    )

    return {
        "file_path": str(file_path),
        "metadata": metadata.model_dump(),
    }


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------

_SECTION_HEADINGS = [
    "Business",
    "Risk Factors",
    "Properties",
    "Legal Proceedings",
    "Management's Discussion and Analysis",
    "Financial Statements",
    "Quantitative and Qualitative Disclosures",
    "Controls and Procedures",
    "Market Risk",
]


def _extract_tables_from_page(page: pdfplumber.page.Page) -> list[TableData]:
    """Extract tables from a single pdfplumber page."""
    tables: list[TableData] = []
    for raw_table in page.extract_tables():
        if not raw_table or len(raw_table) < 2:
            continue
        headers = [str(c).strip() if c else "" for c in raw_table[0]]
        rows = [
            [str(c).strip() if c else "" for c in row]
            for row in raw_table[1:]
        ]
        tables.append(TableData(name="", headers=headers, rows=rows))
    return tables


def parse_filing(
    file_path: str,
    metadata: dict,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[dict]:
    """Parse a PDF filing into chunks with metadata.

    Parameters
    ----------
    file_path : str
        Path to the downloaded PDF file.
    metadata : dict
        FilingMetadata dict (from ``download_filing``).
    chunk_size : int
        Target chunk size in characters.
    chunk_overlap : int
        Overlap between consecutive chunks in characters.

    Returns
    -------
    list of DocumentChunk dicts.
    """
    filing_meta = FilingMetadata(**metadata)
    chunks: list[dict] = []

    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        chunks = _parse_pdf(file_path, filing_meta, chunk_size, chunk_overlap)
    else:
        chunks = _parse_text_file(file_path, filing_meta, chunk_size, chunk_overlap)

    return chunks


def _parse_pdf(
    file_path: str,
    meta: FilingMetadata,
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict]:
    chunks: list[dict] = []
    with pdfplumber.open(file_path) as pdf:
        full_text_parts: list[tuple[str, int, list[TableData]]] = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            tables = _extract_tables_from_page(page)
            full_text_parts.append((text, page.page_number, tables))

    current_section = "General"
    buffer = ""
    buffer_pages: list[int] = []
    buffer_tables: list[TableData] = []

    for text, page_num, tables in full_text_parts:
        for heading in _SECTION_HEADINGS:
            if heading.lower() in text.lower():
                current_section = heading
                break

        buffer += ("\n" if buffer else "") + text
        if page_num not in buffer_pages:
            buffer_pages.append(page_num)
        buffer_tables.extend(tables)

        while len(buffer) >= chunk_size:
            chunk_text = buffer[:chunk_size]
            buffer = buffer[chunk_size - chunk_overlap:]

            chunk_id = _make_chunk_id(meta.ticker, meta.filing_type, current_section, len(chunks))
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    metadata=meta,
                    section_title=current_section,
                    page_numbers=list(buffer_pages),
                    tables=buffer_tables,
                ).model_dump()
            )
            buffer_pages = [buffer_pages[-1]] if buffer_pages else []
            buffer_tables = []

    if buffer.strip():
        chunk_id = _make_chunk_id(meta.ticker, meta.filing_type, current_section, len(chunks))
        chunks.append(
            DocumentChunk(
                chunk_id=chunk_id,
                text=buffer,
                metadata=meta,
                section_title=current_section,
                page_numbers=list(buffer_pages),
                tables=buffer_tables,
            ).model_dump()
        )

    return chunks


def _parse_text_file(
    file_path: str,
    meta: FilingMetadata,
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict]:
    """Fallback parser for HTML / plain-text filings."""
    raw = Path(file_path).read_text(errors="ignore")
    clean = re.sub(r"<[^>]+>", " ", raw)
    clean = re.sub(r"\s+", " ", clean).strip()

    section_positions: list[tuple[int, str]] = [(0, "General")]
    for heading in _SECTION_HEADINGS:
        pattern = re.compile(re.escape(heading), re.IGNORECASE)
        for m in pattern.finditer(clean):
            section_positions.append((m.start(), heading))
    section_positions.sort(key=lambda x: x[0])

    def _section_at(pos: int) -> str:
        current = "General"
        for sp, name in section_positions:
            if sp > pos:
                break
            current = name
        return current

    chunks: list[dict] = []
    pos = 0
    while pos < len(clean):
        chunk_text = clean[pos : pos + chunk_size]
        section = _section_at(pos)
        chunk_id = _make_chunk_id(meta.ticker, meta.filing_type, section, len(chunks))
        chunks.append(
            DocumentChunk(
                chunk_id=chunk_id,
                text=chunk_text,
                metadata=meta,
                section_title=section,
                page_numbers=[],
                tables=[],
            ).model_dump()
        )
        pos += chunk_size - chunk_overlap

    return chunks


# ---------------------------------------------------------------------------
# Convenience: extract risk factors section
# ---------------------------------------------------------------------------

def get_risk_factors(ticker: str) -> dict:
    """Download the latest 10-K and return only the Risk Factors chunks.

    Returns
    -------
    dict with ``ticker``, ``filing_date``, ``chunks`` (list of chunk dicts).
    """
    result = download_filing(ticker, form="10-K")
    all_chunks = parse_filing(result["file_path"], result["metadata"])
    risk_chunks = [c for c in all_chunks if "risk" in c.get("section_title", "").lower()]
    return {
        "ticker": ticker,
        "filing_date": result["metadata"]["filing_date"],
        "source_url": result["metadata"]["source_url"],
        "num_chunks": len(risk_chunks),
        "chunks": risk_chunks,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk_id(ticker: str, form: str, section: str, idx: int) -> str:
    raw = f"{ticker}_{form}_{section}_{idx}"
    short_hash = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"{ticker}_{form}_{section.replace(' ', '')}_{idx:04d}_{short_hash}"
