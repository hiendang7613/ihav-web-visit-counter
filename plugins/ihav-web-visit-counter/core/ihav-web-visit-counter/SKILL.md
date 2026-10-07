---
name: ihav-web-visit-counter
description: Monthly visits estimates for a website URL or domain, including source-specific dates, stale labels, available traffic history and country shares. Use when someone asks how much traffic a website gets, how many visits it receives, or which countries its audience comes from.
---

# ihav-web-visit-counter

Run the bundled command for each lookup. Replace `<skill-directory>` with the installed directory that contains this `SKILL.md`:

Run it as one command. Keep the script path and website argument quoted as data.
Do not prepend `echo`, add pipes, or combine it with other shell commands.

On macOS/Linux, use `python3`. On Windows, use `py -3`:

```bash
python3 "<skill-directory>/scripts/visits.py" "example.com"
```

```powershell
py -3 "<skill-directory>/scripts/visits.py" "example.com"
```

Replace `example.com` with the URL or domain supplied by the user. Add `--json` when you need the structured result contract. Do not estimate a number from memory, search snippets or the domain name.

If the command returns a rank-only result, say that monthly visits are unknown. If it returns an estimate, call it a third-party estimate and preserve the selected provider, source link, timestamp, country shares and visits history actually returned. WebTrafficChecker's analysis date is not a reporting month. TrafficLens's scrape date is not a reporting month; preserve its formatted count string as approximate, and keep the `stale` label when present. Do not add a confidence range: this release has no measured error interval.

In JSON, `monthly_visits` is always an integer or `null`; `monthly_visits_text` carries the display string. When an estimate has `monthly_visits: null`, use `monthly_visits_text` for its displayed value.

The CLI returns at most one provider's estimate per lookup. Never average or merge values. If TrafficLens returns rank-only data, let the CLI's Tranco result stand; do not turn ranks into visits or present rank history as visits history. TrafficLens is a partial fallback and its terms name SimilarWeb among upstreams, so do not imply its estimate is owner analytics or that reuse terms have been cleared.

If the command reports HTTP 401, 403, 429, a challenge, or a network error, report the message as returned. The CLI may continue to the next separate provider once. Do not retry the stopped source. Do not try another browser, endpoint, proxy, or route to that source.

See [shared answer rules](references/answer-rules.md) for wording and evidence rules.
