# Privacy

Demand Radar runs locally inside Claude Code, but to gather evidence it **does
query external services** with search terms derived from your demand hypothesis;
the report itself is generated and stored on your machine.

## Data Read

The plugin reads local inputs:

- The demand hypothesis / prompt you provide to `/demand` (your product idea,
  target customer, the claim to validate).
- Any local configuration you set, such as the optional Reddit OAuth credentials
  in environment variables (`REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` /
  `REDDIT_USER_AGENT`) and the output directory override (`$COWORK_OUTPUTS_DIR`).

## Network & External Services

To validate a demand, Demand Radar sends **search terms derived from your
hypothesis** (keywords, competitor names, app names) to third-party services and
reads their public responses. The connectors under
`skills/demand/scripts/connectors/` query:

- **Hacker News** — via the HN Algolia search API (`hn.algolia.com`). No key
  required.
- **iTunes / Apple App Store** — the iTunes Search API and the customer-reviews
  RSS feed (`itunes.apple.com`). No key required.
- **Google Play** — app reviews via the optional `google-play-scraper` library.
  Used only if that dependency is installed; otherwise skipped.
- **Reddit** — best-effort, via Reddit's official PRAW OAuth client when the
  optional `praw` library and `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`
  credentials are present, otherwise the public `.json` endpoint (which may be
  rate-limited or blocked). Reddit access is best-effort and the run does not
  depend on it.

In addition, the skill uses Claude Code's web search / web fetch to find
industry reports, market data, competitor listings, and broader community
discussion.

Each of these services is operated by a third party and is governed by **its own
privacy policy and terms of service**; the search terms you send are subject to
that service's policies. No API key is required to run Demand Radar unless you
choose to enable a connector that needs one (only Reddit OAuth does, and it is
optional). The plugin itself does not upload any telemetry or analytics.

## Data Written

The plugin writes local report artifacts:

- `~/.demand-radar/reports/*.html` — the generated validation reports (the
  default output directory; honors `$COWORK_OUTPUTS_DIR` when set).
- `reports/*.html` — local report output within a checkout (gitignored).
- `docs/sample-report.html` — the committed showcase report shipped with the repo.

## Report Contents

A generated report may include quoted snippets from the public sources that were
fetched (Hacker News comments, App Store / Google Play reviews, forum and search
results) together with your own demand hypothesis. Treat the report files as you
wish — keep them private unless you intentionally share them, since they combine
your idea with third-party content.
