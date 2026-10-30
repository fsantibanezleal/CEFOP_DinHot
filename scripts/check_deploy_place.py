#!/usr/bin/env python3
"""One deploy place, decided first (ADR-0055, the 2026-10-04 base requirements).

deploy/TARGET names the place: `pages` or `vps`. A product carries the files of that place only: a Pages product has
the Pages workflow and no VPS unit or site file; a VPS product has its unit and site files and no Pages workflow.
The template keeps both on-ramps until instantiation (its sentinel is present), so only TARGET is checked there.
Stdlib only. Usage: python scripts/check_deploy_place.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    target_file = ROOT / "deploy" / "TARGET"
    if not target_file.exists():
        print("deploy place: deploy/TARGET is missing (pages or vps, decided before the first deploy)")
        return 1
    target = target_file.read_text(encoding="utf-8").strip()
    if target not in {"pages", "vps"}:
        print(f"deploy place: deploy/TARGET is {target!r}, not pages or vps")
        return 1
    if (ROOT / ".template-source").exists():
        print(f"deploy place: OK, {target} (template: both on-ramps kept until instantiation)")
        return 0
    pages_workflow = (ROOT / ".github" / "workflows" / "deploy-pages.yml").exists()
    vps_files = sorted(p.name for p in (ROOT / "deploy").glob("*") if p.suffix in {".service", ".nginx"})
    errs = []
    if target == "pages":
        if not pages_workflow:
            errs.append("the target is pages and .github/workflows/deploy-pages.yml is missing")
        if vps_files:
            errs.append(f"the target is pages and VPS files remain: {', '.join(vps_files)}")
    else:
        if pages_workflow:
            errs.append("the target is vps and the Pages workflow remains (two deploy places)")
        if not vps_files:
            errs.append("the target is vps and deploy/ holds no unit or site file")
    for e in errs:
        print(f"deploy place: {e}")
    if not errs:
        print(f"deploy place: OK, {target} only")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
