# Terms and risks

## WebTrafficChecker

The source-terms review found that WebTrafficChecker's terms allow automated access when it remains reasonable, does not circumvent rate limits, and does not place an unreasonable load on its infrastructure. The same terms prohibit using the API to build a substantially similar or competing service and allow the operator to suspend access for abusive or excessive use.

The maintainers chose to use the endpoint without first asking the operator. This is an accepted project risk, not a determination that the plugin is outside the competing-service clause. No documented request limits were found. V0 reduces load with one request per lookup and a 24-hour local cache, identifies itself with a descriptive User-Agent, attributes the source, and stops on access refusal or a challenge. It makes no retry or alternate-route attempt.

## Tranco

Tranco supplies a composite rank list whose upstream data sources have different licenses. The plugin downloads the latest list locally and does not bundle it in the repository. Public access does not establish unrestricted commercial redistribution or use rights. Review the current provenance and applicable upstream terms for your use.

## TrafficLens

TrafficLens's terms restrict extraction at scale without consent and limit reproduction and commercial exploitation of its content. Its terms and privacy page name SimilarWeb among its upstream data sources. That creates possible upstream terms risk in addition to TrafficLens's own restrictions; we have not established a license that authorizes reproducing its estimates in a public plugin. The maintainers chose TrafficLens as a conditional, partial-coverage middle fallback after a bounded probe returned a stale GitHub estimate and only rank data for Python. This choice records an accepted product risk; it is not legal clearance or a claim that every domain will have a visit count.

The adapter makes one request per lookup only after WebTrafficChecker has no usable estimate, caches estimate results for 24 hours, attributes TrafficLens, preserves rounded strings, and shows its scrape date and stale marker. It does not retry, scrape alternate pages, or use a browser. A TrafficLens rank-only response is skipped in favor of the separate Tranco rank fallback.

## Data handling

The normalized requested domain is sent to WebTrafficChecker when there is no fresh estimate cache. If it returns no usable estimate, the domain is sent once to TrafficLens. If neither supplies a visit estimate, the plugin downloads Tranco's public list and searches it locally. The plugin does not send cookies, account credentials, or API keys. Runtime files are stored in `.ihav_space/ihav-web-visit-counter/` below the current working directory and may contain queried domains and provider responses. Set `IHAV_CACHE_DIR` or `--cache-dir` to change the location; remove the directory to clear local records. Rank-only results are not cached.

## Blocks

HTTP 401, 403, 429, and recognizable challenge content stop that source. The plugin may continue to the next separate source once; it never retries or changes routes for the blocked source. If a later provider returns an estimate or rank, that result is returned with the prior outcome noted. If no fallback result is available, a block exits `4`. No browser, stealth layer, CAPTCHA solver, proxy rotation, fake User-Agent, or alternate route to the blocked source is used. Network and download failures use exit code `5` when no usable provider result is returned.
