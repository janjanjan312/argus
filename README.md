# ARGUS – AI-Powered Equity Research Agent

**Team**: ARGUS Team (CUHK)
**Course**: FTEC5660 Group Project
**Members**: Ruoxuan Xu · Shiliang Chen · Chuanrui Huo
**Target Coverage**: AI / Technology sector

---

## 1. Project Overview

ARGUS is an agentic AI system that automates institutional-grade equity research, focused on covering AI and technology sector companies. It ingests unstructured financial data (SEC filings, earnings reports) and real-time market data (stock prices, news), then uses RAG and LLM-based agents to generate analyst-quality insights with verifiable citations. The tool assists equity research analysts by eliminating data-gathering friction and enabling faster, citation-backed analysis for tech stocks.

### Architecture

| Layer | Description |
|-------|-------------|
| L1 Data Ingestion | PDF acquisition & parsing, stock/news/financial API wrappers exposed as Function Calling Tools |
| L2 Knowledge Retrieval | Vectorization, RAG retrieval, knowledge base management |
| L3 Agent Orchestration | Multi-agent orchestration framework, fact-checking, final output generation |

---

## 2. Target Use Cases

| Use Case | Sample Query | Tools |
|----------|-------------|-------|
| Company Financial Performance | "What is the latest revenue, gross profit, and cash flow of NVDA?" | `get_financial_statements`, `get_key_metrics`, `get_peer_comparison` + RAG (MD&A) |
| Stock Valuation & Market Performance | "What is the P/E ratio of MSFT compared to its sector?" | `get_stock_price`, `get_stock_info`, `get_sector_pe`, `get_analyst_estimates` |
| Macro Economy & Industry Trends | "How is the overall market performing?" | `get_market_overview`, `get_sector_pe` |
| News & Market Event Analysis | "What recent news have impacted META's stock price?" | `get_company_news`, `get_earnings_data`, `get_stock_price` |
| Risk & Compliance Analysis | "What are the regulatory risks affecting GOOGL per its latest filings?" | `get_risk_factors`, `download_filing` + RAG (Legal Proceedings) |

---

## 3. Data Layer Implementation

### 3.1 Tool Reference

All 12 data tools are registered in `data_tools/registry.py`, providing OpenAI Function Calling JSON Schemas (`TOOL_DEFINITIONS`) and a function dispatch map (`TOOL_MAP`). The LLM autonomously selects which tools to call based on the user's query.

| # | Tool | Source | Parameters | Description |
|---|------|--------|-----------|-------------|
| 1 | `get_stock_price` | yfinance | ticker, period | Historical OHLCV prices and % change |
| 2 | `get_stock_info` | yfinance | ticker | Company profile, P/E, market cap, beta |
| 3 | `get_financial_statements` | yfinance | ticker, statement_type | Income statement / balance sheet / cash flow |
| 4 | `get_market_overview` | yfinance | (none) | Major index snapshot (S&P 500, NASDAQ, HSI) |
| 5 | `get_company_news` | Finnhub | ticker, from_date, to_date | Recent company news articles |
| 6 | `get_earnings_data` | Finnhub | ticker | Quarterly EPS actual vs. estimate + surprise |
| 7 | `get_sector_pe` | yfinance | sector | Sector-level average P/E (sampled from top companies) |
| 8 | `get_peer_comparison` | yfinance | ticker | Key metrics comparison with industry peers |
| 9 | `get_analyst_estimates` | yfinance | ticker | Analyst price targets + Buy/Hold/Sell consensus |
| 10 | `get_key_metrics` | yfinance | ticker | ROE, margins, leverage, EV/EBITDA over time |
| 11 | `download_filing` | SEC EDGAR | ticker, form | Download latest SEC filing (10-K / 20-F / 8-K) |
| 12 | `get_risk_factors` | SEC EDGAR | ticker | Extract Risk Factors section from 10-K |

### 3.2 PDF Pipeline

SEC filings are downloaded via `edgartools` and parsed with `pdfplumber` into document chunks with full citation metadata (company, filing type, date, section title, page numbers, accession number, source URL) for RAG ingestion.

### 3.3 Initial Company Coverage

The following companies have been pre-loaded into the knowledge base as the initial seed corpus. The system is not limited to these companies — it dynamically fetches filings, stock data, and news for any publicly listed company at query time via API tools.

| Category | Company | Ticker | Pre-downloaded Filing | Date |
|----------|---------|--------|-----------------------|------|
| AI Infrastructure | NVIDIA | NVDA | `NVDA_10-K_20260225.html` | 2026-02 |
| AI Infrastructure | TSMC | TSM | `TSM_20-F_20250417.html` | 2025-04 |
| US Tech Giants | Microsoft | MSFT | `MSFT_10-K_20250730.html` | 2025-07 |
| US Tech Giants | Alphabet/Google | GOOGL | `GOOGL_10-K_20260205.html` | 2026-02 |
| US Tech Giants | Meta | META | `META_10-K_20260129.html` | 2026-01 |
| US Tech Giants | Apple | AAPL | `AAPL_10-K_20251031.html` | 2025-10 |
| China Tech | Tencent | 0700.HK | `Tencent_2025FY_HKEXAnnouncement.pdf` + `Tencent_2025FY_EarningsPresentation.pdf` | 2026-03 |
| China Tech | Alibaba | BABA | `BABA_20-F_20250626.html` | 2025-06 |
| China Tech | Baidu | BIDU | `BIDU_20-F_20260317.html` | 2026-03 |
| AI Software | Palantir | PLTR | `PLTR_10-K_20260217.html` | 2026-02 |

---

## 4. Data Presentation

Project presentation materials and demo videos are stored in `data_presentation/`.

- `ARGUS_data.pptx`: presentation deck
- `1.mov`, `2.mov`, `3.mov`: original presentation/demo recordings
- `1.mp4`, `2.mp4`, `3.mp4`: compressed versions for easier preview and sharing
