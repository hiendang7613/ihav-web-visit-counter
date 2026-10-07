# Changelog

## 0.1.2 — 2026-10-08

- Ignore result caches for a different domain or with malformed values, then continue the normal provider chain. Keep valid legacy cache shapes readable.
- Keep cache warnings out of stored results, so a later cache hit no longer repeats a warning from the run that refreshed the cache.
- Close HTTP error response bodies on every handled return or exception without retrying blocked sources.
- Bound raw JSON integers before provider field conversion so unsupported numbers continue the same fallback chain on Python 3.9 and later.
- Reject invalid or oversized decimal strings consistently across supported Python versions so malformed counts or ranks cannot interrupt fallback.
- Accept a whole-number float from WebTrafficChecker only up to `2^53`, the range in which a float holds an exact count. A larger value continues to the next provider.
- Validate Tranco rows before storing a daily list, and replace a corrupt cached list with one download. Keep rank-only results separate from visit estimates.
- Decode each fresh Tranco download once, share decimal-string conversion across providers, and remove a duplicate test definition.
- Quote the script path and website argument in the skill commands, and run each lookup as one command without `echo`, pipes or chained commands.
- Show the complete synthetic demo in its first animation frame.
- Add 21 fixture-only regression tests and check that project metadata and both host manifests match the runtime package version. JSON contract version `2` and exit codes remain unchanged.
- Add a fixture-only consumer compatibility command and CI job against pinned public Leaderboards and Competitor Search code, with network access disabled in Python subprocesses. It includes the Counter CLI's exit `2` no-data result.
- Check rounded `T` labels through the actual TrafficLens parser and Counter CLI, and document the pinned Leaderboards `0.2.2` floor/no-weight policy without changing producer or consumer behavior.
- Document sources reviewed for possible future adapters: CrUX, Similarweb rank APIs and the Tranco per-domain API. None of them is part of the provider chain.

## 0.1.1 — 2026-10-04

- Omit WebTrafficChecker's default placeholder country split (US 45.2%, IN 10.3%, BR 6.5%, GB 6.5%, DE 5.2%), which it returns for unranked and many low-traffic domains, and add a note explaining why country shares are missing.
- Refresh the README with shared-catalog installation, feature and JSON examples, a provider flowchart and related plugins.
- Animate the synthetic terminal demo with a reduced-motion fallback and add issue navigation and a pull request template.

## 0.1.0 — 2026-10-04

- Add a CI badge, agent install prompts, a short FAQ and a PNG social preview; use friendly provider names in JSON failure details.
- Add JSON contract version `2` and structured per-provider outcomes to success and error output while preserving existing result fields and exit codes.
- Record provider API HTTP status separately from payload fields, and identify cached provider results without replaying an earlier block as current.

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
- Reconfigure CLI output streams to UTF-8 for agent pipes and add a fixture-backed Windows pipe smoke check.
- Tolerate small future file timestamp skew so cached results and daily lists remain fresh on Windows.
- Return no-data with friendly notes when a primary has no result and later providers fail; round country shares to four decimal places.
- Clarify fallback error codes, describe TrafficLens in the Codex listing, and identify source timestamps as analysis or scrape dates rather than guaranteed reporting months.
