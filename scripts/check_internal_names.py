#!/usr/bin/env python3
"""The tier names never reach a reader (CAOS_MANAGE ``conventions/method-tiers-and-manuscripts.md`` section 0, template 0.14.000).

"Classical", "state of the art", "beyond the state of the art", SOTA, beyond-SOTA, the claim ids ``BS-<n>``, "method tiers"
and the Spanish "enfoque clásico", "estado del arte" and "más allá del estado del arte" are the names the SDD, the plans and the
gates use to sort a product's methods (Felipe, 2026-10-30: "that terms can never reach the manuscripts or the app titles or
sections"). A reader sees each method by its name. The check fails, naming the file, the place and the words, on a tier name in

- a notebook (``notebooks/**/*.ipynb``): its file or folder name; its ``caos.title``; its markdown, the References section excepted (a cited work keeps
  its own title); the comments and the text strings of its code cells (titles, labels, legends); its text outputs;
- a notebook index (``notebooks/**/README.md``), the References section excepted;
- a manuscript source (``manuscripts/**``): its file or folder name; ``.tex``, ``.md`` and ``.txt`` outside the bibliography (a ``thebibliography``
  environment, ``.bib`` files, a References section), the text of an ``.svg`` figure, the strings of a ``.py`` figure script;
- ``product.json``: the title of each ``manuscripts`` entry;
- ``README.md``, the References section excepted;
- the app: the string values of ``content/**/*.json`` and ``frontend/src/**/*.json``, and the strings and JSX text of
  ``frontend/src/**/*.ts(x)`` (tests and generated files excepted).

In a title or a heading (a markdown heading, ``caos.title``, a LaTeX ``\\title``, ``\\section``, ``\\caption``, a manuscript
title, a JSON value under a ``title``, ``heading``, ``label``, ``name``, ``tab`` or ``caption`` key) the bare words "classical",
"clásico" and "tier" are tier names too. What stays: the SDD and ``docs/`` (internal design records), code identifiers, a string
that is a lowercase key (``"sota"``), the ``caos`` metadata ids (``methods``, ``beyond``), ``product.json`` ``covers``, a cited
work's title in References or the bibliography, and a line that carries the marker ``internal-name-ok`` (a reviewed use whose
words mean something else, such as "classical mechanics").

Static, standard library only. Usage: ``python scripts/check_internal_names.py [repo_root]``. Exit 0 clean, 1 on any finding.
"""
from __future__ import annotations

import io
import json
import re
import sys
import tokenize
from pathlib import Path

RULE = "CAOS_MANAGE conventions/method-tiers-and-manuscripts.md section 0"
MARK = "internal-name-ok"
# a tier name wherever a reader sees it
PHRASES = re.compile(
    r"state[\s~-]+of[\s~-]+(?:the[\s~-]+)?art"
    r"|\bsota\b"
    r"|\bestado\s+del\s+arte\b"
    r"|\bclassical\s+(?:tiers?|approach(?:es)?|methods?|models?|baselines?)\b"
    r"|\b(?:enfoques?|m[ée]todos?|modelos?)\s+cl[áa]sic[oa]s?\b"
    r"|\b(?:method|three)\s+tiers?\b|\btiers?\s+of\s+methods?\b"
    r"|\bBS-\d+\b",
    re.IGNORECASE,
)
# in a title or a heading the bare words are tier names too
HEADING_WORDS = re.compile(r"\bclassical\b|\bcl[áa]sic[oa]s?\b|\btiers?\b", re.IGNORECASE)
# a tier name in a file or folder name: the name shows on GitHub, in the index and in every link to it
SLUG = re.compile(r"state-of-(?:the-)?art|(?:^|[-_])sota(?:[-_]|$)|classical-(?:tiers?|approach(?:es)?|methods?|models?|baselines?)", re.IGNORECASE)
MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$")
REFERENCES = re.compile(r"^\s{0,3}#{1,6}\s+(references|referencias|bibliography|bibliografía)\s*$", re.IGNORECASE)
FENCE = re.compile(r"^\s*(```+|~~~+)")
TEX_HEADING = re.compile(r"\\(?:chapter|(?:sub)*section|paragraph|caption|title)\*?\s*[\[{]")
TEX_COMMENT = re.compile(r"(?<!\\)%.*$")
KEY_LIKE = re.compile(r"^[a-z][a-z0-9_]*$")
TITLE_KEYS = {"title", "heading", "label", "name", "tab", "caption"}
JS_STRING = re.compile(r"""'((?:\\.|[^'\\\n])*)'|"((?:\\.|[^"\\\n])*)"|`((?:\\.|[^`\\])*)`""")
JSX_TEXT = re.compile(r">([^<>{}]*[A-Za-z][^<>{}]*)<")
SVG_TEXT = re.compile(r">([^<>]+)<")
MANUSCRIPT_SUFFIXES = {".tex", ".md", ".txt", ".svg", ".py"}


def words(text: str, heading: bool = False) -> list[str]:
    """The tier names in ``text``; in a heading the bare words too."""
    found = [m.group(0) for m in PHRASES.finditer(text)]
    if heading:
        found += [m.group(0) for m in HEADING_WORDS.finditer(text)]
    return found


def finding(rel: str, where: str, found: list[str]) -> str:
    names = ", ".join(sorted({f.lower() for f in found}))
    return f"{rel}: {where}: the tier name {names!r} (internal; name the method instead, {RULE})"


def path_findings(root: Path, path: Path, base: Path) -> list[str]:
    """A tier name in the name of a notebook or a manuscript file, or of a folder under ``base``."""
    found = [m.group(0) for part in path.relative_to(base).with_suffix("").parts for m in SLUG.finditer(part)]
    return [finding(path.relative_to(root).as_posix(), "file name", found)] if found else []


def scan_lines(rel: str, lines: list[str], *, heading_of, where="line") -> list[str]:
    """Each line, and a phrase that wraps onto the next line; ``heading_of(line)`` says whether a line is a heading. A line
    blanked by a filter (a bibliography, a fence) is never joined to its neighbour."""
    out: list[str] = []
    for k, line in enumerate(lines):
        if not line.strip() or MARK in line:
            continue
        found = words(line, heading_of(line))
        nxt = lines[k + 1] if k + 1 < len(lines) and MARK not in lines[k + 1] else ""
        if nxt.strip():
            joined, cut = line.rstrip() + " " + nxt.lstrip(), len(line.rstrip())
            found += [m.group(0) for m in PHRASES.finditer(joined) if m.start() < cut < m.end()]
        if found:
            out.append(finding(rel, f"{where} {k + 1}", found))
    return out


def markdown_text(lines: list[str], state: tuple[bool, int] = (False, 0)) -> tuple[list[str], tuple[bool, int]]:
    """The lines a reader reads as prose and headings: fenced blocks (commands, code) and a References section (with its
    subsections) are blanked. ``state`` (inside a fence, the level of the References heading or 0) carries across the
    cells of a notebook."""
    fenced, refs = state
    kept: list[str] = []
    for line in lines:
        if FENCE.match(line):
            fenced = not fenced
            kept.append("")
            continue
        if fenced:
            kept.append("")
            continue
        m = re.match(r"^\s{0,3}(#{1,6})\s", line)
        if m and not (refs and len(m.group(1)) > refs):
            refs = len(m.group(1)) if REFERENCES.match(line) else 0
        kept.append("" if refs else line)
    return kept, (fenced, refs)


def is_md_heading(line: str) -> bool:
    return bool(MD_HEADING.match(line))


def code_text(source: str) -> list[tuple[int, str]]:
    """(line, text) of the comments and the strings of a Python cell; a lowercase key string is code, not text."""
    clean = "\n".join("" if ln.lstrip().startswith(("%", "!")) else ln for ln in source.splitlines())
    out: list[tuple[int, str]] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(clean + "\n").readline):
            if tok.type == tokenize.COMMENT:
                out.append((tok.start[0], tok.string))
            elif tok.type == tokenize.STRING or tok.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
                body = re.sub(r"^[rbuRBUfF]*('''|\"\"\"|'|\")|('''|\"\"\"|'|\")$", "", tok.string)
                if not KEY_LIKE.match(body):
                    out.append((tok.start[0], body))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        out = [(n, ln) for n, ln in enumerate(clean.splitlines(), 1)]
    return out


def output_text(cell: dict) -> str:
    parts: list[str] = []
    for o in cell.get("outputs", []):
        parts.append("".join(o.get("text", "")))
        data = o.get("data", {})
        for kind in ("text/plain", "text/markdown", "text/html"):
            v = data.get(kind, "")
            parts.append("".join(v) if isinstance(v, list) else str(v))
    return "\n".join(parts)


def notebook_findings(root: Path, path: Path) -> list[str]:
    rel = path.relative_to(root).as_posix()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"{rel}: not readable as a notebook ({e})"]
    out: list[str] = []
    title = str(((doc.get("metadata") or {}).get("caos") or {}).get("title", ""))
    if (found := words(title, heading=True)):
        out.append(finding(rel, "caos.title", found))
    state = (False, 0)
    for i, cell in enumerate(doc.get("cells", []), 1):
        source = "".join(cell.get("source", ""))
        if cell.get("cell_type") == "markdown":
            kept, state = markdown_text(source.splitlines(), (False, state[1]))
            out += scan_lines(rel, kept, heading_of=is_md_heading, where=f"cell {i}, line")
        elif cell.get("cell_type") == "code":
            for n, text in code_text(source):
                if MARK not in text and (found := words(text)):
                    out.append(finding(rel, f"cell {i}, code line {n}", found))
            if (found := words(output_text(cell))):
                out.append(finding(rel, f"cell {i}, output", found))
    return out


def tex_findings(rel: str, text: str) -> list[str]:
    """A LaTeX source without its comments and its bibliography."""
    kept: list[str] = []
    in_bib = False
    for line in text.splitlines():
        line = line if MARK in line else TEX_COMMENT.sub("", line)
        if "\\begin{thebibliography}" in line:
            in_bib = True
        if in_bib or re.search(r"\\bibliography\{|\\printbibliography|\\bibitem", line):
            in_bib = in_bib and "\\end{thebibliography}" not in line
            kept.append("")
            continue
        kept.append(line)
    return scan_lines(rel, kept, heading_of=lambda ln: bool(TEX_HEADING.search(ln)))


def markdown_findings(rel: str, text: str) -> list[str]:
    return scan_lines(rel, markdown_text(text.splitlines())[0], heading_of=is_md_heading)


def manuscript_findings(root: Path) -> list[str]:
    out: list[str] = []
    base = root / "manuscripts"
    if not base.is_dir():
        return out
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in MANUSCRIPT_SUFFIXES:
            continue
        rel = path.relative_to(root).as_posix()
        out += path_findings(root, path, base)
        text = path.read_text(encoding="utf-8", errors="replace")
        suffix = path.suffix.lower()
        if suffix == ".tex":
            out += tex_findings(rel, text)
        elif suffix in {".md", ".txt"}:
            out += markdown_findings(rel, text)
        elif suffix == ".svg":
            for n, line in enumerate(text.splitlines(), 1):
                found = [w for m in SVG_TEXT.finditer(line) for w in words(m.group(1), heading=True)]
                if found:
                    out.append(finding(rel, f"figure text, line {n}", found))
        else:
            for n, s in code_text(text):
                if not s.lstrip().startswith("#") and MARK not in s and (found := words(s)):
                    out.append(finding(rel, f"string, line {n}", found))
    return out


def json_strings(value, key: str = "", path: str = "$"):
    """(path, key, string) of every string value of a JSON document; keys are not text."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield from json_strings(v, str(k), f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from json_strings(v, key, f"{path}[{i}]")
    elif isinstance(value, str):
        yield path, key, value


def json_findings(root: Path, path: Path) -> list[str]:
    """The string values of a JSON file the app reads; keys and lowercase key values are not text."""
    rel = path.relative_to(root).as_posix()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"{rel}: not readable as JSON ({e})"]
    out: list[str] = []
    for where, key, s in json_strings(doc):
        if not KEY_LIKE.match(s) and (found := words(s, heading=key.lower() in TITLE_KEYS)):
            out.append(finding(rel, where, found))
    return out


def source_findings(rel: str, text: str) -> list[str]:
    """The strings of a TypeScript source and its JSX text, which may stand on lines of its own; comments are not text."""
    raw = text.splitlines()
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    lines = [re.sub(r"(?<![:\"'`\\])//.*$", "", ln) for ln in text.splitlines()]
    hits: dict[int, list[str]] = {}
    for n, line in enumerate(lines, 1):
        for m in JS_STRING.finditer(line):
            s = next(g for g in m.groups() if g is not None)
            if not KEY_LIKE.match(s):
                hits.setdefault(n, []).extend(words(s))
    joined = "\n".join(lines)
    for m in JSX_TEXT.finditer(joined):
        for w in PHRASES.finditer(m.group(1)):
            hits.setdefault(joined.count("\n", 0, m.start(1) + w.start()) + 1, []).append(w.group(0))
    return [finding(rel, f"line {n}", found) for n, found in sorted(hits.items())
            if found and not (n <= len(raw) and MARK in raw[n - 1])]


def app_findings(root: Path) -> list[str]:
    out: list[str] = []
    for path in sorted((root / "content").rglob("*.json")) if (root / "content").is_dir() else []:
        out += json_findings(root, path)
    src = root / "frontend" / "src"
    for path in sorted(src.rglob("*")) if src.is_dir() else []:
        name = path.name
        if ".test." in name or ".gen." in name or name.endswith(".d.ts"):
            continue
        if path.suffix == ".json":
            out += json_findings(root, path)
        elif path.suffix in {".ts", ".tsx"}:
            out += source_findings(path.relative_to(root).as_posix(), path.read_text(encoding="utf-8", errors="replace"))
    return out


def findings_of(root: Path) -> list[str]:
    out: list[str] = []
    nb = root / "notebooks"
    if nb.is_dir():
        for path in sorted(nb.rglob("*.ipynb")):
            if ".ipynb_checkpoints" not in path.parts:
                out += path_findings(root, path, nb) + notebook_findings(root, path)
        for path in sorted(nb.rglob("README.md")):
            out += markdown_findings(path.relative_to(root).as_posix(), path.read_text(encoding="utf-8"))
    out += manuscript_findings(root)
    product = root / "product.json"
    if product.is_file():
        try:
            entries = json.loads(product.read_text(encoding="utf-8")).get("manuscripts") or []
        except (OSError, ValueError, AttributeError):
            entries = []
        for i, e in enumerate(entries if isinstance(entries, list) else []):
            if isinstance(e, dict) and (found := words(str(e.get("title", "")), heading=True)):
                out.append(finding("product.json", f"manuscripts[{i}].title", found))
    readme = root / "README.md"
    if readme.is_file():
        out += markdown_findings("README.md", readme.read_text(encoding="utf-8"))
    out += app_findings(root)
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    found = findings_of(root)
    for f in found:
        print(f)
    if found:
        print(f"check_internal_names: {len(found)} finding(s): the tier names are internal ({RULE})")
        return 1
    print("check_internal_names: OK, no tier name in the notebooks, the manuscripts, the README or the app")
    return 0


if __name__ == "__main__":
    sys.exit(main())
