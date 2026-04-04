# ARGUS Data Layer – Interface Contract

This document defines the data contracts between the Data Layer (L1) and the RAG Layer (L2) / Agent Layer (L3).

| Layer | Owner | Responsibility |
|-------|-------|----------------|
| L1 Data Ingestion | Shiliang | PDF 获取与解析、股价/新闻/财务 API 封装 |
| L2 RAG | Ruoxuan | 向量化、检索、知识库管理 |
| L3 Agent | Chuanrui | Agent 编排框架、Fact-check、最终输出 |

---

## 1. For Ruoxuan (L2 RAG): PDF Chunk Format

The data layer produces parsed document chunks via `parse_filing()`. Each chunk is a JSON dict with the following structure:

```json
{
    "chunk_id": "AAPL_10-K_RiskFactors_0003_a1b2c3d4",
    "text": "The Company is subject to laws and regulations worldwide...",
    "metadata": {
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "filing_type": "10-K",
        "filing_date": "2024-11-01",
        "document_title": "AAPL 10-K filed 2024-11-01",
        "accession_no": "0000320193-24-000123",
        "source_url": "https://www.sec.gov/Archives/edgar/data/...",
        "source": "SEC_EDGAR"
    },
    "section_title": "Risk Factors",
    "page_numbers": [45, 46],
    "tables": []
}
```

### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `company` | str | Full company name |
| `ticker` | str | Stock ticker symbol |
| `filing_type` | str | `10-K`, `10-Q`, `8-K`, etc. |
| `filing_date` | str | Filing date (`YYYY-MM-DD`) |
| `document_title` | str | Human-readable document title |
| `accession_no` | str | SEC accession number – unique filing ID, verifiable on EDGAR |
| `source_url` | str | Direct URL to the original filing on SEC.gov |
| `source` | str | `SEC_EDGAR` or `HKEX` |

### Chunking Defaults

- **Chunk size**: ~800 characters (configurable via `chunk_size` parameter)
- **Overlap**: ~120 characters (configurable via `chunk_overlap` parameter)
- All metadata fields are preserved on every chunk for independent citation

### Usage

```python
from data_tools.filings import download_filing, parse_filing

result = download_filing("AAPL", form="10-K")
chunks = parse_filing(result["file_path"], result["metadata"])
# chunks is a list of dicts ready for embedding
```

---

## 2. For Chuanrui (L3 Agent): Function Calling Integration

### Quick Integration

```python
from data_tools.registry import TOOL_DEFINITIONS, TOOL_MAP
import json

# Step 1: Pass TOOL_DEFINITIONS to the LLM
response = openai.chat.completions.create(
    model="gpt-4",
    messages=messages,
    tools=TOOL_DEFINITIONS,
)

# Step 2: Execute the tool calls
for tool_call in response.choices[0].message.tool_calls or []:
    func = TOOL_MAP[tool_call.function.name]
    result = func(**json.loads(tool_call.function.arguments))
    # Append result back to messages as tool response
```

### Available Tools (12 total)

| Tool | Source | Description |
|------|--------|-------------|
| `get_stock_price` | yfinance | Historical OHLCV prices and % change |
| `get_stock_info` | yfinance | Company profile, P/E, market cap, beta |
| `get_financial_statements` | yfinance | Income / balance / cashflow statements |
| `get_market_overview` | yfinance | Major index snapshot (S&P, NASDAQ, HSI) |
| `get_company_news` | Finnhub | Recent company news articles |
| `get_earnings_data` | Finnhub | EPS actual vs. estimate, surprises |
| `get_sector_pe` | yfinance | Sector-level average P/E ratio |
| `get_peer_comparison` | yfinance | Company vs. peer metrics comparison |
| `get_analyst_estimates` | yfinance | Analyst price targets and ratings |
| `get_key_metrics` | yfinance | ROE, margins, leverage ratios over time |
| `download_filing` | SEC EDGAR | Download latest SEC filing |
| `get_risk_factors` | SEC EDGAR | Extract risk factors from 10-K |

### Return Format

All tools return a JSON-serializable `dict`. Pydantic models in `data_tools/schemas.py` document the exact structure of each return value.

### Required Environment Variables

```bash
export FINNHUB_API_KEY="your_key"    # https://finnhub.io/register (free)
# yfinance and SEC EDGAR require no API keys
```

已配置在项目根目录 `.env` 文件中，`data_tools` 包 import 时自动加载。

### API Rate Limits & Usage Constraints

| Source | Rate Limit | Notes |
|--------|-----------|-------|
| **yfinance** | ~2,000 req/hr (undocumented) | 非官方库，避免短时间大量并发请求，建议间隔 0.5s |
| **Finnhub** (free tier) | 60 req/min | `company_news` / `earnings` 正常可用，Demo 演示够用 |
| **SEC EDGAR** | 10 req/sec | 官方要求设置 User-Agent 且不超过 10 req/s |

---

## 3. Query → Tool Mapping

| User Query Category | Recommended Tools |
|---------------------|-------------------|
| Company financial performance | `get_financial_statements`, `get_key_metrics` |
| Stock valuation & market performance | `get_stock_price`, `get_stock_info`, `get_sector_pe` |
| Macro & industry trends | `get_market_overview`, `get_sector_pe` |
| News & market events | `get_company_news`, `get_earnings_data` |
| Risk & compliance | `get_risk_factors`, `download_filing` |
