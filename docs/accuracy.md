# Accuracy notes

## WebTrafficChecker estimate

The value is labeled `estimate` because WebTrafficChecker says it is modelled from rank and public signals. The observed endpoint did not provide a measured confidence interval. The project has not established a comparable owner-published total-visits anchor or holdout error. V0 therefore displays no error range.

The raw `analyzed_at` timestamp is retained. It is not treated as the date range of the measured visits or a confirmed reporting month. The plugin does not invent a date window.

## History and geography

History snapshots come from `historicalRanks` entries that include a valid date and a positive visits value. If several snapshots fall in the same month, the latest dated snapshot is kept. Each point retains its calendar date and is not presented as that month's total. Only returned points are rendered; the source has not been shown to provide a complete 12-month visits history. Country shares are copied from the provider's `geography` field and identified as provider estimates.

## Tranco fallback

Tranco rank is a popularity signal, not a visit count. No rank-to-visits curve or empirical error interval is implemented in v0. If WebTrafficChecker has no usable estimate, is blocked, or fails, and the domain appears in Tranco, the result is `rank_only` with `monthly_visits: null` and a note explaining the fallback.
