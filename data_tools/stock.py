"""
Stock price, valuation, and financial statement data powered by yfinance.
"""

from __future__ import annotations

from datetime import datetime

import yfinance as yf


def get_stock_price(ticker: str, period: str = "6mo") -> dict:
    """Return historical OHLCV prices and overall change for *ticker*.

    Parameters
    ----------
    ticker : str
        Stock symbol, e.g. ``"AAPL"`` or ``"0700.HK"``.
    period : str
        ``"1mo"`` | ``"3mo"`` | ``"6mo"`` | ``"1y"`` | ``"2y"``
    """
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)

    if hist.empty:
        return {"ticker": ticker, "period": period, "prices": [], "latest_close": None, "change_pct": None}

    prices = []
    for idx, row in hist.iterrows():
        prices.append({
            "date": idx.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        })

    latest_close = float(hist["Close"].iloc[-1])
    first_close = float(hist["Close"].iloc[0])
    change_pct = round(((latest_close / first_close) - 1) * 100, 2) if first_close else 0.0

    return {
        "ticker": ticker,
        "period": period,
        "prices": prices,
        "latest_close": round(latest_close, 2),
        "change_pct": change_pct,
    }


def get_stock_info(ticker: str) -> dict:
    """Return company profile and key valuation metrics.

    Includes P/E, P/B, market cap, beta, 52-week range, dividend yield, etc.
    """
    stock = yf.Ticker(ticker)
    info = stock.info or {}

    return {
        "ticker": ticker,
        "company_name": info.get("longName", info.get("shortName", "")),
        "sector": info.get("sector", ""),
        "industry": info.get("industry", ""),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "pb_ratio": info.get("priceToBook"),
        "dividend_yield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "summary": info.get("longBusinessSummary", ""),
    }


def get_financial_statements(ticker: str, statement_type: str = "income") -> dict:
    """Return annual and quarterly financial statements.

    Parameters
    ----------
    ticker : str
    statement_type : str
        ``"income"`` | ``"balance"`` | ``"cashflow"``
    """
    stock = yf.Ticker(ticker)

    if statement_type == "income":
        annual_df = stock.financials
        quarterly_df = stock.quarterly_financials
    elif statement_type == "balance":
        annual_df = stock.balance_sheet
        quarterly_df = stock.quarterly_balance_sheet
    elif statement_type == "cashflow":
        annual_df = stock.cashflow
        quarterly_df = stock.quarterly_cashflow
    else:
        return {"ticker": ticker, "statement_type": statement_type, "error": f"Unknown type: {statement_type}"}

    def _df_to_records(df) -> list[dict]:
        if df is None or df.empty:
            return []
        records = []
        for col in df.columns:
            entry = {"date": col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)}
            for row_label in df.index:
                val = df.loc[row_label, col]
                entry[str(row_label)] = None if (val != val) else float(val)  # NaN check
            records.append(entry)
        return records

    return {
        "ticker": ticker,
        "statement_type": statement_type,
        "currency": "USD",
        "annual": _df_to_records(annual_df),
        "quarterly": _df_to_records(quarterly_df),
    }


def get_market_overview() -> dict:
    """Return current performance of major market indices."""

    indices = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Dow Jones": "^DJI",
        "Hang Seng": "^HSI",
        "Nikkei 225": "^N225",
        "Russell 2000": "^RUT",
    }

    results = []
    for name, symbol in indices.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="5d")
            if hist.empty:
                continue
            latest = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else latest
            change = round(((latest / prev) - 1) * 100, 2) if prev else 0.0
            results.append({
                "name": name,
                "symbol": symbol,
                "latest_close": round(latest, 2),
                "daily_change_pct": change,
            })
        except Exception:
            continue

    return {
        "indices": results,
        "as_of": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
