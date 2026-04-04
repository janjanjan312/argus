"""
Tool registry – the single integration point for the Agent layer.

Exports
-------
TOOL_DEFINITIONS : list[dict]
    OpenAI-compatible Function Calling schemas. Pass directly to the ``tools``
    parameter of ``openai.chat.completions.create()``.

TOOL_MAP : dict[str, Callable]
    Maps each tool name to its Python callable so the Agent can dispatch
    tool-call results.

Usage (Agent side)::

    from data_tools.registry import TOOL_DEFINITIONS, TOOL_MAP
    import json

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=messages,
        tools=TOOL_DEFINITIONS,
    )

    for tool_call in response.choices[0].message.tool_calls:
        func = TOOL_MAP[tool_call.function.name]
        result = func(**json.loads(tool_call.function.arguments))
"""

from __future__ import annotations

from typing import Callable

from .stock import (
    get_stock_price,
    get_stock_info,
    get_financial_statements,
    get_market_overview,
)
from .news import (
    get_company_news,
    get_earnings_data,
)
from .financials import (
    get_sector_pe,
    get_peer_comparison,
    get_analyst_estimates,
    get_key_metrics,
)
from .filings import (
    download_filing,
    parse_filing,
    get_risk_factors,
)

# -------------------------------------------------------------------------
# Function Calling JSON Schema definitions (OpenAI format)
# -------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = [
    # ── Stock / Market ────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": (
                "Retrieve historical OHLCV (Open/High/Low/Close/Volume) price data "
                "and percentage change for a stock over a given time period. "
                "Use this when the user asks about stock price trends, price history, "
                "or how a stock has performed recently."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol, e.g. AAPL, MSFT, 0700.HK",
                    },
                    "period": {
                        "type": "string",
                        "enum": ["1mo", "3mo", "6mo", "1y", "2y"],
                        "description": "Time period for historical prices. Defaults to 6mo.",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_info",
            "description": (
                "Get company profile and key valuation metrics including P/E ratio, "
                "P/B ratio, market cap, beta, 52-week high/low, dividend yield, "
                "sector, and industry. Use this when the user asks about a company's "
                "valuation, fundamentals overview, or basic company information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol, e.g. AAPL, MSFT",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_statements",
            "description": (
                "Retrieve annual and quarterly financial statements (income statement, "
                "balance sheet, or cash flow statement) for a company. Use this when "
                "the user asks about revenue, net income, gross profit, total assets, "
                "liabilities, operating cash flow, or any specific financial line items."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol",
                    },
                    "statement_type": {
                        "type": "string",
                        "enum": ["income", "balance", "cashflow"],
                        "description": "Type of financial statement. Defaults to income.",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_overview",
            "description": (
                "Get a snapshot of major market indices (S&P 500, NASDAQ, Dow Jones, "
                "Hang Seng, etc.) with latest prices and daily changes. Use this when "
                "the user asks about overall market conditions or how the broad market "
                "is performing."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    # ── News / Earnings ────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_company_news",
            "description": (
                "Fetch recent news articles about a specific company. Returns article "
                "titles, sources, summaries, and URLs. Use this when the user asks "
                "about recent news, events, or media coverage of a company."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol, e.g. AAPL",
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD. Defaults to 7 days ago.",
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD. Defaults to today.",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_earnings_data",
            "description": (
                "Retrieve recent quarterly earnings data including actual EPS vs. "
                "analyst estimates, earnings surprises, and surprise percentages. "
                "Use this when the user asks about earnings performance, earnings "
                "beats/misses, or EPS trends."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    # ── Financial Comparison ──────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_sector_pe",
            "description": (
                "Get the average P/E ratio for a market sector (e.g. Technology, "
                "Healthcare). Use this when the user wants to compare a company's "
                "P/E to its sector average or asks about sector-level valuations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sector": {
                        "type": "string",
                        "description": "Sector name, e.g. Technology, Healthcare, Financial Services. Defaults to Technology.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_peer_comparison",
            "description": (
                "Compare a company with its sector peers on key metrics including "
                "market cap, P/E ratio, and price. Use this when the user asks how "
                "a company stacks up against competitors or industry peers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_analyst_estimates",
            "description": (
                "Get analyst consensus price targets (high/low/consensus) and overall "
                "Buy/Hold/Sell recommendation for a stock. Use this when the user "
                "asks about analyst opinions, price targets, or investment ratings."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_key_metrics",
            "description": (
                "Retrieve key financial ratios and metrics over multiple periods, "
                "including ROE, ROA, debt-to-equity, profit margins, EV/EBITDA, "
                "and free cash flow per share. Use this when the user asks about "
                "financial health, profitability ratios, or leverage analysis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    # ── SEC Filings ───────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "download_filing",
            "description": (
                "Download the latest SEC filing (10-K, 10-Q, or 8-K) for a company. "
                "Returns the local file path and filing metadata (date, accession "
                "number, source URL). Use this when the user needs raw filing data "
                "or you need to retrieve a specific SEC document."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol",
                    },
                    "form": {
                        "type": "string",
                        "enum": ["10-K", "10-Q", "8-K"],
                        "description": "Filing type. Defaults to 10-K.",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_factors",
            "description": (
                "Download the latest 10-K filing and extract the Risk Factors "
                "section. Returns parsed text chunks with citation metadata. "
                "Use this when the user asks about regulatory risks, compliance "
                "issues, or potential risk factors from official filings."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
]


# -------------------------------------------------------------------------
# Function name -> callable mapping
# -------------------------------------------------------------------------

TOOL_MAP: dict[str, Callable] = {
    "get_stock_price": get_stock_price,
    "get_stock_info": get_stock_info,
    "get_financial_statements": get_financial_statements,
    "get_market_overview": get_market_overview,
    "get_company_news": get_company_news,
    "get_earnings_data": get_earnings_data,
    "get_sector_pe": get_sector_pe,
    "get_peer_comparison": get_peer_comparison,
    "get_analyst_estimates": get_analyst_estimates,
    "get_key_metrics": get_key_metrics,
    "download_filing": download_filing,
    "get_risk_factors": get_risk_factors,
}
