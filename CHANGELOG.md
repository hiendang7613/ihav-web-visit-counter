# Changelog

## 0.1.0 — 2026-10-03

- Add Claude Code and Codex skills backed by one Python standard-library CLI.
- Add WebTrafficChecker modelled estimates with source, analysis timestamp, returned country shares and returned history.
- Add TrafficLens as a partial middle fallback; preserve rounded visit strings, scrape dates and stale labels, and skip ranking-only responses.
- Keep `monthly_visits` numeric or null in JSON and add `monthly_visits_text` for provider display values.
- Add Tranco daily-list rank fallback that never invents visits.
- Cache all estimate results for 24 hours, keep rank-only results uncached, and return one provider result without averaging.
- Add local caching, blocked-source handling and fixture-only tests.
- Document the provider terms risk and the limits of the available accuracy evidence.
- Run Tranco after a primary block or failure, keep its rank-only result uncached, and treat cache failures as warnings.
- Support Python 3.9, bound Tranco redirects to its HTTPS host, and retain the latest dated history snapshot for each month.
- Use the package version in the HTTP User-Agent and clarify that refused redirects are not followed.
