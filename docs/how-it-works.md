# How it works

The plugin has a shared Python standard-library core and thin Claude Code and Codex skills. Both skills call the same CLI and use the same JSON result contract.

1. Input is parsed as a URL or host. A leading `www.` is removed, IDNs are converted to ASCII, and other subdomains are preserved. The plugin does not guess a public-suffix boundary.
2. A normalized-domain estimate is read from the 24-hour cache, if present. Rank-only results are never cached.
3. The primary adapter makes one GET to WebTrafficChecker's linked JSON endpoint. A positive `traffic.monthlyVisits` is accepted only when `analyzedAt` is also present and parseable.
4. If WebTrafficChecker has no usable estimate, is blocked, or fails, the middle adapter makes one GET to TrafficLens's public Worker route. It accepts only a positive visit count and a parseable `scrapedAt`. The original formatted string is preserved; `source=stale` is rendered as stale. Its scrape timestamp is not a reporting month.
5. A TrafficLens rank-only response or invalid/missing count is skipped. If neither visits provider returns a usable estimate, the Tranco adapter downloads the current top-1M archive only when its local daily-list cache is stale. Rank lookup then happens locally. A successful fallback result explains earlier provider outcomes.
6. Each source is requested at most once. A block stops that source; the next separate source may still run. If no source returns a result, a block exits `4`, a provider/network failure exits `5`, and no matching data exits `2`. There are no browser fallbacks or alternate routes to a blocked source.

One provider supplies each returned estimate. The plugin never averages or merges visits values across sources.

The result cache is best-effort. If its directory cannot be read or written, the lookup continues and adds a cache warning to the result. Since estimate results from every provider are cached, a cached TrafficLens estimate can delay rechecking a recovered WebTrafficChecker for up to 24 hours. This is an accepted trade-off to reduce repeat requests to TrafficLens.

If WebTrafficChecker definitively returns no usable result and later providers also return no result, exit code `2` is used even when a later source fails; each later failure appears in `error.notes` in JSON mode. Exit codes `4` and `5` are used when the primary is blocked or fails and no fallback returns data; `5` also covers an unexpected internal error. A blocked provider is never retried.

Runtime files use `./.ihav_space/ihav-web-visit-counter/` relative to the process working directory. `IHAV_CACHE_DIR` and `--cache-dir` can override the cache location.

## Result kinds

- `estimate`: `monthly_visits` is an integer for WebTrafficChecker and `null` for TrafficLens. `monthly_visits_text` is the display string: comma-grouped for WebTrafficChecker or TrafficLens's returned rounded string. The result also carries the source-specific analysis/scrape timestamp; a stale TrafficLens value remains marked stale. Neither provider has a measured error interval in this release.
- `rank_only`: Tranco rank with `monthly_visits: null` and `monthly_visits_text: null`.
- No matching data and no provider error: CLI exit `2`; it does not invent a number.

## JSON contract

JSON success and error objects both include the integer `contract_version` and a top-level `providers` array. Version `1` describes the result and error fields before these additions. Version `2` adds `contract_version: 2` and structured provider outcomes without changing the existing result fields or exit codes.

Each provider entry has this shape:

```json
{
  "name": "webtrafficchecker",
  "outcome": "blocked",
  "http_status": 403,
  "detail": "The source refused this request."
}
```

`name` is one of `webtrafficchecker`, `trafficlens`, or `tranco`. Entries follow provider order. The CLI includes attempted providers and marks later providers `skipped` after a usable result. `outcome` is `ok`, `no_data`, `blocked`, `failed`, `skipped`, or `cached`. `detail` is short human-readable text; consumers must branch on the structured fields, not its wording.

`http_status` is the HTTP status returned by the provider API. It never uses a nested target-site status such as a DNS status. A challenge page can be `blocked` with HTTP `200`; a transport failure has `http_status: null`. A cache hit has one `cached` entry for the provider that supplied the value. Its `fetched_at` and any available `http_status` refer to the original successful fetch. The cache entry does not repeat an earlier provider block as a current outcome.

Error JSON keeps the existing `error` object and its `notes` strings. It adds the same top-level `contract_version` and `providers` fields. Invalid input has an empty provider array. Exit codes remain `0`, `2`, `4`, `5`, and `64` with their existing meanings.
