# Terms and risks

## WebTrafficChecker

The source-terms review found that WebTrafficChecker's terms allow automated access when it remains reasonable, does not circumvent rate limits, and does not place an unreasonable load on its infrastructure. The same terms prohibit using the API to build a substantially similar or competing service and allow the operator to suspend access for abusive or excessive use.

The maintainers chose to use the endpoint without first asking the operator. This is an accepted project risk, not a determination that the plugin is outside the competing-service clause. No documented request limits were found. V0 reduces load with one request per lookup and a 24-hour local cache, identifies itself with a descriptive User-Agent, attributes the source, and stops on access refusal or a challenge. It makes no retry or alternate-route attempt.

## Tranco

Tranco supplies a composite rank list whose upstream data sources have different licenses. The plugin downloads the latest list locally and does not bundle it in the repository. Public access does not establish unrestricted commercial redistribution or use rights. Review the current provenance and applicable upstream terms for your use.

## Data handling

The normalized requested domain is sent to WebTrafficChecker when there is no fresh cached result. The plugin does not send cookies, account credentials, or API keys. Runtime files are stored in `.ihav_space/ihav-web-visit-counter/` below the current working directory and may contain queried domains and provider responses. Set `IHAV_CACHE_DIR` or `--cache-dir` to change the location; remove the directory to clear local records.

## Blocks

HTTP 401, 403, 429, and recognizable challenge content stop that source. The plugin may continue to the separate Tranco fallback once; if no fallback result is available, a block exits `4`. No browser, stealth layer, CAPTCHA solver, proxy rotation, fake User-Agent, or alternate route to the blocked source is used. Network and download failures use exit code `5` when no usable provider result is returned.
