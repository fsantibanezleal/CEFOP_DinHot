"""The benchmark stage (catalog row benchmark-results owner): runs the protocol of ``pipeline/benchmark/`` and writes
``<derived root>/benchmark/results.json``. Offline, resumable per group, never in CI."""
from __future__ import annotations

from pathlib import Path

from ..benchmark import protocol


def run(derived_root: str | Path, *, seeds: int = 20, workers: int = 12, reduced: bool = False,
        geometries: list[str] | None = None, methods: list[str] | None = None, resume: bool = False, **kw) -> dict:
    return protocol.run(derived_root, seeds=seeds, workers=workers, reduced=reduced, geometries=geometries, methods=methods,
                        resume=resume, **kw)
