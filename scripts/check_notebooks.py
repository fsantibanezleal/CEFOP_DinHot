#!/usr/bin/env python3
"""The product notebooks gate (CAOS_MANAGE ``conventions/product-notebooks.md``, template 0.10.000): the didactic layer is
laid out, mirrored, ordered, covered, annotated, clean and pinned, on committed files, in seconds.

Static, standard library only (CI installs nothing). It never executes a notebook: ``scripts/run_notebooks.py --check`` does,
as a local release gate (ADR-0074). It fails, naming the file and the rule, on

- **layout**: a missing ``notebooks/README.md``, ``notebooks/requirements.txt``, ``notebooks/en/README.md`` or
  ``notebooks/es/README.md``; a stray file in a topic folder (only ``*.ipynb``); a notebook anywhere but
  ``notebooks/<language>/<topic>/<notebook>.ipynb`` (loose at a root or nested deeper: it would be neither checked nor run);
- **mirror**: a path of one language tree absent from the other; counterparts that differ in level, packages, data, beyond
  claims or number of cells;
- **numbering**: topics and notebooks are ``NN-slug``, two digits, contiguous from 01;
- **levels**: a level that decreases inside a topic; a topic without levels 1 and 2; a topic without level 3 whose index row
  (``notebooks/<language>/README.md``) gives no reason (``No level 3: <why>`` / ``Sin nivel 3: <why>``); a notebook the
  index does not list;
- **beyond the state of the art**: a ``BS-`` identifier of the SDD section ``## Beyond the state of the art`` that no level 4
  notebook covers in each language, or a notebook claiming one the SDD does not list;
- **the method tiers** (template 0.13.000; CAOS_MANAGE ``conventions/method-tiers-and-manuscripts.md``): a method of tier ``sota`` in
  the SDD's ``## Method ladder`` table (``| id | tier | method | acceptance criterion | gate |``) that no level 3 notebook names in
  ``caos.methods``, in each language; a level 3 notebook that names none, or a method that is no ``sota`` row; ``caos.methods`` on
  another level. A tree whose SDD has no readable ladder is left to ``scripts/check_sdd.py``, which owns that table;
- **anatomy**: the second-level sections of the tree's language, in order, as the level requires (from template 0.14.000 the
  sections of levels 3 and 4 are ``Comparison`` and ``Evidence``: the tier names never title a notebook); a first cell that is not
  markdown; a code cell not directly preceded by a markdown cell, or without a comment;
- **metadata**: the ``caos`` block (language, topic, level, title, packages, data, sources, beyond) must agree with the
  tree, the folder, ``notebooks/requirements.txt`` (each package an exact line of it, ``name==version`` or
  ``name @ git+https://github.com/<owner>/<repo>.git@<tag>``, shown in the Setup text as its ``pip install`` line; the second
  form also with the sentence "not yet published on PyPI; installed from its release tag") and the repository (every data
  path exists); notebook metadata beyond kernelspec, language_info and caos, and cell metadata beyond tags;
- **references**: every link of ``caos.sources`` appears in the notebook's References section;
- **sources**: every link of ``caos.sources`` must be a source the SDD lists (its research basis summarises the persisted
  research claim by claim, each with its source; a notebook cites nothing else);
- **no re-implementation**: a code cell that defines a function or a class the pipeline's engine modules
  (``data-pipeline/**/model/*.py``) or oracles (``data-pipeline/**/oracles.py``) already define, or that a method package of
  the product (``product.json`` ``method_packages``, a PyPI distribution) already defines (a notebook imports a method,
  never copies it; a method package not installed here is an info line, ``run_notebooks.py`` checks its names; one with no
  exact ``name==version`` line in ``notebooks/requirements.txt`` is a finding); a code cell that runs ``pip`` or ``conda`` (the Setup text shows the install command, a notebook never
  runs it);
- **clean**: execution counts that are not 1, 2, 3 in order; an error output, a traceback printed to stdout or a stderr
  stream; an absolute or machine path (a drive letter in any literal form, a home folder, the POSIX roots ``/opt/``,
  ``/tmp/``, ``/root/``, ``/var/``, ``/srv/``) or a token pattern in any cell or output; a notebook or an image above the
  limits. A user name is not statically decidable (the template holds no deny-list of names): a product reviews it itself
  (guide 08, section 5);
- **the bar** (template 0.12.000, ``conventions/product-notebooks.md`` section 1, thresholds in ``scripts/notebook_bar.json``): a notebook is a
  worked lesson, so each one is measured and fails below its floors, one finding line naming the notebook, the measure, the value and the
  floor: method cells (calls into a method package, a pipeline module or, at level 3, a pinned reference implementation), figures and
  the words that read each, explanatory prose, setup cells, reproduction checks, long sentences shared with another notebook of the tree,
  generic filler, two statements on a line, long lines and cells, the question in the first cell, an answer that quotes a number an output
  shows, a method cell and a figure under Comparison (level 3) and a figure or table under Evidence (level 4);
- **CI**: ``.github/workflows/ci.yml`` runs this check and ``check_readme_areas.py``, and no workflow executes the notebooks.

Usage: ``python scripts/check_notebooks.py [repo_root] [--pypi]``. Exit 0 clean, 1 on any finding. ``--pypi`` is opt-in and never
runs in CI (ADR-0074): it reads ``https://pypi.org/pypi/<name>/<version>/json`` for the pin of each method package and fails on
anything but HTTP 200, so a Setup cell never tells a reader to install a version that is not published.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import re
import sys
import tokenize
import urllib.error
import urllib.request
from pathlib import Path

# the size limits of a committed notebook: the whole file (outputs included) and each embedded image, so the set stays
# readable on GitHub and cheap to clone (the convention's section 6; the template's proposal, 2026-10-20)
MAX_NOTEBOOK_BYTES = 3_000_000
MAX_IMAGE_BYTES = 400_000

LANGS = ("en", "es")
# (English heading, Spanish heading, lowest level that requires it): the anatomy of convention section 4, in order
SECTIONS = (
    ("Objectives", "Objetivos", 1),
    ("Setup", "Preparación", 1),
    ("Data", "Datos", 1),
    ("Method", "Método", 1),
    ("Comparison", "Comparación", 3),
    ("Evidence", "Evidencia", 4),
    ("Results", "Resultados", 1),
    ("Summary", "Resumen", 1),
    ("References", "Referencias", 1),
)
NO_LEVEL_3 = {"en": "No level 3:", "es": "Sin nivel 3:"}
MIN_REASON_WORDS = 4
NOTEBOOK_KEYS = {"kernelspec", "language_info", "caos"}
CAOS_KEYS = ("language", "topic", "level", "title", "packages", "data", "sources", "beyond")
OPTIONAL_KEYS = ("methods",)  # level 3 only: the ids of the SDD's sota methods the notebook runs
LADDER_SECTION = "Method ladder"
LADDER_HEAD = ["id", "tier", "method", "acceptance criterion", "gate"]
RULE = "CAOS_MANAGE conventions/method-tiers-and-manuscripts.md"
BEYOND_SECTION = "Beyond the state of the art"  # the SDD's section: an internal record, never a notebook heading
# the notebook sections of levels 3 and 4 (template 0.14.000): the tier names are internal and never a heading a reader
# sees (CAOS_MANAGE conventions/method-tiers-and-manuscripts.md section 0); scripts/check_internal_names.py holds the rest
COMPARISON_SECTION = "Comparison"
EVIDENCE_SECTION = "Evidence"
SLUG = re.compile(r"^(\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)$")
NOTEBOOK = re.compile(r"^(\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)\.ipynb$")
BS_ID = re.compile(r"\bBS-\d+\b")
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[A-Za-z0-9._,-]+\])?==(\d[0-9A-Za-z.+!_-]*)$")
# a package installed from its release tag (convention section 5, decided 2026-10-20): name @ git+https://github.com/<owner>/<repo>.git@<tag>
GIT_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*) @ (git\+https://github\.com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+\.git)@(v?\d[0-9A-Za-z.+_-]*)$")
TAG_SENTENCE = {"en": "not yet published on PyPI; installed from its release tag",
                "es": "todavía no publicado en PyPI; instalado desde su etiqueta de versión"}
# a drive letter (one or two backslashes, as a Python literal or a repr, or a slash), a home folder, an absolute POSIX root:
# a machine path never belongs in a committed notebook (convention section 6)
MACHINE_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:(?:\\{1,2}|/(?!/))|/home/|/Users/|\\Users\\|/mnt/[a-z]/|(?<![\w.~-])/(?:opt|tmp|root|var|srv)/")
# a notebook that installs: a pip or conda magic or shell line, `-m pip`, or a `pip install`, outside a comment
RUNS_PIP = re.compile(r"^\s*[%!]\s*(?:pip|conda|mamba)\b|-m['\"]?\s*,?\s*['\"]?pip\b|\bpip\s+install\b", re.M)
TRACEBACK = "Traceback (most recent call last)"
NOTEBOOK_PATH = "notebooks/<language>/<topic>/<notebook>.ipynb"
TOKENS = (
    re.compile(r"\bghp_[A-Za-z0-9]{20,}"), re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), re.compile(r"\bAKIA[0-9A-Z]{16}\b"), re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token|passw(?:or)?d)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"),
)
HEADING2 = re.compile(r"^##\s+(?!#)(.+?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```+|~~~+)")
CI = ".github/workflows"


def text_of(source) -> str:
    return "".join(source) if isinstance(source, list) else (source if isinstance(source, str) else "")


def has_comment(code: str) -> bool:
    """A comment token (never a ``#`` inside a string); an unparsable cell falls back to a line that starts with ``#``."""
    try:
        return any(t.type == tokenize.COMMENT for t in tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return any(ln.strip().startswith("#") for ln in code.splitlines())


def headings(markdown: str) -> list[str]:
    """The second-level headings of a markdown text, outside code fences."""
    out: list[str] = []
    fenced = False
    for line in markdown.splitlines():
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced and (m := HEADING2.match(line)):
            out.append(m[1].strip())
    return out


def output_texts(cell: dict) -> list[str]:
    """Every text a cell's outputs carry (images are measured, not read)."""
    out: list[str] = []
    for o in cell.get("outputs", []) or []:
        if not isinstance(o, dict):
            continue
        out.append(text_of(o.get("text", "")))
        out.append(str(o.get("ename", "")) + " " + str(o.get("evalue", "")) + " " + text_of(o.get("traceback", "")))
        for mime, value in (o.get("data") or {}).items():
            if not mime.startswith("image/") or mime == "image/svg+xml":
                out.append(text_of(value) if not isinstance(value, (dict, list)) else json.dumps(value))
    return out


def image_sizes(cell: dict) -> list[tuple[str, int]]:
    sizes: list[tuple[str, int]] = []
    for o in cell.get("outputs", []) or []:
        for mime, value in ((o.get("data") or {}).items() if isinstance(o, dict) else []):
            if mime.startswith("image/"):
                raw = text_of(value)
                sizes.append((mime, len(raw) if mime == "image/svg+xml" else len(raw.rstrip("=\n")) * 3 // 4))
    return sizes


def engine_names(root: Path) -> set[str]:
    """The public functions and classes the pipeline's methods define: the engine (``data-pipeline/**/model/*.py``) and the
    oracles (``data-pipeline/**/oracles.py``); a notebook imports them and never defines its own."""
    names: set[str] = set()
    pipeline = root / "data-pipeline"
    for path in sorted([*pipeline.glob("**/model/*.py"), *pipeline.glob("**/oracles.py")]) if pipeline.is_dir() else []:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        names.update(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_"))
    return names


def defined_names(code: str) -> set[str]:
    """The functions and classes a code cell defines at its top level (IPython magics and shell lines are dropped)."""
    clean = "\n".join("" if ln.lstrip().startswith(("%", "!")) else ln for ln in code.splitlines())
    try:
        return {n.name for n in ast.parse(clean).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    except SyntaxError:
        return set()


PYPI_TIMEOUT_SECONDS = 20
PYPI_URL = "https://pypi.org/pypi/{name}/{version}/json"


def normalized(name: str) -> str:
    """A distribution name as PEP 503 compares it."""
    return re.sub(r"[-_.]+", "-", name).lower()


def method_packages(root: Path, findings: list[str] | None = None) -> list[str]:
    """The distributions ``product.json`` declares as the product's method packages (optional key ``method_packages``, a list of
    names; absent or empty: none). A key of another shape is a finding; a missing or unreadable file declares none."""
    try:
        doc = json.loads((root / "product.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    value = doc.get("method_packages") if isinstance(doc, dict) else None
    if value is None:
        return []
    if not (isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)):
        if findings is not None:
            findings.append("product.json: method_packages: must be a list of strings (PyPI distribution names)")
        return []
    return list(dict.fromkeys(x.strip() for x in value))


def import_name(dist: str) -> str:
    """The top-level module of a distribution: its ``top_level.txt``, else the first folder or module of its files, else the
    distribution name with ``-`` read as ``_``."""
    try:
        d = importlib.metadata.distribution(dist)
    except importlib.metadata.PackageNotFoundError:
        return dist.replace("-", "_")
    top = (d.read_text("top_level.txt") or "").split()
    top = [t for t in top if not t.startswith("_") and not t.endswith(".libs")] or top
    if top:
        return top[0]
    for f in d.files or []:
        first = f.parts[0] if f.parts else ""
        if first and first != ".." and not first.endswith((".dist-info", ".egg-info", ".data", ".whl", ".libs")) \
                and first != "__pycache__":
            return first[:-3] if first.endswith(".py") else first
    return dist.replace("-", "_")


def package_public_names(module: str) -> set[str] | None:
    """The top-level ``def``, ``async def`` and ``class`` names, not starting with ``_``, of every ``.py`` file under the
    installed folder of ``module``; None when it is not installed. Files under a ``tests`` folder and modules whose name starts
    with ``_`` are left out (``__init__.py`` stays). The folder is found without importing the package and its source is read
    with ``ast``, never executed."""
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ValueError):
        spec = None
    if spec is None:
        return None
    if spec.submodule_search_locations:
        bases = [Path(loc) for loc in spec.submodule_search_locations]
        files = [p for b in bases for p in sorted(b.rglob("*.py"))]
    elif spec.origin and spec.origin.endswith(".py"):
        bases, files = [Path(spec.origin).parent], [Path(spec.origin)]
    else:
        return None
    names: set[str] = set()
    for path in files:
        rel = next((path.relative_to(b) for b in bases if b in path.parents), Path(path.name))
        if "tests" in rel.parts[:-1] or (path.stem.startswith("_") and path.name != "__init__.py"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        names.update(n.name for n in tree.body
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.name.startswith("_"))
    return names


def method_pin(root: Path, dist: str) -> str | None:
    """The version of the exact ``name==version`` line (extras allowed) that pins ``dist`` in ``notebooks/requirements.txt``."""
    for line in requirement_lines(root):
        m = PIN.match(line)
        if m and normalized(m[1]) == normalized(dist):
            return m[2]
    return None


def method_state(root: Path, infos: list[str] | None = None, strict: bool = False) -> tuple[dict[str, str], list[str]]:
    """The names the method packages define (name to distribution) and the findings about the packages themselves: a package
    with no exact pin and, when ``strict`` (the runner), a package not installed. The static check reports the latter as an
    info line and leaves its names to ``run_notebooks.py``."""
    findings: list[str] = []
    names: dict[str, str] = {}
    for dist in method_packages(root, findings):
        if method_pin(root, dist) is None:
            findings.append(f"notebooks/requirements.txt: pins: method package {dist!r} (product.json method_packages) has no exact pin "
                            f"({dist}==version)")
        public = package_public_names(import_name(dist))
        if public is None:
            if strict:
                findings.append(f"product.json: method_packages: {dist!r} is not installed in this environment; build it from "
                                "notebooks/requirements.txt (scripts/setup.sh --notebooks)")
            elif infos is not None:
                infos.append(f"check_notebooks: {dist} not installed here; its names are checked by run_notebooks.py")
            continue
        for name in public:
            names.setdefault(name, dist)
    return names, findings


def http_status(url: str) -> int:
    """The HTTP status of a GET of ``url``; the one network call of this script, made only under ``--pypi``."""
    req = urllib.request.Request(url, headers={"User-Agent": "caos-check-notebooks"})
    try:
        with urllib.request.urlopen(req, timeout=PYPI_TIMEOUT_SECONDS) as response:
            return int(response.status)
    except urllib.error.HTTPError as e:
        return int(e.code)


def pypi_findings(root: Path) -> list[str]:
    """The pin of each method package must exist on PyPI: anything but HTTP 200 is a finding naming the URL and the status."""
    out: list[str] = []
    for dist in method_packages(root):
        version = method_pin(root, dist)
        if version is None:
            continue  # the missing pin is already a finding of the static check
        url = PYPI_URL.format(name=dist, version=version)
        try:
            status: object = http_status(url)
        except OSError as e:
            status = f"unreachable ({e})"
        if status != 200:
            out.append(f"{url}: pypi: the pin {dist}=={version} of notebooks/requirements.txt is not published (answer: {status}); "
                       "a Setup cell would tell a reader to install a version that does not exist")
    return out


def method_copy_findings(rel: str, cells: list, methods: dict[str, str]) -> list[str]:
    """A code cell that defines a name a method package defines: the notebook imports it and never copies it."""
    out: list[str] = []
    for i, c in enumerate(cells, 1):
        if isinstance(c, dict) and c.get("cell_type") == "code":
            for copied in sorted(defined_names(text_of(c.get("source", ""))) & set(methods)):
                out.append(f"{rel}: engine: code cell {i} defines {copied!r}, which the method package {methods[copied]!r} already defines; "
                           "import it instead of re-implementing it")
    return out


DOI = re.compile(r"10\.\d{4,9}/[^\s)>\]|`]+")
LINK = re.compile(r"https?://[^\s)>\]|`]+")


def canonical(source: str) -> str:
    """A source as the SDD can hold it: its DOI when it names one (lower case), else the link without a closing slash or dot."""
    m = DOI.search(source)
    return ("doi:" + m[0].rstrip(".,;/").lower()) if m else source.strip().rstrip("/.,;").lower()


def sdd_sources(root: Path) -> set[str]:
    sdd = root / "docs" / "design" / "SDD.md"
    text = sdd.read_text(encoding="utf-8") if sdd.is_file() else ""
    return {canonical(m[0]) for m in DOI.finditer(text)} | {canonical(m[0]) for m in LINK.finditer(text)}


def requirement_lines(root: Path) -> list[str]:
    """The requirement lines of ``notebooks/requirements.txt``, without comments and blank lines."""
    path = root / "notebooks" / "requirements.txt"
    lines: list[str] = []
    if path.is_file():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.split(" #")[0].strip()
            if line and not line.startswith("#"):
                lines.append(line)
    return lines


def is_exact(line: str) -> bool:
    """An exact requirement line: ``name==version`` (PyPI) or ``name @ git+https://github.com/<owner>/<repo>.git@<tag>``."""
    return bool(PIN.match(line) or GIT_PIN.match(line))


def read_pins(root: Path) -> set[str]:
    """The exact requirement lines of ``notebooks/requirements.txt``: what a notebook's ``caos.packages`` may hold."""
    return {line for line in requirement_lines(root) if is_exact(line)}


def unpinned_lines(root: Path) -> list[str]:
    return [line for line in requirement_lines(root) if not is_exact(line)]


def install_spec(package: str) -> str:
    """What the Setup install line shows for a package: ``name==version``, or the ``git+https://...@<tag>`` part."""
    m = GIT_PIN.match(package)
    return f"{m[2]}@{m[3]}" if m else package


def sections_of(cells: list[dict]) -> dict[str, str]:
    """The markdown text of each second-level section (keyed by its heading), code fences respected."""
    out: dict[str, list[str]] = {}
    current: str | None = None
    fenced = False
    for c in cells:
        if c["cell_type"] != "markdown":
            continue
        for line in text_of(c["source"]).splitlines():
            if FENCE.match(line):
                fenced = not fenced
            elif not fenced and (m := HEADING2.match(line)):
                current = m[1].strip()
                out.setdefault(current, [])
                continue
            if current is not None:
                out[current].append(line)
        fenced = False
    return {k: "\n".join(v) for k, v in out.items()}


def install_lines(text: str) -> list[str]:
    """The ``pip install`` commands of a text, a trailing backslash joining the next line to its command."""
    lines = text.splitlines()
    out: list[str] = []
    n = 0
    while n < len(lines):
        command = lines[n]
        while command.rstrip().endswith("\\") and n + 1 < len(lines):
            n += 1
            command = command.rstrip()[:-1] + " " + lines[n].strip()
        if re.search(r"\bpip\s+install\b", command):
            out.append(command)
        n += 1
    return out


def without_comments(code: str) -> str:
    """A code cell without its comment tokens (a ``#`` inside a string stays); an unparsable cell loses its ``#`` lines."""
    try:
        keep = [t for t in tokenize.generate_tokens(io.StringIO(code).readline) if t.type != tokenize.COMMENT]
        return tokenize.untokenize(keep)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return "\n".join(ln for ln in code.splitlines() if not ln.strip().startswith("#"))


def sdd_section(root: Path, title: str) -> list[str] | None:
    """The lines of the SDD's level-2 section ``title`` (fences respected), None when the SDD or the section is absent."""
    sdd = root / "docs" / "design" / "SDD.md"
    if not sdd.is_file():
        return None
    body: list[str] | None = None
    fenced = False
    for line in sdd.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line):
            fenced = not fenced
        if not fenced and (m := re.match(r"^##\s+(?:\d+\.\s*)?(.+?)\s*$", line)) and not line.startswith("###"):
            if body is not None:
                break
            if m[1].strip().lower() == title.lower():
                body = []
            continue
        if body is not None:
            body.append(line)
    return body


def sdd_ladder(root: Path) -> dict[str, str] | None:
    """The SDD's method ladder as ``{id: tier}`` (tier in lower case), None when there is no table with the ladder's columns."""
    body = sdd_section(root, LADDER_SECTION)
    if body is None:
        return None
    ladder: dict[str, str] | None = None
    for line in body:
        if FENCE.match(line):
            continue
        if not line.strip().startswith("|"):
            if ladder is not None:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if ladder is None:
            if [c.lower() for c in cells] == LADDER_HEAD:
                ladder = {}
        elif len(cells) == len(LADDER_HEAD) and not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            ladder[cells[0]] = cells[1].lower()
    return ladder


def sdd_claims(root: Path) -> tuple[set[str] | None, str | None]:
    """The ``BS-`` identifiers of the SDD section, ``set()`` for 'None claimed.', and the problem reading it, if any."""
    sdd = root / "docs" / "design" / "SDD.md"
    if not sdd.is_file():
        return None, "docs/design/SDD.md is missing"
    body = sdd_section(root, BEYOND_SECTION)
    if body is None:
        return None, f"the SDD has no section '## {BEYOND_SECTION}' (list the BS- claims, or say 'None claimed.')"
    text = "\n".join(body)
    ids = set(BS_ID.findall(text))
    none = "None claimed." in text
    if ids and none:
        return None, "the section says 'None claimed.' and lists BS- claims"
    if not ids and not none:
        return None, "the section lists no BS- claim and does not say 'None claimed.'"
    return ids, None


class Tree:
    """One language tree: its topics, notebooks and the parsed documents."""

    def __init__(self, root: Path, lang: str) -> None:
        self.lang = lang
        self.base = root / "notebooks" / lang
        self.topics = sorted(p.name for p in self.base.iterdir() if p.is_dir()) if self.base.is_dir() else []

    def files(self) -> set[str]:
        if not self.base.is_dir():
            return set()
        return {p.relative_to(self.base).as_posix() for p in self.base.rglob("*")}


def load(path: Path, rel: str, findings: list[str]) -> dict | None:
    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        findings.append(f"{rel}: layout: not readable as JSON ({e})")
        return None
    if not isinstance(nb, dict) or nb.get("nbformat") != 4 or not isinstance(nb.get("cells"), list) \
            or not isinstance(nb.get("metadata"), dict):
        findings.append(f"{rel}: layout: not a notebook of format 4 (needs nbformat 4, cells and metadata)")
        return None
    for i, c in enumerate(nb["cells"], 1):
        if not isinstance(c, dict) or c.get("cell_type") not in {"markdown", "code"} or "source" not in c:
            findings.append(f"{rel}: layout: cell {i} is not a markdown or code cell with a source")
            return None
    return nb


def check_numbering(names: list[str], pattern: re.Pattern[str], rel: str, kind: str, findings: list[str]) -> None:
    nums: list[int] = []
    for n in names:
        m = pattern.match(n)
        if not m:
            findings.append(f"{rel}: numbering: {kind} {n!r} is not NN-slug (two digits, lower case English slug)")
        else:
            nums.append(int(m[1]))
    if nums and nums != list(range(1, len(nums) + 1)):
        findings.append(f"{rel}: numbering: the {kind}s are numbered {nums}, not 01 up to {len(nums):02d} with no gap or repeat")


def check_notebook(root: Path, lang: str, topic: str, name: str, nb: dict, pins: set[str], claims: set[str],
                   engine: set[str], listed: set[str], findings: list[str], ladder: dict[str, str] | None = None) -> None:
    rel = f"notebooks/{lang}/{topic}/{name}"
    path = root / rel
    size = path.stat().st_size
    if size > MAX_NOTEBOOK_BYTES:
        findings.append(f"{rel}: size: {size} bytes is above the {MAX_NOTEBOOK_BYTES} byte limit of a notebook")
    meta = nb["metadata"]
    cells = nb["cells"]
    # ---- metadata
    extra = sorted(set(meta) - NOTEBOOK_KEYS)
    if extra:
        findings.append(f"{rel}: metadata: notebook metadata beyond kernelspec, language_info and caos: {extra}")
    for key in ("kernelspec", "language_info"):
        if not isinstance(meta.get(key), dict):
            findings.append(f"{rel}: metadata: {key} is missing")
    caos = meta.get("caos")
    level = 0
    if not isinstance(caos, dict):
        findings.append(f"{rel}: metadata: the caos block is missing")
    else:
        level = caos.get("level") if isinstance(caos.get("level"), int) and not isinstance(caos.get("level"), bool) else 0
        for key in CAOS_KEYS:
            if key not in caos:
                findings.append(f"{rel}: metadata: caos.{key} is missing")
        for key in sorted(set(caos) - set(CAOS_KEYS) - set(OPTIONAL_KEYS)):
            findings.append(f"{rel}: metadata: caos.{key} is not a field of the block")
        if caos.get("language") != lang:
            findings.append(f"{rel}: metadata: caos.language is {caos.get('language')!r}, the tree is {lang!r}")
        if caos.get("topic") != topic:
            findings.append(f"{rel}: metadata: caos.topic is {caos.get('topic')!r}, the folder is {topic!r}")
        if "level" in caos and level not in {1, 2, 3, 4}:
            findings.append(f"{rel}: metadata: caos.level is {caos.get('level')!r}, not 1, 2, 3 or 4")
        if "title" in caos and not (isinstance(caos["title"], str) and caos["title"].strip()):
            findings.append(f"{rel}: metadata: caos.title is empty")
        markdown_all = "\n".join(text_of(c["source"]) for c in cells if c["cell_type"] == "markdown")
        packages = caos.get("packages")
        if "packages" in caos and not (isinstance(packages, list) and all(isinstance(p, str) for p in packages)):
            findings.append(f"{rel}: metadata: caos.packages is not a list of exact requirement lines of notebooks/requirements.txt")
        else:
            sections = sections_of(cells)
            if packages and not any(c["cell_type"] == "code" and "importlib.metadata" in text_of(c["source"]) for c in cells):
                findings.append(f"{rel}: anatomy: no code cell prints the versions of the packages (importlib.metadata.version), "
                                "as the Setup section's last step")
            setup = sections.get("Setup" if lang == "en" else "Preparación", "")
            commands = install_lines(setup)
            for p in packages or []:
                if not is_exact(p):
                    findings.append(f"{rel}: metadata: package {p!r} is not an exact requirement line "
                                    "(name==version, or name @ git+https://github.com/<owner>/<repo>.git@<tag>)")
                elif p not in pins:
                    findings.append(f"{rel}: metadata: package {p!r} is not a pin of notebooks/requirements.txt (an exact line of it)")
                else:
                    spec = install_spec(p)
                    if spec not in markdown_all:
                        findings.append(f"{rel}: metadata: package {p!r} is not written in the notebook's text (the Setup `pip install` line)")
                    elif not any(spec in c for c in commands):
                        findings.append(f"{rel}: anatomy: the Setup section shows no `pip install` line with {spec!r} "
                                        "(the familiar install command, in a markdown code block)")
                    if GIT_PIN.match(p) and TAG_SENTENCE[lang] not in setup:
                        findings.append(f"{rel}: anatomy: {p!r} is installed from its release tag, so the Setup section says "
                                        f"\"{TAG_SENTENCE[lang]}\"")
        data = caos.get("data")
        if "data" in caos and not (isinstance(data, list) and all(isinstance(d, str) for d in data)):
            findings.append(f"{rel}: metadata: caos.data is not a list of repository paths")
        else:
            for d in data or []:
                if d.startswith("/") or MACHINE_PATH.search(d) or ".." in Path(d).parts or not (root / d).is_file():
                    findings.append(f"{rel}: metadata: data path {d!r} is not a file of the repository (a path from the repository root)")
        sources = caos.get("sources")
        if "sources" in caos and not (isinstance(sources, list) and sources and all(isinstance(s, str) and s.startswith("http") for s in sources)):
            findings.append(f"{rel}: metadata: caos.sources is not a non-empty list of https links")
        else:
            references = sections_of(cells).get("References" if lang == "en" else "Referencias", "").lower()
            for src in sources or []:
                if canonical(src) not in listed:
                    findings.append(f"{rel}: sources: {src!r} is not a source the SDD lists (add it to the SDD's research basis, or cite another)")
                key = canonical(src)
                if (key[4:] if key.startswith("doi:") else key) not in references:
                    findings.append(f"{rel}: sources: the References section does not list {src!r} (it lists every source cited)")
        beyond = caos.get("beyond")
        if "beyond" in caos and not (isinstance(beyond, list) and all(isinstance(b, str) for b in beyond)):
            findings.append(f"{rel}: metadata: caos.beyond is not a list of BS- identifiers")
        elif isinstance(beyond, list):
            if beyond and level != 4:
                findings.append(f"{rel}: metadata: caos.beyond lists claims but the level is {level}, not 4")
            if level == 4 and not beyond:
                findings.append(f"{rel}: metadata: a level 4 notebook lists the BS- claims it demonstrates in caos.beyond")
            for b in beyond:
                if b not in claims:
                    findings.append(f"{rel}: metadata: {b!r} is not a claim of the SDD's '## {BEYOND_SECTION}' section")
        methods = caos.get("methods", [])
        if not (isinstance(methods, list) and all(isinstance(m, str) for m in methods)):
            findings.append(f"{rel}: metadata: caos.methods is not a list of ids of the SDD's Method ladder")
        else:
            if methods and level != 3:
                findings.append(f"{rel}: metadata: caos.methods lists methods but this is a level {level} notebook: "
                                "only a level 3 notebook names the sota methods it runs")
            if level == 3 and not methods and any(t == "sota" for t in (ladder or {}).values()):
                findings.append(f"{rel}: metadata: a level 3 notebook lists the sota methods of the SDD's Method ladder it runs "
                                f"in caos.methods ({RULE})")
            for m in methods:
                if ladder is not None and ladder.get(m) != "sota":
                    findings.append(f"{rel}: metadata: {m!r} is not a sota method of the SDD's Method ladder (tier sota)")
    # ---- anatomy
    if not cells or cells[0]["cell_type"] != "markdown":
        findings.append(f"{rel}: anatomy: the first cell is not a markdown cell (title, level, prerequisites, reading time)")
    seen: list[str] = []
    for c in cells:
        if c["cell_type"] == "markdown":
            seen.extend(headings(text_of(c["source"])))
    want = [(en if lang == "en" else es) for en, es, low in SECTIONS if level >= low and level in {1, 2, 3, 4}]
    if level in {1, 2, 3, 4}:
        every = {en if lang == "en" else es for en, es, _ in SECTIONS}
        for w in want:
            if w not in seen:
                findings.append(f"{rel}: anatomy: the section '## {w}' is missing (level {level}, language {lang})")
        for s in seen:
            if s not in want:
                why = "a section of a higher level" if s in every else "not a section of the anatomy"
                findings.append(f"{rel}: anatomy: the section '## {s}' is {why} for level {level}")
        got = [s for s in seen if s in want]
        if len(got) != len(set(got)):
            findings.append(f"{rel}: anatomy: a section appears twice")
        elif got != [w for w in want if w in got]:
            findings.append(f"{rel}: anatomy: sections out of order: {got}, expected {[w for w in want if w in got]}")
    previous = None
    for i, c in enumerate(cells, 1):
        if c["cell_type"] == "code":
            code = text_of(c["source"])
            if previous != "markdown":
                findings.append(f"{rel}: anatomy: code cell {i} is not preceded by a markdown cell that says what it does and why")
            if not has_comment(code):
                findings.append(f"{rel}: anatomy: code cell {i} carries no comment line")
            if RUNS_PIP.search(without_comments(code)):
                findings.append(f"{rel}: anatomy: code cell {i} runs pip or conda: a notebook never runs pip itself (convention section 4); "
                                "the Setup text shows the install command")
            for copied in sorted(defined_names(code) & engine):
                findings.append(f"{rel}: engine: code cell {i} defines {copied!r}, which the pipeline's engine or oracle modules already define; "
                                "import it instead of re-implementing it")
        previous = c["cell_type"]
    # ---- cell metadata and clean
    expected = 1
    for i, c in enumerate(cells, 1):
        cm = c.get("metadata", {})
        if not isinstance(cm, dict) or set(cm) - {"tags"}:
            findings.append(f"{rel}: metadata: cell {i} metadata beyond tags: {sorted(set(cm) - {'tags'}) if isinstance(cm, dict) else cm!r}")
        texts = [text_of(c["source"])]
        if c["cell_type"] == "code":
            count = c.get("execution_count")
            if count != expected:
                findings.append(f"{rel}: execution: code cell {i} has execution_count {count!r}, expected {expected} "
                                "(run scripts/run_notebooks.py: only the runner writes outputs)")
            expected += 1
            for o in c.get("outputs", []) or []:
                if o.get("output_type") == "error":
                    findings.append(f"{rel}: output: code cell {i} holds an error output ({o.get('ename')})")
                if o.get("output_type") == "stream" and o.get("name") == "stderr":
                    findings.append(f"{rel}: output: code cell {i} holds a stderr stream")
                if o.get("output_type") != "error" and TRACEBACK in text_of(o.get("text", "")):
                    findings.append(f"{rel}: output: code cell {i} prints a traceback ({TRACEBACK!r}) to its output")
            texts += output_texts(c)
            for mime, n in image_sizes(c):
                if n > MAX_IMAGE_BYTES:
                    findings.append(f"{rel}: size: an image ({mime}) of code cell {i} is {n} bytes, above the {MAX_IMAGE_BYTES} byte limit")
        for t in texts:
            if m := MACHINE_PATH.search(t):
                findings.append(f"{rel}: path: cell {i} holds a machine path ({m[0]!r}): use a path relative to the repository root")
            for pat in TOKENS:
                if pat.search(t):
                    findings.append(f"{rel}: secret: cell {i} holds a token pattern")
                    break


def counterpart_findings(root: Path, en_docs: dict[str, dict], es_docs: dict[str, dict], findings: list[str]) -> None:
    for key in sorted(set(en_docs) & set(es_docs)):
        a, b = en_docs[key], es_docs[key]
        ca, cb = a["metadata"].get("caos"), b["metadata"].get("caos")
        rel = f"notebooks/es/{key}"
        if isinstance(ca, dict) and isinstance(cb, dict):
            for field in ("level", "packages", "data", "beyond", "methods"):
                if ca.get(field) != cb.get(field):
                    findings.append(f"{rel}: mirror: caos.{field} differs from its English counterpart")
        kinds_a = [c["cell_type"] for c in a["cells"]]
        kinds_b = [c["cell_type"] for c in b["cells"]]
        if kinds_a != kinds_b:
            findings.append(f"{rel}: mirror: {len(kinds_b)} cells in a different order of kinds than the English counterpart's "
                            f"{len(kinds_a)}: it is not a full counterpart")


def index_findings(root: Path, lang: str, tree: Tree, levels: dict[str, dict[str, int]], findings: list[str]) -> None:
    path = root / "notebooks" / lang / "README.md"
    if not path.is_file():
        return
    rel = f"notebooks/{lang}/README.md"
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    for topic in tree.topics:
        row = [ln for ln in lines if topic in ln]
        if not row:
            findings.append(f"{rel}: index: the topic {topic} has no row")
            continue
        have = set(levels.get(topic, {}).values())
        if have and 3 not in have:
            line = next((ln for ln in row if NO_LEVEL_3[lang] in ln), None)
            reason = line.split(NO_LEVEL_3[lang], 1)[1].strip(" |*_") if line else ""
            if len(reason.split()) < MIN_REASON_WORDS:
                findings.append(f"{rel}: levels: the topic {topic} has no level 3 notebook and its row gives no reason "
                                f"('{NO_LEVEL_3[lang]} <why, {MIN_REASON_WORDS} words or more>')")
        for name in levels.get(topic, {}):
            if name not in text:
                findings.append(f"{rel}: index: the notebook {topic}/{name} is not listed")


def ci_findings(root: Path, findings: list[str]) -> None:
    ci = root / CI / "ci.yml"
    if not ci.is_file():
        findings.append(f"{CI}/ci.yml: ci: the workflow is missing")
    else:
        text = ci.read_text(encoding="utf-8")
        for script in ("check_notebooks.py", "check_readme_areas.py"):
            if f"python scripts/{script}" not in text:
                findings.append(f"{CI}/ci.yml: ci: no step runs `python scripts/{script}` (a static check, in CI and locally)")
    for wf in sorted((root / CI).glob("*.y*ml")) if (root / CI).is_dir() else []:
        if "run_notebooks" in wf.read_text(encoding="utf-8"):
            findings.append(f"{CI}/{wf.name}: ci: runs the notebooks; the execution is a local release gate, never CI (ADR-0074)")


def form_findings(root: Path, infos: list[str] | None = None, docs_out: dict[str, dict[str, dict]] | None = None) -> list[str]:
    """The checks of the notebooks' form (layout, mirror, numbering, levels, anatomy, metadata, references, engine, clean). The
    parsed documents of each tree go into ``docs_out`` (language to ``topic/notebook`` to document) when given."""
    findings: list[str] = []
    nb = root / "notebooks"
    for rel in ("README.md", "requirements.txt", "en/README.md", "es/README.md"):
        if not (nb / rel).is_file() or not (nb / rel).read_text(encoding="utf-8").strip():
            findings.append(f"notebooks/{rel}: layout: missing or empty")
    for line in unpinned_lines(root):
        findings.append(f"notebooks/requirements.txt: pins: {line!r} is not an exact pin "
                        "(name==version, or name @ git+https://github.com/<owner>/<repo>.git@<tag>)")
    for found_at in sorted(nb.rglob("*.ipynb")) if nb.is_dir() else []:
        rel = found_at.relative_to(nb).parts
        if not (len(rel) == 3 and rel[0] in LANGS):
            findings.append(f"notebooks/{'/'.join(rel)}: layout: a notebook lives at {NOTEBOOK_PATH} "
                            "(a notebook elsewhere is neither checked nor run)")
    claims, problem = sdd_claims(root)
    if problem:
        findings.append(f"docs/design/SDD.md: beyond: {problem}")
    ladder = sdd_ladder(root)
    pins = read_pins(root)
    engine = engine_names(root)
    methods, method_findings = method_state(root, infos)
    findings.extend(method_findings)
    listed = sdd_sources(root)
    trees = {lang: Tree(root, lang) for lang in LANGS}
    for lang in LANGS:
        if not trees[lang].base.is_dir():
            findings.append(f"notebooks/{lang}: layout: the {lang} tree is missing")
    a, b = trees["en"].files(), trees["es"].files()
    for lang, mine, other in (("es", b, a), ("en", a, b)):
        for rel in sorted(other - mine):
            findings.append(f"notebooks/{lang}/{rel}: mirror: absent from the {lang} tree (present in {'en' if lang == 'es' else 'es'})")
    docs: dict[str, dict[str, dict]] = docs_out if docs_out is not None else {}
    for lang in LANGS:
        docs.setdefault(lang, {})
    levels: dict[str, dict[str, dict[str, int]]] = {lang: {} for lang in LANGS}
    covered: dict[str, set[str]] = {lang: set() for lang in LANGS}
    run3: dict[str, set[str]] = {lang: set() for lang in LANGS}  # the sota methods the level 3 notebooks name
    for lang, tree in trees.items():
        check_numbering(tree.topics, SLUG, f"notebooks/{lang}", "topic", findings)
        for topic in tree.topics:
            folder = tree.base / topic
            for stray in sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix != ".ipynb"):
                findings.append(f"notebooks/{lang}/{topic}/{stray.name}: layout: only notebooks live in a topic folder")
            names = sorted(p.name for p in folder.iterdir() if p.suffix == ".ipynb")
            check_numbering(names, NOTEBOOK, f"notebooks/{lang}/{topic}", "notebook", findings)
            order: list[int] = []
            for name in names:
                doc = load(folder / name, f"notebooks/{lang}/{topic}/{name}", findings)
                if doc is None:
                    continue
                docs[lang][f"{topic}/{name}"] = doc
                check_notebook(root, lang, topic, name, doc, pins, claims or set(), engine, listed, findings, ladder)
                findings.extend(method_copy_findings(f"notebooks/{lang}/{topic}/{name}", doc["cells"], methods))
                caos = doc["metadata"].get("caos")
                lv = caos.get("level") if isinstance(caos, dict) else None
                if isinstance(lv, int) and not isinstance(lv, bool):
                    levels[lang].setdefault(topic, {})[name] = lv
                    order.append(lv)
                    if lv == 4 and isinstance(caos.get("beyond"), list):
                        covered[lang].update(x for x in caos["beyond"] if isinstance(x, str))
                    if lv == 3 and isinstance(caos.get("methods"), list):
                        run3[lang].update(x for x in caos["methods"] if isinstance(x, str))
            if order != sorted(order):
                findings.append(f"notebooks/{lang}/{topic}: levels: the level decreases inside the topic ({order}); the reading order never goes down")
            have = set(order)
            for need in (1, 2):
                if names and need not in have:
                    findings.append(f"notebooks/{lang}/{topic}: levels: the topic has no level {need} notebook")
        index_findings(root, lang, tree, levels[lang], findings)
    for lang in LANGS:
        for claim in sorted((claims or set()) - covered[lang]):
            findings.append(f"notebooks/{lang}: beyond: the SDD claim {claim} is covered by no level 4 notebook (caos.beyond)")
        for method in sorted(m for m, tier in (ladder or {}).items() if tier == "sota" and m not in run3[lang]):
            findings.append(f"notebooks/{lang}: tiers: the sota method {method} of the SDD's Method ladder is named by no level 3 notebook "
                            f"(caos.methods): every state-of-the-art method has a level 3 notebook that runs it ({RULE})")
    counterpart_findings(root, docs["en"], docs["es"], findings)
    ci_findings(root, findings)
    return findings


# ---------------------------------------------------------------------------------------------------------------------------
# The measured floors of the bar (convention section 1, template 0.12.000). Static, on the committed cells and outputs, and the
# same verdict whatever is installed: import names come from product.json, notebooks/requirements.txt and the static name map of
# scripts/notebook_bar.json, never from the environment. The thresholds, the tooling modules, the filler sentences, the map and the
# fingerprints of the template's example live in scripts/notebook_bar.json.
# ---------------------------------------------------------------------------------------------------------------------------
BAR_FILE = Path(__file__).resolve().with_name("notebook_bar.json")
SENTINEL = ".template-source"
SECTION_EN = {es: en for en, es, _ in SECTIONS}
SCAFFOLD_SECTIONS = {"Setup", "Data", "References"}
MARKERS = {"en": ("**Question:**", "**Answer:**"), "es": ("**Pregunta:**", "**Respuesta:**")}
FIGURE_MIMES = ("image/png", "image/svg+xml", "image/jpeg", "application/vnd.plotly.v1+json")
# calls that read a file, find a path, reshape what was read or configure the session: what a setup or input/output cell holds
READ_CALLS = {"Path", "resolve", "parent", "joinpath", "exists", "is_file", "is_dir", "cwd", "read_text", "read_bytes", "read_json",
              "load", "loads", "open", "read", "read_csv", "read_parquet", "loadtxt", "genfromtxt", "glob", "rglob", "getenv"}
BENIGN_CALLS = READ_CALLS | {"sorted", "list", "dict", "set", "tuple", "len", "str", "int", "float", "enumerate", "zip", "range",
                             "items", "keys", "values", "get", "startswith", "endswith", "strip", "split", "join", "lower",
                             "upper", "format", "replace", "isinstance", "version", "dumps", "display", "head", "tail", "DataFrame", "describe", "info"}
CONFIG_CALL = re.compile(r"^(?:sys\.path\.|.*rcParams|.*set_printoptions|.*\bseed$|.*filterwarnings|.*simplefilter|.*style\.use"
                         r"|matplotlib\.use|.*\bversion$)")
PLOT_CALLS = {"plot", "scatter", "bar", "barh", "hist", "imshow", "show", "subplots", "figure", "savefig", "loglog", "semilogx",
              "semilogy", "fill_between", "errorbar", "contour", "contourf", "pcolormesh", "heatmap", "boxplot", "violinplot",
              "step", "stem", "pie", "hexbin", "plot_surface", "axhline", "axvline", "annotate", "legend"}
COMPARE_CALLS = {"allclose", "array_equal", "array_equiv"}
VALIDATION_ATTRS = {"shape", "ndim", "dtype", "size"}
VALIDATION_CALLS = {"len", "isinstance", "hasattr", "callable"}
COMPOUND = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.AsyncFor,
            ast.AsyncWith)
INLINE_BODY = (ast.If, ast.For, ast.While, ast.With, ast.AsyncFor, ast.AsyncWith)
FLOOR_LEVEL_DEFAULT = 2
HEAVY_WORDS = 4   # a sentence of fewer words may be repeated: a label, a short pointer
BUILTIN_METHODS = {"index", "count", "get", "keys", "items", "values", "copy", "append", "extend", "pop", "insert", "remove", "sort", "reverse",
                   "clear", "update", "setdefault", "join", "split", "rsplit", "strip", "lstrip", "rstrip", "lower", "upper", "replace",
                   "format", "startswith", "endswith", "find", "rfind", "add", "discard", "union", "intersection", "difference",
                   "encode", "decode", "title", "capitalize", "isdigit", "zfill", "center", "ljust", "rjust"}   # of list, dict, str, tuple, set
# a number in prose or in an output: thousands groups, a decimal part, an exponent, a percent sign
NUMBER = re.compile(r"[-+]?\d+(?:[.,]\d+)*(?:[eE][-+]?\d+)?\s?%?")
VERSION = re.compile(r"\b\d+\.\d+\.\d+(?:\.\d+)*\b")
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?\b")


def load_bar(path: Path | None = None) -> dict:
    """The bar's configuration (tooling, filler, floors, import names, fingerprints) from ``scripts/notebook_bar.json``."""
    return json.loads((path or BAR_FILE).read_text(encoding="utf-8"))


def floor_at(bar: dict, key: str, level: int):
    value = bar["floors"][key]
    return value.get(str(level), value.get(str(FLOOR_LEVEL_DEFAULT))) if isinstance(value, dict) else value


def parse_code(code: str) -> ast.Module | None:
    """A code cell as a syntax tree (IPython magics and shell lines are blanked); None when it does not parse."""
    clean = "\n".join("" if ln.lstrip().startswith(("%", "!")) else ln for ln in code.splitlines())
    try:
        return ast.parse(clean)
    except SyntaxError:
        return None


def strip_markup(text: str) -> str:
    """Markdown without what a reader does not read as prose: fenced and indented code, HTML comments, tables, display and inline math."""
    kept: list[str] = []
    fenced = False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            kept.append(line)
    text = re.sub(r"<!--.*?-->", " ", "\n".join(kept), flags=re.S)
    out: list[str] = []
    code = in_list = False
    prev_blank = True
    for line in text.splitlines():
        s = line.strip()
        if not s:
            out.append(line)
            prev_blank = True
            continue
        indented = line.startswith(("    ", "\t"))
        item = bool(re.match(r"(?:[-*+]|\d+[.)])\s", s))
        if item:
            in_list = True
        elif not indented:
            in_list = False
        if indented and not item and not in_list and (prev_blank or code):
            code, prev_blank = True, False
            continue
        code = prev_blank = False
        if not s.startswith("|"):
            out.append(line)
    return re.sub(r"\$\$.*?\$\$|\$[^$\n]*\$", " ", "\n".join(out), flags=re.S)


def count_words(text: str) -> int:
    return sum(1 for t in text.split() if re.search(r"\w", t))


def words_of(text: str) -> int:
    """The words of a markdown text, without code, comments, tables and math; a token counts when it holds a letter or digit."""
    return count_words(strip_markup(text))


def tooling_modules(bar: dict) -> set[str]:
    return set(sys.stdlib_module_names) | set(bar.get("tooling", []))


def pipeline_modules(root: Path) -> set[str]:
    """The top-level modules the pipeline offers a notebook: the packages and modules directly under ``data-pipeline/`` and under its
    ``src/`` (the skeleton the template ships: ``src/core``, ``src/io``, ``src/model``)."""
    out: set[str] = set()
    for base in (root / "data-pipeline", root / "data-pipeline" / "src"):
        for p in sorted(base.iterdir()) if base.is_dir() else []:
            if p.suffix == ".py":
                out.add(p.stem)
            elif p.is_dir() and not p.name.startswith((".", "_")) and any(p.rglob("*.py")):
                out.add(p.name)
    return out


def pin_name(line: str) -> str:
    """The distribution of an exact requirement line (``name==version`` or ``name @ git+...``)."""
    return re.split(r"\s*(?:==|@)", line, maxsplit=1)[0].split("[")[0].strip()


def static_import_name(dist: str, bar: dict, declared: dict[str, str]) -> str:
    """The module a distribution is imported as, from the product's own map (``product.json`` ``import_names``), the static map of
    ``notebook_bar.json`` and the distribution name; never from what is installed."""
    key = normalized(dist)
    return declared.get(key) or bar.get("import_names", {}).get(key) or key.replace("-", "_")


def declared_import_names(root: Path) -> dict[str, str]:
    try:
        doc = json.loads((root / "product.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    value = doc.get("import_names") if isinstance(doc, dict) else None
    return {normalized(k): v for k, v in value.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(value, dict) else {}


def method_modules(root: Path, caos: dict | None, level: int, bar: dict) -> dict[str, str]:
    """The modules a notebook's method calls may come from, each with its kind: ``product`` (the method packages of ``product.json`` and
    the pipeline's modules) or ``reference`` (at level 3 only, the non-tooling packages the notebook pins)."""
    declared = declared_import_names(root)
    mods = {m: "reference" for m in (
        static_import_name(pin_name(p), bar, declared) for p in (caos.get("packages") or [] if isinstance(caos, dict) and level == 3 else [])
        if isinstance(p, str))}
    mods.update({static_import_name(d, bar, declared): "product" for d in method_packages(root)})
    mods.update({m: "product" for m in pipeline_modules(root)})
    return {m: k for m, k in mods.items() if m and m not in tooling_modules(bar)}


def root_name(node: ast.AST) -> str | None:
    """The name an attribute, call or subscript chain starts from."""
    while True:
        if isinstance(node, ast.Attribute):
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Subscript):
            node = node.value
        else:
            return node.id if isinstance(node, ast.Name) else None


def chain_names(node: ast.AST) -> list[str]:
    """The attribute names along a chain, last first (``a.b.c(...)`` gives ``['c', 'b']``)."""
    out: list[str] = []
    while True:
        if isinstance(node, ast.Attribute):
            out.append(node.attr)
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Subscript):
            node = node.value
        else:
            return out


def callee(node: ast.Call) -> str:
    """The last name of what a call calls (``a.b.c(...)`` gives ``c``)."""
    f = node.func
    return f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")


def string_list(value) -> list[str] | None:
    return list(dict.fromkeys(x.strip() for x in value)) if isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value) else None


def product_names(root: Path, key: str) -> tuple[set[str] | None, bool]:
    """The dotted names ``product.json`` lists under ``key`` (``method_entrypoints``, ``artifact_loaders``): the set, or None when the key is
    absent; the flag says the key is there but is not a list of strings."""
    try:
        doc = json.loads((root / "product.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, False
    if not isinstance(doc, dict) or key not in doc:
        return None, False
    names = string_list(doc[key])
    return (set(names), False) if names is not None else (None, True)


def reexport_map(root: Path, bar: dict, entry: set[str] | None) -> dict[str, str]:
    """Where a declared name is defined, for a re-export: ``notebook_bar.json`` ``reexports`` (name used to name defined) and, for a package
    whose source is in the repository (under ``data-pipeline/``, ``data-pipeline/src/`` or the root), the ``from .module import name`` of its
    ``__init__.py``; read with ``ast``, never by importing."""
    out = {k: v for k, v in bar.get("reexports", {}).items() if isinstance(k, str) and isinstance(v, str)}
    for pkg in sorted({e.split(".")[0] for e in entry or ()}):
        for base in (root / "data-pipeline", root / "data-pipeline" / "src", root):
            init = base / pkg / "__init__.py"
            if not init.is_file():
                continue
            try:
                tree = ast.parse(init.read_text(encoding="utf-8"))
            except (OSError, SyntaxError, UnicodeDecodeError):
                continue
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom) and n.level <= 1 and (n.module or n.level == 0):
                    module = n.module if n.level == 0 else ".".join([pkg, *(n.module.split(".") if n.module else [])])
                    for a in n.names:
                        if a.name != "*" and f"{pkg}.{a.asname or a.name}" != f"{module}.{a.name}":
                            out.setdefault(f"{pkg}.{a.asname or a.name}", f"{module}.{a.name}")
            break
    return out


def is_constant(node: ast.AST) -> bool:
    """A value that holds no name and no call: nothing the notebook read or computed."""
    return not any(isinstance(n, (ast.Name, ast.Call)) for n in ast.walk(node))


class Ctx:
    """What the floors know about names. ``alias`` maps every imported name to its dotted path. A method cell runs one of the product's
    ``method_entrypoints`` (dotted names, ``module.function`` or ``module.Class``) or a method of an object built from one (``objects``);
    with no list declared the modules of ``method_packages`` and of the pipeline stand in (the product is told to declare it). ``bound``
    holds the names taken from a pinned reference implementation (level 3) and, with no entry points, from those modules."""

    def __init__(self, bar: dict, entry: set[str] | None = None, artifacts: set[str] | None = None,
                 reexport: dict[str, str] | None = None, factories: set[str] | None = None) -> None:
        self.bound: dict[str, tuple[str, str]] = {}   # name -> (dotted module path, kind)
        self.alias: dict[str, str] = {}               # name -> dotted path, for every import
        self.objects: set[str] = set()                # names holding an object an entry point built
        self.entry, self.artifacts = entry, artifacts or set()
        self.reexport = reexport or {}
        self.entry_canon = {self.canon(e) for e in entry} if entry is not None else None
        self.factories = {self.canon(f) for f in factories or ()}   # functions whose return value is a method object
        cfg = bar.get("non_method", {})
        self.callee_re = re.compile(cfg.get("callee", r"^$"), re.I)
        self.modules = set(cfg.get("modules", []))

    def bind(self, tree: ast.Module, methods: dict[str, str]) -> None:
        """Record the imports of this tree, and bind the names it takes from a reference (or, with no entry points, a method) module."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    local = a.asname or a.name.split(".")[0]
                    self.alias[local] = a.name if a.asname else a.name.split(".")[0]
                    if (kind := methods.get(a.name.split(".")[0])):
                        self.bound[local] = (self.alias[local], kind)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                for a in node.names:
                    local = a.asname or a.name
                    self.alias[local] = f"{node.module}.{a.name}"
                    if (kind := methods.get(node.module.split(".")[0])):
                        self.bound[local] = (node.module, kind)

    def loader(self, name: str) -> bool:
        return name in READ_CALLS or bool(self.callee_re.search(name))

    def dotted(self, node: ast.AST) -> str | None:
        """The dotted path of a name or attribute chain whose root is an import (``sir.simulate`` is ``pipeline.model.sir.simulate``)."""
        parts: list[str] = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name) and node.id in self.alias:
            return ".".join([self.alias[node.id], *reversed(parts)])
        return None

    def artifact(self, call: ast.Call) -> bool:
        return self.dotted(call.func) in self.artifacts

    def canon(self, dotted: str) -> str:
        """A dotted name as the package defines it, a re-export (``pkg.score`` for ``pkg.core.score``) resolved."""
        return self.reexport.get(dotted, dotted)

    def class_entry(self, dotted: str | None) -> bool:
        """Whether a dotted name is a declared entry point that is a class (CapWords), or a member of one (a constructor or a factory)."""
        if dotted is None or self.entry_canon is None:
            return False
        parts = dotted.split(".")
        return any(parts[k - 1][:1].isupper() and self.canon(".".join(parts[:k])) in self.entry_canon for k in range(len(parts), 0, -1))

    def object_call(self, node: ast.AST) -> bool:
        """Whether a call builds an object whose methods count: a constructor or a factory of a declared class, a method of such an object,
        a chain from one. The return value of a function entry point is data, never an object."""
        if not isinstance(node, ast.Call):
            return False
        d = self.dotted(node.func)
        if self.class_entry(d) or (d is not None and self.canon(d) in self.factories):
            return True
        f = node.func
        return isinstance(f, ast.Attribute) and f.attr not in BUILTIN_METHODS and self.object_base(f.value)

    def object_base(self, base: ast.AST) -> bool:
        """The object itself (a name bound to one, an item of a table of them, a chain of calls from one), never an attribute of it."""
        while isinstance(base, ast.Subscript):
            base = base.value
        return (isinstance(base, ast.Name) and base.id in self.objects) or self.object_call(base)

    def builds(self, node: ast.AST) -> bool:
        """Whether a value is an object of a declared class, or a table that holds one."""
        if isinstance(node, (ast.Dict, ast.List, ast.Tuple, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)):
            return any(self.object_call(n) for n in ast.walk(node))
        return self.object_call(node)

    def entry_call(self, call: ast.Call) -> str | None:
        """``product`` for a call of an entry point, or of a method (not of a builtin container) of an object built from a declared class."""
        if self.entry_canon is None:
            return None
        d = self.dotted(call.func)
        if (d is not None and (self.canon(d) in self.entry_canon or self.canon(d) in self.factories)) or self.class_entry(d):
            return "product"
        f = call.func
        if isinstance(f, ast.Attribute) and f.attr not in BUILTIN_METHODS and not is_constant_args(call) and self.object_base(f.value):
            return "product"
        return None

    def kind_of(self, call: ast.Call) -> str | None:
        """``product`` or ``reference`` when the call runs the product's method (an entry point, a method of what one built) or a pinned
        reference implementation; None for everything else: a reader, a loader, a version print, a lookup, a dunder chain, a call into
        the pipeline's io, schema or config modules."""
        names = chain_names(call.func)
        if any(n.startswith("__") and n.endswith("__") for n in names):
            return None
        if (kind := self.entry_call(call)):
            return kind
        root = root_name(call.func)
        if root not in self.bound or (self.entry is not None and self.bound[root][1] != "reference"):
            return None
        path, kind = self.bound[root]
        if self.modules & (set(path.split(".")) | set(names[1:])) or self.loader(callee(call)):
            return None
        return kind


def is_constant_args(call: ast.Call) -> bool:
    """A call with no argument that is a name or a call: it takes nothing the notebook read or computed."""
    return all(is_constant(a) for a in [*call.args, *(k.value for k in call.keywords)])


class CallCounter(ast.NodeVisitor):
    """The calls a cell executes that run the product's method (kinds in ``kinds``). A function, class or lambda body is not executed by
    defining it, a branch that never runs is not either, an unconsumed generator is not, and what an entry point builds is bound as an
    object for the cells after it."""

    def __init__(self, ctx: Ctx) -> None:
        self.ctx, self.kinds = ctx, []

    def visit_FunctionDef(self, node: ast.AST) -> None:
        return None

    visit_AsyncFunctionDef = visit_ClassDef = visit_Lambda = visit_FunctionDef

    def visit_If(self, node: ast.If) -> None:
        if isinstance(node.test, ast.Constant) and not node.test.value:
            for s in node.orelse:
                self.visit(s)
            return
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if not isinstance(node.value, ast.GeneratorExp):
            self.visit(node.value)
        names = [n.id for t in node.targets for n in ast.walk(t) if isinstance(n, ast.Name)]
        dotted = self.ctx.dotted(node.value) if isinstance(node.value, (ast.Name, ast.Attribute)) else None
        for name in names:  # an alias made by assignment is followed; a name rebound to anything else loses its alias and its object
            if dotted:
                self.ctx.alias[name] = dotted
            else:
                self.ctx.alias.pop(name, None)
            self.ctx.objects.discard(name)
        if self.ctx.builds(node.value):
            self.ctx.objects.update(names)

    def _comprehension(self, node: ast.AST) -> None:
        for g in node.generators:  # a comprehension over an empty literal never runs its element
            it = g.iter
            if (isinstance(it, (ast.List, ast.Tuple, ast.Set)) and not it.elts) or (isinstance(it, ast.Dict) and not it.keys):
                return
        self.generic_visit(node)

    visit_ListComp = visit_SetComp = visit_DictComp = visit_GeneratorExp = _comprehension

    def visit_Call(self, node: ast.Call) -> None:
        if kind := self.ctx.kind_of(node):
            self.kinds.append(kind)
        self.generic_visit(node)


def calls_method(tree: ast.AST, ctx: Ctx) -> bool:
    """A method call anywhere in the tree, function bodies included (it keeps a method out of a setup cell)."""
    return any(isinstance(n, ast.Call) and ctx.kind_of(n) for n in ast.walk(tree))


def calls_plot(tree: ast.AST) -> bool:
    return any(isinstance(n, ast.Call) and callee(n) in PLOT_CALLS for n in ast.walk(tree))


def reads(call: ast.Call, ctx: Ctx, readers: set[str]) -> bool:
    return callee(call) in readers or ctx.loader(callee(call))


def benign_value(value: ast.AST, ctx: Ctx, readers: set[str]) -> bool:
    """A value a setup assignment may hold: it reads or locates something (calls among the reading, path and light-reshaping names, a
    reader the notebook defined, a loader), or it is a path built with ``/`` or a plain pick out of a name."""
    calls = [n for n in ast.walk(value) if isinstance(n, ast.Call)]
    if calls:
        return all(callee(c) in BENIGN_CALLS or reads(c, ctx, readers) for c in calls)
    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Div):
        return all(isinstance(n, (ast.Name, ast.Constant, ast.BinOp, ast.Div, ast.Attribute, ast.Load)) for n in ast.walk(value))
    nodes = list(ast.walk(value))
    # no call: a pick out of data already read (names, subscripts, comprehensions), never arithmetic and never bare constants
    return not any(isinstance(n, ast.BinOp) for n in nodes) and any(isinstance(n, ast.Name) for n in nodes)


def is_version_print(call: ast.Call) -> bool:
    return ast.unparse(call.func) == "print" and any(
        (isinstance(n, ast.Call) and callee(n) == "version") or (isinstance(n, ast.Attribute) and n.attr == "__version__")
        for n in ast.walk(call))


def holds_read(value: ast.AST, ctx: Ctx, readers: set[str], read_data: set[str]) -> bool:
    """Whether an expression reads a file or picks out of what was read."""
    return any((isinstance(m, ast.Call) and reads(m, ctx, readers)) or (isinstance(m, ast.Name) and m.id in read_data) for m in ast.walk(value))


def collect_reads(tree: ast.Module, ctx: Ctx, readers: set[str], read_data: set[str]) -> None:
    """Record the names this cell assigns from a read (an assignment or a loop over read data that runs no method)."""
    for n in ast.walk(tree):
        if isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None and not calls_method(n.value, ctx) \
                and holds_read(n.value, ctx, readers, read_data):
            for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                read_data.update(x.id for x in ast.walk(t) if isinstance(x, ast.Name))
        elif isinstance(n, ast.For) and holds_read(n.iter, ctx, readers, read_data):
            read_data.update(x.id for x in ast.walk(n.target) if isinstance(x, ast.Name))


def prints_read_data(call: ast.Call, ctx: Ctx, readers: set[str], read_data: set[str]) -> bool:
    """A print or display of read data: names of what a notebook read, and no arithmetic and no call but a reader or a light reshaping."""
    args = [*call.args, *(k.value for k in call.keywords)]
    nodes = [m for a in args for m in ast.walk(a)]
    if any(isinstance(m, ast.BinOp) for m in nodes):
        return False
    inner = [m for m in nodes if isinstance(m, ast.Call)]
    if not all(callee(m) in BENIGN_CALLS or callee(m) == "print" or reads(m, ctx, readers) for m in inner):
        return False
    return any(isinstance(m, ast.Name) and m.id in read_data for m in nodes)


def scaffolding(stmt: ast.stmt, ctx: Ctx, readers: set[str], read_data: set[str]) -> bool:
    """One statement of a setup or input/output cell: an import, a version print, path discovery, a reader definition, a plain
    assignment of read data, a print of read data; never a method call and never a plot."""
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
        # a reader reads a file, even when it builds the product's own parameter object from it; a wrapper around a method is no reader
        has_read = any(isinstance(n, ast.Call) and callee(n) in READ_CALLS for n in ast.walk(stmt))
        return not calls_plot(stmt) and (has_read or not calls_method(stmt, ctx))
    if calls_method(stmt, ctx) or calls_plot(stmt):
        return False
    if isinstance(stmt, (ast.Import, ast.ImportFrom)):
        return True
    if isinstance(stmt, ast.Expr):
        v = stmt.value
        if isinstance(v, ast.Constant):
            return True
        return isinstance(v, ast.Call) and (bool(CONFIG_CALL.match(ast.unparse(v.func))) or is_version_print(v)
                                            or (callee(v) in {"print", "display"} and prints_read_data(v, ctx, readers, read_data))
                                            or (callee(v) in {"head", "tail", "describe", "info"} and root_name(v.func) in read_data))
    if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and stmt.value is not None:
        return benign_value(stmt.value, ctx, readers)
    if isinstance(stmt, (ast.For, ast.If, ast.With, ast.Try)):
        head = [stmt.iter] if isinstance(stmt, ast.For) else ([stmt.test] if isinstance(stmt, ast.If) else [])
        listed = [h for h in head if isinstance(h, (ast.Tuple, ast.List)) and all(isinstance(e, ast.Constant) for e in h.elts)]
        if not all(h in listed or benign_value(h, ctx, readers) for h in head):
            return False
        inner = [*stmt.body, *getattr(stmt, "orelse", [])]
        return bool(inner) and all(scaffolding(s, ctx, readers, read_data) for s in inner)
    return False


def mentions(node: ast.AST, tainted: set[str], derived_fns: set[str], ctx: Ctx, computed: frozenset[str] | set[str] = frozenset()) -> bool:
    """Whether an expression holds a committed result: a ``data/derived/`` path in a string, a name assigned from one (and not recomputed
    since), a call to a function of the notebook that builds such a path, or a call of one of the loaders ``product.json`` declares
    in ``artifact_loaders`` (a measurement a notebook compares with is not a committed result of the product). What a method call returns was computed here, however it was fed, so its arguments are not looked at."""
    if isinstance(node, ast.Call) and ctx.kind_of(node):
        return False
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and "derived" in node.value:
        return True
    if isinstance(node, ast.Name) and node.id in tainted and node.id not in computed:
        return True
    if isinstance(node, ast.Call) and (callee(node) in derived_fns or ctx.artifact(node)):
        return True
    return any(mentions(ch, tainted, derived_fns, ctx, computed) for ch in ast.iter_child_nodes(node))


def walk_reporting(node: ast.AST):
    """The nodes of a tree that report a value, leaving out the tests of ``if``, ``while`` and conditional expressions and the filters of
    comprehensions (a comparison there selects, it does not report)."""
    yield node
    for field, value in ast.iter_fields(node):
        if (isinstance(node, (ast.If, ast.While, ast.IfExp)) and field == "test") or (isinstance(node, ast.comprehension) and field == "ifs"):
            continue
        for child in value if isinstance(value, list) else [value]:
            if isinstance(child, ast.AST):
                yield from walk_reporting(child)


def validation_like(test: ast.AST) -> bool:
    """An assert that validates an input (a shape, a length, a type, ``is None``), not a result."""
    for n in ast.walk(test):
        if isinstance(n, ast.Attribute) and n.attr in VALIDATION_ATTRS:
            return True
        if isinstance(n, ast.Call) and callee(n) in VALIDATION_CALLS:
            return True
        if isinstance(n, ast.Compare) and any(isinstance(c, ast.Constant) and c.value is None for c in n.comparators):
            return True
    return False


def is_reproduction(tree: ast.Module, tainted: set[str], derived_fns: set[str], ctx: Ctx, computed: set[str]) -> bool:
    """A cell that checks a recomputed value against a committed one: ``allclose``, ``array_equal``, anything under ``numpy.testing``,
    an ``assert`` of a result, an ``isclose`` that reports, or a ``==``, ``!=`` or difference that sets a value read from a committed
    result (``data/derived/``, a loader of the package) against a value the notebook computed."""
    parent = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}

    def committed(a: ast.AST) -> bool:
        return mentions(a, tainted, derived_fns, ctx, computed)

    def recomputed(a: ast.AST) -> bool:
        return any((isinstance(m, ast.Name) and m.id in computed) or (isinstance(m, ast.Call) and ctx.kind_of(m)) for m in ast.walk(a))

    def sets_against(a: ast.AST, b: ast.AST) -> bool:
        both = all(any(isinstance(m, (ast.Name, ast.Call)) for m in ast.walk(x)) for x in (a, b))
        return both and ((committed(a) and recomputed(b)) or (committed(b) and recomputed(a)))

    for n in ast.walk(tree):
        if isinstance(n, ast.Assert) and not validation_like(n.test) and (committed(n.test) or recomputed(n.test)):
            return True
        if isinstance(n, ast.Call):
            name = callee(n)
            if "testing" in ast.unparse(n.func).split("."):
                return True
            if name.startswith("assert_"):
                if root_name(n.func) in ctx.alias:
                    continue  # the product's own refusal (blastfrag.splits.assert_no_leakage) is the method at work, not a check
                return True
            if name in COMPARE_CALLS:
                return True
            if name == "isclose":
                p = parent.get(n)
                if isinstance(p, (ast.Expr, ast.Assign, ast.Assert, ast.UnaryOp, ast.BoolOp)) or \
                        (isinstance(p, ast.Call) and callee(p) in {"print", "all", "any", "bool"}):
                    return True
    for n in walk_reporting(tree):
        if isinstance(n, ast.Compare) and any(isinstance(o, (ast.Eq, ast.NotEq)) for o in n.ops) and len(n.comparators) == 1 \
                and sets_against(n.left, n.comparators[0]):
            return True
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Sub) and sets_against(n.left, n.right):
            return True
    return False


def taint_cell(tree: ast.Module, tainted: set[str], derived_fns: set[str], readers: set[str], ctx: Ctx) -> None:
    """Record what this cell defines: readers (a function that reads a file), derived readers (one that builds a ``derived`` path)
    and the names assigned from a committed result."""
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(isinstance(m, ast.Call) and (callee(m) in READ_CALLS or callee(m) in readers) for m in ast.walk(n)):
                readers.add(n.name)
            if any(isinstance(m, ast.Constant) and isinstance(m.value, str) and "derived" in m.value for m in ast.walk(n)) \
                    or any(isinstance(m, ast.Call) and callee(m) in derived_fns for m in ast.walk(n)):
                derived_fns.add(n.name)
        elif isinstance(n, ast.Assign) and mentions(n.value, tainted, derived_fns, ctx) and not calls_method(n.value, ctx):
            # what a method call returns was computed here, however it was fed
            for t in n.targets:
                tainted.update(x.id for x in ast.walk(t) if isinstance(x, ast.Name))


def note_computed(tree: ast.Module, ctx: Ctx, computed: set[str]) -> None:
    """Record the names this cell assigns from a method call: values the notebook computed."""
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(isinstance(m, ast.Call) and ctx.kind_of(m) for m in ast.walk(n.value)):
            for t in n.targets:
                computed.update(x.id for x in ast.walk(t) if isinstance(x, ast.Name))


def output_text(cell: dict) -> str:
    """The text a cell's outputs show: streams, plain text and HTML results."""
    out: list[str] = []
    for o in cell.get("outputs", []) or []:
        if isinstance(o, dict):
            out.append(text_of(o.get("text", "")))
            for mime in ("text/plain", "text/html"):
                out.append(text_of((o.get("data") or {}).get(mime, "")))
    return "\n".join(out)


def figures_of(cell: dict, seen: set[str]) -> int:
    """The figures a cell shows that no earlier cell of the notebook showed: an image or a plotly output, counted once by its content."""
    n = 0
    for o in cell.get("outputs", []) or []:
        for mime in FIGURE_MIMES:
            payload = (o.get("data") or {}).get(mime) if isinstance(o, dict) else None
            if payload:
                key = hashlib.sha1((mime + json.dumps(payload, sort_keys=True)).encode("utf-8")).hexdigest()
                if key not in seen:
                    seen.add(key)
                    n += 1
                break
    return n


def has_table(cell: dict) -> bool:
    """A table in a markdown cell (a separator row) or in an output (an HTML table)."""
    if cell["cell_type"] == "markdown":
        return bool(re.search(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$", text_of(cell["source"]), re.M))
    return "<table" in output_text(cell)


def sentences_of(text: str) -> list[str]:
    """The sentences of a markdown text, in order: markup stripped, whitespace collapsed, split at blank lines, list items and at ``.``,
    ``:`` or ``;`` followed by whitespace; lower case for the comparison."""
    out: list[str] = []
    for block in re.split(r"\n\s*\n|\n(?=\s*(?:[-*+]|\d+[.)])\s)", strip_markup(text)):
        flat = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", re.sub(r"\s+", " ", block).strip())
        out.extend(s.strip().lower() for s in re.split(r"(?<=[.:;])\s+", flat) if s.strip())
    return out


def long_sentences(text: str, minimum: int) -> set[str]:
    """The sentences of a markdown text longer than ``minimum`` characters."""
    return {s for s in sentences_of(text) if len(s) > minimum}


def fingerprint(sentence: str) -> str:
    return hashlib.sha1(sentence.encode("utf-8")).hexdigest()[:12]


class Reading:
    """What the floors read out of one notebook: its text by section, its method cells, figures, setup and reproduction cells."""

    def __init__(self, nb: dict, lang: str, root: Path, bar: dict) -> None:
        caos = nb["metadata"].get("caos")
        lv = caos.get("level") if isinstance(caos, dict) else None
        self.level = lv if isinstance(lv, int) and not isinstance(lv, bool) and lv in {1, 2, 3, 4} else 0
        self.lang, self.cells, self.bar = lang, nb["cells"], bar
        methods = method_modules(root, caos, self.level, bar)
        self.section: list[str | None] = []     # the section each cell sits in (English name); None before the first heading
        self.md_lines: list[tuple[str | None, str]] = []
        self.prose_sections: dict[str | None, list[str]] = {}
        self.method_cells: list[int] = []
        self.product_cells: list[int] = []
        self.setup_cells: list[int] = []
        self.repro_cells: list[int] = []
        self.fig_cells: list[tuple[int, int]] = []   # (cell index, figures)
        self.line_findings: list[str] = []
        entry, _ = product_names(root, "method_entrypoints")
        artifacts, _ = product_names(root, "artifact_loaders")
        factories, _ = product_names(root, "method_factories")
        ctx = Ctx(bar, entry, artifacts, reexport_map(root, bar, entry), factories)
        readers: set[str] = set()
        read_data: set[str] = set()
        tainted: set[str] = set()
        derived_fns: set[str] = set()
        computed: set[str] = set()
        seen_figures: set[str] = set()
        current: str | None = None
        for i, c in enumerate(self.cells):
            if c["cell_type"] == "markdown":
                fenced = False
                for line in text_of(c["source"]).splitlines():
                    if FENCE.match(line):
                        fenced = not fenced
                    elif not fenced and (m := HEADING2.match(line)):
                        current = SECTION_EN.get(m[1].strip(), m[1].strip())
                    self.md_lines.append((current, line))
                    self.prose_sections.setdefault(current, []).append(line)
                self.section.append(current)
                continue
            self.section.append(current)
            code = text_of(c["source"])
            if n := figures_of(c, seen_figures):
                self.fig_cells.append((i, n))
            tree = parse_code(code)
            self.line_findings.extend(self.layout_of(i + 1, code, tree))
            if tree is None:
                continue
            ctx.bind(tree, methods)
            counter = CallCounter(ctx)
            counter.visit(tree)
            taint_cell(tree, tainted, derived_fns, readers, ctx)
            collect_reads(tree, ctx, readers, read_data)
            if counter.kinds:
                self.method_cells.append(i)
                if "product" in counter.kinds:
                    self.product_cells.append(i)
            elif tree.body and all(scaffolding(s, ctx, readers, read_data) for s in tree.body):
                self.setup_cells.append(i)
            note_computed(tree, ctx, computed)
            if is_reproduction(tree, tainted, derived_fns, ctx, computed):
                self.repro_cells.append(i)

    def layout_of(self, number: int, code: str, tree: ast.Module | None) -> list[str]:
        """The cell's layout findings: a line too long, too many lines of logic, two statements on one line."""
        out: list[str] = []
        f = self.bar["floors"]
        longest = max((len(ln) for ln in code.splitlines()), default=0)
        if longest > f["line_chars_max"]:
            out.append(f"code cell {number} has a line of {longest} characters, the limit is {f['line_chars_max']}")
        logic = sum(1 for ln in code.splitlines() if ln.strip() and not ln.strip().startswith("#"))
        if logic > f["logic_lines_max"]:
            out.append(f"code cell {number} has {logic} lines of logic, the limit is {f['logic_lines_max']}")
        if tree is not None:
            lines: dict[int, int] = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.stmt) and not isinstance(node, COMPOUND):
                    lines[node.lineno] = lines.get(node.lineno, 0) + 1
                if isinstance(node, INLINE_BODY) and node.body and node.body[0].lineno == node.lineno:
                    out.append(f"code cell {number} line {node.lineno} holds a compound statement and its body, one statement per line")
            for ln in sorted(k for k, v in lines.items() if v > 1):
                out.append(f"code cell {number} line {ln} holds {lines[ln]} statements, one statement per line")
        return out

    def prose(self, left_out: set[str | None]) -> str:
        return "\n".join("\n".join(v) for k, v in self.prose_sections.items() if k not in left_out)

    def units(self) -> list[str]:
        """The sentences of the explanatory prose, in order."""
        return sentences_of(self.prose(SCAFFOLD_SECTIONS))

    def heavy(self) -> dict[str, int]:
        """The sentences of the notebook that occur more than twice in it, with their number of occurrences. A heading and a label or a
        sentence of fewer than four words ("Units: days.", "See the figure.") may come back; the once-only word count still applies to them."""
        counts: dict[str, int] = {}
        for sentence in self.units():
            if not sentence.startswith("#") and count_words(sentence) >= HEAVY_WORDS:
                counts[sentence] = counts.get(sentence, 0) + 1
        return {k: v for k, v in counts.items() if v > 2}

    def words(self) -> int:
        """The words of the explanatory prose, every sentence counted once however often it is repeated."""
        seen: set[str] = set()
        total = 0
        for sentence in self.units():
            if sentence not in seen:
                seen.add(sentence)
                total += count_words(sentence)
        return total

    def sentences(self) -> set[str]:
        return long_sentences(self.prose(SCAFFOLD_SECTIONS | {None}), self.bar["floors"]["long_sentence_chars"])

    def question(self) -> str:
        """The paragraph of the first cell that states the question, normalised; empty when there is none."""
        first = text_of(self.cells[0]["source"]) if self.cells and self.cells[0]["cell_type"] == "markdown" else ""
        marker = MARKERS[self.lang][0]
        if marker not in first:
            return ""
        return re.sub(r"\s+", " ", re.split(r"\n\s*\n|\n\s*[-*]\s", first[first.index(marker):], maxsplit=1)[0]).strip().lower()


def candidates(token: str) -> list[tuple[float, float]]:
    """The values a written number can mean, each with the half-width of the rounding it was written with: a decimal comma or point, a
    thousands separator, an exponent, a percent sign."""
    t = token.strip()
    percent = t.endswith("%")
    t = t.rstrip("% ").lstrip("+")
    exponent = 0
    m = re.match(r"^(.*?)[eE]([-+]?\d+)$", t)
    if m:
        t, exponent = m[1], int(m[2])
    reading: list[tuple[str, int]] = []   # (digits with a point, decimals)
    body = t.lstrip("-")
    seps = re.findall(r"[.,]", body)
    if not seps:
        reading.append((body, 0))
    else:
        last = max(body.rfind("."), body.rfind(","))
        head, tail = body[:last], body[last + 1:]
        if not re.search(r"[.,]", head) or re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", head):
            reading.append((re.sub(r"[.,]", "", head) + "." + tail, len(tail)))   # the last mark is the decimal mark
        if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", body):
            reading.append((re.sub(r"[.,]", "", body), 0))                          # every mark is a thousands separator
    out: list[tuple[float, float]] = []
    for digits, decimals in reading:
        if abs(exponent) > 300:
            continue  # beyond any float a notebook prints
        value = float(digits) * (-1 if t.startswith("-") else 1) * 10.0 ** exponent
        half = 0.5 * 10.0 ** (exponent - decimals)
        out.append((value / 100, half / 100) if percent else (value, half))
    return out


def number_tokens(text: str) -> list[str]:
    """The numbers of a text, without version numbers and dates."""
    return [m.group(0) for m in NUMBER.finditer(DATE.sub(" ", VERSION.sub(" ", text)))]


def answer_matches(paragraph: str, outputs: str) -> tuple[bool, list[str]]:
    """Whether a number the answer quotes agrees, to the precision it is written with, with a number an output shows. Years, lone digits,
    version numbers and dates never count as the answer's numbers."""
    quoted: list[str] = []
    for tok in number_tokens(paragraph):
        core = tok.strip().rstrip("% ")
        if re.fullmatch(r"[-+]?\d", core) or re.fullmatch(r"(?:19\d\d|20\d\d|2100)", core.lstrip("+")):
            continue
        if re.fullmatch(r"[-+]?\d[eE][-+]?\d+", core):
            continue  # one significant digit and an exponent: any number of that order matches
        quoted.append(tok.strip())
    shown = [v for tok in number_tokens(outputs) for v, _ in candidates(tok)]
    for tok in quoted:
        for value, half in candidates(tok):
            signed = tok.strip().startswith(("-", "+"))
            if any(abs((o if signed else abs(o)) - (value if signed else abs(value))) <= half * (1 + 1e-9) + 1e-12 for o in shown):
                return True, quoted
    return False, quoted


def reading_findings(rel: str, r: Reading, bar: dict) -> list[str]:
    out: list[str] = []
    level = r.level or FLOOR_LEVEL_DEFAULT
    f = bar["floors"]
    tag = f"the floor at level {level} is" if r.level else f"the floor at level {FLOOR_LEVEL_DEFAULT} (no valid level declared) is"

    def below(measure: str, value: int, floor: int) -> None:
        if value < floor:
            out.append(f"{rel}: bar: {measure} {value}, {tag} {floor}")

    def above(measure: str, value: int, floor: int, why: str) -> None:
        if value > floor:
            out.append(f"{rel}: bar: {measure} {value}, the floor is at most {floor} ({why})")

    below("method cells", len(r.method_cells), floor_at(bar, "method_cells", level))
    if r.level == 3:
        below("method cells that call the product's own method (package or pipeline)", len(r.product_cells), f["level3_product_cells_min"])
    below("figures", sum(n for _, n in r.fig_cells), floor_at(bar, "figures", level))
    below("explanatory prose words", r.words(), floor_at(bar, "prose_words", level))
    above("setup and input/output cells", len(r.setup_cells), f["setup_cells_max"], "one setup cell holds the imports, versions and readers")
    above("reproduction checks", len(r.repro_cells), f["reproduction_checks_max"], "checking an artifact is the test suite's job")
    if (heavy := r.heavy()):
        first = max(heavy, key=heavy.get)
        out.append(f"{rel}: bar: {len(heavy)} sentences occur more than twice inside the notebook, none is allowed "
                   f"(first: {first[:60]!r} x{heavy[first]}): prose is written once per idea")
    enough = f["words_after_figure"]
    for i, _ in r.fig_cells:
        nxt = r.cells[i + 1] if i + 1 < len(r.cells) else None
        if nxt is None or nxt["cell_type"] != "markdown":
            out.append(f"{rel}: bar: the figure of code cell {i + 1} is not followed by a markdown cell that reads it")
        elif (n := words_of(text_of(nxt["source"]))) < enough:
            out.append(f"{rel}: bar: the figure of code cell {i + 1} is followed by {n} words, the floor is {enough}")
    flat = " ".join(" ".join(ln for _, ln in r.md_lines).split()).lower()
    for sentence in bar["filler"]:
        if sentence.lower() in flat:
            out.append(f"{rel}: bar: generic filler sentence {sentence!r} (it would fit any product)")
    question, answer = MARKERS[r.lang]
    if not r.question():
        out.append(f"{rel}: bar: the first cell does not state the question ({question})")
    results = "\n".join(r.prose_sections.get("Results", []))
    if answer not in results:
        out.append(f"{rel}: bar: the Results section does not answer it ({answer})")
    else:
        paragraph = re.split(r"\n\s*\n", results[results.index(answer):], maxsplit=1)[0]
        computed_outputs = "\n".join(output_text(c) for i, c in enumerate(r.cells) if c["cell_type"] == "code" and r.section[i] != "Setup")
        ok, quoted = answer_matches(paragraph, computed_outputs)
        if not ok:
            out.append(f"{rel}: bar: the answer quotes no number that appears in an output of the notebook, at the precision the answer writes it "
                       f"(numbers in the answer: {quoted[:6]})")
    if r.level == 3:
        if not [i for i in r.method_cells if r.section[i] == COMPARISON_SECTION]:
            out.append(f"{rel}: bar: no method cell under {COMPARISON_SECTION}: a level 3 notebook runs the published method it compares")
        if not sum(n for i, n in r.fig_cells if r.section[i] == COMPARISON_SECTION):
            out.append(f"{rel}: bar: no figure under {COMPARISON_SECTION}: a level 3 notebook compares the methods with a figure")
    if r.level == 4:
        shown_beyond = sum(n for i, n in r.fig_cells if r.section[i] == EVIDENCE_SECTION) \
            + sum(1 for i, c in enumerate(r.cells) if r.section[i] == EVIDENCE_SECTION and has_table(c))
        if not shown_beyond:
            out.append(f"{rel}: bar: no figure or table under {EVIDENCE_SECTION}: a level 4 notebook measures its claim")
    out.extend(f"{rel}: bar: {message}" for message in r.line_findings)
    return out


def example_fingerprints(root: Path, bar: dict) -> list[str]:
    """The fingerprints of the long sentences of the example notebooks of ``root``, both trees."""
    out: set[str] = set()
    for lang in LANGS:
        for path in sorted((root / "notebooks" / lang).rglob("*.ipynb")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
                out.update(fingerprint(s) for s in Reading(doc, lang, root, bar).sentences())
            except (OSError, ValueError, KeyError, TypeError):
                continue
    return sorted(out)


def write_fingerprints(root: Path) -> int:
    """Rewrite ``example_fingerprints`` of ``scripts/notebook_bar.json`` from the example notebooks of ``root`` (run it when the
    template's example notebooks change)."""
    bar = load_bar()
    bar["example_fingerprints"] = " ".join(example_fingerprints(root, bar))
    BAR_FILE.write_text(json.dumps(bar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return len(bar["example_fingerprints"].split())


def bar_findings(root: Path, docs: dict[str, dict[str, dict]], bar: dict | None = None) -> list[str]:
    """The floors of the bar for every parsed notebook, the sentences and questions shared inside one tree, and the sentences copied from the
    template's example (a product has no sentinel file; the template itself does and is left out)."""
    bar = bar or load_bar()
    out: list[str] = []
    template = (root / SENTINEL).exists()
    entry, malformed = product_names(root, "method_entrypoints")
    if any(docs.get(lang) for lang in LANGS) and not entry:
        out.append("product.json: bar: " + ("method_entrypoints must be a list of dotted names (module.function or module.Class)" if malformed else
                   "product.json declares no method_entrypoints: the dotted names (module.function or module.Class) that run the product's "
                   "method, without which a call of the method cannot be told from a lookup"))
    copied = set(str(bar.get("example_fingerprints", "")).split())
    for lang in LANGS:
        readings = {key: Reading(doc, lang, root, bar) for key, doc in docs.get(lang, {}).items()}
        for key, r in readings.items():
            out.extend(reading_findings(f"notebooks/{lang}/{key}", r, bar))
        owners: dict[str, set[str]] = {}
        for key, r in readings.items():
            for s in r.sentences():
                owners.setdefault(s, set()).add(key)
        maximum = bar["floors"]["repeated_sentences_max"]
        minimum = bar["floors"]["long_sentence_chars"]
        questions: dict[str, list[str]] = {}
        for key, r in readings.items():
            if q := r.question():
                questions.setdefault(q, []).append(key)
        for key, r in readings.items():
            shared = sorted(s for s in r.sentences() if len(owners[s]) > 1)
            if len(shared) > maximum:
                out.append(f"notebooks/{lang}/{key}: bar: {len(shared)} sentences over {minimum} characters "
                           f"are shared with another notebook of the tree, the floor is at most {maximum} (first: {shared[0][:70]!r})")
            if (q := r.question()) and len(questions[q]) > 1 and key != questions[q][0]:
                out.append(f"notebooks/{lang}/{key}: bar: the question is the one of {questions[q][0]}: no two notebooks of a tree share a question")
            if copied and not template:
                n = sum(1 for s in r.sentences() if fingerprint(s) in copied)
                if n > maximum:
                    out.append(f"notebooks/{lang}/{key}: bar: {n} sentences over {minimum} characters are copied from the template's example "
                               f"notebooks, the floor is at most {maximum}: write the notebook for this product")
    return out


def findings_of(root: Path, infos: list[str] | None = None, bar: dict | None = None) -> list[str]:
    """Every finding: the form of the notebooks, then the floors of the bar."""
    docs: dict[str, dict[str, dict]] = {}
    findings = form_findings(root, infos, docs)
    findings.extend(bar_findings(root, docs, bar))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(prog="check_notebooks", description=__doc__.split(chr(10))[0])
    ap.add_argument("root", nargs="?", help="the repository root (default: this script's repository)")
    ap.add_argument("--pypi", action="store_true",
                    help="also read PyPI for the pin of each method package (opt-in, needs the network, never CI)")
    ap.add_argument("--write-fingerprints", action="store_true",
                    help="rewrite example_fingerprints of scripts/notebook_bar.json from this repository's notebooks (template maintainers)")
    a = ap.parse_args()
    root = Path(a.root).resolve() if a.root else Path(__file__).resolve().parents[1]
    if a.write_fingerprints:
        print(f"check_notebooks: {write_fingerprints(root)} example fingerprints written to {BAR_FILE.name}")
        return 0
    infos: list[str] = []
    findings = findings_of(root, infos)
    if a.pypi:
        findings.extend(pypi_findings(root))
    for line in infos:
        print(line)
    if findings:
        print("NOTEBOOKS CHECK FAILED:")
        for f in findings:
            print(f"  - {f}")
        return 1
    count = sum(1 for _ in (root / "notebooks").rglob("*.ipynb"))
    print(f"check_notebooks: OK, {count} notebooks in two trees, mirrored, ordered, annotated and clean"
          + (", method-package pins published on PyPI" if a.pypi and method_packages(root) else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
