"""The committed readiness document (data/derived/readiness.json) is a pure function of docs/contracts/catalog.md and
the repository: recompute it and compare. Exit 0 and ``readiness: current`` when it matches; exit 1 naming each
differing entry and the command that regenerates it. Stdlib only (CI runs it with nothing installed; ADR-0074).

Usage: python scripts/check_readiness.py [repo_root]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "data-pipeline"))

from pipeline.core import readiness  # noqa: E402

FIX = "python data-pipeline/run.py readiness"


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
