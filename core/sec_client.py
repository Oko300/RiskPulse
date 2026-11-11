"""Shared SEC EDGAR HTTP client with rate limiting and proper User-Agent."""

from __future__ import annotations

import os
import time
from typing import Any, Optional

import httpx

# SEC requires a descriptive User-Agent. Users must set SEC_EDGAR_USER_AGENT.
DEFAULT_UA = "RiskPulse/0.1 (hermes-plugin; contact@example.com)"

# Hard limit under SEC's 10 req/sec ceiling
_MIN_INTERVAL = 0.12  # ~8 req/sec
_last_request = 0.0


def _get_user_agent() -> str:
    ua = os.environ.get("SEC_EDGAR_USER_AGENT", "").strip()
    if not ua:
        # Fallback that still identifies the tool; user should override
        return DEFAULT_UA
    return ua


def _rate_limit() -> None:
    global _last_request
    now = time.monotonic()
    elapsed = now - _last_request
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request = time.monotonic()


def get_json(url: str, timeout: float = 30.0) -> Any:
    """GET JSON from SEC EDGAR with rate limiting and proper headers."""
    _rate_limit()
    headers = {
        "User-Agent": _get_user_agent(),
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    }
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()


def get_text(url: str, timeout: float = 45.0) -> str:
    """GET text/HTML from SEC EDGAR."""
    _rate_limit()
    headers = {
        "User-Agent": _get_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    }
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text


def resolve_cik(ticker: str) -> Optional[str]:
    """Resolve a ticker symbol to a zero-padded 10-digit CIK."""
    ticker = ticker.strip().upper()
    if not ticker:
        return None

    # Official SEC ticker → CIK map (updated frequently by SEC)
    url = "https://www.sec.gov/files/company_tickers.json"
    data = get_json(url)

    for entry in data.values():
        if str(entry.get("ticker", "")).upper() == ticker:
            cik = str(entry["cik_str"]).zfill(10)
            return cik
    return None


def company_submissions(cik: str) -> dict:
    """Fetch the company submissions JSON for a CIK."""
    cik = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    return get_json(url)
