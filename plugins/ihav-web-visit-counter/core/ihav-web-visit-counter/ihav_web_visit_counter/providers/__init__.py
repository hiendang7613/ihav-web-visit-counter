"""Provider adapters in lookup order."""

from __future__ import annotations

from . import trafficlens, tranco, webtrafficchecker


# Keep the source chain explicit so replacing the fallback only changes its adapter.
PROVIDERS = (webtrafficchecker, trafficlens, tranco)
