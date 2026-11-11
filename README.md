# RiskPulse

**Live SEC EDGAR risk analysis for US public companies — built as a Hermes Agent plugin.**

RiskPulse gives Hermes two focused tools that pull real data from the SEC:

| Tool | What it does |
|------|--------------|
| `analyze_8k_risk` | Scans recent Form 8-K filings for material events (restatements, leadership changes, impairments, bankruptcy signals, etc.) and returns a risk score + narrative |
| `analyze_insider_activity` | Scans recent Form 4 insider filings and surfaces volume / potential open-market selling patterns by officers and directors |

Both tools are **pattern-detection only**. They are **not** investment, legal, or financial advice. Always verify against the primary filings on SEC EDGAR.

---

## Requirements

- Hermes Agent `>= 0.21.0`
- Python packages: `httpx`, `beautifulsoup4`, `lxml` (declared in `plugin.yaml`)
- Environment variable:

```bash
SEC_EDGAR_USER_AGENT="Your Name or Company (you@example.com)"
```

SEC requires a descriptive User-Agent with a real contact email.

---

## Install (for testing)

```bash
# From the plugin directory
hermes plugins install . --enable

# Or after pushing to GitHub
hermes plugins install <your-github-user>/RiskPulse --enable
```

Then start a new Hermes session (or `/reload-plugins`) and ask:

> Analyze 8-K risk for TSLA over the last 120 days  
> Check insider activity for AAPL

---

## Disclosure (for catalog reviewers)

- **Network**: Makes HTTPS requests only to `data.sec.gov` and `www.sec.gov` (official SEC EDGAR endpoints).
- **No credentials stored**: The only required env var is a non-secret User-Agent string.
- **No self-updating code**.
- **No core overrides** – uses only the public `ctx.tool` registration surface.
- **Outputs are explicitly labeled as estimates / pattern detection**.

---

## Project layout

```
RiskPulse/
├── plugin.yaml          # Hermes plugin manifest
├── __init__.py          # register(ctx) – registers the two tools
├── core/
│   ├── sec_client.py    # Rate-limited SEC EDGAR client + CIK resolution
│   └── risk_rules.py    # 8-K item taxonomy + Form 4 classification helpers
├── tools/
│   ├── eight_k.py       # analyze_8k_risk implementation
│   └── insider.py       # analyze_insider_activity implementation
└── README.md
```

---

## License

MIT
