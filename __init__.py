"""
RiskPulse – Hermes Agent plugin
Live SEC EDGAR risk analysis for US public companies.
"""

from __future__ import annotations

import json
from typing import Any

from .tools.eight_k import analyze_8k_risk
from .tools.insider import analyze_insider_activity


def register(ctx):
    """Register RiskPulse tools with Hermes."""

    # ------------------------------------------------------------------
    # Tool 1: analyze_8k_risk
    # ------------------------------------------------------------------
    schema_8k = {
        "name": "analyze_8k_risk",
        "description": (
            "Analyze recent Form 8-K filings for a US public company and surface "
            "material risk events (bankruptcy, restatement, delisting, leadership "
            "changes, material impairments, etc.). Returns a risk score, level, "
            "list of filings, and a plain-language narrative. "
            "Data source: live SEC EDGAR. Not investment advice."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "US stock ticker symbol, e.g. AAPL, TSLA, MSFT",
                },
                "lookback_days": {
                    "type": "integer",
                    "description": "How many days back to search (default 180, max 730)",
                    "default": 180,
                },
            },
            "required": ["ticker"],
        },
    }

    def handle_8k(params: dict[str, Any], **kwargs):
        ticker = params.get("ticker", "")
        lookback = int(params.get("lookback_days", 180))
        result = analyze_8k_risk(ticker=ticker, lookback_days=lookback)
        return json.dumps(result, default=str)

    ctx.register_tool(
        name="analyze_8k_risk",
        toolset="riskpulse",
        schema=schema_8k,
        handler=handle_8k,
    )

    # ------------------------------------------------------------------
    # Tool 2: analyze_insider_activity
    # ------------------------------------------------------------------
    schema_insider = {
        "name": "analyze_insider_activity",
        "description": (
            "Analyze recent Form 4 insider transactions for a US public company. "
            "Surfaces volume of insider filings and highlights potential open-market "
            "selling clusters by officers and directors. "
            "Data source: live SEC EDGAR. Not investment advice."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "US stock ticker symbol, e.g. AAPL, TSLA",
                },
                "lookback_days": {
                    "type": "integer",
                    "description": "Days to look back (default 90, max 365)",
                    "default": 90,
                },
                "max_filings": {
                    "type": "integer",
                    "description": "Maximum number of Form 4 filings to inspect (default 20)",
                    "default": 20,
                },
            },
            "required": ["ticker"],
        },
    }

    def handle_insider(params: dict[str, Any], **kwargs):
        ticker = params.get("ticker", "")
        lookback = int(params.get("lookback_days", 90))
        max_f = int(params.get("max_filings", 20))
        result = analyze_insider_activity(
            ticker=ticker,
            lookback_days=lookback,
            max_filings=max_f,
        )
        return json.dumps(result, default=str)

    ctx.register_tool(
        name="analyze_insider_activity",
        toolset="riskpulse",
        schema=schema_insider,
        handler=handle_insider,
    )
