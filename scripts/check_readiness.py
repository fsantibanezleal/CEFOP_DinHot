"""The committed readiness document (data/derived/readiness.json) is a pure function of docs/contracts/catalog.md and
the repository: recompute it and compare. Exit 0 and ``readiness: current`` when it matches; exit 1 naming each
differing entry and the command that regenerates it. Stdlib only (CI runs it with nothing installed; ADR-0074).

Usage: python scripts/check_readiness.py [judged_root]

The judged root (default: this checkout) holds only what is judged: the catalog, VERSION, the authored inputs and the baked
documents. The readiness provider (``readiness_provider`` of scripts/local/workflow.json) and the engine
(data-pipeline/pipeline) always come from the checkout that holds this script, the product root, so a generation stage, which
holds neither, is admitted by the product's own rules, and code planted in a judged root is never loaded (0.15.001, #102, #91)."""
from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
FIX = "python data-pipeline/run.py readiness"


def custom_provider(root):
    """An explicit read-only validate(root) hook, never an inferred template engine."""
    config_path = root / "scripts/local/workflow.json"
    if not config_path.is_file():
        return None
    config = json.loads(config_path.read_text(encoding="utf-8"))
    name = config.get("readiness_provider")
    if name is None:
        if config.get("product_admission"):
            raise ValueError("Custom product admission requires an explicit readiness_provider script")
        return None
    if not isinstance(name, str) or not name or Path(name).is_absolute() or ".." in Path(name).parts:
        raise ValueError("readiness_provider must name a Python script inside the product")
    path = root / name
    if path.suffix != ".py" or not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError("readiness_provider is missing or escapes the product")
    for component in (path, *path.parents):
        if component == root:
            break
        if component.is_symlink() or getattr(component, "is_junction", lambda: False)():
            raise ValueError("readiness_provider cannot contain redirected paths")
    spec = importlib.util.spec_from_file_location("product_readiness_provider", path)
    provider = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(provider)
    validate = getattr(provider, "validate", None)
    if not callable(validate):
        raise ValueError("readiness_provider must implement validate(root)")
    return validate


def differences(fresh: dict, committed: dict) -> list[str]:
    out = []
    for key in ("schema", "product_version", "catalog_sha256"):
        if fresh.get(key) != committed.get(key):
            out.append(f"{key}: committed {committed.get(key)!r}, computed {fresh.get(key)!r}")
    old = {e.get("id"): e for e in committed.get("contracts", [])}
    new = {e["id"]: e for e in fresh["contracts"]}
    for rid in sorted(old.keys() | new.keys()):
        if rid not in new:
            out.append(f"contracts/{rid}: committed, but not a catalog row")
        elif rid not in old:
            out.append(f"contracts/{rid}: a catalog row, but not committed")
        elif old[rid] != new[rid]:
            fields = sorted(k for k in old[rid].keys() | new[rid].keys() if old[rid].get(k) != new[rid].get(k))
            out.append(f"contracts/{rid}: {', '.join(fields)} differ (committed state {old[rid].get('state')!r}, "
                       f"computed {new[rid]['state']!r})")
    if [e.get("id") for e in committed.get("contracts", [])] != [e["id"] for e in fresh["contracts"]] and not out:
        out.append("contracts: the order differs from the catalog's")
    return out


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE
    try:
        # the product root decides how a root is judged; the judged root is only data
        provider = custom_provider(HERE)
        if provider is not None:
            if provider(root) is False:
                raise ValueError("Custom product admission returned false")
            print("readiness: current (declared product provider)")
            return 0
        sys.path.insert(0, str(HERE / "data-pipeline"))
        from pipeline.core import readiness
    except Exception as exc:  # Provider errors are refusals, never an absent-template import crash.
        print(f"readiness: invalid admission provider\n  {exc}")
        return 1
    derived = root / "data" / "derived"
    path = derived / "readiness.json"
    try:
        fresh = readiness.compute(repo_root=root, derived_root=derived, models_dir=root / "models")
    except ValueError as exc:  # a catalog the rules do not accept: nothing can be published from it
        print(f"readiness: invalid catalog\n  {exc}")
        return 1
    if not path.is_file():
        print(f"readiness: stale\n  {path} is absent\n  fix: {FIX}")
        return 1
    committed_bytes = path.read_bytes()
    diffs = differences(fresh, json.loads(committed_bytes.decode("utf-8")))
    expected = json.dumps(fresh, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if not diffs and committed_bytes != expected:
        diffs = ["bytes: same content, different serialisation"]
    if diffs:
        print("readiness: stale")
        for d in diffs:
            print(f"  {d}")
        print(f"  fix: {FIX}")
        return 1
    print("readiness: current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
