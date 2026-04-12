from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional

import pdfplumber
from edgar import Company, set_identity

from .schemas import DocumentChunk, FilingMetadata, TableData

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "filings"

set_identity("ARGUS Research argus@research.ai")


# =========================
# Download
# =========================
def download_filing(
    ticker: str,
    form: str = "10-K",
    save_dir: Optional[str] = None,
) -> dict:

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


# =========================
# Section Headings
# =========================
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


def _match_section(text: str) -> str | None:
    for heading in _SECTION_HEADINGS:
        if re.search(rf"\b{re.escape(heading)}\b", text, re.IGNORECASE):
            return heading
    return None


# =========================
# Table Extraction
# =========================
def _extract_tables_from_page(page: pdfplumber.page.Page) -> list[TableData]:
    tables: list[TableData] = []
    for raw_table in page.extract_tables():
        if not raw_table or len(raw_table) < 2:
            continue

        headers = [str(c).strip() if c else "" for c in raw_table[0]]
        rows = [[str(c).strip() if c else "" for c in row] for row in raw_table[1:]]

        tables.append(TableData(name="", headers=headers, rows=rows))

    return tables


# =========================
# Main Parse
# =========================
def parse_filing(
    file_path: str,
    metadata: dict,
    chunk_size: int = 600,
    chunk_overlap: int = 100,
) -> list[dict]:

    filing_meta = FilingMetadata(**metadata)
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        return _parse_pdf(file_path, filing_meta, chunk_size, chunk_overlap)
    else:
        return _parse_text_file(file_path, filing_meta, chunk_size, chunk_overlap)


# =========================
# PDF Parser
# =========================
def _parse_pdf(file_path, meta, chunk_size, chunk_overlap):

    chunks = []

    with pdfplumber.open(file_path) as pdf:
        full_text_parts = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            tables = _extract_tables_from_page(page)
            full_text_parts.append((text, page.page_number, tables))

    current_section = "General"
    buffer = ""
    buffer_pages = []
    buffer_tables = []

    for text, page_num, tables in full_text_parts:

        matched = _match_section(text)
        if matched:
            current_section = matched

        buffer += ("\n" if buffer else "") + text

        if page_num not in buffer_pages:
            buffer_pages.append(page_num)

        buffer_tables.extend(tables)

        while len(buffer) >= chunk_size:

            chunk_text = buffer[:chunk_size]
            chunk_text = f"[Section: {current_section}]\n{chunk_text}"

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
        chunk_text = f"[Section: {current_section}]\n{buffer}"

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

    return chunks


# =========================
# TEXT Parser
# =========================
def _parse_text_file(file_path, meta, chunk_size, chunk_overlap):

    raw = Path(file_path).read_text(errors="ignore")

    clean = re.sub(r"<[^>]+>", " ", raw)
    clean = re.sub(r"\s+", " ", clean).strip()

    section_positions = [(0, "General")]

    for heading in _SECTION_HEADINGS:
        pattern = re.compile(rf"\b{re.escape(heading)}\b", re.IGNORECASE)
        for m in pattern.finditer(clean):
            section_positions.append((m.start(), heading))

    section_positions.sort(key=lambda x: x[0])

    def _section_at(pos):
        current = "General"
        for sp, name in section_positions:
            if sp > pos:
                break
            current = name
        return current

    chunks = []
    pos = 0

    while pos < len(clean):

        section = _section_at(pos)

        chunk_text = clean[pos : pos + chunk_size]
        chunk_text = f"[Section: {section}]\n{chunk_text}"

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


def _make_chunk_id(ticker, form, section, idx):
    raw = f"{ticker}_{form}_{section}_{idx}"
    short_hash = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"{ticker}_{form}_{section.replace(' ', '')}_{idx:04d}_{short_hash}"