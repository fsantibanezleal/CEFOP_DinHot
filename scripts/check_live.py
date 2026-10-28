#!/usr/bin/env python3
"""T9: after a deploy, the live site is this build (failure classes 2, 13, 21).

Checks the deployed origin, retrying for a bounded time while the host's cache catches up:
  - build.json names the expected commit (the site serves the build that was pushed, not an older one);
  - every standard route answers 200 with HTML, with and without its trailing slash;
  - a file that does not exist answers 404 (no fallback that would hide a missing artifact);
  - the artifact index answers JSON.
Stdlib only. Usage: python scripts/check_live.py --url https://<site>/ --sha <commit> [--tries 20 --wait 15]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

ROUTES = ("", "introduction", "app", "methodology", "implementation", "experiments", "benchmark")


def get(url: str) -> tuple[int, str, bytes]:
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "caos-check-live"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.headers.get("content-type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("content-type", "") if e.headers else "", e.read() if e.fp else b""
    except urllib.error.URLError as e:
        return 0, str(e.reason), b""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--tries", type=int, default=20)
    p.add_argument("--wait", type=float, default=15.0)
    a = p.parse_args()
    base = a.url if a.url.endswith("/") else a.url + "/"

    for attempt in range(1, a.tries + 1):
        status, _, body = get(f"{base}build.json?t={time.time():.0f}")
        sha = ""
        if status == 200:
            try:
                sha = json.loads(body).get("sha", "")
            except ValueError:
                sha = ""
        if sha == a.sha:
            break
        print(f"live: attempt {attempt}: build.json answered {status} with sha {sha[:12] or 'none'}; waiting")
        time.sleep(a.wait)
    else:
        print(f"live: the site never served build {a.sha[:12]} ({a.tries} attempts)")
        return 1

    errs: list[str] = []
    for route in ROUTES:
        forms = [route] if route == "" else [route, route + "/"]
        for form in forms:
            status, ctype, _ = get(base + form)
            if status != 200 or "text/html" not in ctype:
                errs.append(f"/{form} answered {status} {ctype}")
    status, _, _ = get(base + "__caos_live_missing__.json")
    if status != 404:
        errs.append(f"a missing file answered {status}, not 404")
    status, ctype, _ = get(base + "data/manifests/index.json")
    if status != 200 or "json" not in ctype:
        errs.append(f"the artifact index answered {status} {ctype}")
    for e in errs:
        print(f"live: {e}")
    if not errs:
        print(f"live: OK, {base} serves build {a.sha[:12]}; every route answers, a missing file is a 404")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
