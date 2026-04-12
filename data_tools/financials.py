"""
Industry comparison, analyst estimates, and key financial metrics
powered by yfinance (free, no API key required).
"""

from __future__ import annotations

from datetime import datetime

import yfinance as yf

# Major tech peers used as fallback when yfinance doesn't provide a peer list
_TECH_PEERS = {
    "AAPL": ["MSFT", "GOOGL", "META", "AMZN", "NVDA"],
    "MSFT": ["AAPL", "GOOGL", "META", "AMZN", "ORCL"],
    "GOOGL": ["META", "MSFT", "AMZN", "AAPL", "NFLX"],
    "META": ["GOOGL", "SNAP", "PINS", "MSFT", "NFLX"],
    "AMZN": ["MSFT", "GOOGL", "AAPL", "BABA", "SHOP"],
    "NVDA": ["AMD", "INTC", "AVGO", "QCOM", "TSM"],
    "TSM": ["NVDA", "INTC", "AMD", "AVGO", "QCOM"],
    "AMD": ["NVDA", "INTC", "AVGO", "QCOM", "TSM"],
}


def _get_info(ticker: str) -> dict:
    return yf.Ticker(ticker).info or {}


# ---------------------------------------------------------------------------
# Sector / Industry PE
# ---------------------------------------------------------------------------

def get_sector_pe(sector: str = "Technology") -> dict:
    """Return sector-level average P/E by sampling major companies in that sector.

    Parameters
    ----------
    sector : str
        Sector name, e.g. ``"Technology"``, ``"Healthcare"``.
    """
    sector_samples = {
        "Technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "AVGO", "ORCL", "CRM", "ADBE", "AMD"],
        "Healthcare": ["JNJ", "UNH", "PFE", "ABT", "TMO", "MRK", "LLY", "ABBV"],
        "Financial Services": ["JPM", "BAC", "WFC", "GS", "MS", "BLK", "C", "AXP"],
        "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX"],
        "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "T"],
    }

    tickers = sector_samples.get(sector, sector_samples["Technology"])
    pe_values = []
    details = []

    for sym in tickers:
        try:
            info = _get_info(sym)
            pe = info.get("trailingPE")
            if pe and pe > 0:
                pe_values.append(pe)
                details.append({
                    "ticker": sym,
                    "company_name": info.get("shortName", ""),
                    "pe_ratio": round(pe, 2),
                })
        except Exception:
            continue

    avg_pe = round(sum(pe_values) / len(pe_values), 2) if pe_values else None

    return {
        "sector": sector,
        "average_pe": avg_pe,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "sample_size": len(pe_values),
        "details": details,
    }


# ---------------------------------------------------------------------------
# Peer Comparison
# ---------------------------------------------------------------------------

def get_peer_comparison(ticker: str) -> dict:
    """Return a comparison of *ticker* against its sector peers.

    Uses yfinance data for all companies.
    """
    peer_symbols = _TECH_PEERS.get(ticker.upper(), [])

    if not peer_symbols:
        info = _get_info(ticker)
        sector = info.get("sector", "")
        industry = info.get("industry", "")
        for known_ticker, known_peers in _TECH_PEERS.items():
            if known_ticker != ticker.upper():
                try:
                    ki = _get_info(known_ticker)
                    if ki.get("industry") == industry or ki.get("sector") == sector:
                        peer_symbols = [known_ticker] + known_peers[:4]
                        break
                except Exception:
                    continue
        if not peer_symbols:
            peer_symbols = list(_TECH_PEERS.keys())[:5]

    all_symbols = [ticker.upper()] + [p for p in peer_symbols if p != ticker.upper()]

    peers = []
    for sym in all_symbols:
        try:
            info = _get_info(sym)
            peers.append({
                "ticker": sym,
                "company_name": info.get("longName", info.get("shortName", "")),
                "market_cap": info.get("marketCap"),
                "pe_ratio": round(info["trailingPE"], 2) if info.get("trailingPE") else None,
                "forward_pe": round(info["forwardPE"], 2) if info.get("forwardPE") else None,
                "price": info.get("currentPrice", info.get("regularMarketPrice")),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
            })
        except Exception:
            continue

    company_name = ""
    for p in peers:
        if p["ticker"] == ticker.upper():
            company_name = p["company_name"]
            break

    return {
        "ticker": ticker,
        "company_name": company_name,
        "peers": peers,
    }


# ---------------------------------------------------------------------------
# Analyst Estimates
# ---------------------------------------------------------------------------

def get_analyst_estimates(ticker: str) -> dict:
    """Return analyst consensus price targets and recommendation for *ticker*.

    Uses yfinance's analyst data.
    """
    stock = yf.Ticker(ticker)
    info = stock.info or {}

    target_mean = info.get("targetMeanPrice")
    target_high = info.get("targetHighPrice")
    target_low = info.get("targetLowPrice")
    num_analysts = info.get("numberOfAnalystOpinions", 0)
    recommendation = info.get("recommendationKey", "N/A")

    rec_detail = []
    try:
        recs = stock.recommendations
        if recs is not None and not recs.empty:
            for idx, row in recs.tail(10).iterrows():
                entry = {"date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)}
                for col in recs.columns:
                    entry[str(col)] = int(row[col]) if str(row[col]).isdigit() else str(row[col])
                rec_detail.append(entry)
    except Exception:
        pass

    return {
        "ticker": ticker,
        "target_consensus": target_mean,
        "target_high": target_high,
        "target_low": target_low,
        "recommendation": recommendation,
        "number_of_analysts": num_analysts or 0,
        "details": rec_detail,
    }


# ---------------------------------------------------------------------------
# Key Metrics
# ---------------------------------------------------------------------------

def get_key_metrics(ticker: str) -> dict:
    """Return key financial ratios and metrics from yfinance."""
    stock = yf.Ticker(ticker)
    info = stock.info or {}

    current_metrics = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "pb_ratio": info.get("priceToBook"),
        "ps_ratio": info.get("priceToSalesTrailing12Months"),
        "ev_to_ebitda": info.get("enterpriseToEbitda"),
        "ev_to_revenue": info.get("enterpriseToRevenue"),
        "profit_margins": info.get("profitMargins"),
        "gross_margins": info.get("grossMargins"),
        "operating_margins": info.get("operatingMargins"),
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "debt_to_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "quick_ratio": info.get("quickRatio"),
        "free_cash_flow": info.get("freeCashflow"),
        "operating_cash_flow": info.get("operatingCashflow"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "dividend_yield": info.get("dividendYield"),
        "payout_ratio": info.get("payoutRatio"),
        "beta": info.get("beta"),
    }

    return {
        "ticker": ticker,
        "metrics": [current_metrics],
    }
