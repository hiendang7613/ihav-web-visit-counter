# Accuracy notes

## Provider estimates

WebTrafficChecker says its value is modelled from rank and public signals. TrafficLens may return a scraped or upstream estimate; it returned one rounded value marked stale in the retained probe. The observed responses did not provide a measured confidence interval. The project has not established comparable owner-published total-visits anchors or holdout error. This release therefore displays no error range.

WebTrafficChecker's positive `monthlyVisits` is not enough to establish usable data. The adapter rejects a response when `traffic.isRanked` is false, `traffic.globalRank` is zero, null or missing, or the category is `Unranked Website`. A live check returned a placeholder value of 65 and a default country split for a nonexistent domain; neither value is shown. The lookup continues to TrafficLens and then Tranco. When no source has usable data, the CLI exits `2` with no visit number. Low-traffic or unranked domains receive a number only if a downstream visits provider returns one.

WebTrafficChecker's raw `analyzed_at` timestamp is retained. TrafficLens's raw `scraped_at` timestamp is retained and displayed; when the provider marks its response stale, the CLI also displays “stale”. Neither timestamp is treated as the date range of measured visits or a confirmed reporting month. Formatted TrafficLens values stay approximate strings and are not expanded to exact-looking integers. The plugin does not invent a date window.

## History and geography

WebTrafficChecker history snapshots come from `historicalRanks` entries that include a valid date and a positive visits value. If several snapshots fall in the same month, the latest dated snapshot is kept. Each point retains its calendar date and is not presented as that month's total. Only returned points are rendered; the source has not been shown to provide a complete 12-month visits history. TrafficLens rank history is never presented as visits history. Country shares are copied from the provider response and identified as provider estimates.

Only one source answers each lookup. The plugin never averages or merges separate estimates. The retained GitHub probes differed by about 29.8%, but they used different sources and timestamps, and the TrafficLens value was stale. This is not an accuracy measurement or a confidence interval.

Estimate results from every provider are cached for 24 hours. A cached TrafficLens estimate can therefore delay rechecking a recovered WebTrafficChecker for up to 24 hours. This is an accepted trade-off to reduce repeat requests to TrafficLens.

## Tranco rank fallback

Tranco rank is a popularity signal, not a visit count. No rank-to-visits curve or empirical error interval is implemented. If neither WebTrafficChecker nor TrafficLens has a usable visit count, and the domain appears in Tranco, the result is `rank_only` with `monthly_visits: null` and a note explaining the fallback. TrafficLens's rank-only payload is skipped and does not change this rule.
