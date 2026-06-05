# Contributing

Contributions are welcome.

## Development checks

The connectors, aggregation/triangulation scripts, and report generator are
plain Python 3. The core connectors (Hacker News, App Store / iTunes, Reddit
fallback) and all of `triangulate.py`, `aggregate_scores.py`, and
`generate_report.py` use only the **Python standard library** — nothing to
install for those. Two connectors have **optional** enhancements.

Set up an isolated environment and install the optional dependencies before
opening a pull request:

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install the optional connector dependencies
#   google-play-scraper -> enables the Google Play reviews connector
#   praw                -> enables Reddit OAuth (stable) mode
pip install -r skills/demand/scripts/requirements.txt
```

Syntax-check every script and connector:

```bash
python3 -m py_compile \
  skills/demand/scripts/triangulate.py \
  skills/demand/scripts/aggregate_scores.py \
  skills/demand/scripts/generate_report.py \
  skills/demand/scripts/connectors/hn_algolia.py \
  skills/demand/scripts/connectors/itunes.py \
  skills/demand/scripts/connectors/play_reviews.py \
  skills/demand/scripts/connectors/reddit.py
```

## Testing locally

Run the connectors and scripts directly against a sample demand. These make
real network calls to the external services they wrap, so use short, generic
search terms and respect each service's rate limits while testing.

```bash
# Connectors (network) — query external services with a sample search term
python3 skills/demand/scripts/connectors/hn_algolia.py "remote team notes"
python3 skills/demand/scripts/connectors/itunes.py search "Notion"
python3 skills/demand/scripts/connectors/itunes.py reviews <app_id>
python3 skills/demand/scripts/connectors/play_reviews.py com.notion.id   # needs google-play-scraper
python3 skills/demand/scripts/connectors/reddit.py "remote team notes"   # best-effort, may be rate-limited

# Aggregation / triangulation (local, deterministic)
python3 skills/demand/scripts/triangulate.py /tmp/evidence.json --out /tmp/tri.json
python3 skills/demand/scripts/aggregate_scores.py /tmp/judges.json --out /tmp/agg.json

# Report generator (local) — turn a report.json into self-contained HTML
python3 skills/demand/scripts/generate_report.py \
  --report /tmp/report.json \
  --output /tmp/demand-report.html --open
```

To test the installed experience, add this repo as a marketplace and reinstall:

```bash
/plugin marketplace add LeifDiao/demand-radar
/plugin install demand-radar@demand-radar-marketplace
```

Then start a new session so Claude Code picks up the updated skill. After
changing a connector, verify it both succeeds and degrades gracefully (the
connectors are written to return a friendly error payload — not crash — when a
service is unavailable, rate-limited, or an optional dependency is missing).

## Design principles

- **Deterministic where it counts.** Triangulation (`triangulate.py`) and score
  aggregation (`aggregate_scores.py`) are deterministic math (independent-source
  counting, median, spread flags, weighted verdict): same input → same output.
  The model does the diagnosis and scoring from the evidence + the validation
  framework; the scripts enforce the hard rules so the model can't soften a
  single-source lead into a "verified" signal.
- **Respect external APIs.** Demand Radar queries third-party services
  (Hacker News / HN Algolia, iTunes / App Store, Google Play, Reddit, plus web
  search). Keep request volume modest, honor each service's rate limits and
  terms of service, and prefer official free endpoints over scraping.
- **Escape report HTML.** All untrusted content fetched from external sources
  flows into the report through `html.escape()` (`esc()` / `inline()` in
  `generate_report.py`). Never interpolate fetched text into the HTML without
  escaping it first.
- **Keep secrets out of the repo.** Any optional credentials (e.g. the Reddit
  OAuth `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`) are read from environment
  variables only. Do not commit keys, tokens, or `.env` files.
- **Do not commit fetched data.** Raw evidence pulled from external services and
  generated reports are local artifacts. `reports/` is gitignored; only the
  curated `docs/sample-report.html` showcase is whitelisted. Do not check in
  scraped reviews, threads, or report output.
- Avoid new external dependencies unless they remove meaningful complexity, and
  keep the core path standard-library-only.
- When you change a scoring rule, update the methodology docs and the relevant
  reference under `skills/demand/references/` to match.
