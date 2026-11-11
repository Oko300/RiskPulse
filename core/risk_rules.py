"""Risk taxonomy for Form 8-K item codes and Form 4 transaction codes."""

from __future__ import annotations

# High-signal 8-K item codes → (severity, category, short label)
EIGHT_K_RISK_ITEMS: dict[str, tuple[int, str, str]] = {
    # Highest severity
    "1.03": (10, "bankruptcy", "Bankruptcy or receivership"),
    "3.01": (9, "delisting", "Notice of delisting or failure to satisfy listing rule"),
    "4.02": (9, "restatement", "Non-reliance on previously issued financial statements"),
    "2.04": (8, "debt", "Triggering events that accelerate or increase a direct financial obligation"),
    "2.06": (7, "impairment", "Material impairments"),
    "5.02": (6, "leadership", "Departure of directors or certain officers; election of directors; appointment of certain officers"),
    "1.01": (5, "material_agreement", "Entry into a material definitive agreement"),
    "1.02": (5, "material_agreement", "Termination of a material definitive agreement"),
    "2.01": (5, "acquisition", "Completion of acquisition or disposition of assets"),
    "2.03": (5, "debt", "Creation of a direct financial obligation or an obligation under an off-balance sheet arrangement"),
    "2.05": (5, "cost", "Costs associated with exit or disposal activities"),
    "5.03": (4, "governance", "Amendments to articles of incorporation or bylaws; change in fiscal year"),
    "7.01": (3, "reg_fd", "Regulation FD disclosure"),
    "8.01": (3, "other", "Other events"),
}

# Form 4 transaction codes that are open-market or high-signal
OPEN_MARKET_SELL = {"S"}          # Open market or private sale of non-derivative security
OPEN_MARKET_BUY = {"P"}           # Open market or private purchase

# Routine / compensation-related (lower risk signal)
ROUTINE_CODES = {"A", "M", "F", "G", "V", "C", "D", "E", "H", "I", "J", "K", "L", "O", "U", "W", "X", "Y", "Z"}


def score_8k_items(item_codes: list[str]) -> dict:
    """Score a list of 8-K item codes and return risk summary."""
    flagged = []
    max_severity = 0
    categories: dict[str, int] = {}

    for code in item_codes:
        code = code.strip()
        if code in EIGHT_K_RISK_ITEMS:
            sev, cat, label = EIGHT_K_RISK_ITEMS[code]
            flagged.append({"code": code, "severity": sev, "category": cat, "label": label})
            max_severity = max(max_severity, sev)
            categories[cat] = categories.get(cat, 0) + 1

    # Simple 0-10 risk score
    if max_severity >= 9:
        level = "SEVERE"
    elif max_severity >= 7:
        level = "ELEVATED"
    elif max_severity >= 5:
        level = "MODERATE"
    elif max_severity >= 3:
        level = "LOW"
    else:
        level = "NONE"

    return {
        "risk_score": max_severity,
        "risk_level": level,
        "flagged_items": flagged,
        "category_counts": categories,
    }


def classify_form4_transactions(transactions: list[dict]) -> dict:
    """Classify Form 4 transactions into open-market vs routine."""
    open_sells = []
    open_buys = []
    routine = []
    officers_directors_selling = 0

    for tx in transactions:
        code = str(tx.get("transactionCode", "")).upper()
        shares = float(tx.get("shares", 0) or 0)
        is_officer = bool(tx.get("isOfficer") or tx.get("isDirector"))

        entry = {
            "code": code,
            "shares": shares,
            "date": tx.get("transactionDate"),
            "owner": tx.get("ownerName"),
            "is_officer_or_director": is_officer,
        }

        if code in OPEN_MARKET_SELL:
            open_sells.append(entry)
            if is_officer:
                officers_directors_selling += 1
        elif code in OPEN_MARKET_BUY:
            open_buys.append(entry)
        else:
            routine.append(entry)

    total_sell_shares = sum(t["shares"] for t in open_sells)
    total_buy_shares = sum(t["shares"] for t in open_buys)

    # Simple heuristic risk score
    score = 0
    if len(open_sells) >= 3:
        score += 4
    if officers_directors_selling >= 2:
        score += 3
    if total_sell_shares > total_buy_shares * 3 and total_sell_shares > 10000:
        score += 2

    if score >= 7:
        level = "ELEVATED"
    elif score >= 4:
        level = "MODERATE"
    elif score >= 2:
        level = "LOW"
    else:
        level = "NONE"

    return {
        "risk_score": min(score, 10),
        "risk_level": level,
        "open_market_sells": open_sells,
        "open_market_buys": open_buys,
        "routine_count": len(routine),
        "officer_or_director_sell_count": officers_directors_selling,
        "total_open_sell_shares": total_sell_shares,
        "total_open_buy_shares": total_buy_shares,
    }
