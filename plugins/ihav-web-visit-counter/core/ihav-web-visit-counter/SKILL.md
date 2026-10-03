---
name: ihav-web-visit-counter
description: Monthly visits estimates for a website URL or domain, including the analysis date, source, available traffic history and country shares. Use when someone asks how much traffic a website gets, how many visits it receives, or which countries its audience comes from.
---

# ihav-web-visit-counter

Run the bundled command for each lookup. Replace `<skill-directory>` with the installed directory that contains this `SKILL.md`:

On macOS/Linux, use `python3`. On Windows, use `py -3`:

```bash
python3 <skill-directory>/scripts/visits.py example.com
```

```powershell
py -3 <skill-directory>/scripts/visits.py example.com
```

Replace `example.com` with the URL or domain supplied by the user. Add `--json` when you need the structured result contract. Do not estimate a number from memory, search snippets or the domain name.

If the command returns a rank-only result, say that monthly visits are unknown. If it returns an estimate, call it a provider-modelled estimate and preserve its analysis date, source, country shares and available history. Do not add a confidence range: this release has no measured error interval.

If the command reports HTTP 401, 403, 429, a challenge, or a network error, report the message as returned. The CLI may use its separate Tranco fallback once. Do not retry the stopped source. Do not try another browser, endpoint, proxy, or route to that source.

See [shared answer rules](references/answer-rules.md) for wording and evidence rules.
