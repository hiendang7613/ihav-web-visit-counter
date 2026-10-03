# Data sources

## WebTrafficChecker

The primary adapter calls `https://webtrafficchecker.com/api/traffic?domain=<domain>` once per cache miss. The observed JSON contains `traffic.monthlyVisits`, `analyzedAt`, `traffic.globalRank`, `geography`, and sometimes `historicalRanks`. A response with no positive visit count or no valid `analyzedAt` is treated as no usable estimate.

The provider's own methodology describes modelled estimates derived from ranking and public signals. It is not site-owner analytics. The returned `analyzedAt` is an analysis timestamp; its month is not assumed to be the visits reporting period. The CLI uses `period: null`, keeps the raw ISO timestamp in `analyzed_at`, and renders “analyzed YYYY-MM-DD”.

The terms allow reasonable, low-volume automated access but prohibit building a substantially similar or competing service with the API. The maintainers decided to proceed without contacting the operator. That accepted risk is described in [terms and risks](terms-and-risks.md). The adapter sends a descriptive User-Agent, caches for 24 hours, makes one request, and stops on a block.

## TrafficLens

The middle adapter makes one keyless GET to the public Worker route `https://traffic-lens-api.admin-d10.workers.dev/api/analyze/<domain>` after WebTrafficChecker returns no usable visit estimate. A usable response must identify the requested domain, include a positive `monthlyVisits` value and a parseable `scrapedAt` timestamp. In the result, `monthly_visits` is `null` and the provider's original formatted value is preserved in `monthly_visits_text`; the renderer marks it approximate and does not expand the rounded value to an exact integer. The result has `kind: estimate`, `period: null`, `analyzed_at: null`, and `scraped_at` copied from the payload. If `source=stale`, the output says “stale” and shows the scrape date.

The retained probe returned a stale rounded GitHub visits value with a scrape date; a separate Python probe returned only `dataKind=ranking`, rank source Tranco, and no visit value. The captured value remains in a parser-test fixture and is not repeated here as a public example. A ranking-only response, missing/invalid count, or missing/invalid scrape timestamp is skipped; it is not relabeled as visits. No reporting month, complete monthly visits history, or measured error interval was observed. Country shares are included only when valid fields are present and rounded to four decimal places in JSON.

This adapter has partial, unverified coverage and is not a validated total-visits source for arbitrary domains. TrafficLens terms restrict extraction at scale and reproduction/commercial use; its terms and privacy page name SimilarWeb among its upstreams. The plugin attributes TrafficLens, caches estimates for 24 hours, requests it once after a missing primary estimate, and stops on access refusal. These safeguards do not establish reuse permission; see [terms and risks](terms-and-risks.md).

## Tranco

The final fallback downloads `https://tranco-list.eu/top-1m.csv.zip` at most once per 24 hours and checks the domain locally. A same-host HTTPS redirect is permitted for this list download; cross-host and HTTP downgrade redirects are rejected. It does not call the per-domain Tranco API. A matching row returns only its rank; it never becomes monthly visits. The reported rank date is the retrieval date because the latest-list archive does not expose a publication date in the CSV captured by this adapter. This rank is used only when neither visits provider returns a usable estimate.

The downloaded list is not bundled in this repository. Its composite signals have different upstream licenses, so users should check the current list provenance and license for their intended use.
