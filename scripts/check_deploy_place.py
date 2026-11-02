#!/usr/bin/env python3
"""One declared deploy place (ADR-0055).

The template writes a single-word ``pages`` or ``vps`` sentinel. An instantiated product may instead write a small
record with one ``target:`` field when its selected VPS topology combines a static site and a separately bounded
service. A Pages deployment must contain only its Pages workflow; VPS deployments must contain a service unit and
nginx site configuration. The template keeps both on-ramps while ``.template-source`` is present.

Stdlib only. Usage: python scripts/check_deploy_place.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACES = {"pages", "vps", "vps-static+vps-service"}


def declared_target(text: str) -> tuple[str | None, str | None]:
    """Return (target, error) for a plain sentinel or a structured record with exactly one target field."""
    raw = text.strip()
    if raw in {"pages", "vps"}:
        return raw, None
    fields = []
    for line in text.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() == "target":
            fields.append(value.split("#", 1)[0].strip())
    if len(fields) != 1 or not fields[0]:
        return None, "structured deploy/TARGET must declare exactly one non-empty target field"
    return fields[0], None


def main() -> int:
    target_file = ROOT / "deploy" / "TARGET"
    if not target_file.is_file():
        print("deploy place: deploy/TARGET is missing (pages or vps, decided before the first deploy)")
        return 1
    target, error = declared_target(target_file.read_text(encoding="utf-8"))
    if error:
        print(f"deploy place: {error}")
        return 1
    if target not in PLACES:
        print(f"deploy place: unsupported target {target!r}; expected pages, vps, or vps-static+vps-service")
        return 1
    if (ROOT / ".template-source").exists():
        print(f"deploy place: OK, {target} (template: both on-ramps kept until instantiation)")
        return 0

    pages_workflow = (ROOT / ".github" / "workflows" / "deploy-pages.yml").is_file()
    deploy = ROOT / "deploy"
    service_files = sorted(p.name for p in deploy.glob("*.service") if p.is_file())
    site_files = sorted(
        p.name for p in deploy.iterdir() if p.is_file() and (p.suffix == ".nginx" or p.name.endswith(".nginx.tls"))
    )
    errors = []
    if target == "pages":
        if not pages_workflow:
            errors.append("the target is pages and .github/workflows/deploy-pages.yml is missing")
        if service_files or site_files:
            errors.append(f"the target is pages and VPS files remain: {', '.join(service_files + site_files)}")
    else:
        if pages_workflow:
            errors.append("the target is VPS and the Pages workflow remains (two deploy places)")
        if not service_files:
            errors.append("the target is VPS and deploy/ holds no service unit")
        if not site_files:
            errors.append("the target is VPS and deploy/ holds no nginx site configuration")
    for error in errors:
        print(f"deploy place: {error}")
    if not errors:
        print(f"deploy place: OK, {target} only")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
