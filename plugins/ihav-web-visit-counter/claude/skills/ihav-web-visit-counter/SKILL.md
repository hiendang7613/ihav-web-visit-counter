---
name: ihav-web-visit-counter
description: Monthly visits estimates for a website URL or domain, including the analysis date, source, available traffic history and country shares. Use when someone asks how much traffic a website gets, how many visits it receives, or which countries its audience comes from.
argument-hint: <website>
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/core/ihav-web-visit-counter/scripts/visits.py *)
---

# ihav-web-visit-counter

Use the bundled command for every traffic lookup. Do not estimate a number from memory, search snippets or the domain name.

Run with `python3` on macOS/Linux or `py -3` on Windows. Replace the argument with the website URL or domain supplied by the user:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/core/ihav-web-visit-counter/scripts/visits.py" "$ARGUMENTS"
```

On Windows, use:

```bash
py -3 "${CLAUDE_PLUGIN_ROOT}/core/ihav-web-visit-counter/scripts/visits.py" "$ARGUMENTS"
```

Use the website URL or domain supplied by the user. If the command returns a rank-only result, say that monthly visits are unknown. If it returns an estimate, call it a provider-modelled estimate and preserve its analysis date, source, country shares and available history. Do not add a confidence range: this release has no measured error interval.

If the command reports HTTP 401, 403, 429, a challenge, or a network error, report the message as returned. The CLI may use its separate Tranco fallback once. Do not retry the stopped source. Do not try another browser, endpoint, proxy, or route to that source.

See [shared answer rules](../../../core/ihav-web-visit-counter/references/answer-rules.md) for wording and evidence rules.
