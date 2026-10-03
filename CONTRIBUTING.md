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

## Pull requests

Describe the provider, its metric definition, date semantics, terms, coverage, cached fields and known errors. Include fixture provenance and a synthetic CLI example when output changes.
