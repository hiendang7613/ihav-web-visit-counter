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

**A traffic estimate is not private analytics.** The plugin tries WebTrafficChecker, then TrafficLens for domains with a returned visit value, then a Tranco rank. TrafficLens coverage is partial and its sample was stale; every number keeps its source and date. No source has an independently measured error interval.

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

Estimate results are cached for 24 hours; rank-only results are not cached. Runtime files are written under `./.ihav_space/ihav-web-visit-counter/` in the current working directory. Set `IHAV_CACHE_DIR` or pass `--cache-dir` to use another location. Add `.ihav_space/` to your project's `.gitignore` if you do not want runtime data tracked.

## What the result means

| Kind | What you receive | What it does not mean |
|---|---|---|
| `estimate` | One provider's monthly-visits value, source link and returned country shares/history. WebTrafficChecker supplies a number and `analyzedAt`; TrafficLens may supply a rounded string such as `631.0M` and `scrapedAt`. | It is not website-owner analytics. WebTrafficChecker's `analyzedAt` is an analysis timestamp; TrafficLens's `scrapedAt` is a scrape timestamp, not a reporting month. A stale TrafficLens value stays marked stale. Neither source publishes a measured error interval in the observed responses. |
| `rank_only` | A rank from Tranco's downloaded daily top-1M list | A rank is not visits. `monthly_visits` remains `null`. |

TrafficLens's rank-only response is skipped; it does not replace the final Tranco rank result or become visits. The plugin never converts rank to visits, averages or merges provider estimates, or creates a 12-month series when a provider has only a few history points. Each lookup returns one provider's result.

## How it works

1. Normalize the URL or domain while preserving subdomains other than a leading `www.`.
2. Return the local 24-hour result cache when it is fresh.
3. Ask WebTrafficChecker once. A usable `monthlyVisits` value becomes `kind: estimate` with the raw `analyzed_at` timestamp.
4. If WebTrafficChecker has no usable estimate, is blocked, or fails, ask TrafficLens once. A valid `monthlyVisits` value becomes a separate `kind: estimate`; its formatted value stays a string, its `period` stays `null`, and its scrape date and stale state are shown. A TrafficLens ranking-only response is skipped.
5. If neither source returns a visit estimate, try the Tranco fallback once. Its result is `kind: rank_only`; it never becomes a visit count. The output says why the fallback was used.
6. Stop a source on HTTP 401, 403, 429, or challenge content. The plugin does not retry that source or use browser routes or block workarounds. One provider answers each lookup; results are never averaged or merged.

## Accuracy, honestly

WebTrafficChecker describes the number as a modelled estimate based on ranking and public signals. The endpoint response observed for v0 includes `monthlyVisits`, `analyzedAt`, a provider rank, geography shares, and some `historicalRanks` points. TrafficLens sometimes returns a rounded visits string and scrape timestamp, but the retained probe was stale and did not include a reporting month. Neither source has a measured error interval, and our probe did not establish a comparable owner-published visits anchor. We therefore show no percentage error band or calibrated rank-to-visits estimate.

WebTrafficChecker's `analyzed_at` timestamp is shown as “analyzed YYYY-MM-DD”. TrafficLens's `scraped_at` timestamp is shown as “scraped YYYY-MM-DD”; when its payload says `source=stale`, the output also says “stale”. Neither timestamp proves which start and end dates the provider used to compute `monthlyVisits`. TrafficLens may return a rounded string rather than an exact integer. History contains only points actually returned by the provider; it is not guaranteed to cover 12 months. Country shares are provider estimates, not site analytics.

Tranco is a popularity ranking. If neither visits provider returns a usable estimate and the domain appears in its list, the plugin shows the rank and leaves visits unknown. If all three providers return no matching data, the CLI exits `2`. If the sources fail, the CLI preserves the first provider error when no fallback result is available.

## Data sources and terms

| Source | Role | Use in this plugin | Notes |
|---|---|---|---|
| [WebTrafficChecker](https://webtrafficchecker.com/) | Primary | Public JSON endpoint; modelled `monthlyVisits`, `analyzedAt`, rank, country shares and any history returned | Terms allow reasonable, low-volume automated use but prohibit using its API to build a substantially similar or competing service. This plugin proceeds without asking the operator, as decided by the maintainers. The clause may apply to this plugin; limits are not documented, and access may be suspended. We cache estimate results for 24 hours, send one request per lookup, attribute the source and stop if access is refused. |
| [TrafficLens](https://trafficlens.io/) | Middle fallback | Keyless public Worker endpoint; may return a formatted `monthlyVisits` string, `scrapedAt`, a stale marker and country shares. Rank-only responses are skipped. | Partial coverage: a retained probe returned a stale GitHub value but only a Tranco rank for Python. TrafficLens terms restrict extraction at scale and reproduction/commercial use; its terms and privacy page name SimilarWeb among upstreams, so upstream terms may also apply. Public access does not establish permission to reproduce this data in a plugin. We retain the raw rounded string, mark stale data, cache estimates for 24 hours, make one request and stop on refusal. |
| [Tranco](https://tranco-list.eu/) | Final fallback | Download the daily top-1M list and perform a local rank lookup | Rank only, not visits. The composite list includes upstream data with different licenses. The plugin downloads it at runtime and does not bundle the list; users should check the source license for their intended use. The per-domain API is not used. |

Public availability is not the same as owner analytics or an unrestricted data license. This plugin is independent and is not affiliated with any listed source. If a source blocks or refuses access, the plugin reports it and stops that source. It does not use stealth browsers, proxies, fake user agents, CAPTCHA solving, or alternate routes to bypass a block. One provider supplies each returned estimate; the plugin never averages results.

See [how it works](docs/how-it-works.md), [accuracy notes](docs/accuracy.md), and [terms and risks](docs/terms-and-risks.md).

## Privacy and local files

The requested domain is sent to WebTrafficChecker. If it returns no usable visit estimate, the domain may also be sent once to TrafficLens. If neither supplies visits, the plugin downloads Tranco's public rank list and searches it locally. It does not send prompts, cookies, API keys, or account credentials. A 24-hour estimate cache and downloaded list live in `.ihav_space/ihav-web-visit-counter/` under the current working directory; remove that folder to clear them. Rank-only results are not cached.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please include a saved response fixture for provider changes; tests must not contact live sites.

## License

MIT. See [LICENSE](LICENSE).
