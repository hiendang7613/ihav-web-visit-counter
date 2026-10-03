# Changelog

## 0.1.0 — 2026-10-03

- Add Claude Code and Codex skills backed by one Python standard-library CLI.
- Add WebTrafficChecker modelled estimates with source, analysis timestamp, returned country shares and returned history.
- Add Tranco daily-list rank fallback that never invents visits.
- Add local 24-hour caching, blocked-source handling and fixture-only tests.
- Document the provider terms risk and the limits of the available accuracy evidence.
- Run Tranco after a primary block or failure, keep its rank-only result uncached, and treat cache failures as warnings.
- Support Python 3.9, bound Tranco redirects to its HTTPS host, and retain the latest dated history snapshot for each month.
