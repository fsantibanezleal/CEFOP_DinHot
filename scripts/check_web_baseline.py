#!/usr/bin/env python3
"""T7: the web baseline a reader never sees go wrong until it does (failure classes 1, 8, 18, 24, 25).

Static checks on frontend/src, against the installed shell (node_modules/@fasl-work/caos-app-shell):
  - every var(--x) the app names is defined, by the shell's stylesheet or by the app's own CSS (an undefined token
    renders as nothing, silently);
  - every class written in a className string has a rule in the shell or in the app's CSS;
  - no app CSS rule restyles a shell component: a rule fails when the subject of its selector (the last compound)
    names a class the shell lists as a component, or names only shell modifiers (`.on` alone styles every shell
    chip); a modifier joined to the app's own class (`.my-row.on`) passes (reserved-classes.json, shell 0.8.0);
  - the shell is pinned exactly (`"@fasl-work/caos-app-shell": "0.8.0"`, never a range), and the installed package is
    that version (ADR-0078 section 5: the build that was gated is the build that ships);
  - a shell entry the source imports comes with its stylesheet (`styles.css` for the shell, `chart.css` for
    `/chart`): this guard reads both from the installed package, so a class the browser never receives a rule for
    passed as styled, and a chart without `chart.css` has no height and is never drawn (CAOS_Fragmenta, 2026-10-08);
  - no App tab named after the plumbing (contract, trace, learned models, bring your own data);
  - no toLocaleString() without a locale, and no toFixed() in a view (numbers go through formatNumber);
  - no <img> of an .svg (an image cannot read the page's theme tokens);
  - no requestAnimationFrame outside the shell's usePausedViz (a loop at rest burns the reader's battery).
Run after `npm ci` in frontend/. Stdlib only. Usage: python scripts/check_web_baseline.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "src"
SHELL = ROOT / "frontend" / "node_modules" / "@fasl-work" / "caos-app-shell"

VAR_USE = re.compile(r"var\(\s*(--[a-zA-Z0-9-]+)")
VAR_DEF = re.compile(r"(--[a-zA-Z0-9-]+)\s*:")
CLASS_RULE = re.compile(r"\.(-?[_a-zA-Z][_a-zA-Z0-9-]*)")
CLASSNAME = re.compile(r"className=(?:\"([^\"]*)\"|'([^']*)'|\{\s*['\"]([^'\"]*)['\"]\s*\})")
TAB_LABEL = re.compile(r"\blabel:\s*\{\s*en:\s*'([^']*)'")
SHELL_IMPORT = re.compile(r"""(?:from|import)\s+['"](@fasl-work/caos-app-shell(?:/[a-z]+)?)['"]""")
# The stylesheet each shell entry needs, and what a reader sees without it.
STYLESHEETS = {
    "@fasl-work/caos-app-shell": ("styles.css", "the shell renders unstyled"),
    "@fasl-work/caos-app-shell/chart": ("chart.css", "a filling chart has no height and is never drawn"),
}
BANNED_TABS = re.compile(r"\b(contract|trace|learned models?|bring your own)\b", re.I)


def css_files() -> list[Path]:
    return sorted(p for p in SRC.rglob("*.css"))


def code_files() -> list[Path]:
    return sorted(p for p in SRC.rglob("*") if p.suffix in {".ts", ".tsx"} and not p.name.endswith(".test.ts"))


def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


RULE = re.compile(r"([^{}]+)\{[^{}]*\}")
EXACT = re.compile(r"^\d+\.\d+\.\d+$")


def selectors(css: str) -> list[str]:
    """Every selector of every style rule, inner rules of @media and @supports included."""
    out: list[str] = []
    for m in RULE.finditer(css):
        head = m.group(1).strip()
        head = head.split("{")[-1].strip()
        if not head or head.startswith("@") or re.match(r"^(from|to|\d+%)", head):
            continue
        out.extend(s.strip() for s in re.split(r",(?![^(]*\))", head) if s.strip())
    return out


def subject_classes(selector: str) -> list[str]:
    """The classes of a selector's subject, the last compound, outside :is()/:not()/:where() arguments."""
    flat = re.sub(r"\([^()]*\)", "", selector)
    parts = [p for p in re.split(r"\s*[>+~]\s*|\s+", flat.strip()) if p]
    last = parts[-1] if parts else ""
    return re.findall(r"\.(-?[_a-zA-Z][_a-zA-Z0-9-]*)", last)


def restyles(selector: str, components: set[str], modifiers: set[str]) -> str | None:
    """Why a selector restyles the shell, or None."""
    classes = subject_classes(selector)
    hit = [c for c in classes if c in components]
    if hit:
        return f"restyles the shell component .{hit[0]}"
    if classes and all(c in modifiers for c in classes):
        return f"styles the shell modifier .{classes[0]} on its own (join it to a class of the app's own)"
    return None


def main() -> int:
    if not SHELL.is_dir():
        print("web baseline: the shell is not installed (run npm ci in frontend/ first)")
        return 1
    shell_css = "".join(strip_comments((SHELL / f).read_text(encoding="utf-8")) for f in ("styles.css", "chart.css"))
    reserved_doc = json.loads((SHELL / "reserved-classes.json").read_text(encoding="utf-8"))
    # 0.8.0 splits the list; a 0.7 list is all components
    components = set(reserved_doc.get("components", reserved_doc["classes"]))
    modifiers = set(reserved_doc.get("modifiers", []))
    app_css = "".join(strip_comments(p.read_text(encoding="utf-8")) for p in css_files())
    defined_vars = set(VAR_DEF.findall(shell_css)) | set(VAR_DEF.findall(app_css))
    styled = set(CLASS_RULE.findall(shell_css)) | set(CLASS_RULE.findall(app_css))
    errs: list[str] = []

    for f in css_files():
        rel = f.relative_to(ROOT).as_posix()
        for sel in selectors(strip_comments(f.read_text(encoding="utf-8"))):
            why = restyles(sel, components, modifiers)
            if why:
                errs.append(f"{rel}: `{sel}` {why} (reserved-classes.json)")

    pkg = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    pin = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}.get("@fasl-work/caos-app-shell")
    installed = json.loads((SHELL / "package.json").read_text(encoding="utf-8")).get("version")
    if not pin or not EXACT.match(pin):
        errs.append(f"frontend/package.json pins the shell as {pin!r}: pin it exactly (\"{installed}\"), never a range")
    elif pin != installed:
        errs.append(f"the installed shell is {installed}, the pin is {pin}: run npm ci")

    sources = "".join(p.read_text(encoding="utf-8") for p in code_files() + css_files())
    entries = set(SHELL_IMPORT.findall(sources))
    for entry, (sheet, effect) in STYLESHEETS.items():
        if entry in entries and f"@fasl-work/caos-app-shell/{sheet}" not in sources:
            errs.append(
                f"the source imports {entry} and never '@fasl-work/caos-app-shell/{sheet}': "
                f"import it in the entry file ({effect})"
            )

    for f in code_files() + css_files():
        rel = f.relative_to(ROOT).as_posix()
        text = f.read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), 1):
            for var in VAR_USE.findall(line):
                if var not in defined_vars:
                    errs.append(f"{rel}:{n}: var({var}) is not defined by the shell or the app")
            if f.suffix == ".css":
                continue
            for groups in CLASSNAME.findall(line):
                for cls in " ".join(groups).split():
                    if cls not in styled:
                        errs.append(f"{rel}:{n}: class {cls!r} has no rule in the shell or the app CSS")
            if re.search(r"\.toLocaleString\(\s*\)", line):
                errs.append(f"{rel}:{n}: toLocaleString() without a locale; use formatNumber or useFormat")
            if f.suffix == ".tsx" and ".toFixed(" in line:
                errs.append(f"{rel}:{n}: toFixed() in a view; use formatNumber or useFormat (locale and absent values)")
            if re.search(r"<img\b[^>]*\.svg", line):
                errs.append(f"{rel}:{n}: an <img> of an SVG cannot read the theme; inline it (?raw)")
            if "requestAnimationFrame" in line:
                errs.append(f"{rel}:{n}: requestAnimationFrame outside usePausedViz")
        if "/workbench/" in rel:
            for label in TAB_LABEL.findall(text):
                if BANNED_TABS.search(label):
                    errs.append(f"{rel}: the App tab {label!r} is named after the plumbing, not the question")

    for e in errs:
        print(f"web baseline: {e}")
    if not errs:
        print(f"web baseline: OK ({len(code_files())} source files, {len(defined_vars)} tokens, {len(styled)} classes)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
