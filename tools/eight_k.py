"""analyze_8k_risk tool – Form 8-K material event risk analysis."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..core.sec_client import resolve_cik, company_submissions
from ..core.risk_rules import score_8k_items, EIGHT_K_RISK_ITEMS


def analyze_8k_risk(ticker: str, lookback_days: int = 180) -> dict[str, Any]:
    """
    Analyze recent Form 8-K filings for a US public company and surface material risk events.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, TSLA)
        lookback_days: How many days back to search (default 180, max 730)

    Returns:
        Structured risk assessment with score, level, flagged items, and narrative.
    """
    ticker = ticker.strip().upper()
    lookback_days = max(1, min(int(lookback_days), 730))

    cik = resolve_cik(ticker)
    if not cik:
        return {
            "success": False,
            "error": f"Could not resolve ticker '{ticker}' to a CIK. Only US domestic filers with a ticker mapping are supported.",
            "ticker": ticker,
        }

    try:
        submissions = company_submissions(cik)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch SEC submissions for {ticker}: {e}",
            "ticker": ticker,
            "cik": cik,
        }

    company_name = submissions.get("name", ticker)
    recent = submissions.get("filings", {}).get("recent", {})

    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).date()

    eight_k_filings = []
    all_item_codes: list[str] = []

    for i, form in enumerate(forms):
        if form not in ("8-K", "8-K/A"):
            continue
        try:
            fdate = datetime.strptime(dates[i], "%Y-%m-%d").date()
        except Exception:
            continue
        if fdate < cutoff:
            continue

        accession = accessions[i].replace("-", "")
        primary = primary_docs[i] if i < len(primary_docs) else ""
        # Items are not always in the recent index; we collect what we can
        # For a fast first version we use the form presence + later enhancement
        eight_k_filings.append({
            "filing_date": dates[i],
            "form": form,
            "accession": accessions[i],
            "primary_document": primary,
            "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary}" if primary else None,
        })

    # Note: The recent filings index does not always include the full list of
    # Item codes. For v0.1 we score based on presence of 8-Ks and provide the
    # list. A future version can fetch individual filing indexes for item codes.
    # For now we return a useful structural result + guidance.

    risk = score_8k_items(all_item_codes)  # will be empty until we parse items

    # Heuristic fallback when we cannot yet extract item codes quickly:
    count = len(eight_k_filings)
    if count == 0:
        level = "NONE"
        score = 0
        reason = f"No Form 8-K filings found for {ticker} in the last {lookback_days} days."
    elif count >= 5:
        level = "MODERATE"
        score = 5
        reason = f"{count} Form 8-K filings in the lookback window. Multiple material event disclosures may warrant review."
    else:
        level = "LOW"
        score = 2
        reason = f"{count} Form 8-K filing(s) found. Review the linked filings for material events."

    narrative = (
        f"RiskPulse analyzed Form 8-K activity for {company_name} ({ticker}) "
        f"over the past {lookback_days} days. "
        f"{reason} "
        "This is a pattern-detection tool, not investment advice. Always read the primary filings on SEC EDGAR."
    )

    return {
        "success": True,
        "ticker": ticker,
        "cik": cik,
        "company_name": company_name,
        "lookback_days": lookback_days,
        "risk_score": score,
        "risk_level": level,
        "risk_reason": reason,
        "filing_count": count,
        "filings": eight_k_filings[:15],  # cap for readability
        "narrative": narrative,
        "disclaimer": "ESTIMATE / PATTERN DETECTION ONLY. Not investment, legal, or financial advice. Verify against the primary SEC filings.",
        "data_source": "SEC EDGAR (data.sec.gov)",
    }
