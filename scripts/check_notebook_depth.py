#!/usr/bin/env python3
"""Current content depth and whole-tool notebook coverage. Standard library only.

Complements check_notebooks.py; never executes a notebook or contacts the network.
Counts cannot accept mathematical/teaching quality: independent review is required.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("_depth_structural_reader", HERE / "check_notebooks.py")
STRUCT = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = STRUCT
spec.loader.exec_module(STRUCT)
LANGS = ("en", "es")
SENSITIVITY = {"en": re.compile(r"sensitiv|parameter|robust|fail|break|limit|regime", re.I),
               "es": re.compile(r"sensibilidad|parámetro|parametro|robust|falla|quiebre|límite|limite|régimen|regimen", re.I)}
OWN = {"en": re.compile(r"your own data|your data|own data|extend|adapt", re.I),
       "es": re.compile(r"tus propios datos|tus datos|datos propios|extender|adaptar", re.I)}
GENERIC = re.compile(r"^\s*(?:\*\*(?:question|pregunta):\*\*\s*)?(?:validate|verify|check|reproduce|run|smoke|sanity|"
                     r"validar|verificar|comprobar|reproducir|ejecutar|correr)\b|smoke test|sanity check|"
                     r"end-to-end run|(?:the|los?|las?) artifacts?\b|artefactos?\b|run (?:the|all) (?:pipeline|stages)", re.I)
DISPLAY = re.compile(r"\$\$(?P<dollar>.+?)\$\$|\\\[(?P<bracket>.+?)\\\]|"
                     r"\\begin\{(?P<env>(?:equation|align)\*?)\}(?P<body>.+?)\\end\{(?P=env)\}", re.S)
SOURCE = re.compile(r"https?://[^\s<>]+|(?<![\w/])10\.\d{4,9}/[^\s<>]+", re.I)


def visible(markdown: str, drop_inline: bool = True) -> str:
    """Remove hidden/code content before counting equations, headings or sources."""
    markdown = STRUCT.visible_markdown(markdown)
    lines, fence = [], None
    for line in markdown.splitlines():
        opening = re.match(r"^\s*(`{3,}|~{3,})", line)
        if opening:
            token = opening[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None and not line.startswith(("    ", "\t")):
            lines.append(line)
    text = "\n".join(lines)
    return re.sub(r"`[^`\n]*`", "", text) if drop_inline else text


def source_identity(token: str) -> str:
    token = unquote(token.rstrip(".,;:)]}"))
    if re.match(r"10\.\d{4,9}/", token, re.I):
        return token.lower()
    parsed = urlsplit(token)
    if parsed.hostname in {"doi.org", "dx.doi.org"}:
        return parsed.path.lstrip("/").lower()
    return parsed._replace(netloc=parsed.netloc.lower(), fragment="").geturl().rstrip("/")


def measures(nb: dict, lang: str, root: Path, bar: dict) -> dict:
    reader = STRUCT.Reading(nb, lang, root, bar)
    equations, sources, heads = set(), set(), []
    section = ""
    for cell in nb["cells"]:
        if cell.get("cell_type") != "markdown":
            continue
        md = visible(STRUCT.text_of(cell.get("source", "")))
        for match in DISPLAY.finditer(md):
            expression = next((match[name] for name in ("dollar", "bracket", "body") if match[name]), "")
            expression = re.sub(r"\s+", "", expression)
            if expression:
                equations.add(expression)
        for line in md.splitlines():
            if line.startswith("## "):
                section = line[3:].strip().lower()
            if line.startswith("### "):
                heads.append(line[4:].strip())
            if section in {"references", "referencias"}:
                sources.update(source_identity(m[0]) for m in SOURCE.finditer(line))
    caos = nb.get("metadata", {}).get("caos") or {}
    first = visible(STRUCT.text_of(nb["cells"][0].get("source", "")), drop_inline=False) if nb["cells"] else ""
    title = next((line[2:] for line in first.splitlines() if line.startswith("# ")), "")
    question = next((line for line in first.splitlines() if re.match(r"\*\*(?:question|pregunta):\*\*", line, re.I)), "")
    def normalized(value):
        value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
        value = re.sub(r"^\*\*(?:question|pregunta):\*\*\s*", "", value, flags=re.I)
        return re.sub(r"[*_~`]", "", value).strip()
    return {"level": reader.level or 2, "prose": reader.words(), "figures": sum(n for _, n in reader.fig_cells),
            "equations": len(equations), "sources": len(sources), "heads": heads,
            "title": normalized(title), "metadata title": normalized(str(caos.get("title", ""))), "question": normalized(question)}


def table_cells(line: str) -> list[str]:
    """GFM requires literal cell pipes to be escaped, including inside inline code."""
    parts, current, escaped = [], [], False
    for char in line.strip():
        if char == "|" and not escaped:
            parts.append("".join(current).strip().strip("`"))
            current = []
        else:
            current.append(char)
        escaped = char == "\\" and not escaped
    parts.append("".join(current).strip().strip("`"))
    if parts and not parts[0]:
        parts.pop(0)
    if parts and not parts[-1]:
        parts.pop()
    return parts


def inventory_table(path: Path, heading: str | None, second: str, findings: list[str], root: Path) -> set[str]:
    name = path.relative_to(root).as_posix()
    try:
        lines = visible(path.read_text(encoding="utf-8"), drop_inline=False).splitlines()
    except (OSError, UnicodeError) as exc:
        findings.append(f"{name}: cannot read inventory ({exc})")
        return set()
    inside, table = heading is None, False
    width = 0
    separator_seen = False
    ids = set()
    for line in lines:
        if line.startswith("## "):
            if table:
                break
            inside = heading is None or re.sub(r"^##\s+(?:\d+\.\s*)?", "", line).strip().lower() == heading
        if not inside:
            continue
        if not line.lstrip().startswith("|"):
            if table:
                break
            continue
        cells = table_cells(line)
        if cells[:2] == ["id", second]:
            table = True
            width = len(cells)
            if width < 3:
                findings.append(f"{name}: malformed inventory header")
        elif table and not separator_seen:
            separator_seen = len(cells) == width and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)
            if not separator_seen:
                findings.append(f"{name}: inventory header has no valid Markdown separator row")
        elif table and cells and cells[0]:
            if len(cells) != width or any(not value for value in cells):
                findings.append(f"{name}: malformed inventory row {cells[0]!r}")
            elif cells[0] in ids:
                findings.append(f"{name}: duplicate inventory ID {cells[0]!r}")
            else:
                ids.add(cells[0])
    if not table or not ids:
        findings.append(f"{name}: no readable nonempty inventory table")
    return ids


def contained(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def inventories(root: Path, findings: list[str]) -> dict[str, set[str]]:
    wanted = {
        "methods": inventory_table(root / "docs/design/SDD.md", "method ladder", "tier", findings, root),
        "contracts": inventory_table(root / "docs/contracts/catalog.md", None, "version", findings, root),
        "stages": set(), "packages": set(),
    }
    try:
        product = json.loads((root / "product.json").read_text(encoding="utf-8"))
        if not isinstance(product, dict):
            raise ValueError("must be an object")
        packages = product.get("method_packages", [])
        if not isinstance(packages, list) or any(not isinstance(p, str) or not p.strip() for p in packages):
            raise ValueError("method_packages must be a list of nonempty distribution names")
        wanted["packages"] = set(packages)
        declared = product.get("pipeline_stage_sources", {})
        if not isinstance(declared, dict):
            raise ValueError("pipeline_stage_sources must map stage IDs to relative Python source paths")
        for stage, source in declared.items():
            if (not isinstance(stage, str) or not stage.strip() or not valid_relative(source, suffix=".py")
                    or not contained(root / source, root) or not (root / source).is_file()):
                raise ValueError(f"pipeline_stage_sources has invalid stage/source {stage!r}: {source!r}")
            wanted["stages"].add(stage)
    except (OSError, UnicodeError, ValueError) as exc:
        findings.append(f"product.json: invalid inventory ({exc})")
    stage_dir = root / "data-pipeline/pipeline/stages"
    for path in sorted(stage_dir.glob("*.py")):
        if not path.name.startswith("_"):
            if not contained(path, root):
                findings.append(f"{path.relative_to(root)}: stage source escapes repository")
            else:
                wanted["stages"].add(path.stem)
    if not wanted["stages"]:
        findings.append("product.json: no pipeline stage inventory; declare real pipeline_stage_sources when stages use another layout")
    return wanted


def valid_relative(value, suffix: str) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and path.as_posix() == value and path.suffix == suffix


def coverage(root: Path, levels: dict[tuple[str, str], int], findings: list[str]) -> None:
    wanted = inventories(root, findings)
    at = "notebooks/coverage.json"
    try:
        cov = json.loads((root / at).read_text(encoding="utf-8"))
        if not isinstance(cov, dict):
            raise ValueError("must be an object")
    except (OSError, UnicodeError, ValueError) as exc:
        findings.append(f"{at}: cannot read coverage ({exc})")
        return
    for group, ids in wanted.items():
        mapped = cov.get(group)
        if not isinstance(mapped, dict):
            findings.append(f"{at}: {group} must be an object of ID to notebook path lists")
            continue
        for identifier in sorted(ids - mapped.keys()):
            findings.append(f"{at}: {group} does not map {identifier}")
        for identifier, paths in mapped.items():
            if not isinstance(paths, list) or not paths:
                findings.append(f"{at}: {group} {identifier} must have a nonempty list of paths")
                continue
            seen = set()
            for value in paths:
                if not valid_relative(value, ".ipynb") or len(PurePosixPath(value).parts) != 2:
                    findings.append(f"{at}: {group} {identifier} has invalid relative notebook path {value!r}")
                    continue
                if value in seen:
                    findings.append(f"{at}: {group} {identifier} repeats path {value}")
                seen.add(value)
                for lang in LANGS:
                    tree = root / "notebooks" / lang
                    path = tree / value
                    if not contained(path, tree) or not path.is_file() or (lang, value) not in levels:
                        findings.append(f"{at}: {group} {identifier} names missing/unreadable or escaping {lang}/{value}")
                    elif group == "methods" and levels[lang, value] < 2:
                        findings.append(f"{at}: methods {identifier} is covered only at level1 by {lang}/{value}")


def check(root: Path, report: bool = False) -> list[str]:
    findings, levels = [], {}
    policy = json.loads((HERE / "notebook_depth.json").read_text(encoding="utf-8"))["floors"]
    bar = STRUCT.load_bar(HERE / "notebook_bar.json")
    for lang in LANGS:
        tree = root / "notebooks" / lang
        paths = sorted(tree.rglob("*.ipynb"))
        if not paths:
            findings.append(f"notebooks/{lang}: no notebooks")
        for path in paths:
            rel = path.relative_to(tree).as_posix()
            at = f"notebooks/{lang}/{rel}"
            try:
                if not contained(path, tree):
                    raise ValueError("notebook escapes language tree")
                nb = json.loads(path.read_text(encoding="utf-8"))
                values = measures(nb, lang, root, bar)
            except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError) as exc:
                findings.append(f"{at}: cannot measure notebook ({exc})")
                continue
            levels[lang, rel] = values["level"]
            if report:
                print(f"{at}: " + ", ".join(f"{key} {values[key]}" for key in ("level", "prose", "figures", "equations", "sources")))
            floors = {"prose": STRUCT.floor_at(bar, "prose_words", values["level"]),
                      "figures": STRUCT.floor_at(bar, "figures", values["level"]),
                      **policy["1" if values["level"] == 1 else "2"]}
            for key, minimum in floors.items():
                if values[key] < minimum:
                    findings.append(f"{at}: {key} {values[key]}, current level{values['level']} floor is {minimum}")
            for key in ("title", "metadata title", "question"):
                if GENERIC.search(values[key]):
                    findings.append(f"{at}: {key} is a run or a check, not a lesson")
            if values["level"] >= 2:
                if not any(SENSITIVITY[lang].search(head) for head in values["heads"]):
                    findings.append(f"{at}: no third-level sensitivity/limits heading")
                if not any(OWN[lang].search(head) for head in values["heads"]):
                    findings.append(f"{at}: no third-level own data heading")
    coverage(root, levels, findings)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", type=Path, default=HERE.parent)
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    findings = check(args.root.resolve(), args.report)
    for finding in findings:
        print(f"  - {finding}")
    print(f"check_notebook_depth: {'FAILED (' + str(len(findings)) + ' findings)' if findings else 'OK'}")
    return int(bool(findings))


if __name__ == "__main__":
    sys.exit(main())
