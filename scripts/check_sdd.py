#!/usr/bin/env python3
"""T10, the SDD gate (ADR-0075, ADR-0078): a design document exists, and every requirement names a gate that is real.

Mirrored from CAOS_OreFlow's scripts/check_sdd.py (the validated reference, 2026-09-28), with two additions: the
ADR-fit section ADR-0078 requires in every SDD, and named TypeScript test cases (``file.test.ts::name``) checked the
way pytest cases are. Hardened after the adversarial reviews of the shell's port (PR #100) and of release 0.05.000
(CAOS_MANAGE ``wip/product-template/review-0-05-000-guards-2026-10-11.md``): a gate is a live test, never a name that
only appears in a string, a comment, another test's body or a skipped test.

Checks, in increasing strength:

0. **The executive view** (CAOS_MANAGE ``conventions/problem-context-first.md``, decided 2026-10-13; template 0.07.000): the
   product commits ``content/executive.json``, valid against the shell's ``executive.schema.json`` version 2.0.0 (read from
   ``frontend/node_modules/@fasl-work/caos-app-shell/src/content/``; without ``npm ci``, or with an older schema, the check
   fails and says so, never passes), each finding naming the field path. The file frames a problem space for a decision
   maker: a title, a key statement, headline figures, the five sub-tabs (pain, context, situation, trends, proposal) at their
   floors and the three illustrations (pain, situation, proposal). On top of the schema the check holds what a schema
   cannot say, the same rules as the shell's ``validateExecutive``: the 4 C's in order, the weights of the causes at most
   100, every action owner a role of the situation, the writing limits in both languages (30 words a sentence, one
   sentence for key messages, captions, actions and checks, two for the key statement, 25 words a paragraph, no equation,
   no inline citation, no promotional or client-bound wording), and the sources: unique ids, every citation names one,
   every source is cited, each an https link whose title and note cite no file. The three illustration files exist under
   ``frontend/public/`` as SVG documents with a viewBox. The SDD's ``Executive brief`` section sits right after
   ``Problem and non-goals``, once, and names the file in a ``Data file: content/executive.json`` line; it restates nothing of
   the view (no part heading, list, table, sentence of the file, or more than 120 words).
   Guide: ``docs/guides/06_executive-brief.md``. Needs the ``jsonschema`` package (``requirements-dev.txt``).
1. ``docs/design/SDD.md`` has the twelve sections the convention requires, each a level-2 heading ``## <name>`` (an
   optional ``N.`` prefix) outside code fences and HTML comments, once, in order, each with a non-blank line under it;
   a research basis citing at least three distinct sources (a DOI counts once however it is written; example,
   localhost and ``.example`` hosts count for none) and a line starting ``UNVERIFIED:``; a resources table with a row
   for each of bake, tests, build and deploy and no empty or placeholder cell (``-``, ``?``, TODO, unknown, n/a, TBD).
2. Every requirement of a live feature (a row ``| ID | statement | gate |`` of
   ``docs/design/features/<slug>/requirements.md``) is stated with SHALL and has a gate cell. Every line that starts
   with ``|`` is a row: one that is indented, has fewer than three cells or has an empty or malformed ID is a finding,
   and every ID-like token of the file must be the ID of a row (a requirement written as a bullet is a finding). IDs are
   unique across all features. A folder of ``features/`` with no ``requirements.md`` is a finding.
3. **The named gate exists and can fail.** A gate cell names at least one file in backticks. Every named file is on
   disk inside the repository. ``path::name`` names a test in a Python test file (``tests/**`` or ``test_*.py``) or a
   TypeScript one (``*.test.ts``, ``*.test.tsx``, ``*.spec.*``): the name is a module-level ``def test_*`` (or a method of
   a ``class Test*``) found by parsing the file, or the whole first string argument of an ``it(``/``test(`` call that
   starts its line (not inside a string, a comment or another test's body), and it is not skipped (``@pytest.mark.skip``,
   ``skipif(True)``, ``pytestmark``, ``pytest.skip`` at module level or first in the body; ``.skip``, ``.todo``, ``xit``,
   ``{ skip: true }``). ``describe`` is not a gate. A plain path (no ``::``) is a gate only when it is a test file or a
   script under ``scripts/`` or ``frontend/scripts/``, never a document or data file.
4. **Every live feature has a ``validation.md``** (``| requirement | adversarial check | gate |``) listing each
   requirement ID exactly once, the check stated as what was planted or refuted, and the gate naming a real test that
   is adversarial: a test under ``tests/adversarial/``, or one whose name starts with ``adversarial`` (Python
   ``test_adversarial_...``, TypeScript ``it('adversarial: ...')``). Anything else proves the requirement passes, not that
   it can fail. A conditional skip (``skipif(<condition>)``, ``pytest.importorskip``) is a precondition, not a skip: such
   a test runs where its tool exists, and a requirement whose only gate needs a tool CI does not install is proven locally.

5. **The App's kind** (0.09.000, WB-015; ADR-0070): ``product.json`` says ``"app": "workbench"`` (the default) or ``"surface"``;
   ``"focus": false`` is valid only on a surface and only with a ``"focus_reason"`` of at least eight words that is no placeholder,
   and the SDD's ADR-0070 row of the ADR fit table carries the same reason as ``not applicable: <reason>``. An unknown ``app``, a
   ``focus`` that is not a boolean, a waiver on a workbench, a waiver without a reason or without its row, a reason that differs
   from the row, a reason without a waiver and a row that says ``not applicable`` while ``product.json`` records no waiver are
   findings. ``frontend/scripts/gate.mjs`` holds the same rules and refuses to run the shell gate when they fail.

6. **The three method tiers** (0.13.000; CAOS_MANAGE ``conventions/method-tiers-and-manuscripts.md``): the ``## Method ladder`` is
   a table ``| id | tier | method | acceptance criterion | gate |`` and each row's tier is ``classical``, ``sota`` (the state of
   the art) or ``beyond`` (beyond it). A product (a tree without ``.template-source``) needs a method in each tier, a section
   ``## Beyond the state of the art`` that lists at least one proposed method ``BS-<n>`` and never says "None claimed.", and a
   ``beyond`` row for each claim; the template keeps its teaching example (``None claimed.``, no ``beyond`` row) but still
   writes the table with its tier column. A ladder without the column fails and says how to add it. The notebook gate covers
   each sota method and each claim; ``scripts/check_manuscripts.py`` covers the manuscripts.

Check 3 is the one that matters: a requirement can name ``tests/test_nothing.py::test_imaginary`` and pass check 2
while verifying nothing, which is the failure the rule exists for.

``Status: planned`` and ``Status: superseded`` (one ``Status:`` line, live when absent) take a feature out of check 3 and
4 only when it is listed with a reason in ``docs/design/features/.status-allow`` (one ``<feature>: <reason>`` per line),
reviewed with the pull request that adds it; otherwise the status is a finding. A planned feature still names the file
each gate will have (counted apart, never reported as a real gate).

Standard library plus ``jsonschema`` (for check 0); exit 1 on any finding. Usage: ``python scripts/check_sdd.py [repo_root]``.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
SDD = ROOT / "docs" / "design" / "SDD.md"
FEATURES = ROOT / "docs" / "design" / "features"
ALLOW = FEATURES / ".status-allow"

SECTIONS = (
    "Problem and non-goals", "Research basis", "Sizing and contracts", "Technology and versions", "Resources", "Lanes",
    "Method ladder", "Cases", "Oracles", "Deploy driver", "Risks and kill criteria", "ADR fit",
)
TIERS = ("classical", "sota", "beyond")
LADDER_HEAD = ["id", "tier", "method", "acceptance criterion", "gate"]
BEYOND_SECTION = "Beyond the state of the art"
RULE = "CAOS_MANAGE conventions/method-tiers-and-manuscripts.md"
TEMPLATE_SENTINEL = ".template-source"  # present only in CAOS_PRODUCT_TEMPLATE (instantiate.py removes it; check_template_residue.py guards it)
BS_ID = re.compile(r"\bBS-\d+\b")
BRIEF = "Executive brief"
GUIDE = "see docs/guides/06_executive-brief.md"
EXEC_FILE = "content/executive.json"
EXEC_SCHEMA = "frontend/node_modules/@fasl-work/caos-app-shell/src/content/executive.schema.json"
EXEC_SCHEMA_VERSION = "2.0.0"  # the contract: the schema of shell 0.13.x and 0.14.x; an older installed schema is refused
# The 4 C's of the proposal, in order (conventions/problem-context-first.md): the shell's FOUR_CS names, English and Spanish.
FOUR_CS = (("Choice", "Elección"), ("Context", "Contexto"), ("Cost", "Costo"), ("Control", "Control"))
MAX_WORDS = 30
MIN_PARAGRAPH_WORDS = 25
EQUATION = re.compile(r"\$|\\\(|\\\[|\\[a-zA-Z]+")
INLINE_CITATIONS = (re.compile(r"\(\s*Source", re.I), re.compile(r"\[\d+\]"), re.compile(r"\(\s*ECB"), re.compile(r"\(\w[^()]*\d{4}\)"))
FILE_CITATIONS = (re.compile(r"\bfile\s*\d", re.I), re.compile(r"\barchivo\s*\d", re.I), re.compile(r"\.pdf\b", re.I), re.compile(r"\bPublished on\b", re.I))
PROMOTIONAL = tuple(re.compile(p, re.I) for p in (
    r"\bour\s+clients?\b", r"\bnuestros?\s+clientes?\b", r"\bcontact\s+us\b", r"\bcontáctenos\b", r"\bbuy\b", r"\bcomprar\b",
    r"\bprices?\b", r"\bprecios?\b", r"\boffers?\b", r"\bofertas?\b"))
DATA_LINE = re.compile(rf"^\s*Data file: `?{re.escape(EXEC_FILE)}`?\s*$")
BRIEF_MAX_WORDS = 120  # the section names the file and says why; the view itself is the file
FENCE = re.compile(r"^\s*(```+|~~~+)")
HEADING = re.compile(r"^(?P<hashes>#{2,3}) (?P<title>.+?)\s*$")
LEVEL2 = re.compile(r"^## (?:\d+[.)]?\s+)?(?P<title>.+?)\s*$")
BULLET = re.compile(r"^\s*[-*+] ")
NUMBERED = re.compile(r"^\s*\d+[.)] ")
MIN_SOURCES = 3
SOURCE = re.compile(r"\b10\.\d{4,9}/[^\s)>\]|]+|https?://[^\s)>\]|]+")
UNVERIFIED = re.compile(r"^\s*(?:[-*+]\s+)?(?:\*\*)?UNVERIFIED(?:\*\*)?\s*:", re.M)
PLACEHOLDER = {"-", "?", "todo", "unknown", "n/a", "na", "tbd", "..."}
RESOURCE_HEAD = ["stage", "memory", "disk", "time", "where it runs"]
RESOURCE_STAGES = ("bake", "tests", "build", "deploy")  # training is listed when the product trains
VALIDATION_HEAD = ["requirement", "adversarial check", "gate"]
ID_OK = re.compile(r"^[A-Z]{2,}-\d+[a-z]?$")
ID_TOKEN = re.compile(r"(?<![A-Za-z0-9-])(?!ADR-)[A-Z]{2,}-\d{3}[a-z]?\b")
TICKED = re.compile(r"`([^`]+)`")
FILE_LIKE = re.compile(r"^[\w./<>*-]+\.(py|ts|tsx|mjs|js|json|md|yml|yaml)(::[^`]+)?$")
STATUS_ANY = re.compile(r"^Status:\s*(\S*)\s*$", re.M | re.I)
HTML_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.S)
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs", ".sh", ".ps1"}
PLACEHOLDER_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "example.com", "example.org", "example.net", "example.edu"}
# words that fill a place without saying anything; a text made only of them, or with too few other distinct words, is a placeholder
FILLER = {"tbd", "tba", "tbc", "todo", "fixme", "xxx", "lorem", "ipsum", "dolor", "sit", "amet", "placeholder", "unknown", "n/a", "na",
          "none", "foo", "bar", "baz", "asdf", "qwerty", "x", "y", "z"}
TOKEN = re.compile(r"[A-Za-z0-9%][A-Za-z0-9%.'/-]*")
DOI_REGISTRANT_PLACEHOLDER = re.compile(r"^(?:0+|1234|12345|9999)$")
DOI_SUFFIX_PLACEHOLDER = re.compile(r"(?i)^(?:fake|example|test|placeholder|tbd|todo|xxx|dummy|made-?up|lorem)")
LOCAL_ONLY = re.compile(r"local-only:\s*(?P<why>[^|;]+)", re.I)
MATH_FENCE = re.compile(r"^\s*(?:```+|~~~+)\s*(?:math|latex|tex)\b", re.I)


# ---------------------------------------------------------------- markup

def strip_fences(text: str, mark_math: bool = False) -> str:
    """The text without fenced code blocks (``` and ~~~, closed by the same fence; an unclosed one runs to the end).
    ``mark_math`` leaves a ``$$`` line where a math block was, so that a check for equations still sees it."""
    out: list[str] = []
    fence: str | None = None
    for line in text.replace("\r\n", "\n").split("\n"):
        m = FENCE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)
                if mark_math and MATH_FENCE.match(line):
                    out.append("$$")
            else:
                out.append(line)
        elif m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not line.strip().lstrip(fence[0]).strip():
            fence = None
    return "\n".join(out)


def strip_comments(text: str) -> str:
    return HTML_COMMENT.sub("", text.replace("\r\n", "\n"))


def strip_markup(text: str, mark_math: bool = False) -> str:
    """The text a reader sees as structure: no fenced blocks and no HTML comments."""
    return strip_comments(strip_fences(text, mark_math))


def section_text(text: str, name: str) -> str | None:
    """The body of the ``## <name>`` section of already-stripped text (up to the next ``## `` heading), None when absent."""
    lines = text.split("\n")
    start = next((i for i, ln in enumerate(lines) if (m := LEVEL2.match(ln)) and m["title"].lower() == name.lower()), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start + 1:end])


def table_rows(text: str, head: list[str]) -> list[list[str]] | None:
    """The data rows of the first table whose header cells are ``head`` (case-insensitive), None if there is none."""
    rows: list[list[str]] | None = None
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            if rows is not None:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if rows is None:
            if [c.lower() for c in cells] == head:
                rows = []
        elif not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            rows.append(cells)
    return rows


# ---------------------------------------------------------------- the SDD sections

def canonical_source(raw: str) -> str | None:
    """One key per work: a DOI however written, or a URL; None for a placeholder (example, localhost, .example hosts)."""
    raw = raw.rstrip(".,;")
    m = re.match(r"^https?://(?:dx\.)?doi\.org/(10\..+)$", raw, re.I)
    doi = m[1] if m else raw if raw.startswith("10.") else None
    if doi is not None:
        parts = re.match(r"^10\.(\d+)/(.*)$", doi)
        if parts and (DOI_REGISTRANT_PLACEHOLDER.match(parts[1]) or DOI_SUFFIX_PLACEHOLDER.match(parts[2])):
            return None  # 10.0000/fake and 10.1234/example are not works
        return "doi:" + doi.lower()
    m = re.match(r"^https?://([^/:?#]+)(?::\d+)?([^?#]*)(\?[^#]*)?", raw, re.I)
    if not m:
        return None
    host = m[1].lower().removeprefix("www.")
    labels = host.split(".")
    if host in PLACEHOLDER_HOSTS or labels[-1] in {"example", "test", "invalid", "localhost"} or (len(labels) > 1 and labels[-2] == "example"):
        return None
    return host + m[2].rstrip("/") + (m[3] or "")


def research_findings(body: str) -> list[str]:
    out: list[str] = []
    keys = {k for m in SOURCE.finditer(body) if (k := canonical_source(m.group(0)))}
    if len(keys) < MIN_SOURCES:
        out.append(f"SDD.md research basis cites {len(keys)} sources (distinct DOIs 10.x/y or http URLs, none of them a "
                   f"placeholder); at least {MIN_SOURCES} are required")
    if not UNVERIFIED.search(body):
        out.append("SDD.md research basis has no line starting 'UNVERIFIED:' (write 'UNVERIFIED: none' when everything was confirmed)")
    return out


def stage_label(cell: str) -> list[str]:
    """The words naming a stage in the first cell of a resources row (before any parenthesis or colon)."""
    return re.findall(r"[a-z]+", re.split(r"[(:]", cell)[0].lower())


def resources_findings(body: str) -> list[str]:
    rows = table_rows(body, RESOURCE_HEAD)
    if rows is None:
        return [f"SDD.md Resources has no table with the columns {' | '.join(RESOURCE_HEAD)}"]
    out: list[str] = []
    for cells in rows:
        label = cells[0] or "(unnamed)"
        if len(cells) != len(RESOURCE_HEAD) or any(not c for c in cells):
            out.append(f"SDD.md Resources row {label!r} has an empty cell")
        for c in cells:
            if c.lower().strip("`*_ ") in PLACEHOLDER:
                out.append(f"SDD.md Resources row {label!r} has a placeholder cell {c!r}; write a measured or bounded value")
        if any(re.search(r"\bTBD\b", c, re.I) for c in cells):
            out.append(f"SDD.md Resources row {label!r} says TBD; write a measured or bounded value")
    named = [stage_label(c[0]) for c in rows if c]
    for stage in RESOURCE_STAGES:
        if not any(w and w[0] == stage and not set(w[1:]) & set(RESOURCE_STAGES) for w in named):
            out.append(f"SDD.md Resources has no row for the {stage} (one row per stage, its name first in the first cell)")
    return out


def sections_findings(text: str) -> list[str]:
    """The twelve sections: present once as ``## <name>`` outside fences and comments, in order, each with a body."""
    lines = strip_markup(text).split("\n")
    heads = [(i, m["title"].lower()) for i, ln in enumerate(lines) if (m := LEVEL2.match(ln))]
    titles = [t for _, t in heads]
    out: list[str] = []
    last = -1
    for name in SECTIONS:
        low = name.lower()
        if low not in titles:
            out.append(f"SDD.md has no section for {name!r} (a level-2 heading '## {name}' outside a code fence or a comment)")
            continue
        if titles.count(low) > 1:
            out.append(f"SDD.md has more than one section {name!r}")
        at = titles.index(low)
        start = heads[at][0]
        end = heads[at + 1][0] if at + 1 < len(heads) else len(lines)
        if not any(ln.strip() for ln in lines[start + 1:end]):
            out.append(f"SDD.md section {name!r} is empty")
        if at < last:
            out.append(f"SDD.md section {name!r} is out of order")
        last = max(last, at)
    return out


# ---------------------------------------------------------------- the executive view

def outline(text: str) -> list[tuple[int, str, int]]:
    """Level-2 and level-3 headings of already-stripped text, as (level, title, line index). A level-2 title has its
    ``N.`` prefix dropped, as the twelve-section check does, so that ``## 2. Executive brief`` is the brief."""
    out: list[tuple[int, str, int]] = []
    for i, line in enumerate(text.splitlines()):
        m = HEADING.match(line)
        if m:
            level = len(m["hashes"])
            title = LEVEL2.match(line)["title"] if level == 2 else m["title"].strip()
            out.append((level, title, i))
    return out


def words(text: str) -> list[str]:
    """The distinct words of a text that say something: markup and punctuation off, placeholder words (TBD, lorem ...) out."""
    seen: dict[str, None] = {}
    for tok in TOKEN.findall(re.sub(r"[`*_]", " ", text)):
        tok = tok.strip(".,;:'/-").lower()
        if tok and tok not in FILLER:
            seen[tok] = None
    return list(seen)


def too_short(text: str, floor: int) -> bool:
    """True when the text has fewer than ``floor`` distinct words that say something: empty, a placeholder or a stub."""
    return len(words(text)) < floor


def load_executive() -> tuple[dict | None, list[str]]:
    """The parsed ``content/executive.json`` and what is wrong with reading it."""
    path = ROOT / EXEC_FILE
    if not path.is_file():
        return None, [f"{EXEC_FILE} is missing: the executive view is one data file every product writes first, from its research ({GUIDE})"]
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, OSError) as e:
        return None, [f"{EXEC_FILE} is not valid JSON: {e}"]
    if not isinstance(data, dict):
        return None, [f"{EXEC_FILE} is not valid JSON of the executive view: the document must be an object, not {type(data).__name__}"]
    return data, []


def field_path(parts) -> str:
    """``outcomes[1].proof.unit`` from the path of a schema error."""
    out = ""
    for p in parts:
        out += f"[{p}]" if isinstance(p, int) else (f".{p}" if out else str(p))
    return out


def schema_findings(data: dict) -> list[str]:
    """The data against the shell's ``executive.schema.json`` (installed by ``npm ci``), one finding per violation with
    its field path. A schema that cannot be read, or a validator that is not installed, is a finding: a check that
    could not run never passes."""
    schema_path = ROOT / EXEC_SCHEMA
    if not schema_path.is_file():
        return [f"{EXEC_SCHEMA} is absent: run 'npm ci' in frontend/ (the shell's schema is the contract of {EXEC_FILE}, and a file "
                "that was not validated is not accepted)"]
    try:
        import jsonschema  # noqa: PLC0415
    except ImportError:
        return ["the jsonschema package is not installed: pip install jsonschema==4.26.0 (it is in requirements-dev.txt); "
                f"{EXEC_FILE} cannot be validated without it"]
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
    except (ValueError, OSError, jsonschema.SchemaError) as e:
        return [f"{EXEC_SCHEMA} cannot be read as a JSON Schema: {e}"]
    if f"version {EXEC_SCHEMA_VERSION}" not in str(schema.get("title", "")):
        return [f"{EXEC_SCHEMA} is not version {EXEC_SCHEMA_VERSION} (its title says {schema.get('title')!r}): the executive view is written to "
                f"schema {EXEC_SCHEMA_VERSION} of shell 0.13.x and 0.14.x; run 'npm ci' in frontend/ with the pinned shell"]
    out: list[str] = []
    for err in sorted(validator.iter_errors(data), key=lambda e: [str(p) for p in e.absolute_path]):
        where = field_path(err.absolute_path)
        if err.validator == "required":
            missing = [k for k in err.validator_value if k not in err.instance]
            where = field_path([*err.absolute_path, *missing[:1]])
            out.append(f"{EXEC_FILE}: {where} is required and missing")
        elif err.validator == "additionalProperties":
            extra = [k for k in err.instance if k not in err.schema.get("properties", {})]
            out.append(f"{EXEC_FILE}: {field_path([*err.absolute_path, *extra[:1]])} is not a field of the executive view (nothing else is allowed)")
        elif err.validator == "anyOf":
            out.append(f"{EXEC_FILE}: {where or '(file)'} matches none of the allowed forms")
        else:
            out.append(f"{EXEC_FILE}: {where or '(file)'}: {err.message[:120]}")
    return out


def sentences_of(text: str) -> list[str]:
    """A sentence ends at ``.``, ``?`` or ``!`` followed by a space or the end; a decimal point is not an end."""
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()]


def words_in(text: str) -> int:
    return sum(1 for w in text.split() if re.search(r"[^\W_]", w))


def writing_problems(text: str, max_sentences: int | None = None, min_words: int | None = None) -> list[str]:
    """What breaks the writing limits of the view in one text, as the shell's ``writingProblems`` says it."""
    out: list[str] = []
    sentences = sentences_of(text)
    for s in sentences:
        n = words_in(s)
        if n > MAX_WORDS:
            out.append(f"a sentence of {n} words; the limit is {MAX_WORDS}")
    if max_sentences is not None and len(sentences) > max_sentences:
        out.append(f"must be one sentence, has {len(sentences)}" if max_sentences == 1 else f"has {len(sentences)} sentences; the limit is {max_sentences}")
    if min_words is not None and words_in(text) < min_words:
        out.append(f"has {words_in(text)} words; a paragraph needs at least {min_words} (no one-line sections)")
    if EQUATION.search(text):
        out.append("holds an equation or a TeX marker; the executive view holds none")
    if any(rx.search(text) for rx in INLINE_CITATIONS):
        out.append('holds an inline citation; give the source in "sources"')
    for rx in PROMOTIONAL:
        m = rx.search(text)
        if m:
            out.append(f'holds promotional or client-bound wording ("{m.group(0)}"); the executive view is general, never a client, never a pitch')
    return out


def source_text_problems(text: str, max_sentences: int | None = None) -> list[str]:
    """A source's title or note: the sentence limit, and no file name or number in place of the link."""
    out: list[str] = []
    sentences = sentences_of(text)
    for s in sentences:
        n = words_in(s)
        if n > MAX_WORDS:
            out.append(f"a sentence of {n} words; the limit is {MAX_WORDS}")
    if max_sentences is not None and len(sentences) > max_sentences:
        out.append(f"must be one sentence, has {len(sentences)}")
    written = re.search(r"https?://", text, re.I) is not None
    for rx in FILE_CITATIONS:
        if rx.pattern.startswith(r"\.pdf") and written:
            continue
        m = rx.search(text)
        if m:
            out.append(f'cites a file name or number in place of the link ("{m.group(0)}"); give the publication as the title and its https link as the url')
    return out


def text_fields(d: dict) -> list[tuple[str, dict, int | None, int | None]]:
    """Every text field with its path, the most sentences it may hold and the fewest words (the shell's ``executiveTextFields``)."""
    out: list[tuple[str, dict, int | None, int | None]] = []

    def add(path, text, sentences=None, min_words=None):
        out.append((path, text, sentences, min_words))

    def figure(base, f):
        for k in ("heading", "value", "unit"):
            add(f"{base}.{k}", f[k])

    add("title", d["title"], 1)
    add("key_statement", d["key_statement"], 2)
    for i, f in enumerate(d["headline_figures"]):
        figure(f"headline_figures[{i}]", f)
    pain, context, situation, trends, proposal = d["pain"], d["context"], d["situation"], d["trends"], d["proposal"]
    add("pain.key_message", pain["key_message"], 1)
    for i, p in enumerate(pain["paragraphs"]):
        add(f"pain.paragraphs[{i}]", p, None, MIN_PARAGRAPH_WORDS)
    for i, b in enumerate(pain["bearers"]):
        for k in ("who", "cost", "measure"):
            add(f"pain.bearers[{i}].{k}", b[k])
    for i, f in enumerate(pain["figures"]):
        figure(f"pain.figures[{i}]", f)
    for i, c in enumerate(pain["causes"]):
        add(f"pain.causes[{i}].cause", c["cause"])
    add("context.key_message", context["key_message"], 1)
    for i, p in enumerate(context["paragraphs"]):
        add(f"context.paragraphs[{i}]", p, None, MIN_PARAGRAPH_WORDS)
    add("context.setting", context["setting"])
    for i, f in enumerate(context["forces"]):
        add(f"context.forces[{i}].force", f["force"])
    for i, e in enumerate(context["evidence"]):
        add(f"context.evidence[{i}].statement", e["statement"], 1)
    add("situation.key_message", situation["key_message"], 1)
    for i, r in enumerate(situation["roles"]):
        for k in ("role", "decides", "needs"):
            add(f"situation.roles[{i}].{k}", r[k])
    add("situation.interaction", situation["interaction"], 1)
    for i, a in enumerate(situation["state_of_the_art"]):
        for k in ("approach", "achieves", "falls_short"):
            add(f"situation.state_of_the_art[{i}].{k}", a[k])
    figure("situation.status", situation["status"])
    add("situation.status.date", situation["status"]["date"])
    add("trends.key_message", trends["key_message"], 1)
    for i, t in enumerate(trends["items"]):
        add(f"trends.items[{i}].trend", t["trend"])
        add(f"trends.items[{i}].signal.statement", t["signal"]["statement"], 1)
        add(f"trends.items[{i}].effect", t["effect"])
    add("proposal.key_message", proposal["key_message"], 1)
    for i, p in enumerate(proposal["paragraphs"]):
        add(f"proposal.paragraphs[{i}]", p, None, MIN_PARAGRAPH_WORDS)
    for i, c in enumerate(proposal["four_cs"]):
        add(f"proposal.four_cs[{i}].c", c["c"])
        add(f"proposal.four_cs[{i}].applies", c["applies"], 1)
    for i, a in enumerate(proposal["actions"]):
        add(f"proposal.actions[{i}].action", a["action"], 1)
        add(f"proposal.actions[{i}].owner", a["owner"])
        add(f"proposal.actions[{i}].horizon", a["horizon"])
        add(f"proposal.actions[{i}].check", a["check"], 1)
    for i, r in enumerate(proposal["risks"]):
        add(f"proposal.risks[{i}]", r, 1)
    for i, u in enumerate(proposal["unknowns"]):
        add(f"proposal.unknowns[{i}]", u, 1)
    if "handoff" in proposal:
        add("proposal.handoff", proposal["handoff"], 1)
    for name in ("pain", "situation", "proposal"):
        add(f"illustrations.{name}.caption", d["illustrations"][name]["caption"], 1)
    return out


def citations(d: dict) -> list[tuple[str, str]]:
    """Every citation of a source as (field path, source id), in the order the view shows them."""
    out = [(f"headline_figures[{i}].source", f["source"]) for i, f in enumerate(d["headline_figures"])]
    out += [(f"pain.figures[{i}].source", f["source"]) for i, f in enumerate(d["pain"]["figures"])]
    out += [(f"context.evidence[{i}].source", e["source"]) for i, e in enumerate(d["context"]["evidence"])]
    out += [(f"situation.state_of_the_art[{i}].source", a["source"]) for i, a in enumerate(d["situation"]["state_of_the_art"])]
    out.append(("situation.status.source", d["situation"]["status"]["source"]))
    out += [(f"trends.items[{i}].signal.source", t["signal"]["source"]) for i, t in enumerate(d["trends"]["items"])]
    return out


def rules_findings(d: dict) -> list[str]:
    """What the schema cannot say, on a structurally sound file: the 4 C's, the weights, the owners, the writing and the sources."""
    out: list[str] = []

    def add(path: str, message: str) -> None:
        out.append(f"{EXEC_FILE}: {path}: {message}")

    for i, row in enumerate(d["proposal"]["four_cs"]):
        en, es = FOUR_CS[i]
        if row["c"]["en"] != en or row["c"]["es"] != es:
            found = f'"{row["c"]["en"]}" and "{row["c"]["es"]}"'
            add(f"proposal.four_cs[{i}].c", f'must be "{en}" in English and "{es}" in Spanish (the 4 C\'s in order); found {found}')
    total = sum(c["weight"] for c in d["pain"]["causes"])
    if total > 100:
        add("pain.causes", f"the weights add to {total} percent; non-overlapping causes add to at most 100")
    roles = {(r["role"]["en"], r["role"]["es"]) for r in d["situation"]["roles"]}
    for i, a in enumerate(d["proposal"]["actions"]):
        if (a["owner"]["en"], a["owner"]["es"]) not in roles:
            names = ", ".join(f'"{r[0]}"' for r in sorted(roles))
            add(f"proposal.actions[{i}].owner", f"must be one of the roles of the current situation ({names}), written the same in both languages")
    for path, text, sentences, min_words in text_fields(d):
        for lang in ("en", "es"):
            for m in writing_problems(text[lang], sentences, min_words):
                add(f"{path}.{lang}", m)
    ids: dict[str, int] = {}
    for i, s in enumerate(d["sources"]):
        if s["id"] in ids:
            add(f"sources[{i}].id", f'"{s["id"]}" is already the id of sources[{ids[s["id"]]}]')
        else:
            ids[s["id"]] = i
        for lang in ("en", "es"):
            for m in source_text_problems(s["title"][lang]):
                add(f"sources[{i}].title.{lang}", m)
            if "note" in s:
                for m in source_text_problems(s["note"][lang], 1):
                    add(f"sources[{i}].note.{lang}", m)
    cited: set[str] = set()
    for path, sid in citations(d):
        if sid not in ids:
            add(path, f'"{sid}" is not the id of any source (the ids are {", ".join(ids)})')
        else:
            cited.add(sid)
    for i, s in enumerate(d["sources"]):
        if s["id"] not in cited:
            add(f"sources[{i}].id", f'"{s["id"]}" is cited by no figure or claim; every source backs a figure or a claim')
    return out


def illustration_findings(data: dict) -> list[str]:
    """The three illustration files exist under ``frontend/public/`` (the site root the shell fetches them from), inside it,
    and are SVG documents with a viewBox. What they draw is the shell's gate and the reviewer's judgement."""
    out: list[str] = []
    site = (ROOT / "frontend" / "public").resolve()
    for name, ill in data.get("illustrations", {}).items():
        files = ill.get("file") if isinstance(ill, dict) else None
        if isinstance(files, str):
            files = {"": files}
        if not isinstance(files, dict):
            continue
        for lang, rel in files.items():
            where = f"illustrations.{name}.file" + (f".{lang}" if lang else "")
            if not isinstance(rel, str) or rel.startswith(("http://", "https://", "//", "/")):
                out.append(f"{EXEC_FILE}: {where} must be a path under frontend/public/ ({rel!r})")
                continue
            target = (site / rel).resolve()
            if site not in target.parents:
                out.append(f"{EXEC_FILE}: {where} leaves frontend/public/ ({rel!r})")
            elif not target.is_file():
                out.append(f"{EXEC_FILE}: {where}: frontend/public/{rel} does not exist")
            else:
                svg = target.read_text(encoding="utf-8", errors="replace")
                if not re.search(r"<svg\b[^>]*\bviewBox=\"[^\"]+\"", svg):
                    out.append(f"{EXEC_FILE}: {where}: frontend/public/{rel} is not an SVG document with a viewBox")
    return out


def executive_findings() -> list[str]:
    data, out = load_executive()
    if data is None:
        return out
    out = schema_findings(data)
    if out:  # the later rules read the structure: run them only on a structurally sound file, so a typo never throws
        return out
    out += rules_findings(data)
    out += illustration_findings(data)
    return out


def restated(data: dict | None, body: str) -> list[str]:
    """Why a brief section restates the view instead of naming its file: a part heading, a list, a table, a copied sentence
    of the data file, or more than ``BRIEF_MAX_WORDS`` words."""
    out: list[str] = []
    lines = [ln for ln in body.splitlines() if ln.strip()]
    if any(HEADING.match(ln) and ln.lstrip().startswith("###") for ln in lines):
        out.append("a part heading (the four parts of the old brief are not the standard)")
    if any(BULLET.match(ln) or NUMBERED.match(ln) for ln in lines):
        out.append("a list")
    if any(ln.lstrip().startswith("|") for ln in lines):
        out.append("a table")
    if data is not None:
        flat = " ".join(re.sub(r"[\s`*_]+", " ", body).lower().split())
        copied = next((s for text in _texts(data) for part in sentences_of(text)
                       if len((s := " ".join(part.lower().split()).rstrip(".?!")).split()) >= 4 and s in flat), None)
        if copied:
            out.append(f"a sentence of {EXEC_FILE} ({copied[:40]!r}...)")
    prose = [ln for ln in lines if not DATA_LINE.match(ln)]
    n = len(" ".join(prose).split())
    if n > BRIEF_MAX_WORDS:
        out.append(f"{n} words; at most {BRIEF_MAX_WORDS}")
    return out


def _texts(node) -> list[str]:
    """Every English and Spanish text of the data file (a ``{en, es}`` object), for the restating check."""
    out: list[str] = []
    if isinstance(node, dict):
        if set(node) == {"en", "es"} and all(isinstance(v, str) for v in node.values()):
            out += list(node.values())
        else:
            for k, v in node.items():
                if k != "sources":
                    out += _texts(v)
    elif isinstance(node, list):
        for v in node:
            out += _texts(v)
    return out


def brief_findings(text: str, data: dict | None) -> list[str]:
    """The ``Executive brief`` section: right after ``Problem and non-goals``, once, before ``Research basis``, naming the data
    file in a ``Data file: content/executive.json`` line and restating nothing of the view. Read from the text a reader
    sees: no fenced block (a ``~~~`` fence is closed only by ``~~~``) and no HTML comment."""
    text = strip_markup(text, mark_math=True)
    lines = text.splitlines()
    heads = outline(text)
    twos = [(t, i) for lv, t, i in heads if lv == 2]
    names = [t.lower() for t, _ in twos]
    if BRIEF.lower() not in names:
        return [f"SDD.md has no section {BRIEF!r} (it names {EXEC_FILE} and restates nothing, before any development): {GUIDE}"]
    pos = names.index(BRIEF.lower())
    out: list[str] = []
    if names.count(BRIEF.lower()) > 1:
        out.append(f"SDD.md has more than one section {BRIEF!r}: {GUIDE}")
    if "problem and non-goals" in names and pos != names.index("problem and non-goals") + 1:
        out.append(f"SDD.md section {BRIEF!r} must come right after 'Problem and non-goals': {GUIDE}")
    if "research basis" in names and names.index("research basis") < pos:
        out.append(f"SDD.md section {BRIEF!r} must come before 'Research basis': {GUIDE}")
    start = twos[pos][1]
    end = twos[pos + 1][1] if pos + 1 < len(twos) else len(lines)
    body = "\n".join(lines[start + 1:end])
    if not any(DATA_LINE.match(ln) for ln in body.splitlines()):
        out.append(f"SDD.md {BRIEF!r} has no line 'Data file: {EXEC_FILE}': the executive view is that file, and the SDD names it: {GUIDE}")
    why = restated(data, body)
    if why:
        out.append(f"SDD.md {BRIEF!r} restates the executive view instead of naming its file ({'; '.join(why)}): {GUIDE}")
    return out


APP_KINDS = ("workbench", "surface")
MIN_REASON_WORDS = 8
PLACEHOLDER_WORD = re.compile(r"^(?:tbd|tba|tbc|todo|fixme|xxx|lorem|ipsum|placeholder|n/a|na|none|unknown)$", re.I)
NOT_APPLICABLE = re.compile(r"^not applicable:\s*(.+)$", re.I)
ADR_0070_ROW = re.compile(r"^\s*\|\s*ADR-0070\s*\|")


def app_kind_findings(text: str) -> list[str]:
    """The App's kind in ``product.json`` (``app``, ``focus``, ``focus_reason``) against the ADR-0070 row of the SDD (WB-015)."""
    path = ROOT / "product.json"
    try:
        # a tree without product.json (a sandboxed copy of the SDD alone) declares nothing: a workbench with Focus, the default
        doc = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except ValueError as exc:
        return [f"product.json is not valid JSON ({exc})"]
    if not isinstance(doc, dict):
        return ["product.json is not a JSON object"]
    out: list[str] = []
    app = doc.get("app", "workbench")
    if app not in APP_KINDS:
        out.append(f'product.json "app" is {json.dumps(app)}: it must be "workbench" (the default) or "surface"')
    focus = doc.get("focus")
    if "focus" in doc and not isinstance(focus, bool):
        out.append('product.json "focus" must be true or false')
    waived = focus is False
    raw = doc.get("focus_reason")
    reason = " ".join(raw.split()) if isinstance(raw, str) else ""
    if not waived and "focus_reason" in doc:
        out.append('product.json has a "focus_reason" but "focus" is not false: remove the reason, or record the waiver with "focus": false')
    if waived:
        if app != "surface":
            out.append('product.json "focus": false is valid only with "app": "surface": a workbench App cannot waive Focus mode (ADR-0070, WB-014)')
        words = reason.split()
        if not reason:
            out.append('product.json "focus": false needs a non-empty "focus_reason" saying why ADR-0070 does not apply')
        elif len(words) < MIN_REASON_WORDS:
            out.append(f'product.json "focus_reason" has {len(words)} word(s): at least {MIN_REASON_WORDS} are needed to say why ADR-0070 does not apply')
        elif any(PLACEHOLDER_WORD.match(re.sub(r"[^\w/]", "", w)) for w in words) or re.search(r"<[^>]*>|\.\.\.", reason):
            out.append('product.json "focus_reason" is placeholder text: write the real reason')
    row = next((ln for ln in text.splitlines() if ADR_0070_ROW.match(ln)), None)
    cells = [c.strip() for c in row.strip().strip("|").split("|")] if row else []
    stated = next((m for m in (NOT_APPLICABLE.match(c) for c in cells) if m), None)
    if waived:
        if row is None:
            out.append('SDD.md has no ADR-0070 row in its ADR fit table: a waiver of Focus mode is recorded there as "not applicable: <reason>"')
        elif stated is None:
            out.append('SDD.md ADR-0070 row does not say "not applicable: <reason>": the waiver in product.json "focus_reason" is not recorded there')
        elif reason and " ".join(stated[1].split()) != reason:
            out.append(f'SDD.md ADR-0070 row gives a reason that differs from product.json "focus_reason" '
                       f'(SDD: "{" ".join(stated[1].split())}"; product.json: "{reason}")')
    elif stated is not None:
        out.append('SDD.md ADR-0070 row says "not applicable" but product.json records no waiver ("focus": false with a "focus_reason"): Focus mode applies')
    return out


def ladder_findings(stripped: str) -> list[str]:
    """The three method tiers (rule: CAOS_MANAGE ``conventions/method-tiers-and-manuscripts.md``) in the ladder table and the
    section on the beyond of already-stripped text. The template (``.template-source``) keeps its teaching example; a product needs
    a method in each tier and at least one ``BS-<n>`` claim, each claim with its ``beyond`` row."""
    body = section_text(stripped, "Method ladder")
    if body is None:
        return []  # sections_findings names the missing section
    template = (ROOT / TEMPLATE_SENTINEL).is_file()
    tiers = "classical, sota, beyond"
    rows = table_rows(body, LADDER_HEAD)
    if rows is None:
        return ["SDD.md Method ladder has no table with the columns | id | tier | method | acceptance criterion | gate |: add the "
                f"tier column, one of {tiers} for each method, and an id for each ({RULE})"]
    out: list[str] = []
    seen: dict[str, str] = {}
    by_tier: dict[str, list[str]] = {t: [] for t in TIERS}
    for cells in rows:
        if len(cells) != len(LADDER_HEAD):
            out.append(f"SDD.md Method ladder row {' | '.join(cells)[:60]!r} has {len(cells)} cells, the table has {len(LADDER_HEAD)}")
            continue
        rid, tier, method = cells[0], cells[1].lower(), cells[2]
        if not rid or rid.lower() in PLACEHOLDER:
            out.append("SDD.md Method ladder has a row with no id (M-1, M-2 for the classical and sota methods, BS-1 for a beyond one)")
            continue
        if rid in seen:
            out.append(f"SDD.md Method ladder lists the id {rid} twice")
        seen[rid] = tier
        if tier not in TIERS:
            out.append(f"SDD.md Method ladder row {rid} has the tier {cells[1]!r}: it must be one of {tiers}")
            continue
        if not method or method.lower() in PLACEHOLDER or not cells[3] or cells[3].lower() in PLACEHOLDER:
            out.append(f"SDD.md Method ladder row {rid} has an empty or placeholder method or acceptance criterion")
        by_tier[tier].append(rid)
    section = section_text(stripped, BEYOND_SECTION)
    claims = set(BS_ID.findall(section)) if section is not None else set()
    for rid in by_tier["beyond"]:
        if rid not in claims:
            out.append(f"SDD.md Method ladder row {rid} is a beyond method but the section '{BEYOND_SECTION}' lists no {rid}")
    for claim in sorted(claims - set(by_tier["beyond"])):
        out.append(f"SDD.md lists {claim} under '{BEYOND_SECTION}' but the Method ladder has no beyond method row with that id "
                   "(a validation protocol, a calibration or a benchmark design is not a method beyond the state of the art)")
    if template:
        return out
    for tier in TIERS:
        if not by_tier[tier]:
            out.append(f"SDD.md Method ladder has no {tier} method: every CAOS product implements the three tiers "
                       f"(classical, state of the art, beyond it) ({RULE})")
    if section is None:
        out.append(f"SDD.md has no section '## {BEYOND_SECTION}': list at least one proposed method BS-<n> ({RULE})")
    else:
        if re.search(r"none\s+claimed", section, re.I):
            out.append(f"SDD.md '{BEYOND_SECTION}' says \"None claimed.\": that holds only for the template's teaching example, "
                       f"a product proposes at least one method BS-<n> ({RULE})")
        if not claims:
            out.append(f"SDD.md '{BEYOND_SECTION}' lists no proposed method BS-<n>: a product proposes at least one, with its hypothesis, "
                       f"its method and the evaluation that would confirm or refute it ({RULE})")
    return out


def sdd_findings() -> list[str]:
    if not SDD.is_file():
        return [f"{SDD.relative_to(ROOT).as_posix()} is missing"]
    text = SDD.read_text(encoding="utf-8")
    data, _ = load_executive()
    out: list[str] = brief_findings(text, data)
    out += executive_findings()
    out += sections_findings(text)
    out += app_kind_findings(text)
    stripped = strip_markup(text)
    out += ladder_findings(stripped)
    research = section_text(stripped, "Research basis")
    resources = section_text(stripped, "Resources")
    if research is not None:
        out += research_findings(research)
    if resources is not None:
        out += resources_findings(resources)
    return out


# ---------------------------------------------------------------- is this name a test that can fail?

def _is_skip_mark(node: ast.AST) -> bool:
    """``pytest.mark.skip``, ``pytest.mark.skip(...)``, ``pytest.mark.skipif(True, ...)``, ``unittest.skip(...)``."""
    call = node.func if isinstance(node, ast.Call) else node
    chain: list[str] = []
    while isinstance(call, ast.Attribute):
        chain.append(call.attr)
        call = call.value
    if not isinstance(call, ast.Name):
        return False
    chain = [call.id, *reversed(chain)]
    if chain[-2:] == ["mark", "skip"] or (chain[0] == "unittest" and chain[-1] == "skip"):
        return True
    if chain[-2:] == ["mark", "skipif"] and isinstance(node, ast.Call):
        first = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == "condition"), None)
        return isinstance(first, ast.Constant) and first.value is True
    return False


def _unconditional_skip_call(stmt: ast.stmt) -> bool:
    """A statement that is ``pytest.skip(...)`` (not ``importorskip``, which is a precondition)."""
    if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
        return False
    f = stmt.value.func
    return isinstance(f, ast.Attribute) and f.attr == "skip" and isinstance(f.value, ast.Name) and f.value.id == "pytest"


def _module_skipped(tree: ast.Module) -> bool:
    for stmt in tree.body:
        if _unconditional_skip_call(stmt):
            return True
        if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in stmt.targets):
            marks = stmt.value.elts if isinstance(stmt.value, (ast.List, ast.Tuple)) else [stmt.value]
            if any(_is_skip_mark(m) for m in marks):
                return True
    return False


def py_test_state(path: Path, name: str) -> str:
    """'ok', 'skipped', 'absent' or 'unparsable' for a test of a Python file (parsed, so a def in a string or a comment is no test)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, ValueError):
        return "unparsable"
    target = name.split("[")[0]
    if not target.startswith("test"):
        return "absent"  # a helper or a fixture of a test file is not a test
    candidates: list[tuple[ast.AST, bool]] = []  # (function, skipped by its class)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target:
            candidates.append((node, False))
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            class_skipped = any(_is_skip_mark(d) for d in node.decorator_list)
            candidates += [(f, class_skipped) for f in node.body
                           if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name == target]
    if not candidates:
        return "absent"
    if _module_skipped(tree):
        return "skipped"
    for fn, class_skipped in candidates:
        if not class_skipped and not any(_is_skip_mark(d) for d in fn.decorator_list) and not any(_unconditional_skip_call(s) for s in fn.body):
            return "ok"
    return "skipped"


def pinned_packages() -> set[str]:
    """The packages the repository pins in a requirements file (a documented setup installs them), lower case, ``-`` as ``_``."""
    out: set[str] = set()
    for path in [*ROOT.glob("requirements*.txt"), ROOT / "data-pipeline" / "requirements.txt"]:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", line)
            if m and not line.lstrip().startswith(("-", "#")):
                out.add(m[1].lower().replace("-", "_"))
    return out


def _chain(node: ast.AST) -> list[str]:
    """``a.b.c(...)`` or ``a.b.c`` as ['a', 'b', 'c']; [] for anything else."""
    node = node.func if isinstance(node, ast.Call) else node
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    return [node.id, *reversed(parts)] if isinstance(node, ast.Name) else []


def _skip_reason(node: ast.AST, aliases: set[str], pinned: set[str]) -> str | None:
    """Why this node makes a test skip for lack of something, or None: a ``skipif`` mark (or a name bound to one),
    ``pytest.skip(...)``, or ``pytest.importorskip(<a package the repository does not pin>)``."""
    chain = _chain(node)
    if chain[-2:] == ["mark", "skipif"] or chain[-1:] in (["skipIf"], ["skipUnless"]):
        return "a skipif mark"
    if isinstance(node, ast.Name) and node.id in aliases:
        return f"{node.id}, a skipif mark"
    if chain == ["pytest", "skip"]:
        return "pytest.skip"
    if chain == ["pytest", "importorskip"] and isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant):
        package = str(node.args[0].value).split(".")[0].lower().replace("-", "_")
        if package not in pinned:
            return f"pytest.importorskip({package!r}), a package no requirements file pins"
    return None


def py_skip_condition(path: Path, name: str) -> str | None:
    """Why a (live) Python test skips when a tool is missing, or None when it always runs: a skipif mark on the test, its
    class or the module (``pytestmark``, or a name bound to a mark), a ``pytest.skip`` call or an ``importorskip`` of a
    package the repository does not pin, in the test or at module level. An importorskip of a pinned package is a
    precondition of the documented setup, not a missing tool."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, ValueError):
        return None
    pinned = pinned_packages()
    alias_statements = [s for s in tree.body if isinstance(s, ast.Assign) and _skip_reason(s.value, set(), pinned) == "a skipif mark"
                        and not any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in s.targets)]
    aliases = {t.id for s in alias_statements for t in s.targets if isinstance(t, ast.Name)}
    target = name.split("[")[0]

    def first(nodes) -> str | None:
        return next((r for n in nodes for r in [_skip_reason(n, aliases, pinned)] if r), None)

    reason = first(n for s in tree.body if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                   and s not in alias_statements for n in ast.walk(s) if isinstance(n, ast.Call))
    if reason:
        return reason
    for node in tree.body:
        funcs: list[tuple[ast.AST, list[ast.expr]]] = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target:
            funcs.append((node, []))
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            funcs += [(f, node.decorator_list) for f in node.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name == target]
        for fn, class_decorators in funcs:
            found = first([*class_decorators, *fn.decorator_list]) or first(n for n in ast.walk(fn) if isinstance(n, ast.Call))
            if found:
                return found
    return None


def mask_ts(src: str) -> tuple[str, dict[int, int]]:
    """TypeScript source with comments blanked and the content of string and template literals replaced by ``_``, plus
    {index of an opening quote: index of its closing quote}. What is left is code only."""
    out = list(src)
    spans: dict[int, int] = {}
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j == -1 else j
            out[i:j] = " " * (j - i)
            i = j
        elif c == "/" and src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out[i:j] = [ch if ch == "\n" else " " for ch in src[i:j]]
            i = j
        elif c in "'\"`":
            j = i + 1
            while j < n and src[j] != c and not (c != "`" and src[j] == "\n"):
                j += 2 if src[j] == "\\" else 1
            if j < n and src[j] == c:
                out[i + 1:j] = [ch if ch == "\n" else "_" for ch in src[i + 1:j]]
                spans[i] = j
                i = j + 1
            else:
                i = j
        else:
            i += 1
    return "".join(out), spans


def ts_test_state(path: Path, name: str) -> str:
    """'ok', 'skipped' or 'absent' for the test (an ``it(`` or ``test(`` call starting its line, outside strings, comments
    and other tests' bodies) whose whole first string argument is ``name``."""
    src = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    code, spans = mask_ts(src)
    call = re.compile(r"^[ \t]*(?P<x>x?)(?:test|it)(?P<mods>(?:\.\w+)*)\s*\(\s*(?P<q>['\"`])", re.M)
    found = "absent"
    inside_until = -1
    for m in call.finditer(code):
        if m.start() < inside_until:
            continue  # nested in the body of an earlier test
        open_paren = code.index("(", m.start("x"))
        depth, k = 0, open_paren
        while k < len(code):
            depth += (code[k] == "(") - (code[k] == ")")
            k += 1
            if depth == 0:
                break
        inside_until = k
        q = m.start("q")
        end = spans.get(q)
        if end is None or re.sub(r"\\(['\"`\\])", r"\1", src[q + 1:end]) != name:
            continue
        options = re.match(r"\s*,\s*\{([^}]*)\}", code[end + 1:])
        mods = [x for x in m["mods"].split(".") if x]
        if m["x"] or {"skip", "todo", "skipIf"} & set(mods) or (options and re.search(r"\b(?:skip|todo)\s*:\s*(?!false\b)(?=\S)", options.group(1))):
            found = "skipped"
            continue
        return "ok"
    return found


def test_state(path: Path, name: str) -> str:
    return py_test_state(path, name) if path.suffix == ".py" else ts_test_state(path, name)


# ---------------------------------------------------------------- gates

def is_test_file(rel: str) -> bool:
    p = Path(rel)
    if p.suffix == ".py":
        return rel.startswith("tests/") or p.name.startswith("test_") or p.name.endswith("_test.py")
    if p.suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
        return bool(re.search(r"\.(test|spec)\.[jt]sx?$|\.(test|spec)\.mjs$", p.name)) or rel.startswith("tests/")
    return False


def is_script(rel: str) -> bool:
    return rel.startswith(("scripts/", "frontend/scripts/")) and Path(rel).suffix in CODE_SUFFIXES


def adversarial_name(rel: str, name: str) -> bool:
    """A claim a reviewer verifies, not proof: a test under tests/adversarial/, or one named ``test_adversarial_...`` (Python)
    or ``adversarial: ...`` (a TypeScript title); ``adversarialish`` and a bare ``test_adversarial`` are not."""
    base = name.split("[")[0]
    return rel.startswith("tests/adversarial/") or base.startswith(("test_adversarial_", "adversarial: "))


def gate_findings(rel: str, rid: str, gate: str, *, adversarial: bool = False) -> list[str]:
    out: list[str] = []
    named = [t for t in TICKED.findall(gate) if FILE_LIKE.match(t)]
    if not named:
        return [f"{rel} {rid}: the gate names no file ({gate.strip()[:80]!r})"]
    for target in named:
        path_part, sep, test = target.partition("::")
        path = (ROOT / path_part).resolve()
        if not (path == ROOT or ROOT in path.parents):
            out.append(f"{rel} {rid}: names {path_part!r}, which resolves outside the repository")
            continue
        if not path.is_file():
            out.append(f"{rel} {rid}: names {path_part!r}, which does not exist")
            continue
        if not sep:
            if not (is_test_file(path_part) or is_script(path_part)):
                out.append(f"{rel} {rid}: {path_part} is neither a test file nor a script under scripts/ or frontend/scripts/; "
                           "a plain path gate cannot be a document or a data file")
            continue
        if path.suffix not in {".py", ".ts", ".tsx"} or not is_test_file(path_part):
            out.append(f"{rel} {rid}: {path_part}::{test} names a test in {path_part}, which is not a Python or TypeScript test file")
            continue
        state = test_state(path, test)
        if state == "skipped":
            out.append(f"{rel} {rid}: {path_part} test {test!r} is skipped or todo, so it cannot fail")
        elif state in {"absent", "unparsable"}:
            why = "cannot be parsed" if state == "unparsable" else f"defines no live test {test!r}"
            out.append(f"{rel} {rid}: {path_part} {why} (a test {test!r}: a def at module level or in a Test class, or an "
                       "it( or test( call that starts its line, with the whole name)")
        elif adversarial and not adversarial_name(path_part, test):
            out.append(f"{rel} {rid}: {path_part}::{test} is not adversarial; a validation gate is a test under tests/adversarial/ "
                       "or one named test_adversarial_... or it('adversarial: ...')")
    return out


def skipping_findings(vrel: str, rid: str, named: list[str], check: str) -> list[str]:
    """A validation row proves a requirement can fail only if a gate of the row runs. When every live test it names
    skips for lack of a tool (a skipif mark, pytest.skip, an importorskip of a package no requirements file pins), CI
    and a clone without the tool never run it: the row needs a second gate that runs without the tool, or says in its
    check cell ``local-only: <why, at least five words>`` (a reviewed exception: the check runs where the tool is)."""
    reasons: list[str] = []
    for target in named:
        path_part, _, test = target.partition("::")
        path = (ROOT / path_part).resolve()
        if not (ROOT in path.parents and path.is_file()) or test_state(path, test) != "ok":
            continue  # reported by gate_findings
        why = py_skip_condition(path, test) if path.suffix == ".py" else None
        if why is None:
            return []
        reasons.append(f"{target} ({why})")
    if not reasons:
        return []
    exception = LOCAL_ONLY.search(check)
    if exception and not too_short(exception["why"], 5):
        return []
    return [f"{vrel} {rid}: every test the row names skips when a tool is missing, so it counts as not run: {'; '.join(reasons)}; "
            "name a second gate in the row that runs without that tool, or write 'local-only: <why>' (five words or more) in its check"]


def validation_findings(feature: Path, rel: str, ids: list[str]) -> list[str]:
    """validation.md of a live feature: every requirement ID exactly once, a stated check, an adversarial gate that is real."""
    vpath = feature / "validation.md"
    vrel = vpath.relative_to(ROOT).as_posix()
    if not vpath.is_file():
        return [f"{rel}: the feature has no validation.md ({vrel})"]
    rows = table_rows(strip_markup(vpath.read_text(encoding="utf-8")), VALIDATION_HEAD)
    if not rows:
        return [f"{vrel}: no table with the columns {' | '.join(VALIDATION_HEAD)} and rows"]
    out: list[str] = []
    seen: dict[str, int] = {}
    for cells in rows:
        rid = cells[0] if cells else ""
        seen[rid] = seen.get(rid, 0) + 1
        if rid not in ids:
            out.append(f"{vrel} {rid or '(blank)'}: not a requirement of this feature")
            continue
        if len(cells) != 3 or not cells[1].strip():
            out.append(f"{vrel} {rid}: the adversarial check is empty (state what was planted or refuted)")
            continue
        named = [t for t in TICKED.findall(cells[2]) if FILE_LIKE.match(t)]
        if not any("::" in t for t in named):
            out.append(f"{vrel} {rid}: the gate names no test (path::name), got {cells[2].strip()[:80]!r}")
            continue
        out.extend(gate_findings(vrel, rid, cells[2], adversarial=True))
        out.extend(skipping_findings(vrel, rid, named, cells[1]))
    for rid in ids:
        if seen.get(rid, 0) == 0:
            out.append(f"{vrel} {rid}: no validation row")
        elif seen[rid] > 1:
            out.append(f"{vrel} {rid}: listed more than once")
    return out


# ---------------------------------------------------------------- requirements files

def allowed() -> dict[str, str]:
    """``.status-allow``: feature -> reason (an entry with no reason is no entry)."""
    if not ALLOW.is_file():
        return {}
    out: dict[str, str] = {}
    for ln in ALLOW.read_text(encoding="utf-8").splitlines():
        if ln.strip() and not ln.lstrip().startswith("#"):
            area, _, reason = ln.partition(":")
            if reason.strip():
                out[area.strip()] = reason.strip()
    return out


def requirement_rows(text: str) -> tuple[list[dict[str, str]], list[str]]:
    """Every table line outside a code fence: the parsed ``| ID | statement | gate |`` rows and the malformed ones."""
    rows: list[dict[str, str]] = []
    bad: list[str] = []
    for line in strip_markup(text).split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|", 2)]
        if cells[0].lower() == "id" or (cells[0] and set(cells[0]) <= set("-: ")):
            continue
        if len(cells) < 3 or not cells[0] or line != line.lstrip() or not stripped.endswith("|"):
            bad.append(stripped[:80])
            continue
        rows.append({"id": cells[0], "statement": cells[1], "gate": cells[2]})
    return rows, bad


def main() -> int:
    findings = sdd_findings()
    live = planned = 0
    skipped: list[str] = []
    pending: list[str] = []
    seen: dict[str, str] = {}
    listed = allowed()
    folders = sorted(p for p in FEATURES.iterdir() if p.is_dir() and not p.name.startswith(".")) if FEATURES.is_dir() else []
    if not folders:
        findings.append("docs/design/features/ has no feature folder (<feature>/requirements.md)")
    for folder in folders:
        req = folder / "requirements.md"
        rel = req.relative_to(ROOT).as_posix()
        if not req.is_file():
            findings.append(f"{rel}: the feature folder {folder.name} has no requirements.md")
            continue
        text = req.read_text(encoding="utf-8")
        marks = [m.group(1).lower() for m in STATUS_ANY.finditer(strip_markup(text))]
        if len(marks) > 1:
            findings.append(f"{rel}: more than one Status line")
        state = marks[0] if marks else "live"
        if state not in {"live", "planned", "superseded"}:
            findings.append(f"{rel}: Status {state!r} is not live, planned or superseded")
            continue
        if state != "live" and folder.name not in listed:
            findings.append(f"{rel}: Status {state} takes the feature out of the gate; list it with its reason in "
                            "docs/design/features/.status-allow ('<feature>: <reason>')")
            continue
        if state == "superseded":
            skipped.append(folder.name)
            continue
        rows, bad = requirement_rows(text)
        findings.extend(f"{rel}: malformed requirement row (indented, fewer than three cells, no closing pipe or an empty ID): {b!r}" for b in bad)
        row_ids = {r["id"] for r in rows}
        for token in sorted(set(ID_TOKEN.findall(strip_markup(text))) - row_ids):
            findings.append(f"{rel}: {token} appears outside the ID column of a requirement row (a bullet, a split row or a lost row)")
        if not rows:
            findings.append(f"{rel}: no requirement rows")
        if state == "planned":
            pending.append(folder.name)
        for r in rows:
            rid = r["id"]
            if not ID_OK.match(rid):
                findings.append(f"{rel} {rid!r}: the ID does not match the form AB-001")
            elif rid in seen:
                findings.append(f"{rel} {rid}: duplicate ID (first in {seen[rid]})")
            else:
                seen[rid] = rel
            if "SHALL" not in r["statement"]:
                findings.append(f"{rel} {rid}: the statement has no SHALL")
            if state == "planned":
                planned += 1
                if not any(FILE_LIKE.match(t) for t in TICKED.findall(r["gate"])):
                    findings.append(f"{rel} {rid}: the planned gate names no file ({r['gate'].strip()[:80]!r})")
                continue
            live += 1
            if not r["gate"].strip():
                findings.append(f"{rel} {rid}: no gate")
                continue
            findings.extend(gate_findings(rel, rid, r["gate"]))
        if rows and state != "planned":
            findings.extend(validation_findings(folder, rel, [r["id"] for r in rows]))
    if findings:
        print("SDD CHECK FAILED:")
        for f in findings:
            print(f"  - {f}")
        return 1
    note = f"; superseded, not checked: {', '.join(skipped)}" if skipped else ""
    note += f"; {planned} planned requirements, gates not yet built: {', '.join(pending)}" if pending else ""
    print(f"check_sdd: OK, SDD.md complete, {live} live requirements with real gates{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
