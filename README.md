<p align="center">
  <img src="assets/hero.svg" alt="Website traffic estimate shown with its analysis date, source and country shares" width="100%">
</p>

<h1 align="center">ihav-web-visit-counter</h1>

<p align="center">Ask your coding agent how much traffic a website gets. See the estimate, its date and its source. If no estimate is available, see a rank instead of a guess.</p>

<p align="center">
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-4F46E5.svg"></a>
  <img alt="Python standard library only" src="https://img.shields.io/badge/runtime-Python%20stdlib-0F172A.svg">
  <img alt="Claude Code and Codex" src="https://img.shields.io/badge/works%20with-Claude%20Code%20%7C%20Codex-F59E0B.svg">
</p>

**A traffic estimate is not private analytics.** This plugin uses one public modelled estimate source and a rank-only fallback. Every number keeps its source; v0 has no independently measured error interval.

[Install](#install) · [Demo](#demo) · [Usage](#usage) · [Accuracy](#accuracy-honestly) · [Sources and terms](#data-sources-and-terms)

## Install

Requires Python 3.9 or later. The plugin core uses only the Python standard library. It does not need a paid account, API key, or browser.

Claude Code:

```bash
claude plugin marketplace add hiendang7613/ihav-web-visit-counter
claude plugin install ihav-web-visit-counter@ihav-web-visit-counter
```

Codex:

```bash
codex plugin marketplace add hiendang7613/ihav-web-visit-counter
codex plugin add ihav-web-visit-counter@ihav-web-visit-counter
```

Restart the host after installation. Ask in plain language, or use `/ihav-web-visit-counter example.com` in Claude Code. If another command owns the short name, use `/ihav-web-visit-counter:ihav-web-visit-counter`. In Codex, mention `$ihav-web-visit-counter:ihav-web-visit-counter` or ask in plain language.

## Demo

**Synthetic example.** These figures are invented to show the output format. They are not a provider result and do not describe `example.com`.

```text
example.com
  ~2,430,000 estimated monthly visits · analyzed 2026-09-11
  Error range: not independently measured
  History snapshots 2026-08-13 → 2026-09-11  ▁█
  Top countries: US 41.0% · IN 9.0% · GB 6.0%
  Source: WebTrafficChecker · https://webtrafficchecker.com/traffic/example.com
  Note: This is a provider-modelled estimate, not the website owner's analytics.
```

`assets/hero.svg` and `assets/demo.svg` use the same clearly labelled synthetic example.

![Synthetic terminal result example](assets/demo.svg)

## Usage

Ask your agent:

- “How many monthly visits does `example.com` get?”
- “Show the traffic history for `example.com`.”
- “Which countries appear in the estimate for `example.com`?”

From a terminal, run the bundled command from the plugin skill directory:

```bash
python3 scripts/visits.py example.com
python3 scripts/visits.py https://www.example.com/pricing --json
```

On Windows, use `py -3` in place of `python3`.

The JSON output follows a stable result contract. Expected exit codes:

| Code | Meaning |
|---:|---|
| `0` | Estimate or rank result returned |
| `2` | Neither source returned a matching result and neither reported a provider error |
| `4` | Access refused, rate-limited, or a challenge was detected; the source stops without retry |
| `5` | Network/download failure or provider error when no fallback succeeds |
| `64` | Invalid input or command arguments |

The result cache lasts 24 hours. Runtime files are written under `./.ihav_space/ihav-web-visit-counter/` in the current working directory. Set `IHAV_CACHE_DIR` or pass `--cache-dir` to use another location. Add `.ihav_space/` to your project's `.gitignore` if you do not want runtime data tracked.

## What the result means

| Kind | What you receive | What it does not mean |
|---|---|---|
| `estimate` | WebTrafficChecker's modelled monthly visits number, its `analyzedAt` timestamp, source link, and any country shares or history it returned | It is not website-owner analytics. The provider publishes no measured error interval in the observed response. `analyzedAt` is an analysis timestamp, not a confirmed reporting month. |
| `rank_only` | A rank from Tranco's downloaded daily top-1M list | A rank is not visits. `monthly_visits` remains `null`. |

The current fallback does not convert rank to visits. It does not create a 12-month series when the provider has only a few history points.

## How it works

1. Normalize the URL or domain while preserving subdomains other than a leading `www.`.
2. Return the local 24-hour result cache when it is fresh.
3. Ask WebTrafficChecker once. A usable monthlyVisits value becomes `kind: estimate` with the raw `analyzed_at` timestamp.
4. If WebTrafficChecker has no usable estimate, is blocked, or fails, try the separate Tranco fallback once. The result is `kind: rank_only`; it never becomes a visit count. The output says why the fallback was used.
5. Stop a source on HTTP 401, 403, 429, or challenge content. The plugin does not retry that source or use browser routes or block workarounds.

## Accuracy, honestly

WebTrafficChecker describes the number as a modelled estimate based on ranking and public signals. The endpoint response observed for v0 includes `monthlyVisits`, `analyzedAt`, a provider rank, geography shares, and some `historicalRanks` points. Its source terms do not publish an error interval, and our probe did not establish a comparable owner-published visits anchor. We therefore show no percentage error band or calibrated rank-to-visits estimate.

The `analyzed_at` timestamp is shown as “analyzed YYYY-MM-DD”. It does not prove which start and end dates the provider used to compute `monthlyVisits`. History contains only points actually returned by the provider; it is not guaranteed to cover 12 months. Country shares are provider estimates, not site analytics.

Tranco is a popularity ranking. If the primary estimate is absent and the domain appears in its list, the plugin shows the rank and leaves visits unknown. If both sources return no matching data, the CLI exits `2`. If the sources fail, the CLI preserves the first provider error when no fallback result is available.

## Data sources and terms

| Source | Role | Use in this plugin | Notes |
|---|---|---|---|
| [WebTrafficChecker](https://webtrafficchecker.com/) | Primary | Public JSON endpoint; modelled `monthlyVisits`, `analyzedAt`, rank, country shares and any history returned | Terms allow reasonable, low-volume automated use but prohibit using its API to build a substantially similar or competing service. This plugin proceeds without asking the operator, as decided by the maintainers. The clause may apply to this plugin; limits are not documented, and access may be suspended. We cache results for 24 hours, send one request per lookup, attribute the source and stop if access is refused. |
| [Tranco](https://tranco-list.eu/) | Fallback | Download the daily top-1M list and perform a local rank lookup | Rank only, not visits. The composite list includes upstream data with different licenses. The plugin downloads it at runtime and does not bundle the list; users should check the source license for their intended use. The per-domain API is not used. |

Public availability is not the same as owner analytics or an unrestricted data license. This plugin is independent and is not affiliated with either source. If a source blocks or refuses access, the plugin reports it and stops that source. It does not use stealth browsers, proxies, fake user agents, CAPTCHA solving, or alternate routes to bypass a block.

See [how it works](docs/how-it-works.md), [accuracy notes](docs/accuracy.md), and [terms and risks](docs/terms-and-risks.md).

## Privacy and local files

The requested domain is sent to WebTrafficChecker. When its estimate is unavailable, the plugin downloads Tranco's public rank list and searches it locally. It does not send prompts, cookies, API keys, or account credentials. A 24-hour result cache and downloaded list live in `.ihav_space/ihav-web-visit-counter/` under the current working directory; remove that folder to clear them.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please include a saved response fixture for provider changes; tests must not contact live sites.

## License

MIT. See [LICENSE](LICENSE).
