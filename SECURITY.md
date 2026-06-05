# Security

Demand Radar fetches public evidence from external services (using search terms
derived from your demand hypothesis) and renders a local, self-contained HTML
report from it.

## Reporting Issues

If you find a security issue, please open a private report through GitHub
security advisories when available, or contact the maintainer through the GitHub
profile linked in this repository. Please do not file public issues for
security-sensitive reports.

## Scope

Unlike a fully local tool, Demand Radar **does make network calls**: its Python
connectors query third-party APIs (Hacker News / HN Algolia, iTunes / App Store,
Google Play, Reddit) and the skill performs web search and fetch. Untrusted text
returned by those services is escaped before it is rendered into the HTML report.

Security-sensitive areas include:

- **Report HTML injection** from untrusted fetched content. Reviews, comments,
  forum posts, and snippets returned by external services are attacker-influenced
  text. `generate_report.py` passes all such content through `html.escape()`
  (`esc()` / `inline()`) before rendering; a bug that lets fetched content reach
  the HTML unescaped is a security issue.
- **Handling of any API keys or tokens.** The optional Reddit OAuth credentials
  (`REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` / `REDDIT_USER_AGENT`) are read
  from environment variables only and must never be logged, written into reports,
  or committed.
- **Unsafe local path handling** when writing reports or temporary evidence files
  (e.g. path traversal via a demand slug or output path).
- **Over-broad network requests** — connectors should query only the intended
  endpoints with the user's search terms, at modest volume, and must not exfiltrate
  local data beyond the search terms required to run a query.
- **Leaking the user's demand hypothesis to third parties.** Search terms derived
  from the hypothesis are sent to the external services that are queried; any
  change that broadens what is sent, or sends it to unexpected destinations, is in
  scope.

Demand Radar escapes untrusted fetched content before rendering HTML, limits its
network requests to the official free endpoints its connectors target plus web
search, and keeps any credentials in environment variables rather than the repo.
