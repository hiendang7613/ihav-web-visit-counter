# Contributing

Thanks for helping improve the plugin.

## Before changing a provider

- Keep each source in its own adapter and preserve the result contract.
- Do not treat rank, pageviews, visitors or sessions as total visits without a clear definition.
- Keep attribution, source date and metric period semantics visible.
- Check current source terms before adding automated access or redistributing data.
- Do not add stealth, fingerprint spoofing, proxy rotation, CAPTCHA solving or alternate routes for blocked requests.

## Tests

Use saved response fixtures only. Tests must not contact live websites or depend on a key.

```bash
python -m unittest discover -s tests -v
```

CI also runs `tests/consumer_compatibility.py` on Python 3.11 against actual public
Leaderboards 0.2.2 and Competitor Search 0.1.0 code, pinned to full commit hashes in
`.github/workflows/ci.yml`. It checks rounded estimates, rank-only results, weight
allocation, payload provenance and blocked-source no-retry behavior. Socket access
is disabled in the runner and its Python children; provider responses are fixtures.
The no-data case comes from the actual Counter CLI and verifies that exit `2`
does not block a later host in Competitor Search.

Run the same checks against local checkouts or installed plugin directories:

```bash
python tests/consumer_compatibility.py \
  --leaderboards-plugin /path/to/ihav-leaderboards/plugins/ihav-leaderboards \
  --competitor-plugin /path/to/ihav-competitor-search/plugins/ihav-competitor-search
```

`--counter-plugin` can select an installed Counter directory; its default is this
checkout's plugin. The WebTrafficChecker input is the saved `github.json` fixture;
the rounded `1.2K`, rank and blocked results are synthetic test cases. When updating
a CI consumer pin, verify the public commit and run the checks against that exact
source. Testing a newer local development version does not change CI's pinned scope.

## Pull requests

Describe the provider, its metric definition, date semantics, terms, coverage, cached fields and known errors. Include fixture provenance and a synthetic CLI example when output changes.
