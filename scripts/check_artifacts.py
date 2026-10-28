"""Validate CONTRACT 2 on disk (the pipeline -> web artifact contract): the index references every case; each
manifest exists; each artifact it names exists, is non-empty, and its byte size matches the manifest; each lane
matches its gate verdict. A manifest names one artifact (`artifact: {path, bytes}`, the lane and gate at the
manifest's top level) or several (`artifacts: [{path, bytes, lane, gate, ...}]`, one per variant baked apart, each
with its own lane and gate). Stdlib only (runs in CI WITHOUT installing the package). Exit non-zero on any drift.

Used by scripts/smoke.* and by .github/workflows/ci.yml, the mechanical guard that a product can't regress to
serving artifacts that don't match their manifests.
Usage: python scripts/check_artifacts.py [repo_root]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
MANIFESTS = DERIVED / "manifests"


def artifacts_of(m: dict) -> list[dict]:
    """The artifact entries a manifest names, each with the lane and gate it is judged by."""
    if isinstance(m.get("artifacts"), list):
        return [dict(a) for a in m["artifacts"]]
    if isinstance(m.get("artifact"), dict):
        return [{**m["artifact"], "lane": m.get("lane"), "gate": m.get("gate", {})}]
    return []


def declared_absent() -> set[str]:
    """The paths the readiness document declares absent: the ``missing`` of every row whose state is ``partial``
    (catalog, Missing-data states). Empty when the document is absent or unreadable: nothing is tolerated then."""
    try:
        rows = json.loads((DERIVED / "readiness.json").read_text(encoding="utf-8")).get("contracts", [])
        return {m for r in rows if isinstance(r, dict) and r.get("state") == "partial"
                for m in r.get("missing", []) if isinstance(m, str)}
    except (OSError, ValueError, AttributeError):
        return set()


def main() -> int:
    idx_path = MANIFESTS / "index.json"
    if not idx_path.exists():
        print(f"FAIL: missing {idx_path} (run scripts/precompute.sh first)")
        return 1
    index = json.loads(idx_path.read_text(encoding="utf-8"))
    errs: list[str] = []
    tolerated = declared_absent()
    n_art = 0
    n_declared_absent = 0

    def absent(rel: str, what: str, path: Path) -> None:
        """A declared-absent path is a warning (a partial bake builds); any other absence is drift."""
        nonlocal n_declared_absent
        if rel in tolerated:
            n_declared_absent += 1
            print(f"WARN: {what} {rel} is absent, as readiness.json declares (partial)")
        else:
            errs.append(f"missing {what}: {path}")

    for rel in index.get("files", []) or []:
        f = DERIVED / rel
        if not f.is_file() or f.stat().st_size == 0:
            if rel in tolerated and not f.exists():
                n_declared_absent += 1
                print(f"WARN: file {rel} is absent, as readiness.json declares (partial)")
            else:
                errs.append(f"declared by the index but missing or empty: {f}")
    for entry in index.get("cases", []):
        mp = DERIVED / entry["manifest_path"]
        if not mp.exists():
            absent(entry["manifest_path"], "manifest", mp)
            continue
        m = json.loads(mp.read_text(encoding="utf-8"))
        arts = artifacts_of(m)
        if not arts:
            errs.append(f"{entry['case_id']}: the manifest names no artifact (artifact or artifacts)")
        for a in arts:
            n_art += 1
            art = DERIVED / a["path"]
            if not art.exists():
                absent(a["path"], "artifact", art)
                continue
            size = art.stat().st_size
            if size != a.get("bytes"):
                errs.append(f"byte drift {art}: manifest={a.get('bytes')} disk={size}")
            if size == 0:
                errs.append(f"empty artifact: {art}")
            if (a.get("gate") or {}).get("lane") != a.get("lane"):
                errs.append(f"lane/gate mismatch: {entry['case_id']} {a['path']}")
    if errs:
        print("CONTRACT 2 DRIFT:")
        for e in errs:
            print("  -", e)
        return 1
    print(f"CONTRACT 2 OK: {len(index.get('cases', []))} cases, {n_art} artifacts, manifests <-> artifacts consistent"
          + (f" ({n_declared_absent} declared absent)." if n_declared_absent else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
