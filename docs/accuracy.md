# Accuracy notes

## Provider estimates

WebTrafficChecker says its value is modelled from rank and public signals. TrafficLens may return a scraped or upstream estimate; it returned one rounded value marked stale in the retained probe. The observed responses did not provide a measured confidence interval. The project has not established comparable owner-published total-visits anchors or holdout error. This release therefore displays no error range.

WebTrafficChecker's raw `analyzed_at` timestamp is retained. TrafficLens's raw `scraped_at` timestamp is retained and displayed; when the provider marks its response stale, the CLI also displays “stale”. Neither timestamp is treated as the date range of measured visits or a confirmed reporting month. Formatted TrafficLens values stay approximate strings and are not expanded to exact-looking integers. The plugin does not invent a date window.

## History and geography

WebTrafficChecker history snapshots come from `historicalRanks` entries that include a valid date and a positive visits value. If several snapshots fall in the same month, the latest dated snapshot is kept. Each point retains its calendar date and is not presented as that month's total. Only returned points are rendered; the source has not been shown to provide a complete 12-month visits history. TrafficLens rank history is never presented as visits history. Country shares are copied from the provider response and identified as provider estimates.

Only one source answers each lookup. The plugin never averages or merges separate estimates. The retained GitHub probes differed by about 29.8%, but they used different sources and timestamps, and the TrafficLens value was stale. This is not an accuracy measurement or a confidence interval.

## Tranco rank fallback

Tranco rank is a popularity signal, not a visit count. No rank-to-visits curve or empirical error interval is implemented. If neither WebTrafficChecker nor TrafficLens has a usable visit count, and the domain appears in Tranco, the result is `rank_only` with `monthly_visits: null` and a note explaining the fallback. TrafficLens's rank-only payload is skipped and does not change this rule.
