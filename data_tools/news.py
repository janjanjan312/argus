"""
Financial news and earnings data powered by Finnhub.

Requires a free API key from https://finnhub.io/register.
Set the environment variable ``FINNHUB_API_KEY`` before use.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import finnhub


def _client() -> finnhub.Client:
    key = os.environ.get("FINNHUB_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "FINNHUB_API_KEY is not set. Get a free key at https://finnhub.io/register"
        )
    return finnhub.Client(api_key=key)


def get_company_news(
    ticker: str,
    from_date: str = "",
    to_date: str = "",
) -> dict:
    """Return recent news articles for *ticker*.

    Parameters
    ----------
    ticker : str
        Stock symbol, e.g. ``"AAPL"``.
    from_date : str
        Start date in ``YYYY-MM-DD`` format.  Defaults to 7 days ago.
    to_date : str
        End date in ``YYYY-MM-DD`` format.  Defaults to today.
    """
    if not to_date:
        to_date = datetime.now().strftime("%Y-%m-%d")
    if not from_date:
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    client = _client()
    raw = client.company_news(ticker, _from=from_date, to=to_date)

    articles = []
    for item in (raw or [])[:30]:
        articles.append({
            "title": item.get("headline", ""),
            "url": item.get("url", ""),
            "source": item.get("source", ""),
            "published_at": datetime.fromtimestamp(item["datetime"]).strftime("%Y-%m-%d %H:%M")
            if item.get("datetime")
            else "",
            "summary": item.get("summary", ""),
        })

    return {
        "ticker": ticker,
        "from_date": from_date,
        "to_date": to_date,
        "articles": articles,
    }


def get_earnings_data(ticker: str) -> dict:
    """Return recent quarterly earnings (actual vs. estimate) for *ticker*.

    Combines earnings calendar and earnings surprises.
    """
    client = _client()

    surprises = client.company_earnings(ticker, limit=8) or []

    earnings = []
    for item in surprises:
        actual = item.get("actual")
        estimate = item.get("estimate")
        surprise = None
        surprise_pct = None
        if actual is not None and estimate is not None and estimate != 0:
            surprise = round(actual - estimate, 4)
            surprise_pct = round((surprise / abs(estimate)) * 100, 2)

        earnings.append({
            "period": item.get("period", ""),
            "actual_eps": actual,
            "estimate_eps": estimate,
            "surprise": surprise,
            "surprise_pct": surprise_pct,
        })

    return {
        "ticker": ticker,
        "earnings": earnings,
    }
