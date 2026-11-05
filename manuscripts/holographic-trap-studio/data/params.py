#!/usr/bin/env python3
"""Read the keyword defaults of every method of the engine and write ``params.json``.

The technical report states the parameters of each method with the value the code uses. They are read here from the signature of
each method's ``run`` function and from the ``SPEC`` of its module, so the report types none of them. ``extract_methods.py`` turns
the file into the macros and the parameter table of the report.

Run from the repository root with the pipeline environment (it imports the engine, which needs numpy):

    .venv-pipeline/Scripts/python.exe manuscripts/holographic-trap-studio/data/params.py
"""
from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

COMMON = {"setup", "target", "device", "budget", "rng", "init"}   # the interface arguments every method takes


def encode(v):
    """A JSON value for a default: numbers and strings as they are, a tuple as a list, ``None`` as null."""
    if isinstance(v, (tuple, list)):
        return [encode(x) for x in v]
    if isinstance(v, (int, float, str, bool)) or v is None:
        return v
    return repr(v)


def collect() -> dict:
    pkg = importlib.import_module("pipeline.model.holo.methods")
    out: dict[str, dict] = {}
    for sub in pkgutil.iter_modules(pkg.__path__):
        if not sub.ispkg:
            continue
        subpkg = importlib.import_module(f"{pkg.__name__}.{sub.name}")
        for mod in pkgutil.iter_modules(subpkg.__path__):
            if mod.name.startswith("_"):
                continue
            m = importlib.import_module(f"{subpkg.__name__}.{mod.name}")
            spec, run = getattr(m, "SPEC", None), getattr(m, "run", None)
            if spec is None or run is None:
                continue
            params = {}
            for name, p in inspect.signature(run).parameters.items():
                if name in COMMON or p.default is inspect.Parameter.empty:
                    continue
                params[name] = encode(p.default)
            out[spec.id] = {"name": spec.name, "family": spec.family, "lane": spec.lane, "targets": list(spec.targets),
                            "dims": list(spec.dims), "module": f"{sub.name}/{mod.name}", "params": params}
    return dict(sorted(out.items()))


def main() -> int:
    methods = collect()
    (HERE / "params.json").write_text(json.dumps({"schema": "dinhot.manuscript-params/v1", "methods": methods}, indent=1,
                                                 ensure_ascii=False), encoding="utf-8")
    print(f"wrote params.json: {len(methods)} methods, {sum(len(v['params']) for v in methods.values())} defaults")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
