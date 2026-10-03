# How it works

The plugin has a shared Python standard-library core and thin Claude Code and Codex skills. Both skills call the same CLI and use the same JSON result contract.

1. Input is parsed as a URL or host. A leading `www.` is removed, IDNs are converted to ASCII, and other subdomains are preserved. The plugin does not guess a public-suffix boundary.
2. A normalized-domain estimate is read from the 24-hour cache, if present. Rank-only results are never cached.
3. The primary adapter makes one GET to WebTrafficChecker's linked JSON endpoint. A positive `traffic.monthlyVisits` is accepted only when `analyzedAt` is also present and parseable.
4. If WebTrafficChecker has no usable estimate, is blocked, or fails, the middle adapter makes one GET to TrafficLens's public Worker route. It accepts only a positive visit count and a parseable `scrapedAt`. The original formatted string is preserved; `source=stale` is rendered as stale. Its scrape timestamp is not a reporting month.
5. A TrafficLens rank-only response or invalid/missing count is skipped. If neither visits provider returns a usable estimate, the Tranco adapter downloads the current top-1M archive only when its local daily-list cache is stale. Rank lookup then happens locally. A successful fallback result explains earlier provider outcomes.
6. Each source is requested at most once. A block stops that source; the next separate source may still run. If no source returns a result, a block exits `4`, a provider/network failure exits `5`, and no matching data exits `2`. There are no browser fallbacks or alternate routes to a blocked source.

One provider supplies each returned estimate. The plugin never averages or merges visits values across sources.

The result cache is best-effort. If its directory cannot be read or written, the lookup continues and adds a cache warning to the result.

Runtime files use `./.ihav_space/ihav-web-visit-counter/` relative to the process working directory. `IHAV_CACHE_DIR` and `--cache-dir` can override the cache location.

## Result kinds

- `estimate`: either WebTrafficChecker's modelled `monthlyVisits` value and analysis timestamp, or TrafficLens's formatted visit string and scrape timestamp. A stale TrafficLens value remains marked stale. Neither provider has a measured error interval in this release.
- `rank_only`: Tranco rank with `monthly_visits: null`.
- No matching data and no provider error: CLI exit `2`; it does not invent a number.
