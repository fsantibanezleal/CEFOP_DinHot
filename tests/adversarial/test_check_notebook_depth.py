"""Portable depth CLI adversaries. Generated prose/images below are parser fixtures,
not teaching content or numerical evidence. Production curriculum is checked too.
"""
from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_notebook_depth.py"
REL = "01-topic/01-lesson.ipynb"


def prose(n: int) -> str:
    lines = []
    for i in range(n // 14 + 1):
        key = chr(97 + i // 26) + chr(97 + i % 26)
        lines.append(f"Parameter {key} changes the measured response while independent controls identify the applicable physical regime.")
    return "\n\n".join(lines)


def lesson(lang: str = "en", level: int = 2) -> dict:
    headings = ("Method", "References", "Sensitivity to prices", "Use your own data") if lang == "en" else (
        "Método", "Referencias", "Sensibilidad a los costos", "Usa tus propios datos")
    method, references, sensitivity, own = headings
    question = "Question" if lang == "en" else "Pregunta"
    cells = [{"cell_type": "markdown", "source": f"# Prices and decisions\n\n**{question}:** How does a price move the solution?", "metadata": {}},
             {"cell_type": "markdown", "source": f"## {method}\n\n{prose(1650)}\n\n$$a=b$$\n\n$$b=c$$\n\n### {sensitivity}\n\n### {own}", "metadata": {}}]
    for i in range(3):
        cells.extend([{"cell_type": "code", "source": "# fixture output\nprint(1)", "metadata": {}, "execution_count": i + 1,
                       "outputs": [{"output_type": "display_data", "metadata": {}, "data": {
                           "image/png": base64.b64encode(b"parser-fixture-image-" + bytes([i])).decode()}}]},
                      {"cell_type": "markdown", "metadata": {}, "source": prose(50)}])
    cells.append({"cell_type": "markdown", "metadata": {}, "source": f"## {references}\n\n" + "\n".join(
        f"- https://doi.org/10.1000/source{i}" for i in range(4))})
    return {"cells": cells, "metadata": {"caos": {"level": level, "language": lang, "title": "Prices and decisions"}}}


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def product(root: Path) -> Path:
    (root / "docs/design").mkdir(parents=True)
    (root / "docs/contracts").mkdir(parents=True)
    (root / "docs/design/SDD.md").write_text(
        "## Method ladder\n\n| id | tier | method |\n|---|---|---|\n| M-1 | classical | Real method |\n", encoding="utf-8")
    (root / "docs/contracts/catalog.md").write_text(
        "| id | version | owner |\n|---|---|---|\n| trace | 1.0.0 | pipeline |\n", encoding="utf-8")
    stage = root / "data-pipeline/pipeline/stages/evaluate.py"
    stage.parent.mkdir(parents=True)
    stage.write_text("def run(x):\n    return x\n", encoding="utf-8")
    write_json(root / "product.json", {"method_packages": ["scientific-package"]})
    for lang in ("en", "es"):
        write_json(root / "notebooks" / lang / REL, lesson(lang))
    write_json(root / "notebooks/coverage.json", {"methods": {"M-1": [REL]}, "contracts": {"trace": [REL]},
                                                "stages": {"evaluate": [REL]}, "packages": {"scientific-package": [REL]}})
    return root


def run(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPT), str(root), *extra], capture_output=True, encoding="utf-8", timeout=30)


def change(root: Path, mutate, lang: str = "en") -> None:
    path = root / "notebooks" / lang / REL
    nb = json.loads(path.read_text(encoding="utf-8"))
    mutate(nb)
    write_json(path, nb)


def test_adversarial_depth_floors_and_duplicate_images(tmp_path: Path) -> None:
    root = product(tmp_path)
    assert run(root).returncode == 0
    change(root, lambda nb: nb["cells"][1].update(source="## Method\nShort prose."))
    result = run(root)
    assert result.returncode == 1 and "prose" in result.stdout
    root = product(tmp_path / "duplicate")
    change(root, lambda nb: nb["cells"][4]["outputs"][0]["data"].update(nb["cells"][2]["outputs"][0]["data"]))
    assert "figures 2" in run(root).stdout


def test_adversarial_equations_and_sources_are_distinct_visible_content(tmp_path: Path) -> None:
    root = product(tmp_path)
    change(root, lambda nb: nb["cells"][1].update(source=nb["cells"][1]["source"].replace("$$b=c$$", "<!-- $$c=d$$ -->\n```tex\n$$c=d$$\n```\n$$a=b$$")))
    assert "equations 1" in run(root).stdout
    root = product(tmp_path / "sources")
    change(root, lambda nb: nb["cells"][-1].update(source="## References\nhttps://doi.org/10.1000/one\n10.1000/one\nhttps://doi.org/10.1000/one\n<!-- https://example.com/hidden -->"))
    assert "sources 1" in run(root).stdout


@pytest.mark.parametrize("lang", ["en", "es"])
def test_adversarial_sensitivity_own_data_and_generic_questions(tmp_path: Path, lang: str) -> None:
    root = product(tmp_path)
    change(root, lambda nb: nb["cells"][1].update(source="\n".join(line for line in nb["cells"][1]["source"].splitlines() if not line.startswith("### "))), lang)
    result = run(root)
    assert result.returncode == 1 and "sensitivity" in result.stdout and "own data" in result.stdout
    root = product(tmp_path / "question")
    change(root, lambda nb: nb["cells"][0].update(source="# Validate the artifacts\n\n**Question:** Run the pipeline end to end?"))
    assert "not a lesson" in run(root).stdout


@pytest.mark.parametrize("group", ["methods", "contracts", "stages", "packages"])
def test_adversarial_complete_tool_coverage(tmp_path: Path, group: str) -> None:
    root = product(tmp_path)
    path = root / "notebooks/coverage.json"
    cov = json.loads(path.read_text())
    cov[group] = {}
    write_json(path, cov)
    assert f"{group} does not map" in run(root).stdout


@pytest.mark.parametrize("bad", [None, [], "01-topic/01-lesson.ipynb", [None], [1], ["../en/01-topic/01-lesson.ipynb"], ["/tmp/x.ipynb"], ["C:/x.ipynb"], ["01-topic/no.txt"], [REL, REL]])
def test_adversarial_malformed_and_escaping_coverage_fails_closed(tmp_path: Path, bad) -> None:
    root = product(tmp_path)
    path = root / "notebooks/coverage.json"
    cov = json.loads(path.read_text())
    cov["contracts"]["trace"] = bad
    write_json(path, cov)
    result = run(root)
    assert result.returncode == 1 and "coverage.json" in result.stdout and "Traceback" not in result.stderr


@pytest.mark.parametrize("path", ["product.json", "docs/design/SDD.md", "docs/contracts/catalog.md"])
def test_adversarial_inventory_admission(tmp_path: Path, path: str) -> None:
    root = product(tmp_path)
    (root / path).unlink()
    result = run(root)
    assert result.returncode == 1 and path in result.stdout


def test_cli_and_ci_are_static(tmp_path: Path) -> None:
    root = product(tmp_path)
    result = run(root, "--report")
    assert result.returncode == 0 and "prose" in result.stdout
    assert "python scripts/check_notebook_depth.py" in (ROOT / ".github/workflows/ci.yml").read_text()


def test_adversarial_static_cli_refuses_bad_notebook_without_execution(tmp_path: Path) -> None:
    root = product(tmp_path)
    canary = tmp_path / "must-not-execute.txt"
    stage = root / "data-pipeline/pipeline/stages/evaluate.py"
    stage.write_text(f"from pathlib import Path\nPath({str(canary)!r}).touch()\n", encoding="utf-8")
    change(root, lambda nb: nb["cells"].append({"cell_type": "code", "metadata": {}, "source": "raise RuntimeError('must not execute')", "execution_count": None, "outputs": []}))
    result = subprocess.run([sys.executable, "-I", "-S", str(SCRIPT), str(root)], capture_output=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not canary.exists()
    change(root, lambda nb: nb["cells"][1].update(source="## Method\nShort prose."))
    result = run(root)
    assert result.returncode == 1 and "prose" in result.stdout
    assert not canary.exists()


def test_adversarial_committed_curriculum_mutation_fails(tmp_path: Path) -> None:
    root = tmp_path / "copy"
    for name in ("notebooks", "data-pipeline/pipeline"):
        shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("product.json", "docs/design/SDD.md", "docs/contracts/catalog.md"):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    assert run(root).returncode == 0
    path = sorted((root / "notebooks/es").rglob("*.ipynb"))[0]
    nb = json.loads(path.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            cell["outputs"] = []
    write_json(path, nb)
    result = run(root)
    assert result.returncode == 1 and "notebooks/es/" in result.stdout and "figures 0" in result.stdout


def test_committed_curriculum_meets_current_depth() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("opening,closing", [("<div hidden>", "</div>"), ("<div style='display:none'>", "</div>"),
                                               ("<span style='visibility:hidden'>", "</span>"), ("<!--", ""),
                                               ("<template>", "</template>"), ("<script>", "</script>"),
                                               ("<pre>", "</pre>"), ("<code>", "</code>")])
def test_adversarial_hidden_dom_and_unclosed_comments_earn_nothing(tmp_path: Path, opening: str, closing: str) -> None:
    root = product(tmp_path)
    def hide(nb):
        nb["cells"][1]["source"] = opening + nb["cells"][1]["source"] + closing
        nb["cells"][-1]["source"] = opening + nb["cells"][-1]["source"] + closing
    change(root, hide)
    result = run(root)
    assert result.returncode == 1
    assert "equations 0" in result.stdout and "sources 0" in result.stdout, result.stdout
    import re
    assert int(re.search(r"prose (\d+)", result.stdout)[1]) < 150, result.stdout
    assert "sensitivity" in result.stdout and "own data" in result.stdout


@pytest.mark.parametrize("source", ["fenced-methods", "hidden-catalog", "malformed-method-row", "mismatched-env"])
def test_adversarial_unrendered_inventories_and_equations_fail(tmp_path: Path, source: str) -> None:
    root = product(tmp_path)
    sdd, catalog = root / "docs/design/SDD.md", root / "docs/contracts/catalog.md"
    if source == "fenced-methods":
        sdd.write_text("```md\n" + sdd.read_text() + "```\n", encoding="utf-8")
    elif source == "hidden-catalog":
        catalog.write_text("<!--\n" + catalog.read_text() + "-->\n", encoding="utf-8")
    elif source == "malformed-method-row":
        sdd.write_text(sdd.read_text().replace("| M-1 | classical | Real method |", "| M-1 |"), encoding="utf-8")
    else:
        change(root, lambda nb: nb["cells"][1].update(source=nb["cells"][1]["source"].replace("$$b=c$$", "\\begin{equation*}b=c\\end{equation}")))
    result = run(root)
    assert result.returncode == 1, result.stdout
    assert "inventory" in result.stdout or "equations 1" in result.stdout


@pytest.mark.parametrize("source", ["# Run the pipeline end to end\n\n**Question:** How does a price move the solution?",
                                      "# Prices and decisions\n\n**Question:** **Run** the whole pipeline?"])
def test_adversarial_visible_heading_and_formatted_question_are_checked(tmp_path: Path, source: str) -> None:
    root = product(tmp_path)
    change(root, lambda nb: nb["cells"][0].update(source=source))
    result = run(root)
    assert result.returncode == 1 and "not a lesson" in result.stdout


@pytest.mark.parametrize("kind", ["latex-angle", "escaped-angle", "opacity-half", "escaped-pipe", "inline-code-cell", "autolink", "css-visible-last"])
def test_legitimate_visible_math_html_and_table_content_pass(tmp_path: Path, kind: str) -> None:
    root = product(tmp_path)
    if kind == "latex-angle":
        change(root, lambda nb: nb["cells"][1].update(source=nb["cells"][1]["source"].replace(
            "$$a=b$$", "\\begin{equation}x<y\\end{equation}").replace("$$b=c$$", "\\[x<z\\]")))
    elif kind == "escaped-angle":
        change(root, lambda nb: nb["cells"][1].update(source="Literal &lt;code&gt; token. Following words remain visible.\n\n" + nb["cells"][1]["source"]))
    elif kind == "opacity-half":
        change(root, lambda nb: nb["cells"][1].update(source="<div style='opacity:0.5'>" + nb["cells"][1]["source"] + "</div>"))
    elif kind == "escaped-pipe":
        path = root / "docs/design/SDD.md"
        path.write_text(path.read_text().replace("Real method", r"Method x \| y"), encoding="utf-8")
    elif kind == "autolink":
        change(root, lambda nb: nb["cells"][-1].update(source="## References\n" + "\n".join(
            f"<https://doi.org/10.1000/source{i}>" for i in range(4))))
    elif kind == "css-visible-last":
        change(root, lambda nb: nb["cells"][1].update(source="<div style='display:none; display:block'>" + nb["cells"][1]["source"] + "</div>"))
    else:
        path = root / "docs/design/SDD.md"
        path.write_text(path.read_text().replace("M-1", "`M-1`").replace("Real method", "`pipeline.model.run`"), encoding="utf-8")
    result = run(root)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("kind", ["missing-separator", "duplicate-id"])
def test_adversarial_authoritative_table_integrity(tmp_path: Path, kind: str) -> None:
    root = product(tmp_path)
    path = root / "docs/design/SDD.md"
    source = path.read_text()
    if kind == "missing-separator":
        source = source.replace("|---|---|---|\n", "")
    else:
        source += "| M-1 | classical | Different method hidden by duplicate ID |\n"
    path.write_text(source, encoding="utf-8")
    result = run(root)
    assert result.returncode == 1 and "inventory" in result.stdout
