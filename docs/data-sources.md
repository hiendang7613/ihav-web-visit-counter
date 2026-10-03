# Data sources

## WebTrafficChecker

The primary adapter calls `https://webtrafficchecker.com/api/traffic?domain=<domain>` once per cache miss. The observed JSON contains `traffic.monthlyVisits`, `analyzedAt`, `traffic.globalRank`, `geography`, and sometimes `historicalRanks`. A response with no positive visit count or no valid `analyzedAt` is treated as no usable estimate.

The provider's own methodology describes modelled estimates derived from ranking and public signals. It is not site-owner analytics. The returned `analyzedAt` is an analysis timestamp; its month is not assumed to be the visits reporting period. The CLI uses `period: null`, keeps the raw ISO timestamp in `analyzed_at`, and renders “analyzed YYYY-MM-DD”.

The terms allow reasonable, low-volume automated access but prohibit building a substantially similar or competing service with the API. The maintainers decided to proceed without contacting the operator. That accepted risk is described in [terms and risks](terms-and-risks.md). The adapter sends a descriptive User-Agent, caches for 24 hours, makes one request, and stops on a block.

## Tranco

The fallback downloads `https://tranco-list.eu/top-1m.csv.zip` at most once per 24 hours and checks the domain locally. A same-host HTTPS redirect is permitted for this list download; cross-host and HTTP downgrade redirects are rejected. It does not call the per-domain Tranco API. A matching row returns only its rank; it never becomes monthly visits. The reported rank date is the retrieval date because the latest-list archive does not expose a publication date in the CSV captured by this adapter.

The downloaded list is not bundled in this repository. Its composite signals have different upstream licenses, so users should check the current list provenance and license for their intended use.
