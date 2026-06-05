# Demand Radar Methodology

Demand Radar's report quality comes ~90% from its framework and ~10% from how much data it crawls. This page documents the framework.

## 1. Framing (The Mom Test, applied)

Before any search, a vague idea is forced into a **falsifiable hypothesis** with five parts: ICP · job/pain · current workaround · the claim to test · Go criteria. A good claim contains something data can disprove (a *who* + a *behavior* + a *motivation/payment*). Bad claims ("this market is big") can't be killed by any evidence and are rejected.

## 2. Two evidence pillars

| Pillar | Sources | Answers |
|---|---|---|
| **Top-down** | Industry reports (Gartner/IDC/Statista), official stats, funding data, public filings, policy | Market size, growth, capital flow, official framing |
| **Bottom-up** | Hacker News, App Store / Google Play reviews, search demand, social | Is the pain real, who has it, what they use today, willingness to pay |

The two are cross-checked. **Contradictions are first-class findings** — "report says the market is huge but the community is silent" means either a silent B2B market or an analyst-inflated one.

## 3. Evidence grading

| Grade | Definition | Can support |
|---|---|---|
| **Hard** | Real behavior with money: payment, retention, funding, filings | Willingness-to-pay / market-size conclusions |
| **Behavioral** | Real usage/search/discussion: review quotes, search trends, upvoted complaints | Pain-is-real / prevalence |
| **Opinion** | "I'd buy it" / "sounds nice" | Lead only — never a conclusion on its own |
| **Analyst** | Forecasts/qualitative judgements in reports | Direction; must cross with behavioral |

## 4. Triangulation (`triangulate.py`)

A signal counts as **verified** only when ≥2 *independent* sources confirm it (independent = different platform, not reposts).
- 1 source → lead (unverified)
- 2 sources → verified (medium)
- ≥3 sources **and** hard evidence → strong (high)

The model assigns each evidence item a `signal` label (semantic judgement); the script counts distinct sources and assigns confidence (deterministic). This stops single-source leads from being talked up into "verified."

## 5. The 7-axis scorecard + multi-judge scoring

Pain intensity (×1.5) · prevalence · current-alternative gap · **willingness to pay (×2)** · market size & trend · competition/whitespace · reachability. Each axis 0–5.

Three judge agents (neutral / optimistic / strict) score independently; `aggregate_scores.py` takes the median per axis, flags axes where judges disagree by ≥2 points, and computes the weighted verdict band:

| Weighted % | Verdict |
|---|---|
| ≥ 70% | Go |
| 50–70% | Conditional |
| 30–50% | Pivot |
| < 30% | No-go |

## 6. Adversarial red-team + closed-loop re-score

A dedicated red-team agent attacks the hypothesis with seven kill-modes (fake demand / vitamin-not-painkiller / saturated / declining / nobody pays / unreachable / sample bias), citing counter-evidence. Evidence-backed attacks are folded back in and the scorecard is **re-aggregated** to a final verdict. Any "Go" must survive this. If the red-team finds nothing, "could not refute" is itself a strong positive signal.

## 7. Honesty rails

- No fabricated data — every number traces to a URL
- No conclusion without evidence — missing data is scored "insufficient," not guessed
- "Not found" is never written as "doesn't exist" — it goes in the forced **"what we couldn't verify"** section
- Confidence is reported per claim and never inflated to please the user

## Zero-login data access

Demand Radar uses **official free APIs + web search only** — no scrapers, no OAuth, no keys. Reddit is excluded from default runs because it blocks the crawler; bottom-up community signal is covered by Hacker News, App Store / Google Play reviews, and general web search over comparison blogs and accessible forums. Sources that require login or anti-bot evasion (large-scale Reddit, Product Hunt tokens, G2/Amazon full review scrapes, exact search volume) are reserved for a future paid, pluggable connector layer.
