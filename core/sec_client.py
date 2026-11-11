"""Shared SEC EDGAR HTTP client with rate limiting and proper User-Agent."""

from __future__ import annotations

import os
import time
from typing import Any, Optional

import httpx

DEFAULT_UA = "RiskPulse/0.1 (success; 300joh@.com)"

_MIN_INTERVAL = 0.15
_last_request = 0.0

# Fallback map used when www.sec.gov/files/company_tickers.json is blocked (403).
# Covers the most common tickers so the plugin remains useful for demos and everyday use.
_FALLBACK_TICKERS: dict[str, str] = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "GOOG": "0001652044",
    "AMZN": "0001018724",
    "META": "0001326801",
    "TSLA": "0001318605",
    "NVDA": "0001045810",
    "BRK-B": "0001067983",
    "BRK.B": "0001067983",
    "JPM": "0000019617",
    "V": "0001403161",
    "JNJ": "0000200406",
    "WMT": "0000104169",
    "PG": "0000080424",
    "MA": "0001141391",
    "UNH": "0000731766",
    "HD": "0000354950",
    "XOM": "0000034088",
    "CVX": "0000093410",
    "LLY": "0000059478",
    "ABBV": "0001551152",
    "AVGO": "0001730168",
    "COST": "0000909832",
    "PEP": "0000077476",
    "KO": "0000021344",
    "MRK": "0000310158",
    "TMO": "0000097745",
    "NFLX": "0001065280",
    "AMD": "0000002488",
    "INTC": "0000050863",
    "CRM": "0001108524",
    "ORCL": "0001341439",
    "ADBE": "0000796343",
    "CSCO": "0000858877",
    "ACN": "0001467373",
    "MCD": "0000063908",
    "DIS": "0001744489",
    "CMCSA": "0001166691",
    "NKE": "0000320187",
    "TXN": "0000097476",
    "QCOM": "0000804328",
    "IBM": "0000051143",
    "AMAT": "0000006951",
    "INTU": "0000896878",
    "AMGN": "0000318154",
    "ISRG": "0001035267",
    "BKNG": "0001075531",
    "SBUX": "0000829224",
    "GE": "0000040545",
    "CAT": "0000018230",
    "BA": "0000012927",
    "GS": "0000886982",
    "MS": "0000895421",
    "BLK": "0001364742",
    "SPY": "0000884396",
    "QQQ": "0001067839",
}


def _get_user_agent() -> str:
    ua = os.environ.get("SEC_EDGAR_USER_AGENT", "").strip()
    return ua or DEFAULT_UA


def _rate_limit() -> None:
    global _last_request
    now = time.monotonic()
    elapsed = now - _last_request
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request = time.monotonic()


def _headers(accept: str = "application/json") -> dict[str, str]:
    return {
        "User-Agent": _get_user_agent(),
        "Accept": accept,
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }


def get_json(url: str, timeout: float = 30.0) -> Any:
    """GET JSON from SEC EDGAR with rate limiting and proper headers."""
    _rate_limit()
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url, headers=_headers("application/json"))
        resp.raise_for_status()
        return resp.json()


def get_text(url: str, timeout: float = 45.0) -> str:
    """GET text/HTML from SEC EDGAR."""
    _rate_limit()
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(
            url,
            headers=_headers("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        )
        resp.raise_for_status()
        return resp.text


def resolve_cik(ticker: str) -> Optional[str]:
    """Resolve a ticker symbol to a zero-padded 10-digit CIK."""
    ticker = ticker.strip().upper()
    if not ticker:
        return None

    # 1) Try official SEC ticker map
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        data = get_json(url)
        for entry in data.values():
            if str(entry.get("ticker", "")).upper() == ticker:
                return str(entry["cik_str"]).zfill(10)
    except Exception:
        # Network block / 403 / timeout – fall through to local map
        pass

    # 2) Fallback map (covers major US tickers)
    if ticker in _FALLBACK_TICKERS:
        return _FALLBACK_TICKERS[ticker]

    return None


def company_submissions(cik: str) -> dict:
    """Fetch the company submissions JSON for a CIK."""
    cik = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    return get_json(url)
