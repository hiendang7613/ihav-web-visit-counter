# How it works

The plugin has a shared Python standard-library core and thin Claude Code and Codex skills. Both skills call the same CLI and use the same JSON result contract.

1. Input is parsed as a URL or host. A leading `www.` is removed, IDNs are converted to ASCII, and other subdomains are preserved. The plugin does not guess a public-suffix boundary.
2. A normalized-domain result is read from the 24-hour cache, if present.
3. The primary adapter makes one GET to WebTrafficChecker's linked JSON endpoint. A positive `traffic.monthlyVisits` is accepted only when `analyzedAt` is also present and parseable.
4. The `analyzed_at` timestamp is retained as returned and the result `period` stays `null`. It is not a reporting-month claim.
5. If the primary endpoint has no usable result, is blocked, or fails, the Tranco adapter downloads the current top-1M archive only when its local daily-list cache is stale. Rank lookup then happens locally. A successful fallback result explains the primary outcome.
6. Each source is requested at most once. A block stops that source; the separate Tranco source may still run. If no source returns a result, a block exits `4`, a provider/network failure exits `5`, and no matching data exits `2`. There are no browser fallbacks or alternate routes to a blocked source.

The result cache is best-effort. If its directory cannot be read or written, the lookup continues and adds a cache warning to the result.

Runtime files use `./.ihav_space/ihav-web-visit-counter/` relative to the process working directory. `IHAV_CACHE_DIR` and `--cache-dir` can override the cache location.

## Result kinds

- `estimate`: a provider-modelled WebTrafficChecker `monthlyVisits` value with source link and analysis timestamp. No independently measured error interval exists in v0.
- `rank_only`: Tranco rank with `monthly_visits: null`.
- No matching data and no provider error: CLI exit `2`; it does not invent a number.
