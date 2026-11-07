#!/usr/bin/env python3
"""The manuscript content bar (CAOS_MANAGE ``conventions/manuscript-content-bar.md``): a CAOS product's technical report
and its manuscripts are LaTeX documents with the required structure, the measured depth, and the coverage of every method,
data contract and proposed method of the product.

Usage: ``python scripts/check_manuscript_depth.py [product root] [--only <slug>] [--report]``

Every folder ``manuscripts/<slug>/`` of the product is one manuscript: a main ``.tex`` with ``\\documentclass``, in the folder
or in its ``tex/`` subfolder (sources
included with ``\\input``/``\\include`` are read), a bibliography, and ``coverage.json``:

    {"kind": "technical-report" | "manuscript",
     "title_support": ["tab:main-results", "fig:error-vs-step"],
     "methods":   {"M-1": "sec:euler", ...},      # technical report: every row of the SDD's ## Method ladder
     "contracts": {"trace": "sec:data-trace", ...},# technical report: every row of docs/contracts/catalog.md
     "claims":    {"BS-1": "sec:proposed", ...}}   # manuscript: the proposed methods (## Beyond the state of the art) it reports

The ids are internal and never appear in the text: the map points each one at the ``\\label`` of the section that covers it.
A folder named ``shared``, ``_shared``, ``common``, ``figures`` or ``assets`` holds support files and is not a manuscript.
Exit 1 on any finding; ``--report`` prints the measures of each manuscript as well. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Use the base's already reviewed Markdown visibility/table parser. These three
# companion guards are installed together; all use the standard library only.
from check_notebook_depth import inventory_table, visible

RULE = "conventions/manuscript-content-bar.md"
SUPPORT = {"shared", "_shared", "common", "figures", "assets"}
NOT_LATEX = {".md", ".docx", ".doc", ".odt", ".rtf", ".html", ".htm", ".txt"}
KINDS = ("technical-report", "manuscript")

# The floors of conventions/manuscript-content-bar.md section 4, per kind.
FLOORS = {
    "technical-report": {"words": 12000, "equations": 25, "figures": 10, "tables": 8, "references": 30, "algorithms": 3},
    "manuscript": {"words": 7000, "equations": 12, "figures": 6, "tables": 4, "references": 25, "algorithms": 1},
}
SECTION_WORDS = 350          # every top-level section, except the short ones below
SHORT_SECTION_WORDS = 150    # conclusions, reproducibility, acknowledgements, declarations, appendix sections
SHORT_SECTIONS = ("conclusion", "reproducib", "availability", "acknowledg", "declaration", "funding")
SUBSECTION_WORDS = 150
CAPTION_WORDS = 15
REGION = {"methods": (600, 2), "claims": (1500, 6), "contracts": (120, 0)}  # (words, display equations) per covered item

# Required sections, by kind: each entry is (what the rule calls it, the heading words that satisfy it).
REQUIRED = {
    "technical-report": [
        ("Introduction", ("introduction",)),
        ("Problem formulation", ("problem",)),
        ("Notation", ("notation", "nomenclature", "symbols")),
        ("Data and data contracts", ("data",)),
        ("System architecture", ("architecture", "system", "pipeline")),
        ("Methods", ("method",)),
        ("Experimental protocol", ("protocol", "experimental", "experiments", "evaluation")),
        ("Results", ("result",)),
        ("Validation", ("validation", "verification")),
        ("Discussion", ("discussion",)),
        ("Limitations", ("limitation", "threats to validity")),
        ("Reproducibility", ("reproducib", "availability")),
        ("Conclusions", ("conclusion",)),
    ],
    "manuscript": [
        ("Introduction", ("introduction",)),
        ("Related work", ("related work", "background and related", "prior work", "literature")),
        ("Problem formulation", ("problem", "formulation", "preliminar", "background")),
        ("Proposed method", ("method", "approach", "model", "algorithm")),
        ("Theory", ("theor", "analysis", "derivation", "propert", "guarantee")),
        ("Experimental design", ("experimental", "experiments", "evaluation", "protocol", "setup")),
        ("Results", ("result",)),
        ("Ablation", ("ablation",)),
        ("Discussion", ("discussion",)),
        ("Limitations", ("limitation", "threats to validity")),
        ("Reproducibility", ("reproducib", "availability")),
        ("Conclusions", ("conclusion",)),
    ],
}
VAGUE = re.compile(r"\betc\.|\band so on\b|\band so forth\b|\bamong others\b|\bvarious (?:methods|techniques|approaches)\b",
                   re.I)
UNCERTAINTY = re.compile(r"\\pm\b|±|confidence interval|credible interval|standard deviation|standard error|"
                         r"interquartile|bootstrap", re.I)
HEADER_MACROS = ("docversion", "docdate", "versiondoi", "conceptdoi")

SECTIONING = re.compile(r"\\(section|subsection|subsubsection)\*?\s*(?:\[[^\]]*\])?\s*\{")
LITERAL_ENVS = re.compile(r"\\begin\{(verbatim\*?|lstlisting|minted|comment)\}.*?\\end\{\1\}", re.S)
CONDITIONAL = re.compile(r"\\(?:iffalse|iftrue|ifnum|ifdim|ifx|ifcat|ifodd|ifvmode|ifhmode|ifmmode|ifinner|"
                         r"ifvoid|ifhbox|ifvbox|ifeof|ifcase|ifdefined|ifcsname|iffontchar|else|fi|or)(?![A-Za-z])")
LEVEL = {"section": 1, "subsection": 2, "subsubsection": 3}
MATH_ENVS = r"equation|align|gather|multline|eqnarray|displaymath|flalign|alignat"
DISPLAY = re.compile(r"\\begin\{(?:" + MATH_ENVS + r")\*?\}|\\\[|\$\$")
DROP_ENVS = re.compile(r"\\begin\{(" + MATH_ENVS + r"|tabular\*?|tabularx|longtable|algorithmic|lstlisting|verbatim|"
                       r"tikzpicture|minted)\*?\}.*?\\end\{\1\*?\}", re.S)
DROP_CMDS = re.compile(r"\\(?:cite[a-z]*|ref|eqref|cref|Cref|autoref|label|includegraphics|input|include|url|"
                       r"bibliography|bibliographystyle|documentclass|usepackage|newcommand|renewcommand|hypersetup)"
                       r"\*?(?:\[[^\]]*\])*\{[^{}]*\}")
WORD = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'-]+")


@dataclass
class Section:
    level: int
    title: str
    start: int           # offset of the heading in the body
    end: int = 0         # offset where the section's region ends (next heading of the same or a higher level)
    appendix: bool = False


@dataclass
class Doc:
    folder: Path
    main: Path
    source: str          # all sources, comments removed, inputs expanded
    body: str            # between \begin{document} and \end{document}, bibliography removed
    title: str
    sections: list[Section] = field(default_factory=list)


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", text)


def braced(text: str, at: int) -> tuple[str, int]:
    """The content of the brace group that opens at ``text[at] == '{'`` and the offset after it."""
    depth, i = 0, at
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[at + 1:i], i + 1
        i += 1
    return text[at + 1:], len(text)


def expand(path: Path, folder: Path, seen: set[Path], working_directory: Path | None = None) -> str:
    path = path.resolve()
    working_directory = working_directory or path.parent
    boundary = folder.resolve().parent
    if not path.is_relative_to(boundary):
        raise ValueError(f"LaTeX include escapes manuscripts/: {path.name}")
    if path in seen:
        raise ValueError(f"Repeated or cyclic LaTeX include: {path.name}")
    if not path.is_file():
        raise ValueError(f"Missing LaTeX source/include: {path.name}")
    seen.add(path)
    # A quoted source listing is not active input, structure or countable content.
    text = LITERAL_ENVS.sub(" ", path.read_text(encoding="utf-8"))
    text = re.sub(r"\\verb\*?(?P<delimiter>[^A-Za-z0-9\s]).*?(?P=delimiter)", " ", text, flags=re.S)
    text = strip_comments(text)

    def sub(m: re.Match) -> str:
        name = m.group(1).strip()
        # TeX resolves nested inputs from the main compilation working directory,
        # not from the directory containing the currently expanded input file.
        target = working_directory / name
        if not target.suffix:
            target = target.with_name(target.name + ".tex")
        return expand(target.resolve(), folder, seen, working_directory)

    return re.sub(r"\\(?:input|include)\{([^}]+)\}", sub, text)


def plain(text: str) -> str:
    """The prose of a piece of LaTeX: math, tables, listings and commands removed."""
    t = DROP_ENVS.sub(" ", text)
    t = re.sub(r"\\\[.*?\\\]|\$\$.*?\$\$|\\\(.*?\\\)|(?<!\\)\$.*?(?<!\\)\$", " ", t, flags=re.S)
    t = DROP_CMDS.sub(" ", t)
    t = re.sub(r"\\begin\{[^}]*\}|\\end\{[^}]*\}", " ", t)
    t = re.sub(r"\\[A-Za-z]+\*?", " ", t)
    return re.sub(r"[{}\[\]~]", " ", t)


def words(text: str) -> int:
    return len(WORD.findall(plain(text)))


def clean_title(text: str) -> str:
    # Preserve value-bearing characters, case and unknown commands. Erasing math
    # or selecting alphabetic words silently made 999 equal to 1 (and -1 to 1).
    text = re.sub(r"\\(?:textbf|textit|textnormal|textrm|textsf|texttt|emph|text|mathrm|mathbf|mathit)(?![A-Za-z])\s*", "", text)
    text = re.sub(r"(?<!\\)\$", "", text)
    text = text.replace(r"\(", "").replace(r"\)", "")
    text = re.sub(r"\\([%&#_$])", r"\1", text)
    text = re.sub(r"\\[,;:! ]", " ", text)
    text = text.replace("{", "").replace("}", "").replace("~", " ")
    return " ".join(text.split())


def find_main(folder: Path) -> Path | None:
    """The main source: a ``.tex`` with ``\\documentclass`` in the folder or in its ``tex/`` subfolder, ``main.tex`` first."""
    candidates = sorted(folder.glob("*.tex")) + sorted((folder / "tex").glob("*.tex"))
    with_class = [p for p in candidates if "\\documentclass" in strip_comments(p.read_text(encoding="utf-8", errors="replace"))]
    if not with_class:
        return None
    for p in with_class:
        if p.name == "main.tex":
            return p
    return with_class[0]


def load(folder: Path) -> Doc | None:
    main = find_main(folder)
    if main is None:
        return None
    source = expand(main.resolve(), folder, set())
    begin = source.find("\\begin{document}")
    end = source.rfind("\\end{document}")
    body = source[begin + len("\\begin{document}"):end if end > begin else len(source)] if begin >= 0 else source
    if CONDITIONAL.search(body):
        raise ValueError("Active TeX conditional in manuscript body: content depth is unmeasurable statically; use explicit rendered source before admission")
    body = re.sub(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", " ", body, flags=re.S)
    body = re.sub(r"\\(?:bibliography|printbibliography)\b(?:\{[^}]*\}|\[[^\]]*\])*", " ", body)
    title = ""
    m = re.search(r"\\title\s*(?:\[[^\]]*\])?\s*\{", source)
    if m:
        title, _ = braced(source, m.end() - 1)
    doc = Doc(folder=folder, main=main, source=source, body=body, title=title)
    appendix_at = body.find("\\appendix")
    heads: list[Section] = []
    for m in SECTIONING.finditer(body):
        name, after = braced(body, m.end() - 1)
        heads.append(Section(LEVEL[m.group(1)], " ".join(name.split()), m.start(),
                             appendix=0 <= appendix_at < m.start()))
    for i, s in enumerate(heads):
        s.end = next((h.start for h in heads[i + 1:] if h.level <= s.level), len(body))
    doc.sections = heads
    return doc


def region_of(doc: Doc, label: str) -> tuple[str, Section | None]:
    """The text of the section, subsection or subsubsection that holds ``\\label{label}``."""
    m = re.search(r"\\label\{" + re.escape(label) + r"\}", doc.body)
    if not m:
        return "", None
    holder = None
    for s in doc.sections:
        if s.start <= m.start() < s.end and (holder is None or s.level > holder.level):
            holder = s
    if holder is None:
        return "", None
    return doc.body[holder.start:holder.end], holder


def float_labels(body: str) -> dict[str, str]:
    """Labels defined inside figure and table environments, with the environment kind."""
    out: dict[str, str] = {}
    for m in re.finditer(r"\\begin\{(figure|table|longtable)\*?\}(.*?)\\end\{\1\*?\}", body, re.S):
        for lab in re.findall(r"\\label\{([^}]+)\}", m.group(2)):
            out[lab] = m.group(1)
    return out


def measures(doc: Doc) -> dict[str, int]:
    body = doc.body
    cited = set()
    for keys in re.findall(r"\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}", body):
        cited.update(k.strip() for k in keys.split(",") if k.strip())
    display = len(re.findall(r"\\begin\{(?:" + MATH_ENVS + r")\*?\}", body)) + len(re.findall(r"\\\[", body)) \
        + len(re.findall(r"\$\$", body)) // 2
    return {
        "words": words(body),
        "equations": display,
        "figures": len(re.findall(r"\\begin\{figure\*?\}", body)),
        "tables": len(re.findall(r"\\begin\{(?:table\*?|longtable)\}", body)),
        "references": len(cited),
        "algorithms": len(re.findall(r"\\begin\{algorithm\*?\}", body)),
        "sections": sum(1 for s in doc.sections if s.level == 1),
    }


def sdd_ids(root: Path, findings: list[str] | None = None) -> tuple[list[str], set[str]]:
    """The method ids of the SDD's ## Method ladder and the claim ids of its ## Beyond the state of the art."""
    sdd = root / "docs" / "design" / "SDD.md"
    findings = findings if findings is not None else []
    ids = inventory_table(sdd, "method ladder", "tier", findings, root)
    if not sdd.is_file():
        return [], set()
    markdown = visible(sdd.read_text(encoding="utf-8"), drop_inline=False)
    # Inventory membership comes from the one validated parser. Source order is
    # presentation only and cannot discard inline-code or indented table IDs.
    methods = sorted(ids, key=lambda identifier: (markdown.find(identifier), identifier))
    claims: set[str] = set()
    where = None
    for line in markdown.splitlines():
        if re.match(r"^\s{0,3}##\s", line):
            name = re.sub(r"^\s{0,3}##\s+(?:\d+\.\s*)?", "", line).strip().lower()
            where = ("beyond" if name == "beyond the state of the art"
                     else "novel" if name == "novel contributions" else None)
            continue
        if where == "beyond":
            claims.update(re.findall(r"\bBS-\d+\b", line))
        elif where == "novel":
            claims.update(re.findall(r"\bNC-\d+\b", line))
    return methods, claims


def contract_ids(root: Path) -> list[str]:
    catalog = root / "docs" / "contracts" / "catalog.md"
    if not catalog.is_file():
        return []
    out: list[str] = []
    in_table = False
    for line in catalog.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.lstrip().startswith("|") else None
        if cells is None:
            if in_table:
                break
            continue
        if cells[:2] == ["id", "version"]:
            in_table = True
            continue
        if in_table and cells and not set(cells[0]) <= set("-: "):
            out.append(cells[0].strip("`"))
    return out


def check_doc(root: Path, doc: Doc, cov: dict, methods: list[str], claims: set[str], contracts: list[str],
              declared_titles: dict[str, str]) -> list[str]:
    at = f"manuscripts/{doc.folder.name}"
    kind = cov.get("kind")
    out: list[str] = []
    if kind not in KINDS:
        return [f"{at}/coverage.json: kind is {kind!r}, it must be one of {', '.join(KINDS)}"]
    document_class = re.search(r"\\documentclass(?:\[[^\]]*\])?\s*\{([^}]+)\}", doc.source)
    allowed_classes = {"article", "report", "IEEEtran", "elsarticle", "revtex4-2"}
    if not document_class or document_class.group(1).strip() not in allowed_classes:
        out.append(f"{at}: unsupported document class; use one prescribed by {RULE} section 2")
    structure = DROP_ENVS.sub(" ", doc.body)
    structure = re.sub(r"\\verb\*?(?P<delimiter>[^A-Za-z0-9\s]).*?(?P=delimiter)", " ", structure, flags=re.S)
    if kind == "manuscript" and re.search(r"\\chapter\*?\s*(?:\[[^\]]*\])?\s*\{", structure):
        out.append(f"{at}: a research paper uses sections, not chapter divisions")
    have = measures(doc)
    for key, floor in FLOORS[kind].items():
        if have[key] < floor:
            out.append(f"{at}: {have[key]} {key}, the {kind} floor is {floor}")
    for name, needles in REQUIRED[kind]:
        heads = [s.title.lower() for s in doc.sections if not s.appendix]
        if not any(any(n in h for n in needles) for h in heads):
            if not (name == "Notation" and re.search(r"\\caption\{[^}]*(notation|nomenclature|symbols)", doc.body, re.I)):
                out.append(f"{at}: no section for {name} (a heading with one of: {', '.join(needles)})")
    for s in doc.sections:
        n = words(doc.body[s.start:s.end])
        short = s.appendix or any(k in s.title.lower() for k in SHORT_SECTIONS)
        floor = (SHORT_SECTION_WORDS if short else SECTION_WORDS) if s.level == 1 else SUBSECTION_WORDS
        if s.level <= 2 and n < floor:
            what = "section" if s.level == 1 else "subsection"
            out.append(f"{at}: {what} '{s.title}' has {n} words of prose, the floor is {floor}")
    for m in re.finditer(r"\\begin\{(figure|table|longtable)\*?\}(.*?)\\end\{\1\*?\}", doc.body, re.S):
        cap = re.search(r"\\caption\s*(?:\[[^\]]*\])?\s*\{", m.group(2))
        text = braced(m.group(2), cap.end() - 1)[0] if cap else ""
        lab = re.search(r"\\label\{([^}]+)\}", m.group(2))
        name = lab.group(1) if lab else f"{m.group(1)} at offset {m.start()}"
        if words(text) < CAPTION_WORDS:
            out.append(f"{at}: {m.group(1)} {name}: caption of {words(text)} words, the floor is {CAPTION_WORDS} (what it shows, on what data)")
        if not lab:
            out.append(f"{at}: {m.group(1)} at offset {m.start()} has no \\label, so the text cannot discuss it")
            continue
        outside = doc.body[:m.start()] + doc.body[m.end():]
        if not re.search(r"\\(?:ref|cref|Cref|autoref|eqref)\{[^}]*\b" + re.escape(lab.group(1)) + r"\b", outside):
            out.append(f"{at}: {m.group(1)} {lab.group(1)} is never referenced in the text: every float is read in the prose")
    for hit in VAGUE.finditer(plain(doc.body)):
        out.append(f"{at}: vague wording '{hit.group(0)}': name the items")
    if kind == "manuscript" and not UNCERTAINTY.search(doc.body):
        out.append(f"{at}: no uncertainty is reported (a ± interval, a confidence interval or a standard deviation in the results)")
    missing_macros = [m for m in HEADER_MACROS if f"\\newcommand{{\\{m}}}" not in doc.source]
    if missing_macros:
        missing_text = ", \\".join(missing_macros)
        out.append(f"{at}: the page-1 header block lacks \\{missing_text} (conventions/manuscript-header-standard.md)")
    if not doc.title.strip():
        out.append(f"{at}: no \\title")
    elif clean_title(doc.title) not in declared_titles:
        out.append(f"{at}: the title '{' '.join(doc.title.split())}' is not the title of any product.json manuscripts entry: "
                   f"update the title in both places when the results change ({RULE} section 6)")
    elif declared_titles[clean_title(doc.title)] != kind:
        out.append(f"{at}: product.json declares this title as {declared_titles[clean_title(doc.title)]}, coverage.json says {kind}")
    floats = float_labels(doc.body)
    support = cov.get("title_support")
    if not isinstance(support, list) or not support:
        out.append(f"{at}/coverage.json: title_support is empty: name the result tables and figures that sustain the title")
    else:
        for lab in support:
            if lab not in floats:
                out.append(f"{at}/coverage.json: title_support {lab!r} is not the label of a figure or a table of the manuscript")
    wanted = {"methods": methods, "contracts": contracts} if kind == "technical-report" else {}
    for group, ids in wanted.items():
        mapped = cov.get(group) or {}
        for extra in sorted(set(mapped) - set(ids)):
            out.append(f"{at}/coverage.json: {group} maps unknown inventory ID {extra}")
        for i in ids:
            if i not in mapped:
                out.append(f"{at}/coverage.json: {group} does not map {i}: the technical report covers every "
                           f"{'method of the SDD ladder' if group == 'methods' else 'contract of the catalog'}")
    if kind == "manuscript":
        mapped = cov.get("claims") or {}
        if not mapped:
            out.append(f"{at}/coverage.json: claims is empty: a manuscript reports at least one proposed method")
        for i in mapped:
            if i not in claims:
                out.append(f"{at}/coverage.json: claims maps {i}, which the SDD's '## Beyond the state of the art' or '## Novel contributions' does not list")
    for group, (min_words, min_eq) in REGION.items():
        regions: list[tuple[str, Section]] = []
        for i, lab in (cov.get(group) or {}).items():
            text, holder = region_of(doc, str(lab))
            if holder is None:
                out.append(f"{at}/coverage.json: {group} {i} points at {lab!r}, which is not a \\label inside a section")
                continue
            if group in {"methods", "claims"}:
                for other_id, other in regions:
                    if max(holder.start, other.start) < min(holder.end, other.end):
                        out.append(f"{at}/coverage.json: {group} {other_id} and {i} use overlapping coverage regions; each method or proposal needs its own substantial section")
                regions.append((i, holder))
            n, eq = words(text), len(DISPLAY.findall(text))
            if n < min_words or eq < min_eq:
                out.append(f"{at}: the section '{holder.title}' that covers {i} has {n} words and {eq} display equations; "
                           f"the floor is {min_words} words and {min_eq} equations")
    for bad in re.findall(r"\b(?:M|BS|NC)-\d+\b", plain(doc.body)):
        out.append(f"{at}: the internal id {bad} appears in the text: name the method")
        break
    return out


def check(root: Path, only: str | None = None, report: bool = False) -> list[str]:
    folder = root / "manuscripts"
    if only and (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", only) or not (folder / only).is_dir() or only in SUPPORT):
        return [f"manuscripts/{only}: requested manuscript folder is missing or invalid"]
    template = (root / ".template-source").is_file()
    out: list[str] = []
    try:
        product = json.loads((root / "product.json").read_text(encoding="utf-8"))
        entries = product.get("manuscripts", []) if isinstance(product, dict) else []
    except (OSError, ValueError):
        entries = []
    declared = {clean_title(e["title"]): e.get("kind", "") for e in entries
                if isinstance(e, dict) and isinstance(e.get("title"), str)}
    methods, claims, contracts = [], set(), []
    try:
        methods, claims = sdd_ids(root, out)
        contracts = sorted(inventory_table(root / "docs/contracts/catalog.md", None, "version", out, root))
    except (OSError, UnicodeError, ValueError) as error:
        out.append(f"manuscript coverage inventories: cannot read ({error})")
    kinds_seen: list[str] = []
    claimed: set[str] = set()
    dirs = sorted(p for p in folder.iterdir() if p.is_dir()) if folder.is_dir() else []
    for d in dirs:
        if d.name in SUPPORT or (only and d.name != only):
            continue
        try:
            doc = load(d)
        except (OSError, UnicodeError, ValueError) as error:
            out.append(f"manuscripts/{d.name}: {error}")
            continue
        texts = [p for p in d.rglob("*") if p.suffix.lower() in NOT_LATEX and "data" not in p.relative_to(d).parts
                 and p.name.lower() not in ("readme.md", "metadata.md")]
        if doc is None:
            what = f" ({', '.join(sorted({p.suffix for p in texts}))} only)" if texts else ""
            out.append(f"manuscripts/{d.name}: no LaTeX main file with \\documentclass{what}: a CAOS manuscript is written in LaTeX ({RULE} section 2)")
            continue
        if report:
            print(f"manuscripts/{d.name}: " + ", ".join(f"{k} {v}" for k, v in measures(doc).items()))
        if not (list(d.rglob("*.bib")) or "\\begin{thebibliography}" in doc.source):
            out.append(f"manuscripts/{d.name}: no bibliography (a .bib file or thebibliography)")
        cov_path = d / "coverage.json"
        try:
            cov = json.loads(cov_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            out.append(f"manuscripts/{d.name}: coverage.json is missing ({RULE} section 5)")
            continue
        except ValueError as exc:
            out.append(f"manuscripts/{d.name}/coverage.json is not valid JSON ({exc})")
            continue
        if not isinstance(cov, dict):
            out.append(f"manuscripts/{d.name}/coverage.json is not an object")
            continue
        shape_errors = []
        for group in ("methods", "contracts", "claims"):
            mapping = cov.get(group, {})
            if not isinstance(mapping, dict) or any(not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip() for k, v in mapping.items()):
                shape_errors.append(f"manuscripts/{d.name}/coverage.json: {group} must map nonempty string IDs to nonempty LaTeX label strings")
        support = cov.get("title_support")
        if not isinstance(support, list) or any(not isinstance(v, str) or not v.strip() for v in support):
            shape_errors.append(f"manuscripts/{d.name}/coverage.json: title_support must be a list of label strings")
        if shape_errors:
            out.extend(shape_errors)
            continue
        kinds_seen.append(cov.get("kind", ""))
        claimed.update((cov.get("claims") or {}) if cov.get("kind") == "manuscript" else {})
        out += check_doc(root, doc, cov, methods, claims, contracts, declared)
    if only:
        return out
    if not template and "technical-report" not in kinds_seen:
        out.append(f"manuscripts/: no technical report (a folder whose coverage.json has kind technical-report) ({RULE} section 3)")
    for c in sorted(claims - claimed):
        label = "proposed method" if c.startswith("BS-") else "novel contribution"
        out.append(f"manuscripts/: the {label} {c} of the SDD has no manuscript (coverage.json claims) ({RULE} section 3)")
    return out


def bar_for_source(source: Path) -> list[str] | None:
    """The findings for the manuscript whose sources are at ``source`` (its folder, its ``tex/`` folder or its main file),
    or None when the source is not a CAOS product manuscript (no ``manuscripts/<slug>/`` beside a ``product.json``)."""
    source = source.resolve()
    holder = next((p for p in [source, *source.parents] if p.name == "manuscripts"), None)
    if holder is None or holder == source or not (holder.parent / "product.json").is_file():
        return None
    return check(holder.parent, only=source.relative_to(holder).parts[0])


def require_bar(source: Path) -> None:
    """Exit with the findings when the CAOS product manuscript at ``source`` is below the bar (the publishers call it)."""
    findings = bar_for_source(source)
    if findings:
        print(f"MANUSCRIPT CONTENT CHECK FAILED ({len(findings)} findings; {RULE}):")
        for f in findings:
            print(f"  - {f}")
        sys.exit(f"content bar: {len(findings)} finding(s) in {source}; nothing was reserved or published")


def main() -> int:
    ap = argparse.ArgumentParser(prog="check_manuscript_depth", description=__doc__.split("\n")[0])
    ap.add_argument("root", nargs="?", help="the product repository root (default: this script's repository)")
    ap.add_argument("--only", help="check one manuscript folder (its slug) and skip the product-level coverage")
    ap.add_argument("--report", action="store_true", help="print the measures of each manuscript")
    a = ap.parse_args()
    root = Path(a.root).resolve() if a.root else Path(__file__).resolve().parents[1]
    findings = check(root, a.only, a.report)
    if findings:
        print(f"MANUSCRIPT CONTENT CHECK FAILED ({len(findings)} findings; {RULE}):")
        for f in findings:
            print(f"  - {f}")
        return 1
    print("check_manuscript_depth: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
