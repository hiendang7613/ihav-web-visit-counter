# Answer rules

- Run the bundled CLI; never fill missing traffic with model memory or a search-result snippet.
- `estimate` means WebTrafficChecker's provider-modelled monthly visits number. It is not owner analytics and has no independently measured error interval in v0.
- `period` is `null` in v0. `analyzed_at` is the provider's analysis timestamp and is shown as `analyzed YYYY-MM-DD`; it is not a reporting month or a confirmed visits measurement window.
- Keep the source name and link beside every number. Preserve any country shares and history returned by the provider.
- `rank_only` means the Tranco daily-list rank is known and visits are unknown. A rank is not visits; never convert it into a number.
- If the CLI stops on HTTP 401, 403, 429, challenge, or network failure, report that outcome. The CLI may use the separate Tranco fallback once; it must not retry the stopped source, switch its route, use a browser or work around a block.
- Mention that WebTrafficChecker's terms restrict substantially similar or competing services. This project accepts the risk for low-volume, cached lookups; access may still be suspended.
