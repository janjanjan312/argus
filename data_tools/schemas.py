"""Pydantic models defining the data structures for all data_tools outputs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# PDF / Filing related schemas
# ---------------------------------------------------------------------------

class FilingMetadata(BaseModel):
    """Metadata extracted at download-time from SEC EDGAR or HKEX."""

    company: str
    ticker: str
    filing_type: str = Field(description="e.g. 10-K, 10-Q, 8-K, Annual Report")
    filing_date: str
    document_title: str = ""
    accession_no: str = Field(default="", description="SEC accession number (US filings only)")
    source_url: str = ""
    source: str = Field(default="SEC_EDGAR", description="SEC_EDGAR | HKEX | IR")


class TableData(BaseModel):
    name: str
    headers: list[str] = []
    rows: list[list[str]] = []


class DocumentChunk(BaseModel):
    """A single chunk ready to be ingested by the RAG pipeline."""

    chunk_id: str
    text: str
    metadata: FilingMetadata
    section_title: str = ""
    page_numbers: list[int] = []
    tables: list[TableData] = []


# ---------------------------------------------------------------------------
# Stock data schemas
# ---------------------------------------------------------------------------

class StockPriceResponse(BaseModel):
    ticker: str
    period: str
    prices: list[dict]
    latest_close: float
    change_pct: float


class StockInfoResponse(BaseModel):
    ticker: str
    company_name: str = ""
    sector: str = ""
    industry: str = ""
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    pb_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    summary: str = ""


class FinancialStatementResponse(BaseModel):
    ticker: str
    statement_type: str = Field(description="income | balance | cashflow")
    currency: str = "USD"
    annual: list[dict] = []
    quarterly: list[dict] = []


class MarketOverviewResponse(BaseModel):
    indices: list[dict]
    as_of: str


# ---------------------------------------------------------------------------
# News / Earnings schemas
# ---------------------------------------------------------------------------

class NewsArticle(BaseModel):
    title: str
    url: str
    source: str = ""
    published_at: str = ""
    summary: str = ""


class CompanyNewsResponse(BaseModel):
    ticker: str
    from_date: str
    to_date: str
    articles: list[NewsArticle]


class EarningsDataResponse(BaseModel):
    ticker: str
    earnings: list[dict] = Field(default=[], description="List of quarterly earnings with actual vs estimate")


# ---------------------------------------------------------------------------
# Financial comparison schemas
# ---------------------------------------------------------------------------

class SectorPEResponse(BaseModel):
    sector: str
    average_pe: Optional[float] = None
    date: str = ""
    details: list[dict] = []


class PeerComparisonResponse(BaseModel):
    ticker: str
    company_name: str = ""
    peers: list[dict] = []


class AnalystEstimatesResponse(BaseModel):
    ticker: str
    target_consensus: Optional[float] = None
    target_high: Optional[float] = None
    target_low: Optional[float] = None
    recommendation: str = ""
    number_of_analysts: int = 0
    details: list[dict] = []


class KeyMetricsResponse(BaseModel):
    ticker: str
    metrics: list[dict] = Field(default=[], description="List of annual/quarterly key metric snapshots")
