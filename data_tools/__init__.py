"""
ARGUS Data Tools – L1 Data Ingestion Layer
==========================================

Provides financial data retrieval functions and Function Calling schemas
for the ARGUS equity research agent.

Quick start (Agent side)::

    from data_tools.registry import TOOL_DEFINITIONS, TOOL_MAP

Individual function imports::

    from data_tools.stock import get_stock_price, get_stock_info
    from data_tools.news import get_company_news, get_news_sentiment
    from data_tools.financials import get_peer_comparison, get_key_metrics
    from data_tools.filings import download_filing, parse_filing
"""

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .stock import get_stock_price, get_stock_info, get_financial_statements, get_market_overview
from .news import get_company_news, get_earnings_data
from .financials import get_sector_pe, get_peer_comparison, get_analyst_estimates, get_key_metrics
from .filings import download_filing, parse_filing

__all__ = [
    "get_stock_price",
    "get_stock_info",
    "get_financial_statements",
    "get_market_overview",
    "get_company_news",
    "get_earnings_data",
    "get_sector_pe",
    "get_peer_comparison",
    "get_analyst_estimates",
    "get_key_metrics",
    "download_filing",
    "parse_filing",
]
