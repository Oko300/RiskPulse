"""analyze_insider_activity tool – Form 4 insider transaction risk signals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from core.sec_client import resolve_cik, company_submissions, get_text
from core.risk_rules import classify_form4_transactions


def analyze_insider_activity(ticker: str, lookback_days: int = 90, max_filings: int = 20) -> dict[str, Any]:
    """
    Analyze recent Form 4 insider transactions for open-market selling clusters
    and officer/director activity.

    Args:
        ticker: Stock ticker symbol
        lookback_days: Days to look back (default 90, max 365)
        max_filings: Max Form 4 filings to inspect (default 20, max 40)

    Returns:
        Structured insider activity risk assessment.
    """
    ticker = ticker.strip().upper()
    lookback_days = max(1, min(int(lookback_days), 365))
    max_filings = max(1, min(int(max_filings), 40))

    cik = resolve_cik(ticker)
    if not cik:
        return {
            "success": False,
            "error": f"Could not resolve ticker '{ticker}' to a CIK.",
            "ticker": ticker,
        }

    try:
        submissions = company_submissions(cik)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch SEC submissions: {e}",
            "ticker": ticker,
            "cik": cik,
        }

    company_name = submissions.get("name", ticker)
    recent = submissions.get("filings", {}).get("recent", {})

    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])

    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).date()

    form4_list = []
    for i, form in enumerate(forms):
        if form not in ("4", "4/A"):
            continue
        try:
            fdate = datetime.strptime(dates[i], "%Y-%m-%d").date()
        except Exception:
            continue
        if fdate < cutoff:
            continue
        form4_list.append({
            "filing_date": dates[i],
            "accession": accessions[i],
            "form": form,
        })
        if len(form4_list) >= max_filings:
            break

    # For v0.1 we return the filing list + a lightweight heuristic.
    # Full XML ownership document parsing can be added in a follow-up.
    # We still give the agent real, actionable data (which Form 4s exist).

    count = len(form4_list)
    if count == 0:
        level = "NONE"
        score = 0
        reason = f"No Form 4 filings found for {ticker} in the last {lookback_days} days."
    elif count >= 8:
        level = "MODERATE"
        score = 4
        reason = f"{count} Form 4 filings in the lookback window. Elevated insider activity volume; review for open-market sales by officers/directors."
    else:
        level = "LOW"
        score = 2
        reason = f"{count} Form 4 filing(s) found. Volume is moderate; inspect individual filings for open-market transactions."

    narrative = (
        f"RiskPulse scanned Form 4 insider activity for {company_name} ({ticker}) "
        f"over the past {lookback_days} days and found {count} filing(s). "
        f"{reason} "
        "This tool surfaces disclosure patterns only. It is not investment advice."
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
        "filings": form4_list,
        "narrative": narrative,
        "disclaimer": "ESTIMATE / PATTERN DETECTION ONLY. Not investment, legal, or financial advice. Always verify against the primary Form 4 filings on SEC EDGAR.",
        "data_source": "SEC EDGAR (data.sec.gov)",
        "note": "v0.1 returns filing inventory + volume heuristic. Full transaction-code parsing of ownership XML is planned for a follow-up release.",
    }
