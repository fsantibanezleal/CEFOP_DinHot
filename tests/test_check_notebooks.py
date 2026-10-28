"""The notebooks gate (scripts/check_notebooks.py) and the runner (scripts/run_notebooks.py): one plant per rule, built in a
temporary repository, plus a control (the clean repository passes) and the committed example set.

The plants are the failure each rule exists for. The static check is standard library only, so these tests run wherever
pytest does; the three runner tests that execute a notebook need ``.venv-notebooks`` (``scripts/setup.sh --notebooks``) and
skip without it."""

from __future__ import annotations

import base64
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PYTHON = next((p for p in (ROOT / ".venv-notebooks" / "Scripts" / "python.exe", ROOT / ".venv-notebooks" / "bin" / "python") if p.is_file()), None)


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = load("check_notebooks")
RUNNER = load("run_notebooks")


HEADINGS = {
    "en": ["Objectives", "Setup", "Data", "Method", "State of the art", "Beyond the state of the art", "Results", "Summary", "References"],
    "es": ["Objetivos", "Preparación", "Datos", "Método", "Estado del arte", "Más allá del estado del arte", "Resultados", "Resumen", "Referencias"],
}
LOW = [1, 1, 1, 1, 3, 4, 1, 1, 1]
NO_L3 = {"en": "No level 3:", "es": "Sin nivel 3:"}
PIN = "numpy==2.4.6"
DATA = "data/derived/x.json"
SOURCE = "https://doi.org/10.1098/rspa.1927.0118"


def write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def make_notebook(lang: str, topic: str, level: int, beyond: tuple[str, ...] = ()) -> dict:
    cells: list[dict] = []
    count = [0]

    def md(text: str) -> None:
        cells.append({"cell_type": "markdown", "id": f"c{len(cells):02d}", "metadata": {}, "source": text})

    def code(text: str) -> None:
        count[0] += 1
        cells.append({"cell_type": "code", "id": f"c{len(cells):02d}", "metadata": {}, "source": text,
                      "execution_count": count[0], "outputs": [{"output_type": "stream", "name": "stdout", "text": "ok\n"}]})

    md(f"# Title\n\n- Level: {level}\n- Prerequisites: none\n- Reading time: 10 minutes")
    for heading, low in zip(HEADINGS[lang], LOW):
        if level < low or (low == 4 and level != 4):
            continue
        if heading in ("Setup", "Preparación"):
            md(f"## {heading}\n\nWhat the next cell does, and why. Install with `pip install {PIN}`.")
        elif heading in ("References", "Referencias"):
            md(f"## {heading}\n\n- Doe and Roe (1927). {SOURCE}")
        else:
            md(f"## {heading}\n\nText.")
        if heading in ("Setup", "Preparación", "Method", "Método"):
            versions = "# print the version of a package\nimport importlib.metadata as md\nprint(md.version('numpy'))"
            code(versions if heading in ("Setup", "Preparación") else "# print a number\nprint(1)")
    return {"cells": cells, "nbformat": 4, "nbformat_minor": 5, "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"},
        "caos": {"language": lang, "topic": topic, "level": level, "title": f"{topic} {level}", "packages": [PIN], "data": [DATA],
                 "sources": [SOURCE], "beyond": list(beyond)}}}


TOPICS = {"01-basics": [1, 2], "02-advanced": [1, 2, 3]}


def make_repo(root: Path, claims: tuple[str, ...] = (), level4: tuple[str, ...] = ()) -> Path:
    """A small valid repository: two topics (the first has no level 3 and says why), the SDD section, the CI steps and the data."""
    (root / "notebooks").mkdir(parents=True)
    (root / "notebooks" / "README.md").write_text("# Notebooks\n", encoding="utf-8")
    (root / "notebooks" / "requirements.txt").write_text(f"# pins\n{PIN}\n", encoding="utf-8")
    (root / "data" / "derived").mkdir(parents=True)
    (root / DATA).write_text("{}", encoding="utf-8")
    (root / "docs" / "design").mkdir(parents=True)
    section = "\n".join(f"- {c}: evidence, source" for c in claims) if claims else "None claimed."
    (root / "docs" / "design" / "SDD.md").write_text(f"# SDD\n\n## Research basis\n\nDoe and Roe 1927, https://doi.org/10.1098/rspa.1927.0118\n\n## Oracles\n\ntext\n\n## Beyond the state of the art\n\n{section}\n\n## Deploy driver\n\ntext\n", encoding="utf-8")
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "ci.yml").write_text(
        "steps:\n  - run: python scripts/check_notebooks.py\n  - run: python scripts/check_readme_areas.py\n", encoding="utf-8")
    for lang in ("en", "es"):
        index = [f"# index {lang}", "", "| Topic | Level 3 |", "|---|---|"]
        for topic, levels in TOPICS.items():
            index.append(f"| {topic} | " + (NO_L3[lang] + " the topic has no state of the art to compare" if 3 not in levels else "yes") + " |")
        for topic, levels in TOPICS.items():
            for n, level in enumerate(levels, 1):
                name = f"{n:02d}-note.ipynb"
                index.append(f"- {topic}/{name}")
                write_json(root / "notebooks" / lang / topic / name, make_notebook(lang, topic, level))
        if level4:
            write_json(root / "notebooks" / lang / "02-advanced" / "04-beyond.ipynb", make_notebook(lang, "02-advanced", 4, level4))
            index.append("- 02-advanced/04-beyond.ipynb")
        (root / "notebooks" / lang / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return root


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return make_repo(tmp_path / "repo")


def edit(root: Path, lang: str, rel: str, change) -> None:
    path = root / "notebooks" / lang / rel
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    write_json(path, doc)


def found(root: Path, *needles: str) -> bool:
    """True when one finding holds every needle (a file and the rule or its words)."""
    return any(all(n in f for n in needles) for f in CHECK.form_findings(root))


def test_a_clean_repository_passes(repo: Path) -> None:
    assert CHECK.form_findings(repo) == []


def test_missing_layout_files_are_found(repo: Path) -> None:
    for rel in ("README.md", "requirements.txt", "en/README.md", "es/README.md"):
        saved = (repo / "notebooks" / rel).read_bytes()
        (repo / "notebooks" / rel).unlink()
        assert found(repo, f"notebooks/{rel}", "layout"), rel
        (repo / "notebooks" / rel).write_bytes(saved)
    (repo / "notebooks" / "en" / "01-basics" / "notes.txt").write_text("x", encoding="utf-8")
    assert found(repo, "notes.txt", "only notebooks live in a topic folder")


def test_a_path_missing_from_one_tree_is_found(repo: Path) -> None:
    (repo / "notebooks" / "es" / "02-advanced" / "03-note.ipynb").unlink()
    assert found(repo, "notebooks/es/02-advanced/03-note.ipynb", "mirror")
    (repo / "notebooks" / "en" / "01-basics" / "01-note.ipynb").unlink()
    assert found(repo, "notebooks/en/01-basics/01-note.ipynb", "mirror")


def test_numbering_gap_is_found(repo: Path) -> None:
    for lang in ("en", "es"):
        (repo / "notebooks" / lang / "02-advanced" / "03-note.ipynb").rename(repo / "notebooks" / lang / "02-advanced" / "05-note.ipynb")
    assert found(repo, "02-advanced", "numbering", "no gap or repeat")
    (repo / "notebooks" / "en" / "01-basics").rename(repo / "notebooks" / "en" / "1-basics")
    assert found(repo, "numbering", "'1-basics' is not NN-slug")


def test_a_decreasing_level_is_found(repo: Path) -> None:
    for lang in ("en", "es"):
        edit(repo, lang, "02-advanced/03-note.ipynb", lambda d: d["metadata"]["caos"].update(level=1))
    assert found(repo, "notebooks/en/02-advanced", "levels", "decreases")


def test_a_topic_without_level_two_is_found(repo: Path) -> None:
    edit(repo, "en", "01-basics/02-note.ipynb", lambda d: d["metadata"]["caos"].update(level=1))
    assert found(repo, "notebooks/en/01-basics", "no level 2 notebook")


def test_a_topic_without_level_three_needs_a_reason(repo: Path) -> None:
    index = repo / "notebooks" / "en" / "README.md"
    index.write_text(index.read_text(encoding="utf-8").replace(" the topic has no state of the art to compare", ""), encoding="utf-8")
    assert found(repo, "notebooks/en/README.md", "01-basics", "no level 3", "reason")
    index = repo / "notebooks" / "es" / "README.md"
    index.write_text(index.read_text(encoding="utf-8").replace("Sin nivel 3:", "Sin nivel tres:"), encoding="utf-8")
    assert found(repo, "notebooks/es/README.md", "01-basics", "no level 3")


def test_an_unlisted_notebook_is_found(repo: Path) -> None:
    index = repo / "notebooks" / "es" / "README.md"
    index.write_text(index.read_text(encoding="utf-8").replace("- 02-advanced/03-note.ipynb\n", ""), encoding="utf-8")
    assert found(repo, "notebooks/es/README.md", "03-note.ipynb", "is not listed")


def test_an_uncovered_claim_is_found(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "a", claims=("BS-1", "BS-2"), level4=("BS-1",))
    assert found(root, "notebooks/en", "BS-2", "covered by no level 4 notebook")
    assert found(root, "notebooks/es", "BS-2", "covered by no level 4 notebook")
    assert not found(root, "BS-1", "covered by no level 4")
    unknown = make_repo(tmp_path / "b", claims=("BS-1",), level4=("BS-1", "BS-9"))
    assert found(unknown, "BS-9", "is not a claim of the SDD")
    sdd = unknown / "docs" / "design" / "SDD.md"
    sdd.write_text(sdd.read_text(encoding="utf-8").replace("## Beyond the state of the art", "## Something else"), encoding="utf-8")
    assert found(unknown, "docs/design/SDD.md", "no section")


def test_a_missing_and_a_misordered_section_are_found(repo: Path) -> None:
    def drop_results(doc: dict) -> None:
        doc["cells"] = [c for c in doc["cells"] if not c["source"].startswith("## Results")]
    edit(repo, "en", "01-basics/01-note.ipynb", drop_results)
    assert found(repo, "01-basics/01-note.ipynb", "anatomy", "'## Results' is missing")

    def swap(doc: dict) -> None:
        a = next(i for i, c in enumerate(doc["cells"]) if c["source"].startswith("## Data"))
        b = next(i for i, c in enumerate(doc["cells"]) if c["source"].startswith("## Summary"))
        doc["cells"][a], doc["cells"][b] = doc["cells"][b], doc["cells"][a]
    edit(repo, "en", "01-basics/02-note.ipynb", swap)
    assert found(repo, "01-basics/02-note.ipynb", "sections out of order")
    # a Spanish heading in the English tree is not a section of the anatomy
    edit(repo, "en", "02-advanced/01-note.ipynb", lambda d: d["cells"][1].update(source="## Objetivos\n\nText."))
    assert found(repo, "02-advanced/01-note.ipynb", "'## Objetivos' is not a section of the anatomy")


def test_a_first_cell_that_is_code_is_found(repo: Path) -> None:
    def first_code(doc: dict) -> None:
        doc["cells"][0] = {"cell_type": "code", "id": "c00", "metadata": {}, "source": "# x\n1", "execution_count": 1, "outputs": []}
        for n, c in enumerate((c for c in doc["cells"] if c["cell_type"] == "code"), 1):
            c["execution_count"] = n
    edit(repo, "en", "01-basics/01-note.ipynb", first_code)
    assert found(repo, "01-basics/01-note.ipynb", "the first cell is not a markdown cell")


def test_a_code_cell_without_comment_or_explanation_is_found(repo: Path) -> None:
    def uncomment(doc: dict) -> None:
        next(c for c in doc["cells"] if c["cell_type"] == "code")["source"] = "print(1)  \nx = '# not a comment'"
    edit(repo, "en", "01-basics/01-note.ipynb", uncomment)
    assert found(repo, "01-basics/01-note.ipynb", "carries no comment line")

    def adjacent(doc: dict) -> None:
        i = next(i for i, c in enumerate(doc["cells"]) if c["cell_type"] == "code")
        doc["cells"].insert(i + 1, {"cell_type": "code", "id": "cx", "metadata": {}, "source": "# two in a row\n1", "execution_count": 2, "outputs": []})
        for n, c in enumerate((c for c in doc["cells"] if c["cell_type"] == "code"), 1):
            c["execution_count"] = n
    edit(repo, "es", "01-basics/02-note.ipynb", adjacent)
    assert found(repo, "es/01-basics/02-note.ipynb", "is not preceded by a markdown cell")


def test_the_caos_block_must_agree_with_the_repository(repo: Path) -> None:
    edit(repo, "en", "01-basics/01-note.ipynb", lambda d: d["metadata"]["caos"].update(language="es"))
    assert found(repo, "en/01-basics/01-note.ipynb", "caos.language is 'es'")
    edit(repo, "en", "01-basics/02-note.ipynb", lambda d: d["metadata"]["caos"].update(topic="02-advanced"))
    assert found(repo, "en/01-basics/02-note.ipynb", "caos.topic is '02-advanced'")
    edit(repo, "en", "02-advanced/01-note.ipynb", lambda d: d["metadata"]["caos"].update(packages=["numpy==9.9.9"]))
    assert found(repo, "02-advanced/01-note.ipynb", "numpy==9.9.9", "is not a pin of notebooks/requirements.txt")
    edit(repo, "en", "02-advanced/02-note.ipynb", lambda d: d["metadata"]["caos"].update(data=["data/derived/absent.json"]))
    assert found(repo, "02-advanced/02-note.ipynb", "data path 'data/derived/absent.json'")
    edit(repo, "en", "02-advanced/03-note.ipynb", lambda d: d["metadata"].pop("caos"))
    assert found(repo, "02-advanced/03-note.ipynb", "the caos block is missing")
    # a pin of the requirements file that the text never writes
    edit(repo, "es", "01-basics/01-note.ipynb", lambda d: d["cells"].__setitem__(2, {**d["cells"][2], "source": "## Preparación\n\nInstale."}))
    assert found(repo, "es/01-basics/01-note.ipynb", "is not written in the notebook's text")


def test_extra_metadata_is_found(repo: Path) -> None:
    edit(repo, "en", "01-basics/01-note.ipynb", lambda d: d["metadata"].update(widgets={"state": {}}))
    assert found(repo, "01-basics/01-note.ipynb", "notebook metadata beyond kernelspec, language_info and caos")
    edit(repo, "en", "01-basics/02-note.ipynb", lambda d: d["cells"][1]["metadata"].update(collapsed=True))
    assert found(repo, "01-basics/02-note.ipynb", "cell 2 metadata beyond tags")
    edit(repo, "en", "02-advanced/01-note.ipynb", lambda d: d["cells"][1]["metadata"].update(tags=["note"]))
    assert not found(repo, "02-advanced/01-note.ipynb", "metadata beyond")


def test_execution_counts_must_run_in_order(repo: Path) -> None:
    def skip(doc: dict) -> None:
        next(c for c in doc["cells"] if c["cell_type"] == "code")["execution_count"] = 3
    edit(repo, "en", "01-basics/01-note.ipynb", skip)
    assert found(repo, "01-basics/01-note.ipynb", "execution", "expected 1")
    edit(repo, "en", "01-basics/02-note.ipynb", lambda d: next(c for c in d["cells"] if c["cell_type"] == "code").update(execution_count=None))
    assert found(repo, "01-basics/02-note.ipynb", "execution_count None")


def test_an_error_output_and_a_stderr_stream_are_found(repo: Path) -> None:
    def err(doc: dict) -> None:
        next(c for c in doc["cells"] if c["cell_type"] == "code")["outputs"] = [
            {"output_type": "error", "ename": "ValueError", "evalue": "x", "traceback": ["boom"]}]
    edit(repo, "en", "01-basics/01-note.ipynb", err)
    assert found(repo, "01-basics/01-note.ipynb", "an error output (ValueError)")

    def stderr(doc: dict) -> None:
        next(c for c in doc["cells"] if c["cell_type"] == "code")["outputs"] = [{"output_type": "stream", "name": "stderr", "text": "warn\n"}]
    edit(repo, "es", "01-basics/02-note.ipynb", stderr)
    assert found(repo, "es/01-basics/02-note.ipynb", "a stderr stream")


@pytest.mark.parametrize("text", ["C:\\Users\\someone\\data.csv", "D:" + "/_Repos/x", "/home/someone/x", "/Users/someone/x", "\\Users\\x",
                                  "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4", "-----BEGIN RSA PRIVATE KEY-----", "api_key = 'abcdef123456'"])
def test_a_machine_path_and_a_token_are_found(repo: Path, text: str) -> None:
    edit(repo, "en", "01-basics/01-note.ipynb", lambda d: d["cells"][1].update(source=d["cells"][1]["source"] + f"\n\n{text}"))
    kind = "secret" if any(t in text for t in ("ghp_", "KEY", "api_key")) else "path"
    assert found(repo, "01-basics/01-note.ipynb", f": {kind}:")

    # the same text in an output is found too
    def out(doc: dict) -> None:
        next(c for c in doc["cells"] if c["cell_type"] == "code")["outputs"] = [{"output_type": "stream", "name": "stdout", "text": text + "\n"}]
    edit(repo, "en", "01-basics/02-note.ipynb", out)
    assert found(repo, "01-basics/02-note.ipynb", f": {kind}:")


def test_urls_and_plain_prose_are_not_machine_paths(repo: Path) -> None:
    edit(repo, "en", "01-basics/01-note.ipynb", lambda d: d["cells"][1].update(source="## Objectives\n\nSee https://doi.org/10.1/x and the note: /relative/path, e.g. a:b."))
    assert CHECK.form_findings(repo) == []


def test_oversize_notebook_and_image_are_found(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    png = base64.b64encode(b"\x00" * (CHECK.MAX_IMAGE_BYTES + 100)).decode()

    def image(doc: dict) -> None:
        next(c for c in doc["cells"] if c["cell_type"] == "code")["outputs"] = [
            {"output_type": "display_data", "data": {"image/png": png}, "metadata": {}}]
    edit(repo, "en", "01-basics/01-note.ipynb", image)
    assert found(repo, "01-basics/01-note.ipynb", "an image (image/png)", "limit")
    monkeypatch.setattr(CHECK, "MAX_NOTEBOOK_BYTES", 500)
    assert found(repo, "02-advanced/01-note.ipynb", "size", "byte limit of a notebook")


def test_a_spanish_notebook_that_is_not_a_counterpart_is_found(repo: Path) -> None:
    def drop(doc: dict) -> None:
        doc["cells"] = [c for c in doc["cells"] if c["cell_type"] != "code"][:]
    edit(repo, "es", "01-basics/01-note.ipynb", drop)
    assert found(repo, "es/01-basics/01-note.ipynb", "mirror", "not a full counterpart")
    edit(repo, "es", "01-basics/02-note.ipynb", lambda d: d["metadata"]["caos"].update(data=[]))
    assert found(repo, "es/01-basics/02-note.ipynb", "mirror", "caos.data differs")


def test_a_source_the_sdd_does_not_list_is_found(repo: Path) -> None:
    edit(repo, "en", "01-basics/01-note.ipynb", lambda d: d["metadata"]["caos"].update(sources=["https://doi.org/10.1000/not-in-the-sdd"]))
    assert found(repo, "en/01-basics/01-note.ipynb", "is not a source the SDD lists")
    # a DOI written in another form is the same source
    sdd = repo / "docs" / "design" / "SDD.md"
    sdd.write_text(sdd.read_text(encoding="utf-8") + "\nAlso doi:10.1000/NOT-IN-THE-SDD.\n", encoding="utf-8")
    assert not found(repo, "en/01-basics/01-note.ipynb", "is not a source the SDD lists")
    edit(repo, "en", "01-basics/02-note.ipynb", lambda d: d["metadata"]["caos"].update(sources=[]))
    assert found(repo, "en/01-basics/02-note.ipynb", "caos.sources is not a non-empty list")


def test_a_notebook_that_redefines_the_engine_is_found(repo: Path) -> None:
    model = repo / "data-pipeline" / "pipeline" / "model"
    model.mkdir(parents=True)
    (model / "sir.py").write_text("def simulate(p):\n    return p\n\n\ndef _private():\n    pass\n", encoding="utf-8")

    def copy(doc: dict) -> None:
        next(c for c in doc["cells"] if c["cell_type"] == "code")["source"] = "# a copy of the engine\ndef simulate(p):\n    return p"
    edit(repo, "en", "01-basics/01-note.ipynb", copy)
    assert found(repo, "01-basics/01-note.ipynb", "defines 'simulate'", "import it instead")
    # a helper of the notebook's own and an import are fine
    edit(repo, "en", "01-basics/02-note.ipynb", lambda d: next(c for c in d["cells"] if c["cell_type"] == "code").update(
        source="# a reader of the artifacts\nfrom pipeline.model.sir import simulate\n\n\ndef read_artifact(x):\n    return x"))
    assert not found(repo, "01-basics/02-note.ipynb", "engine")


def test_ci_must_run_the_static_checks_and_never_the_notebooks(repo: Path) -> None:
    ci = repo / ".github" / "workflows" / "ci.yml"
    ci.write_text("steps:\n  - run: python scripts/check_notebooks.py\n", encoding="utf-8")
    assert found(repo, "ci.yml", "check_readme_areas.py")
    ci.write_text("steps:\n  - run: python scripts/check_readme_areas.py\n", encoding="utf-8")
    assert found(repo, "ci.yml", "check_notebooks.py")
    ci.unlink()
    assert found(repo, "ci.yml", "the workflow is missing")
    ci.write_text("steps:\n  - run: python scripts/check_notebooks.py\n  - run: python scripts/check_readme_areas.py\n", encoding="utf-8")
    (repo / ".github" / "workflows" / "nightly.yml").write_text("steps:\n  - run: python scripts/run_notebooks.py\n", encoding="utf-8")
    assert found(repo, "nightly.yml", "runs the notebooks", "local release gate")


def test_notebook_pins_are_exact_and_in_the_sdd_table(tmp_path: Path) -> None:
    """notebooks/requirements.txt is read by the technology-matrix guard: an unpinned line, or a pin the SDD does not hold, fails."""
    sandbox = tmp_path / "t"
    for rel in ("scripts/check_tech_matrix.py", "docs/design/SDD.md", "requirements-precompute.txt", "requirements-dev.txt", "data-pipeline/requirements.txt",
                "notebooks/requirements.txt", "frontend/package.json", "frontend/package-lock.json", "requirements-gpu.txt", "requirements-api.txt", "pyproject.toml"):
        if (ROOT / rel).is_file():
            (sandbox / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, sandbox / rel)

    def tech() -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(sandbox / "scripts" / "check_tech_matrix.py"), str(sandbox)], capture_output=True, text=True, cwd=sandbox)
    assert tech().returncode == 0, tech().stdout
    req = sandbox / "notebooks" / "requirements.txt"
    saved = req.read_text(encoding="utf-8")
    req.write_text(saved + "nbclient>=0.1\n", encoding="utf-8")
    assert tech().returncode == 1 and "nbclient" in tech().stdout
    req.write_text(saved.replace("matplotlib==3.11.2", "matplotlib==3.11.1"), encoding="utf-8")
    assert tech().returncode == 1 and "matplotlib" in tech().stdout
    req.write_text(saved, encoding="utf-8")
    assert CHECK.unpinned_lines(sandbox) == []
    req.write_text(saved + "nbclient>=0.1\n", encoding="utf-8")
    assert CHECK.unpinned_lines(sandbox) == ["nbclient>=0.1"]


def test_the_runner_strips_volatile_metadata() -> None:
    nb = {"cells": [{"cell_type": "code", "id": "a", "source": "1", "execution_count": 1, "outputs": [], "metadata": {
        "execution": {"iopub.execute_input": "2026-10-20T10:00:00"}, "tags": ["keep"], "collapsed": True}},
        {"cell_type": "markdown", "id": "b", "source": "x", "metadata": {"scrolled": True}}],
        "metadata": {"kernelspec": {"display_name": "Python 3.13.1 (venv)", "language": "python", "name": "python3"},
                     "language_info": {"name": "python", "version": "3.13.1", "file_extension": ".py"}, "caos": {"level": 1},
                     "widgets": {"state": {}}, "papermill": {"duration": 1.0}},
        "nbformat": 4, "nbformat_minor": 5}
    clean = RUNNER.strip_volatile(nb)
    assert clean["metadata"] == {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                 "language_info": {"name": "python"}, "caos": {"level": 1}}
    assert clean["cells"][0]["metadata"] == {"tags": ["keep"]} and clean["cells"][1]["metadata"] == {}
    assert nb["metadata"]["widgets"] == {"state": {}}  # the input is not mutated


def runner_repo(tmp_path: Path, body: str) -> tuple[Path, Path]:
    """A temporary repository holding the runner and one notebook whose code cell is ``body``."""
    base = make_repo(tmp_path / "r")
    (base / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts" / "run_notebooks.py", base / "scripts" / "run_notebooks.py")
    (base / "VERSION").write_text("0.0.0\n", encoding="utf-8")
    path = base / "notebooks" / "en" / "01-basics" / "01-note.ipynb"
    doc = json.loads(path.read_text(encoding="utf-8"))
    code = next(c for c in doc["cells"] if c["cell_type"] == "code")
    code["source"], code["outputs"], code["execution_count"] = body, [], None
    write_json(path, doc)
    return base, path


def run_runner(base: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(NOTEBOOK_PYTHON), str(base / "scripts" / "run_notebooks.py"), *args], capture_output=True, encoding="utf-8",
                          errors="replace", cwd=base, timeout=300)


needs_env = pytest.mark.skipif(NOTEBOOK_PYTHON is None, reason="the notebook environment is not built (scripts/setup.sh --notebooks)")


@needs_env
def test_the_runner_executes_in_place_and_check_writes_nothing(tmp_path: Path) -> None:
    base, path = runner_repo(tmp_path, "# a first cell\nprint(6 * 7)")
    before = path.read_bytes()
    checked = run_runner(base, "--check", "--only", "notebooks/en/01-basics/01-note.ipynb")
    assert checked.returncode == 1 and "stale" in checked.stdout, "a notebook never run has no fresh outputs: " + checked.stdout
    assert path.read_bytes() == before, "--check must write nothing"
    ran = run_runner(base, "--only", "notebooks/en/01-basics/01-note.ipynb")
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert path.read_bytes() != before
    doc = json.loads(path.read_text(encoding="utf-8"))
    code = [c for c in doc["cells"] if c["cell_type"] == "code"]
    assert [c["execution_count"] for c in code] == list(range(1, len(code) + 1))
    assert "".join(code[0]["outputs"][0]["text"]) == "42\n"
    assert doc["metadata"]["language_info"] == {"name": "python"} and all(set(c["metadata"]) <= {"tags"} for c in doc["cells"])
    assert run_runner(base, "--check", "--only", "notebooks/en/01-basics/01-note.ipynb").returncode == 0


@needs_env
def test_the_runner_fails_a_raising_notebook_naming_it(tmp_path: Path) -> None:
    base, path = runner_repo(tmp_path, "# this cell raises\nraise RuntimeError('boom')")
    before = path.read_bytes()
    r = run_runner(base, "--check", "--only", "notebooks/en/01-basics/01-note.ipynb")
    assert r.returncode == 1 and "FAIL" in r.stdout and "01-note.ipynb" in r.stdout and "RuntimeError" in r.stdout, r.stdout
    r = run_runner(base, "--only", "notebooks/en/01-basics/01-note.ipynb")
    assert r.returncode == 1 and path.read_bytes() == before, "a failed run must not rewrite the notebook"


@needs_env
def test_the_runner_fails_a_missing_artifact_naming_its_path(tmp_path: Path) -> None:
    base, _ = runner_repo(tmp_path, "# read an artifact that is not there\nfrom pathlib import Path\nPath('../../../data/derived/absent-artifact.json').read_text()")
    r = run_runner(base, "--check", "--only", "notebooks/en/01-basics/01-note.ipynb")
    assert r.returncode == 1 and "absent-artifact.json" in r.stdout, r.stdout


def test_the_committed_set_passes_the_static_check() -> None:
    assert CHECK.findings_of(ROOT) == []


GIT_URL = "git+https://github.com/fsantibanezleal/CAOS_RiskValidation.git@v0.8.0"
GIT_LINE = f"riskvalidation @ {GIT_URL}"


TAG_SENTENCE = {"en": "not yet published on PyPI; installed from its release tag",
                "es": "todavía no publicado en PyPI; instalado desde su etiqueta de versión"}


def use_git_pin(repo: Path, *, sentence: bool = True, install: bool = True, entry: str = GIT_LINE, line: str = GIT_LINE) -> None:
    """F3: the product consumes a package of its own not yet on PyPI, installed from its release tag, in both trees."""
    req = repo / "notebooks" / "requirements.txt"
    req.write_text(req.read_text(encoding="utf-8") + line + "\n", encoding="utf-8")
    for lang in ("en", "es"):
        for topic, levels in TOPICS.items():
            for n in range(1, len(levels) + 1):
                def change(doc: dict, lang: str = lang) -> None:
                    doc["metadata"]["caos"]["packages"] = [PIN, entry]
                    setup = next(c for c in doc["cells"] if c["source"].startswith(("## Setup", "## Preparación")))
                    if install:
                        setup["source"] += f'\n\n```\npip install "{GIT_URL}"\n```'
                    if sentence:
                        setup["source"] += f"\n\n{TAG_SENTENCE[lang]}."
                edit(repo, lang, f"{topic}/{n:02d}-note.ipynb", change)


def test_a_package_installed_from_its_release_tag_passes_in_its_exact_form(repo: Path) -> None:
    use_git_pin(repo)
    assert CHECK.form_findings(repo) == []


def test_a_release_tag_package_needs_its_sentence(repo: Path) -> None:
    use_git_pin(repo, sentence=False)
    assert found(repo, "riskvalidation @ git+", "not yet published on PyPI; installed from its release tag")


def test_a_release_tag_package_needs_the_install_line(repo: Path) -> None:
    use_git_pin(repo, install=False)
    assert found(repo, "pip install", GIT_URL)


@pytest.mark.parametrize("line", [
    "riskvalidation @ https://example.org/riskvalidation-0.8.0.zip",
    "riskvalidation @ git+https://gitlab.com/o/riskvalidation.git@v0.8.0",
    "riskvalidation @ git+https://github.com/o/riskvalidation.git@main",
    "riskvalidation @ git+https://github.com/o/riskvalidation.git",
    "riskvalidation>=0.8.0",
    "riskvalidation==v0.8.0 extra",
])
def test_any_other_requirement_form_is_refused(repo: Path, line: str) -> None:
    req = repo / "notebooks" / "requirements.txt"
    req.write_text(req.read_text(encoding="utf-8") + line + "\n", encoding="utf-8")
    assert found(repo, "notebooks/requirements.txt", "pins", repr(line))


@pytest.mark.parametrize("entry", ["riskvalidation==v0.8.0", "riskvalidation @ git+https://github.com/fsantibanezleal/CAOS_RiskValidation.git@v0.9.0",
                                   "riskvalidation"])
def test_a_package_entry_that_is_not_an_exact_requirements_line_is_refused(repo: Path, entry: str) -> None:
    use_git_pin(repo, entry=entry)
    assert found(repo, "metadata", repr(entry))


@pytest.mark.parametrize("code", [
    "%pip install numpy==2.4.6", "!pip install numpy", "%conda install numpy", "!conda install numpy", "  %pip install numpy",
    "import subprocess, sys\nsubprocess.run([sys.executable, '-m', 'pip', 'install', 'numpy'])",
    "import os\nos.system('python -m pip install numpy')", "import os\nos.system(\"pip install numpy\")",
])
def test_a_notebook_never_runs_pip(repo: Path, code: str) -> None:
    edit(repo, "en", "01-basics/01-note.ipynb", lambda d: next(c for c in d["cells"] if c["cell_type"] == "code").update(source=f"# install\n{code}"))
    assert found(repo, "01-basics/01-note.ipynb", "anatomy", "a notebook never runs pip itself (convention section 4)")


def test_a_comment_that_names_pip_is_not_running_it(repo: Path) -> None:
    edit(repo, "en", "01-basics/01-note.ipynb", lambda d: next(c for c in d["cells"] if c["cell_type"] == "code").update(
        source="# pip install numpy is done in the Setup text, never here\nimport importlib.metadata\nprint(1)"))
    assert CHECK.form_findings(repo) == []


@pytest.mark.parametrize("text", ["p = 'D:\\\\_Datos\\\\sir'", "WindowsPath('D:\\\\_Temp\\\\x')", "c:\\\\Users\\\\someone", "E:/_Datos/sir",
                                  "/opt/runner/work/repo/x", "/tmp/x.json", "/root/.cache/x", "/var/log/x", "/srv/data/x"])
def test_a_drive_path_literal_and_the_posix_roots_are_found(repo: Path, text: str) -> None:
    edit(repo, "en", "01-basics/01-note.ipynb", lambda d: next(c for c in d["cells"] if c["cell_type"] == "code").update(source=f"# a path\n{text}"))
    assert found(repo, "01-basics/01-note.ipynb", ": path:")

    def out(doc: dict) -> None:
        next(c for c in doc["cells"] if c["cell_type"] == "code")["outputs"] = [{"output_type": "stream", "name": "stdout", "text": text + "\n"}]
    edit(repo, "en", "01-basics/02-note.ipynb", out)
    assert found(repo, "01-basics/02-note.ipynb", ": path:")


def test_prose_that_only_looks_like_a_path_is_not_one(repo: Path) -> None:
    text = "Ratio a:b, https://doi.org/10.1/x, https://example.org/opt/y, the path data/tmp/x, ../tmp/z, Note: and 5:1."
    edit(repo, "en", "01-basics/01-note.ipynb", lambda d: d["cells"][1].update(source=f"## Objectives\n\n{text}"))
    assert CHECK.form_findings(repo) == []


def test_a_traceback_printed_to_stdout_is_found(repo: Path) -> None:
    def tb(doc: dict) -> None:
        next(c for c in doc["cells"] if c["cell_type"] == "code")["outputs"] = [
            {"output_type": "stream", "name": "stdout", "text": "Traceback (most recent call last):\n  File \"x\", line 1\nKeyError: 'a'\n"}]
    edit(repo, "en", "01-basics/01-note.ipynb", tb)
    assert found(repo, "01-basics/01-note.ipynb", "output", "prints a traceback")


@pytest.mark.parametrize("rel", ["notebooks/en/00-loose.ipynb", "notebooks/00-loose.ipynb", "notebooks/en/01-basics/extra/01-deep.ipynb",
                                 "notebooks/fr/01-basics/01-note.ipynb"])
def test_a_notebook_outside_the_layout_is_found(repo: Path, rel: str) -> None:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo / "notebooks" / "en" / "01-basics" / "01-note.ipynb", target)
    assert found(repo, rel, "layout", "notebooks/<language>/<topic>/<notebook>.ipynb")


def test_the_install_line_and_the_references_are_enforced(repo: Path) -> None:
    def no_install(doc: dict) -> None:
        setup = next(c for c in doc["cells"] if c["source"].startswith("## Setup"))
        setup["source"] = f"## Setup\n\nThe pin is {PIN} but no command is shown."
    edit(repo, "en", "01-basics/01-note.ipynb", no_install)
    assert found(repo, "en/01-basics/01-note.ipynb", "anatomy", "pip install", PIN)

    def two_pins_one_line(doc: dict) -> None:
        setup = next(c for c in doc["cells"] if c["source"].startswith("## Preparación"))
        setup["source"] = f"## Preparación\n\n```\npip install matplotlib==3.11.2 \\\n  {PIN}\n```"
    edit(repo, "es", "01-basics/01-note.ipynb", two_pins_one_line)
    assert not found(repo, "es/01-basics/01-note.ipynb", "pip install")

    def no_reference(doc: dict) -> None:
        refs = next(c for c in doc["cells"] if c["source"].startswith("## References"))
        refs["source"] = "## References\n\n- Doe and Roe (1927), without a link."
    edit(repo, "en", "01-basics/02-note.ipynb", no_reference)
    assert found(repo, "en/01-basics/02-note.ipynb", "sources", "References", SOURCE)


def test_consecutive_streams_of_one_name_are_coalesced() -> None:
    nb = {"cells": [{"cell_type": "code", "id": "a", "source": "x", "execution_count": 1, "metadata": {}, "outputs": [
        {"output_type": "stream", "name": "stdout", "text": ["R0 = ", "beta / gamma ="]},
        {"output_type": "stream", "name": "stdout", "text": " 2.75\n"},
        {"output_type": "stream", "name": "stderr", "text": "warn\n"},
        {"output_type": "stream", "name": "stdout", "text": "after\n"},
        {"output_type": "display_data", "data": {"text/plain": "x"}, "metadata": {}},
        {"output_type": "stream", "name": "stdout", "text": "tail "},
        {"output_type": "stream", "name": "stdout", "text": "end\n"}]}], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
    outs = RUNNER.strip_volatile(nb)["cells"][0]["outputs"]
    assert [(o["output_type"], o.get("name")) for o in outs] == [("stream", "stdout"), ("stream", "stderr"), ("stream", "stdout"),
                                                                 ("display_data", None), ("stream", "stdout")]
    assert outs[0]["text"] == ["R0 = beta / gamma = 2.75\n"]
    assert "".join(outs[4]["text"]) == "tail end\n"
    assert len(nb["cells"][0]["outputs"]) == 7, "the input is not mutated"


@needs_env
def test_a_print_in_two_chunks_writes_one_stream_byte_identical_across_runs(tmp_path: Path) -> None:
    base, path = runner_repo(tmp_path, "# print in two chunks\nimport time\nprint('a', end='', flush=True)\ntime.sleep(0.3)\nprint('b')")
    args = ("--only", "notebooks/en/01-basics/01-note.ipynb")
    assert run_runner(base, *args).returncode == 0
    first = path.read_bytes()
    doc = json.loads(first.decode("utf-8"))
    outputs = next(c for c in doc["cells"] if c["cell_type"] == "code")["outputs"]
    assert len(outputs) == 1 and "".join(outputs[0]["text"]) == "ab\n", outputs
    assert run_runner(base, *args).returncode == 0
    assert path.read_bytes() == first


@needs_env
def test_check_fails_a_notebook_whose_committed_outputs_are_stale(tmp_path: Path) -> None:
    base, path = runner_repo(tmp_path, "# a first cell\nprint(6 * 7)")
    args = ("--only", "notebooks/en/01-basics/01-note.ipynb")
    assert run_runner(base, *args).returncode == 0
    assert run_runner(base, "--check", *args).returncode == 0, "a fresh in-place run passes the comparison"
    path.write_text(path.read_text(encoding="utf-8").replace('"42\\n"', '"43\\n"'), encoding="utf-8")
    stale = run_runner(base, "--check", *args)
    assert stale.returncode == 1 and "stale" in stale.stdout and "01-note.ipynb" in stale.stdout, stale.stdout


@needs_env
def test_the_runner_refuses_a_notebook_outside_the_layout_and_runs_none(tmp_path: Path) -> None:
    base, path = runner_repo(tmp_path, "# a first cell\nprint(6 * 7)")
    loose = base / "notebooks" / "en" / "00-loose.ipynb"
    shutil.copy2(path, loose)
    before = path.read_bytes()
    r = run_runner(base)
    assert r.returncode == 1 and "00-loose.ipynb" in r.stdout and "notebooks/<language>/<topic>/<notebook>.ipynb" in r.stdout, r.stdout
    assert path.read_bytes() == before, "nothing ran, nothing was written"


def test_a_notebook_that_redefines_the_oracle_is_found(repo: Path) -> None:
    oracles = repo / "data-pipeline" / "pipeline"
    oracles.mkdir(parents=True)
    (oracles / "oracles.py").write_text("def final_size(r0):\n    return r0\n", encoding="utf-8")
    edit(repo, "en", "01-basics/01-note.ipynb", lambda d: next(c for c in d["cells"] if c["cell_type"] == "code").update(
        source="# a copy of the oracle\ndef final_size(r0):\n    return r0"))
    assert found(repo, "01-basics/01-note.ipynb", "defines 'final_size'", "import it instead")


def test_a_notebook_with_packages_prints_their_versions(repo: Path) -> None:
    """F11: the Setup section is followed by a code cell that prints the versions (importlib.metadata)."""
    def drop(doc: dict) -> None:
        for c in doc["cells"]:
            if c["cell_type"] == "code" and "importlib.metadata" in c["source"]:
                c["source"] = "# print a number\nprint(1)"
    edit(repo, "en", "01-basics/01-note.ipynb", drop)
    assert found(repo, "en/01-basics/01-note.ipynb", "anatomy", "importlib.metadata")


FAKE_PIN = "fakepkg==1.2.3"


def fake_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A small package on ``sys.path`` with no distribution metadata: public names in its modules, a private module, a ``tests``
    folder and a nested package. Its ``__init__`` raises at the end, so any import of it fails the test."""
    site = tmp_path / "site"
    pkg = site / "fakepkg"
    (pkg / "tests").mkdir(parents=True)
    (pkg / "sub").mkdir()
    (pkg / "__init__.py").write_text("def init_public():\n    pass\n\n\nraise RuntimeError('fakepkg was imported')\n", encoding="utf-8")
    (pkg / "core.py").write_text("class Solver:\n    pass\n\n\ndef fit_model(x):\n    return x\n\n\nasync def fetch_all():\n    pass\n\n\n"
                                 "def _hidden():\n    pass\n\n\nif True:\n    def nested_not_top_level():\n        pass\n", encoding="utf-8")
    (pkg / "_private.py").write_text("def from_private_module():\n    pass\n", encoding="utf-8")
    (pkg / "tests" / "test_core.py").write_text("def test_inside_tests():\n    pass\n", encoding="utf-8")
    (pkg / "sub" / "__init__.py").write_text("def sub_public():\n    pass\n", encoding="utf-8")
    (pkg / "sub" / "deep.py").write_text("def deep_public():\n    pass\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(site))
    return site


def declare(root: Path, packages, pin: str | None = FAKE_PIN) -> None:
    (root / "product.json").write_text(json.dumps({"name": "x", "method_packages": packages}), encoding="utf-8")
    if pin:
        with (root / "notebooks" / "requirements.txt").open("a", encoding="utf-8") as f:
            f.write(pin + "\n")


def define_in_first_code_cell(root: Path, source: str, lang: str = "en", rel: str = "01-basics/01-note.ipynb") -> None:
    edit(root, lang, rel, lambda d: next(c for c in d["cells"] if c["cell_type"] == "code").update(source=source))


def test_adversarial_the_public_names_of_a_method_package_are_read_without_importing_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_package(tmp_path, monkeypatch)
    names = CHECK.package_public_names("fakepkg")
    assert names == {"init_public", "Solver", "fit_model", "fetch_all", "sub_public", "deep_public"}, names
    assert "fakepkg" not in sys.modules, "the source is read with ast, the package is never imported"
    assert CHECK.package_public_names("a_package_that_is_nowhere_installed") is None


def test_adversarial_a_notebook_that_defines_a_method_package_name_is_found(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_package(tmp_path, monkeypatch)
    declare(repo, ["fakepkg"])
    assert CHECK.form_findings(repo) == []
    define_in_first_code_cell(repo, "# a copy of the method\ndef fit_model(x):\n    return x")
    assert found(repo, "01-basics/01-note.ipynb", "code cell", "defines 'fit_model'", "fakepkg", "import it instead")
    define_in_first_code_cell(repo, "# a class of the package\nclass Solver:\n    pass", lang="es")
    assert found(repo, "notebooks/es/01-basics/01-note.ipynb", "defines 'Solver'", "fakepkg")
    # a private name, a name of the tests folder and a helper of the notebook's own are fine
    define_in_first_code_cell(repo, "# helpers\ndef _hidden():\n    pass\n\n\ndef test_inside_tests():\n    pass\n\n\ndef read_artifact(x):\n    return x",
                              rel="01-basics/02-note.ipynb")
    assert not found(repo, "01-basics/02-note.ipynb", "fakepkg")


def test_adversarial_without_method_packages_the_check_is_unchanged(repo: Path) -> None:
    assert CHECK.form_findings(repo) == []
    for body in ('{"name": "x"}', '{"name": "x", "method_packages": []}'):
        (repo / "product.json").write_text(body, encoding="utf-8")
        infos: list[str] = []
        assert CHECK.form_findings(repo, infos) == [] and infos == []
    (repo / "product.json").write_text("not json", encoding="utf-8")
    assert CHECK.form_findings(repo) == []  # the file is the product's; the key is optional
    (repo / "product.json").write_text('{"method_packages": "fakepkg"}', encoding="utf-8")
    assert found(repo, "product.json", "method_packages", "list of strings")


def test_adversarial_a_method_package_that_is_not_installed_is_info_in_the_static_check(repo: Path) -> None:
    declare(repo, ["not-installed-anywhere"], pin="not-installed-anywhere==0.1.0")
    infos: list[str] = []
    assert CHECK.form_findings(repo, infos) == []
    assert infos == ["check_notebooks: not-installed-anywhere not installed here; its names are checked by run_notebooks.py"]
    result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "check_notebooks.py"), str(repo)], capture_output=True, encoding="utf-8")
    # the minimal plant meets no floor of the bar: every finding is a bar finding, none is about the packages
    assert all(": bar:" in ln for ln in result.stdout.splitlines() if ln.startswith("  - ")), result.stdout
    assert "not-installed-anywhere not installed here; its names are checked by run_notebooks.py" in result.stdout


def test_adversarial_a_method_package_without_a_pin_is_found(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_package(tmp_path, monkeypatch)
    declare(repo, ["fakepkg"], pin=None)
    assert found(repo, "notebooks/requirements.txt", "fakepkg", "no exact pin")
    declare(repo, ["fakepkg"], pin="fakepkg>=1.0")  # a range is no pin
    assert found(repo, "notebooks/requirements.txt", "fakepkg", "no exact pin")
    (repo / "notebooks" / "requirements.txt").write_text(f"{PIN}\nFakePkg[extra]==1.2.3\n", encoding="utf-8")  # an extra and another case are fine
    assert not found(repo, "no exact pin")
    assert CHECK.method_pin(repo, "fakepkg") == "1.2.3"


class FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False


def test_adversarial_the_pypi_check_fails_on_anything_but_200(repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    import urllib.error
    declare(repo, ["fakepkg"], pin="fakepkg[extra]==1.2.3")
    seen: list[str] = []
    status = [200]

    def fake_open(req, timeout=None):
        url = req if isinstance(req, str) else req.full_url
        seen.append(url)
        if status[0] == 200:
            return FakeResponse(200)
        raise urllib.error.HTTPError(url, status[0], "Not Found", None, None)

    monkeypatch.setattr(CHECK.urllib.request, "urlopen", fake_open)
    assert CHECK.pypi_findings(repo) == [] and seen == ["https://pypi.org/pypi/fakepkg/1.2.3/json"]
    status[0] = 404
    out = CHECK.pypi_findings(repo)
    assert len(out) == 1 and "https://pypi.org/pypi/fakepkg/1.2.3/json" in out[0] and "404" in out[0], out
    # the command line: --pypi runs it, a plain run never touches the network (the floors of the bar are tested elsewhere)
    monkeypatch.setattr(CHECK, "bar_findings", lambda *a, **k: [])
    seen.clear()
    monkeypatch.setattr(sys, "argv", ["check_notebooks.py", str(repo)])
    assert CHECK.main() == 0 and seen == []
    monkeypatch.setattr(sys, "argv", ["check_notebooks.py", str(repo), "--pypi"])
    assert CHECK.main() == 1 and seen and "404" in capsys.readouterr().out
    status[0] = 200
    assert CHECK.main() == 0


def test_adversarial_a_network_failure_is_a_pypi_finding(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    declare(repo, ["fakepkg"])

    def refuse(req, timeout=None):
        raise OSError("no route")
    monkeypatch.setattr(CHECK.urllib.request, "urlopen", refuse)
    out = CHECK.pypi_findings(repo)
    assert len(out) == 1 and "https://pypi.org/pypi/fakepkg/1.2.3/json" in out[0] and "no route" in out[0]


def test_adversarial_ci_never_passes_pypi() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "check_notebooks.py --pypi" not in ci and "python scripts/check_notebooks.py" in ci


# ---------------------------------------------------------------- the floors of the bar (template 0.12.000, NB-048 to NB-063)
#
# Each floor has one test: a minimal notebook built in code that meets every floor (the control) and one that fails exactly that
# floor. ``bar_findings`` is called on parsed documents, so the form checks of the other tests stay out of these.

PNG = {"image/png": "iVBORw0KGgo=", "text/plain": ["<Figure size 640x480>"]}
BAR = CHECK.load_bar()
ENGINE = "def run(x):\n    return x * 1.5\n"
REFERENCE = "scipy==1.18.1"


def words(n: int, salt: str) -> str:
    """``n`` distinct words, so no two notebooks share a sentence unless a test asks for it."""
    return " ".join(f"{salt}{i}" for i in range(n))


ENTRYPOINTS = ["pipeline.engine.run", "fakepkg.run", "fakepkg.simulate", "fakepkg.work", "fakepkg.Model", "fakepkg.make_model",
               "fakepkg.predict", "fakepkg.splits.assert_no_leakage", "mine.work", "model.engine.run"]


def bar_repo(tmp_path: Path, methods: tuple[str, ...] = (), entrypoints: list[str] | None = None) -> Path:
    """A repository root with a pipeline (``pipeline.engine.run``), declared method packages and the entry points of the method."""
    root = tmp_path / "bar-repo"
    (root / "data-pipeline" / "pipeline").mkdir(parents=True)
    (root / "data-pipeline" / "pipeline" / "__init__.py").write_text("", encoding="utf-8")
    (root / "data-pipeline" / "pipeline" / "engine.py").write_text(ENGINE, encoding="utf-8")
    (root / "product.json").write_text(json.dumps({"method_packages": list(methods), "artifact_loaders": ["fakepkg.load_case"],
                                                    "method_entrypoints": ENTRYPOINTS if entrypoints is None else entrypoints}), encoding="utf-8")
    return root


SETUP_CODE = ("# imports, versions and the engine\nimport importlib.metadata as md\nimport sys\nfrom pathlib import Path\n\n"
              "import matplotlib.pyplot as plt\nimport numpy as np\n\nsys.path.insert(0, str(Path('../../..').resolve() / 'data-pipeline'))\n"
              "from pipeline.engine import run\n\nprint(md.version('numpy'))")


class Builder:
    """The cells of a notebook that meets the bar, with each knob a test turns to break one floor."""

    def __init__(self, lang: str, level: int, salt: str) -> None:
        self.lang, self.level, self.salt = lang, level, salt
        self.cells: list[dict] = []
        self.count = 0

    def md(self, text: str) -> None:
        self.cells.append({"cell_type": "markdown", "id": f"m{len(self.cells):03d}", "metadata": {}, "source": text})

    def code(self, source: str, text: str = "", figure: bool = False) -> None:
        self.count += 1
        outputs: list[dict] = []
        if text:
            outputs.append({"output_type": "stream", "name": "stdout", "text": text})
        if figure:
            # each figure has its own bytes: the gate counts one picture once, however often it is shown
            outputs.append({"output_type": "display_data", "data": {**PNG, "image/png": f"iVBORw0KGgo{self.count}="}, "metadata": {}})
        self.cells.append({"cell_type": "code", "id": f"c{len(self.cells):03d}", "metadata": {}, "source": source,
                           "execution_count": self.count, "outputs": outputs})


def bar_doc(lang: str = "en", level: int = 2, salt: str = "a", *, methods: int | None = None, figures: int | None = None,
            prose: int | None = None, after: int = 45, setups: int = 1, question: bool = True, answer: bool = True,
            answer_text: str | None = None, extra_code: tuple[str, ...] = (), sota_method: bool = True, sota_figure: bool = True,
            beyond: str = "figure", metadata_level: int | None = None, first_code: str | None = None) -> dict:
    """A notebook at ``level`` that meets every floor of the bar unless a knob is turned."""
    methods = (3 if level == 1 else 5) if methods is None else methods
    figures = (1 if level == 1 else 2) if figures is None else figures
    prose = (560 if level == 1 else 860) if prose is None else prose
    h = dict(zip(HEADINGS["en"], HEADINGS[lang]))
    q, a = ("**Question:**", "**Answer:**") if lang == "en" else ("**Pregunta:**", "**Respuesta:**")
    b = Builder(lang, level, salt)
    b.md(f"# Title {salt}\n\n" + (f"{q} {words(6, salt + 'q')}?\n\n" if question else "") + f"- Level: {level}\n- Reading time: 20 minutes")
    b.md(f"## {h['Objectives']}\n\n{words(40, salt + 'o')}.")
    b.md(f"## {h['Setup']}\n\nInstall with `pip install numpy==2.4.6`.\n\n```bash\npip install numpy==2.4.6\n```")
    b.code(first_code or SETUP_CODE, "2.4.6\n")
    for n in range(setups - 1):
        b.md(f"What setup cell {n} does.")
        b.code(f"# one more import\nimport json\nimport math\nfrom pathlib import Path as P{n}", "")
    b.md(f"## {h['Data']}\n\nThe data are made by the engine itself.")
    b.md(f"## {h['Method']}\n\n{words(prose, salt + 'p')}.")
    for k in range(methods):
        b.md(f"Step {k}: what step number {k} does and why it is there.")
        shown = "total 42.5\n" if k == 0 else f"step {k} {k * 1.5}\n"
        b.code(f"# run the engine at {k}\nvalue_{k} = run({k})\nprint('total 42.5' if {k} == 0 else 'step {k}', value_{k})", shown)
    for k in range(figures):
        b.md(f"Figure {k}: what is drawn.")
        b.code(f"# draw figure {k}\nplt.plot([0, 1], [0, {k + 1}])\nplt.show()", "", figure=True)
        b.md(f"{words(after, salt + f'f{k}')}.")
    for n, source in enumerate(extra_code):
        b.md(f"An extra cell, number {n}.")
        b.code(source, "")
    if level >= 3:
        b.md(f"## {h['State of the art']}\n\nThe reference implementation, run on the same data.")
        if sota_method:
            b.md("Run the reference.")
            b.code("# the pinned reference implementation\nfrom scipy.integrate import solve_ivp\n\nref = solve_ivp(lambda t, y: -y, (0, 1), [1.0])", "")
        if sota_figure:
            b.md("Compare.")
            b.code("# draw the comparison\nplt.plot([0, 1], [1, 0.4])\nplt.show()", "", figure=True)
            b.md(f"{words(after, salt + 'sf')}.")
    if level >= 4:
        b.md(f"## {h['Beyond the state of the art']}\n\nThe claim, measured.")
        if beyond == "figure":
            b.md("Draw it.")
            b.code("# draw the claim\nplt.plot([0, 1], [0, 1])\nplt.show()", "", figure=True)
            b.md(f"{words(after, salt + 'bf')}.")
        elif beyond == "table":
            b.md("| case | error |\n|---|---|\n| a | 0.1 |")
    result = (answer_text if answer_text is not None else f"The total came to 42.5 in the run of notebook {salt}, as the output shows.") if answer else "It went well."
    b.md(f"## {h['Results']}\n\n" + (f"{a} {result}\n\n" if answer else f"{result}\n\n") + words(30, salt + 'r') + ".")
    b.md(f"## {h['Summary']}\n\n- {words(12, salt + 's')}.")
    b.md(f"## {h['References']}\n\n- {SOURCE}")
    packages = ["numpy==2.4.6"] + ([REFERENCE] if level == 3 else [])
    return {"cells": b.cells, "nbformat": 4, "nbformat_minor": 5, "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"},
        "caos": {"language": lang, "topic": "01-t", "level": level if metadata_level is None else metadata_level, "title": "t",
                 "packages": packages, "data": [], "sources": [SOURCE], "beyond": []}}}


def bar_of(root: Path, doc: dict, lang: str = "en", others: tuple[dict, ...] = (), bar: dict | None = None) -> list[str]:
    docs: dict[str, dict[str, dict]] = {"en": {}, "es": {}}
    docs[lang]["01-t/01-n.ipynb"] = doc
    for n, other in enumerate(others, 2):
        docs[lang][f"01-t/{n:02d}-o.ipynb"] = other
    return CHECK.bar_findings(root, docs, bar)


def only(findings: list[str], *needles: str) -> None:
    """The findings are exactly one, and it holds every needle."""
    assert len(findings) == 1 and all(n in findings[0] for n in needles), findings


@pytest.fixture
def bar_root(tmp_path: Path) -> Path:
    return bar_repo(tmp_path)


@pytest.mark.parametrize("lang", ["en", "es"])
@pytest.mark.parametrize("level", [1, 2, 3, 4])
def test_a_notebook_that_meets_the_bar_passes_at_every_level_in_both_languages(bar_root: Path, lang: str, level: int) -> None:
    assert bar_of(bar_root, bar_doc(lang, level), lang) == []


def test_the_bar_file_holds_the_conventions_floors() -> None:
    """The produced contract: keys tooling, filler and floors, with the thresholds of convention section 1."""
    assert {"tooling", "filler", "floors"} <= set(BAR)
    f = BAR["floors"]
    assert f["method_cells"] == {"1": 3, "2": 5, "3": 5, "4": 5} and f["figures"] == {"1": 1, "2": 2, "3": 2, "4": 2}
    assert f["prose_words"] == {"1": 500, "2": 800, "3": 800, "4": 800} and f["words_after_figure"] == 40
    assert (f["setup_cells_max"], f["reproduction_checks_max"], f["repeated_sentences_max"]) == (2, 1, 2)
    assert (f["long_sentence_chars"], f["logic_lines_max"], f["line_chars_max"]) == (50, 30, 120)
    assert {"numpy", "pandas", "matplotlib", "seaborn", "plotly", "IPython", "PIL"} <= set(BAR["tooling"])
    assert len(BAR["filler"]) >= 6 and all(isinstance(s, str) and s for s in BAR["filler"])


def test_the_thresholds_are_read_from_the_file_and_not_written_in_the_script(bar_root: Path) -> None:
    doc = bar_doc("en", 2, methods=4)
    only(bar_of(bar_root, doc), "method cells 4", "the floor at level 2 is 5")
    relaxed = json.loads(json.dumps(BAR))
    relaxed["floors"]["method_cells"]["2"] = 4
    assert bar_of(bar_root, doc, bar=relaxed) == []


def test_nb048_method_cells(bar_root: Path) -> None:
    """The floor is 3 at level 1 and 5 from level 2; the finding names the measure, the value and the floor."""
    assert bar_of(bar_root, bar_doc("en", 1, methods=3)) == []
    only(bar_of(bar_root, bar_doc("en", 1, methods=2)), "method cells 2", "the floor at level 1 is 3")
    assert bar_of(bar_root, bar_doc("en", 2, methods=5)) == []
    only(bar_of(bar_root, bar_doc("en", 2, methods=4)), "method cells 4", "the floor at level 2 is 5")


def test_nb048_what_counts_as_a_method_cell(tmp_path: Path) -> None:
    """Calls into numpy, pandas, matplotlib and the standard library, and a helper the notebook defines, are not method cells."""
    root = bar_repo(tmp_path)
    tooling = ("# numpy is tooling\nz = np.linspace(0, 1, 5)\nprint(z)", "# the standard library is tooling\nimport json\nprint(json.dumps({}))",
               "# a helper defined here wraps the engine\ndef wrapper(x):\n    return run(x)\n\nprint(wrapper)")
    doc = bar_doc("en", 2, methods=4, extra_code=tooling)
    only(bar_of(root, doc), "method cells 4")
    # the helper's own calls do count nothing, a call of the engine does
    doc = bar_doc("en", 2, methods=4, extra_code=("# one real call of the engine\nr = run(3)\nprint(r)",))
    assert bar_of(root, doc) == []
    # a method package of product.json counts at every level, under the name it is imported by
    root2 = bar_repo(tmp_path / "pkg", methods=("fakepkg",))
    code = "# call the package\nfrom fakepkg import work\n\nr = work(1)\nprint(r)"
    doc = bar_doc("en", 2, methods=4, extra_code=(code,))
    assert bar_of(root2, doc) == []


def test_nb048_a_pinned_reference_implementation_counts_at_level_three_only(bar_root: Path) -> None:
    ref = "# the reference implementation\nfrom scipy.integrate import solve_ivp\n\nref = solve_ivp(lambda t, y: -y, (0, 1), [1.0])"
    assert bar_of(bar_root, bar_doc("en", 3, methods=3, extra_code=(ref,))) == []
    only(bar_of(bar_root, bar_doc("en", 3, methods=3)), "method cells 4", "level 3")
    two = bar_doc("en", 2, methods=4, extra_code=(ref,))
    two["metadata"]["caos"]["packages"] = ["numpy==2.4.6", REFERENCE]
    only(bar_of(bar_root, two), "method cells 4", "level 2")


def test_nb049_figures(bar_root: Path) -> None:
    assert bar_of(bar_root, bar_doc("en", 1, figures=1)) == []
    only(bar_of(bar_root, bar_doc("en", 1, figures=0)), "figures 0", "the floor at level 1 is 1")
    only(bar_of(bar_root, bar_doc("en", 2, figures=1)), "figures 1", "the floor at level 2 is 2")


def test_nb050_words_after_each_figure(bar_root: Path) -> None:
    assert bar_of(bar_root, bar_doc("en", 1, after=40)) == []
    only(bar_of(bar_root, bar_doc("en", 1, after=39)), "followed by 39 words", "the floor is 40")
    # a figure that is the last cell, and a figure followed by a code cell, are not read
    doc = bar_doc("en", 1)
    last_figure = max(i for i, c in enumerate(doc["cells"]) if c["cell_type"] == "code" and c["outputs"] and "data" in c["outputs"][-1])
    doc["cells"] = doc["cells"][:last_figure + 1]
    assert any("is not followed by a markdown cell" in f for f in bar_of(bar_root, doc))
    doc = bar_doc("en", 1)
    doc["cells"].insert(last_figure + 1, {"cell_type": "code", "id": "z", "metadata": {}, "source": "# next\nprint(1)",
                                          "execution_count": 99, "outputs": []})
    assert any("is not followed by a markdown cell" in f for f in bar_of(bar_root, doc))


def test_nb051_explanatory_prose_words(bar_root: Path) -> None:
    """The words outside Setup, Data and References: the floor is 500 at level 1 and 800 from level 2."""
    ok = bar_doc("en", 2, prose=800)
    assert bar_of(bar_root, ok) == []
    thin = bar_doc("en", 2, prose=200)
    only(bar_of(bar_root, thin), "explanatory prose words", "the floor at level 2 is 800")
    only(bar_of(bar_root, bar_doc("en", 1, prose=100)), "explanatory prose words", "the floor at level 1 is 500")


def test_nb051_words_in_setup_data_and_references_do_not_count(bar_root: Path) -> None:
    doc = bar_doc("en", 2, prose=200)
    doc["cells"][4]["source"] += "\n\n" + words(900, "padding")  # the Data text
    only(bar_of(bar_root, doc), "explanatory prose words")


def test_nb052_setup_and_input_output_cells(bar_root: Path) -> None:
    assert bar_of(bar_root, bar_doc("en", 2, setups=2)) == []
    only(bar_of(bar_root, bar_doc("en", 2, setups=3)), "setup and input/output cells 3", "at most 2")


def test_nb052_a_reader_and_its_data_are_setup_and_a_computation_is_not(bar_root: Path) -> None:
    reader = ("# a reader of the committed files and the data it reads\nimport json\n\n\ndef read_json(relative):\n"
              "    return json.loads(Path(relative).read_text(encoding='utf-8'))\n\n\nCASES = read_json('data/derived/x.json')")
    doc = bar_doc("en", 2, extra_code=(reader, "# another reader\nOTHER = read_json('data/derived/y.json')"))
    only(bar_of(bar_root, doc), "setup and input/output cells 3")
    work = "# a computation with numpy is not setup\nz = np.linspace(0, 1, 5) ** 2\nprint(z.sum())"
    assert bar_of(bar_root, bar_doc("en", 2, setups=2, extra_code=(work,))) == []


def test_nb052_a_version_loop_and_a_reader_of_the_products_object_are_setup(bar_root: Path) -> None:
    """The example's own setup cell: a loop that prints versions, a reader that builds the product's object from a file, a pick out of data."""
    cell = ("# versions and a reader that builds the product's parameter object\nimport importlib.metadata as md\n\n"
            "for name in (\"numpy\",):\n    print(name, md.version(name))\n\n\n"
            "def read_params(path):\n    return run(json.loads(Path(path).read_text(encoding=\"utf-8\")))\n\n\n"
            "CASES = [c for c in INDEX[\"cases\"]]")
    only(bar_of(bar_root, bar_doc("en", 2, setups=2, extra_code=(cell,))), "setup and input/output cells 3")
    # a wrapper around the method that reads nothing is no reader, and arithmetic is no pick out of data
    wrapper = "# a wrapper\ndef wrapper(x):\n    return run(x)\n\n\ntotal = a + b"
    assert bar_of(bar_root, bar_doc("en", 2, setups=2, extra_code=(wrapper,))) == []


def test_nb053_reproduction_checks(bar_root: Path) -> None:
    check = "# the engine reproduces itself\nimport numpy as np\n\nassert np.allclose(run(2), run(2))\nprint('ok')"
    assert bar_of(bar_root, bar_doc("en", 2, extra_code=(check,))) == []
    only(bar_of(bar_root, bar_doc("en", 2, extra_code=(check, check))), "reproduction checks 2", "at most 1")


@pytest.mark.parametrize("code", [
    "# allclose\nprint(np.allclose(run(2), 3.0))",
    "# array_equal\nprint(np.array_equal([run(2)], [3.0]))",
    "# isclose\nimport math\nprint(math.isclose(run(2), 3.0))",
    "# numpy.testing\nnp.testing.assert_allclose(run(2), 3.0)",
    "# an assert\nassert run(2) == 3.0",
    "# the committed value\nimport json\n\nbaked = json.loads(Path('data/derived/x.json').read_text())\nprint(run(2) == baked['v'])",
    "# an absolute difference with the committed value\nimport json\n\nbaked = json.loads(Path('data/derived/x.json').read_text())\nprint(abs(run(2) - baked['v']))",
])
def test_nb053_every_form_of_reproduction_check_is_counted(bar_root: Path, code: str) -> None:
    only(bar_of(bar_root, bar_doc("en", 2, extra_code=(code, code))), "reproduction checks 2")


def test_nb053_a_comparison_that_is_not_with_a_committed_value_is_not_a_check(bar_root: Path) -> None:
    code = "# two computed values\nprint(run(2) == run(2.0), run(1) != run(2))"
    assert bar_of(bar_root, bar_doc("en", 2, extra_code=(code, code))) == []


def test_nb053_a_method_named_assert_is_not_a_check(bar_root: Path) -> None:
    # the product's own refusal, called through the method package, is the method at work (Fragmenta 04-01: assert_no_leakage)
    code = "# the engine refuses a leaking split\ntry:\n    run.assert_no_leakage(2)\nexcept ValueError as refusal:\n    print(refusal)"
    assert bar_of(bar_root, bar_doc("en", 2, extra_code=(code, code))) == []


def test_nb054_sentences_shared_with_another_notebook(bar_root: Path) -> None:
    shared = [f"This sentence number {n} is long enough to count and it is shared." for n in range(3)]
    other = bar_doc("en", 2, "b")
    one = bar_doc("en", 2, "a")
    for doc in (one, other):
        doc["cells"][1]["source"] += " " + " ".join(shared[:2])
    assert bar_of(bar_root, one, others=(other,)) == []
    for doc in (one, other):
        doc["cells"][1]["source"] += " " + shared[2]
    findings = bar_of(bar_root, one, others=(other,))
    assert len(findings) == 2 and all("3 sentences over 50 characters" in f and "at most 2" in f for f in findings), findings


def test_nb054_the_install_line_the_data_lines_and_the_references_are_not_compared(bar_root: Path) -> None:
    one, other = bar_doc("en", 2, "a"), bar_doc("en", 2, "b")
    line = " ".join(f"The same long sentence {n} that both notebooks carry in these sections." for n in range(5))
    for doc in (one, other):
        for cell in doc["cells"]:
            if cell["cell_type"] == "markdown" and cell["source"].startswith(("## Setup", "## Data", "## References")):
                cell["source"] += "\n\n" + line
    assert bar_of(bar_root, one, others=(other,)) == []


def test_nb054_the_comparison_is_inside_one_tree(bar_root: Path) -> None:
    shared = " ".join(f"A sentence {n} long enough to be counted as shared prose." for n in range(4))
    en, es = bar_doc("en", 2, "a"), bar_doc("es", 2, "b")
    for doc in (en, es):
        doc["cells"][1]["source"] += " " + shared
    docs = {"en": {"01-t/01-n.ipynb": en}, "es": {"01-t/01-n.ipynb": es}}
    assert CHECK.bar_findings(bar_root, docs) == []


@pytest.mark.parametrize("sentence", ["Interpret the method with its units, contract and data provenance",
                                      "Trace the evidence from source contract to result",
                                      "The question is what the artifact represents and where its evidence stops",
                                      "read the physical axes and units of the figure"])
def test_nb055_generic_filler_sentences(bar_root: Path, sentence: str) -> None:
    doc = bar_doc("en", 2)
    assert bar_of(bar_root, doc) == []
    doc["cells"][1]["source"] += f"\n\n{sentence}."
    only(bar_of(bar_root, doc), "generic filler sentence")


def test_nb056_two_statements_on_one_line(bar_root: Path) -> None:
    separate = "# separate lines\nA = run(1)\nB = run(2)\nprint(A, B)"
    assert not any("statements" in f for f in bar_of(bar_root, bar_doc("en", 2, extra_code=(separate,))))
    chained = "# chained\nA = run(1); B = run(2)\nprint(A, B)"
    findings = bar_of(bar_root, bar_doc("en", 2, extra_code=(chained,)))
    assert any("holds 2 statements" in f and "one statement per line" in f for f in findings), findings
    inline_if = "# a compound statement with its body on the header line is one simple statement\nif run(1): print(1)"
    assert not any("statements" in f for f in bar_of(bar_root, bar_doc("en", 2, extra_code=(inline_if,))))


def test_nb056_a_line_over_120_characters_and_a_cell_over_30_lines_of_logic(bar_root: Path) -> None:
    longline = "# one long line\nvalues = [" + ", ".join(str(n) for n in range(60)) + "]\nprint(values)"
    findings = bar_of(bar_root, bar_doc("en", 2, extra_code=(longline,)))
    assert any("a line of" in f and "the limit is 120" in f for f in findings), findings
    exact = "# a line of exactly 120 characters\nname = '" + "x" * (120 - len("name = ''")) + "'"
    assert not any("a line of" in f for f in bar_of(bar_root, bar_doc("en", 2, extra_code=(exact,))))
    many = "# thirty-one lines of logic\n" + "\n".join(f"v{n} = {n}" for n in range(31))
    findings = bar_of(bar_root, bar_doc("en", 2, extra_code=(many,)))
    assert any("31 lines of logic" in f and "the limit is 30" in f for f in findings), findings
    thirty = "# thirty lines of logic\n" + "\n".join(f"v{n} = {n}" for n in range(30))
    assert not any("lines of logic" in f for f in bar_of(bar_root, bar_doc("en", 2, extra_code=(thirty,))))


def test_nb057_the_first_cell_states_the_question_in_each_language(bar_root: Path) -> None:
    only(bar_of(bar_root, bar_doc("en", 2, question=False)), "does not state the question", "**Question:**")
    only(bar_of(bar_root, bar_doc("es", 2, question=False), "es"), "does not state the question", "**Pregunta:**")
    # the English marker does not stand for the Spanish one
    es = bar_doc("es", 2)
    es["cells"][0]["source"] = es["cells"][0]["source"].replace("**Pregunta:**", "**Question:**")
    only(bar_of(bar_root, es, "es"), "**Pregunta:**")


def test_nb058_the_answer_quotes_a_number_that_an_output_shows(bar_root: Path) -> None:
    assert bar_of(bar_root, bar_doc("en", 2, answer_text="The total came to 42.5.")) == []
    only(bar_of(bar_root, bar_doc("en", 2, answer=False)), "does not answer it", "**Answer:**")
    only(bar_of(bar_root, bar_doc("en", 2, answer_text="The total came to 99.9.")), "quotes no number that appears in an output")
    only(bar_of(bar_root, bar_doc("en", 2, answer_text="It came out well, as expected.")), "quotes no number")
    # a decimal comma is read as a point, in the answer as in the output
    assert bar_of(bar_root, bar_doc("es", 2, answer_text="El total fue de 42,5 en la corrida."), "es") == []


def test_nb059_level_three_runs_the_state_of_the_art_and_draws_it(bar_root: Path) -> None:
    only(bar_of(bar_root, bar_doc("en", 3, sota_method=False)), "no method cell under State of the art")
    only(bar_of(bar_root, bar_doc("en", 3, sota_figure=False)), "no figure under State of the art")
    # a method cell and a figure elsewhere do not stand in for the section
    findings = bar_of(bar_root, bar_doc("en", 3, sota_method=False, sota_figure=False))
    assert len(findings) == 2, findings


def test_nb060_level_four_shows_a_figure_or_a_table_under_beyond(bar_root: Path) -> None:
    assert bar_of(bar_root, bar_doc("en", 4, beyond="figure")) == []
    assert bar_of(bar_root, bar_doc("en", 4, beyond="table")) == []
    only(bar_of(bar_root, bar_doc("en", 4, beyond="none")), "no figure or table under Beyond the state of the art")


def test_nb061_a_notebook_without_a_valid_level_is_measured_at_level_two(bar_root: Path) -> None:
    """NB-012 already finds the level; the floors then use level 2, so a level 1 notebook with 3 method cells is short."""
    doc = bar_doc("en", 1, methods=3, figures=1, prose=560, metadata_level=9)
    findings = bar_of(bar_root, doc)
    assert any("method cells 3" in f and "level 2 (no valid level declared)" in f for f in findings), findings
    del doc["metadata"]["caos"]["level"]
    assert any("figures 1" in f for f in bar_of(bar_root, doc))


def test_nb062_the_floors_run_in_the_full_gate_after_the_form_checks(tmp_path: Path) -> None:
    """``findings_of`` is the form checks then the floors; a form-clean repository of thin notebooks fails only the floors."""
    repo = make_repo(tmp_path / "repo")
    findings = CHECK.findings_of(repo)
    assert findings and all(": bar:" in f for f in findings), findings[:3]
    assert CHECK.form_findings(repo) == []


def test_nb063_the_command_line_reports_the_floors_and_exits_one(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    shutil.copy2(ROOT / "scripts" / "check_notebooks.py", tmp_path / "check_notebooks.py")
    shutil.copy2(ROOT / "scripts" / "notebook_bar.json", tmp_path / "notebook_bar.json")
    r = subprocess.run([sys.executable, "-I", str(tmp_path / "check_notebooks.py"), str(repo)], capture_output=True, encoding="utf-8")
    assert r.returncode == 1 and "NOTEBOOKS CHECK FAILED" in r.stdout and ": bar: method cells" in r.stdout, r.stdout


# ---------------------------------------------------------------- the review of the gate (2026-10-27): B1 to B4, M1 to M7, m1, m3, m5
#
# Each test is a reproducer of the adversarial review, built in code; it failed on the gate of the first release candidate and passes now.

def review_root(tmp_path: Path, declared: dict | None = None) -> Path:
    """A product with a method package (``fakepkg``), a pipeline whose ``io`` holds a reader, and the template's ``src`` skeleton filled."""
    root = bar_repo(tmp_path, methods=("fakepkg",))
    (root / "data-pipeline" / "pipeline" / "io").mkdir()
    (root / "data-pipeline" / "pipeline" / "io" / "__init__.py").write_text("", encoding="utf-8")
    (root / "data-pipeline" / "pipeline" / "io" / "formats.py").write_text("def read_json(path):\n    return {}\n", encoding="utf-8")
    (root / "data-pipeline" / "src" / "model").mkdir(parents=True)
    (root / "data-pipeline" / "src" / "model" / "engine.py").write_text("def run(x):\n    return x\n", encoding="utf-8")
    if declared:
        doc = json.loads((root / "product.json").read_text(encoding="utf-8"))
        doc.update(declared)
        (root / "product.json").write_text(json.dumps(doc), encoding="utf-8")
    return root


def method_cells_of(root: Path, doc: dict, lang: str = "en") -> list[int]:
    return CHECK.Reading(doc, lang, root, BAR).method_cells


def test_b1_readers_loaders_versions_and_dunder_chains_are_no_method_cells(tmp_path: Path) -> None:
    """The trash notebook of the review: it reads the baked manifests with the pipeline's own reader and prints a module name."""
    root = review_root(tmp_path)
    cells = ("# import\nimport fakepkg\nfrom pipeline.io.formats import read_json\nfrom pipeline.io.schema import SIRParams",
             "# the pipeline's own reader\nmanifest = read_json(Path('../../../data/derived/manifests/EX02.json'))\nprint(manifest['params'])",
             "# a module name\nprint(read_json.__module__.upper())",
             "# a version\nprint(fakepkg.__version__.upper())",
             "# a version call\nprint(fakepkg.version())",
             "# a loader\nprint(fakepkg.load_case('EX'))",
             "# the product's parameter object\nparams = SIRParams('x', 1, 2, 3, 4)")
    doc = bar_doc("en", 2, methods=0, extra_code=cells)
    assert method_cells_of(root, doc) == []
    only([f for f in bar_of(root, doc) if "method cells" in f], "method cells 0")
    # the same names, one real call of the package each: five method cells
    real = tuple(f"# run {k}\nr{k} = fakepkg.simulate({k})" for k in range(5))
    assert len(method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=("# import\nimport fakepkg", *real)))) == 5


def test_b2_import_names_are_static_and_never_read_from_the_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """scikit-learn is imported as sklearn: the product's map, the static map or the distribution name decide, never what is installed."""
    def refuse(*a, **k):
        raise AssertionError("the floors asked the environment for an import name")
    monkeypatch.setattr(CHECK.importlib.metadata, "distribution", refuse)
    root = review_root(tmp_path)
    sota = "# the reference\nfrom sklearn.linear_model import LinearRegression\n\nmodel = LinearRegression()\nmodel.fit(x, y)"
    doc = bar_doc("en", 3, methods=4)
    doc["metadata"]["caos"]["packages"] = ["numpy==2.4.6", "scikit-learn==1.5.2"]
    for c in doc["cells"]:
        if c["cell_type"] == "code" and "solve_ivp" in c["source"]:
            c["source"] = sota
    assert bar_of(root, doc) == []
    for dist, module in (("scikit-image", "skimage"), ("opencv-python", "cv2"), ("PyWavelets", "pywt"), ("PyYAML", "yaml")):
        assert CHECK.static_import_name(dist, BAR, {}) == module
    assert CHECK.static_import_name("my-dist", BAR, {"my-dist": "mine"}) == "mine"
    declared = review_root(tmp_path / "d", declared={"method_packages": ["my-dist"], "import_names": {"my-dist": "mine"}})
    calls = tuple(f"# call {k}\nr{k} = mine.work({k})" for k in range(5))
    assert len(method_cells_of(declared, bar_doc("en", 2, methods=0, extra_code=("# import\nimport mine", *calls)))) == 5


def test_b2_the_import_name_of_an_installed_distribution_is_never_a_wheel_file_or_a_libs_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    class Fake:
        files = [Path("scipy-1.18.1-cp313-cp313-win_amd64.whl"), Path("numpy.libs/x.dll"), Path("scipy/__init__.py")]

        def read_text(self, name):
            return None
    monkeypatch.setattr(CHECK.importlib.metadata, "distribution", lambda dist: Fake())
    assert CHECK.import_name("scipy") == "scipy"


def test_b3_an_object_built_from_a_method_class_and_its_calls_are_method_cells(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    cells = ("# import\nimport fakepkg", "# build\nmodel = fakepkg.Model(k=3)", "# fit\nmodel.fit(x)", "# predict\ny = model.predict(x)",
             "# residuals\nr = model.residuals(x, y)", "# score\ns = model.score(x, y)", "# plot\nmodel.plot_fit()")
    doc = bar_doc("en", 2, methods=0, extra_code=cells)
    assert len(method_cells_of(root, doc)) == 5  # a call with nothing the notebook read or computed in it (plot_fit()) earns none
    assert not any("method cells" in f for f in bar_of(root, doc))
    # the result of a function is not an object API: attributes of it earn nothing
    plain = ("# import\nimport fakepkg", "# run\nres = fakepkg.simulate(1)", "# look\nprint(res.series.max())", "# look\nprint(res.series.min())")
    assert len(method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=plain))) == 1


@pytest.mark.parametrize("answer,shown", [("The value is 0.42 here.", "0.4213"), ("About 42 % of cases.", "0.42"), ("12,345 cases in all.", "12345"),
                                          ("12.345 cases in all.", "12345"), ("It took 4.20e-02 s.", "0.042"), ("The share is 0,42.", "0.4213"),
                                          ("The value is 2 and 17.", "17")])
def test_b4_the_answer_is_matched_at_the_precision_a_reader_writes_it(tmp_path: Path, answer: str, shown: str) -> None:
    root = review_root(tmp_path)
    doc = bar_doc("en", 2, answer_text=answer)
    for c in doc["cells"]:
        if c["cell_type"] == "code" and c["outputs"] and "total 42.5" in "".join(c["outputs"][0].get("text", "")):
            c["outputs"][0]["text"] = f"computed {shown}\n"
    assert not any("answer quotes" in f for f in bar_of(root, doc)), answer


@pytest.mark.parametrize("answer,shown", [("The value is 0.43 here.", "0.4213"), ("The tools of release 2.4 are used.", "42.5"),
                                          ("Saved in 2026 as planned.", "saved on 2026-10-27"), ("About 43 % of cases.", "0.42"),
                                          ("12,346 cases in all.", "12345")])
def test_b4_a_version_a_year_or_a_number_that_rounds_elsewhere_is_not_the_answer(tmp_path: Path, answer: str, shown: str) -> None:
    root = review_root(tmp_path)
    doc = bar_doc("en", 2, answer_text=answer)
    for c in doc["cells"]:
        if c["cell_type"] == "code" and c["outputs"] and "total 42.5" in "".join(c["outputs"][0].get("text", "")):
            c["outputs"][0]["text"] = f"computed {shown}\n"
    assert any("answer quotes no number" in f for f in bar_of(root, doc)), answer


def test_b4_what_a_setup_cell_prints_is_not_a_computed_number(tmp_path: Path) -> None:
    """The version print of the Setup section shows 2.4.6; an answer that quotes 2.4.6 or 2.4 quotes the tools, not the result."""
    root = review_root(tmp_path)
    assert any("answer quotes no number" in f for f in bar_of(root, bar_doc("en", 2, answer_text="The release 2.4.6 and the number 2.4 hold.")))


def test_m1_hidden_repeated_and_tabular_text_is_no_prose() -> None:
    assert CHECK.words_of("<!-- " + "pad " * 900 + "-->") == 0
    assert CHECK.words_of("Intro.\n\n" + "    x = 1\n" * 300) == 1
    assert CHECK.words_of("\n".join("| a | 1 |" for _ in range(100))) == 0
    assert CHECK.words_of("- item one\n    - nested item words\n") == 5  # a nested list is prose, not code


def test_m1_one_sentence_repeated_is_counted_once_and_is_a_finding(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    sentence = "This one sentence of forty words repeats itself many times over inside the same notebook. "
    doc = bar_doc("en", 2, prose=10)
    doc["cells"][1]["source"] += " " + sentence * 60
    findings = bar_of(root, doc)
    assert any("explanatory prose words" in f for f in findings), findings
    assert any("sentences occur more than twice inside the notebook" in f for f in findings), findings


def test_m2_cells_that_only_read_and_print_are_input_output_cells(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    cells = tuple(f"# read {k}\nd{k} = json.loads(Path('../../../data/derived/{k}.json').read_text())\nprint(d{k})" for k in range(4))
    only(bar_of(root, bar_doc("en", 2, extra_code=cells)), "setup and input/output cells 5")
    # a print of what a method returned is not an input/output cell
    shown = ("# run\nr = run(1)", "# show\nprint(r)", "# show\nprint(r.real)")
    assert not any("setup and input/output" in f for f in bar_of(root, bar_doc("en", 2, extra_code=shown * 3)))


def test_m3_the_forms_of_reproduction_check_the_review_found_are_counted(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    head = ("# import\nimport fakepkg", "# the committed case and the run\nref = fakepkg.load_case('EX')\nsim = fakepkg.run(1)")
    for code in ("print(sim - ref)", "print(np.linalg.norm(sim - ref))", "print(np.round(sim - ref, 6))", "d = abs(sim - ref)\nprint(d)",
                 "fakepkg.testing.assert_allclose(sim, ref)"):
        extra = (*head, f"# check\n{code}", f"# check again\n{code}")
        assert any("reproduction checks" in f for f in bar_of(root, bar_doc("en", 2, extra_code=extra))), code


def test_m3_input_validation_and_a_selector_are_no_reproduction_checks(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    cells = ("# validate\nassert X.shape[0] == len(y)", "# validate again\nassert len(X) > 0",
             "# pick the sample at t = 10\nidx = np.flatnonzero(np.isclose(t, 10.0))")
    assert not any("reproduction checks" in f for f in bar_of(root, bar_doc("en", 2, extra_code=cells)))
    reporting = ("# does it match\nprint(np.isclose(a, b))", "# does it match again\nprint(np.isclose(a, c))")
    assert any("reproduction checks" in f for f in bar_of(root, bar_doc("en", 2, extra_code=reporting)))
    # the product's own refusal named assert_ is the method at work (the 0.12.000 review fix) and testing.assert_ is a check
    refusal = ("# import\nimport fakepkg", "# refuse\nfakepkg.splits.assert_no_leakage(a, b)", "# refuse\nfakepkg.splits.assert_no_leakage(c, d)")
    assert not any("reproduction checks" in f for f in bar_of(root, bar_doc("en", 2, extra_code=refusal)))


def test_m4_two_notebooks_of_a_tree_do_not_share_a_question(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    one, other = bar_doc("en", 2, "a"), bar_doc("en", 2, "b")
    other["cells"][0]["source"] = one["cells"][0]["source"].replace("# Title a", "# Title b")
    findings = bar_of(root, one, others=(other,))
    assert len(findings) == 1 and "no two notebooks of a tree share a question" in findings[0], findings
    assert bar_of(root, one, others=(bar_doc("en", 2, "c"),)) == []


def test_m5_at_level_three_the_reference_implementation_alone_does_not_fill_the_floor(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    reference = tuple(f"# reference {k}\nfrom scipy.integrate import solve_ivp\n\nr{k} = solve_ivp(f, (0, 1), [1.0])" for k in range(6))
    doc = bar_doc("en", 3, methods=0, extra_code=reference)
    findings = [f for f in bar_of(root, doc) if "method cells" in f]
    assert len(findings) == 1 and "method cells that call the product's own method" in findings[0], findings
    assert bar_of(root, bar_doc("en", 3, methods=4)) == []


def test_m7_the_modules_of_the_templates_src_skeleton_are_method_modules(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    calls = tuple(f"# run {k}\nfrom model.engine import run as r{k}\n\nv{k} = r{k}({k})" for k in range(5))
    assert len(method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=calls))) == 5
    assert "model" in CHECK.pipeline_modules(root)


def test_m1_minor_a_branch_that_never_runs_is_no_method_call(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    cells = ("# import\nimport fakepkg", "# never\nif False:\n    fakepkg.run(1)")
    assert method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=cells)) == []


def test_m3_minor_one_picture_shown_twice_counts_once_and_other_figure_kinds_count(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    doc = bar_doc("en", 1, figures=0)
    shot = {"output_type": "display_data", "data": {"image/png": "AAAA", "text/plain": ["<F>"]}, "metadata": {}}
    for k in range(3):
        doc["cells"].append({"cell_type": "code", "id": f"x{k}", "metadata": {}, "source": "# show\nshow()", "execution_count": 90 + k,
                             "outputs": [shot]})
        doc["cells"].append({"cell_type": "markdown", "id": f"y{k}", "metadata": {}, "source": words(45, f"r{k}") + "."})
    assert CHECK.Reading(doc, "en", root, BAR).fig_cells == [(len(doc["cells"]) - 6, 1)]
    jpeg = {"output_type": "display_data", "data": {"image/jpeg": "BBBB"}, "metadata": {}}
    assert CHECK.figures_of({"outputs": [jpeg]}, set()) == 1
    assert CHECK.figures_of({"outputs": [{"output_type": "display_data", "data": {"application/vnd.plotly.v1+json": {"data": []}}}]}, set()) == 1


def test_m5_minor_a_compound_statement_with_its_body_on_its_line_is_found(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    findings = bar_of(root, bar_doc("en", 2, extra_code=("# inline\nif ok: y = 1", "# loop\nfor k in d: print(k)")))
    assert len([f for f in findings if "a compound statement and its body" in f]) == 2, findings


# ---------------------------------------------------------------- the re-review (2026-10-27): NB1 to NB4 and the minors

def test_nb1_a_lookup_of_the_registry_is_no_method_cell_and_the_product_decides(tmp_path: Path) -> None:
    """The second trash notebook: it looks cases up in the registry and prints them, and runs no engine."""
    root = review_root(tmp_path)
    (root / "data-pipeline" / "pipeline" / "registry.py").write_text("def get_case(x):\n    return x\n\n\ndef list_cases():\n    return []\n", encoding="utf-8")
    cells = ("# import\nfrom pipeline.registry import get_case, list_cases",
             *(f"# look up\ncase{k} = get_case('EX02')\nprint(case{k}.params)" for k in range(3)),
             "# how many\nprint(len(list_cases()))", "# which\nprint(list_cases())")
    doc = bar_doc("en", 2, methods=0, extra_code=cells)
    assert method_cells_of(root, doc) == []
    only([f for f in bar_of(root, doc) if "method cells" in f], "method cells 0")
    # a product that declares the lookup as its method gets what it declared
    declared = review_root(tmp_path / "d", declared={"method_entrypoints": [*ENTRYPOINTS, "pipeline.registry.get_case"]})
    assert len(method_cells_of(declared, doc)) == 3
    # a constant-only call of an object's method earns nothing, and neither does an attribute of a result
    objects = ("# import\nimport fakepkg", "# build\nres = fakepkg.simulate(1)", "# look\nprint(res.series.max())", "# look\nprint(res.table.keys())")
    assert len(method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=objects))) == 1


def test_nb1_a_product_must_declare_its_method_entrypoints(tmp_path: Path) -> None:
    root = bar_repo(tmp_path)
    doc = bar_doc("en", 2)
    (root / "product.json").write_text(json.dumps({"method_packages": []}), encoding="utf-8")
    assert any(f.startswith("product.json: bar: product.json declares no method_entrypoints") for f in bar_of(root, doc))
    (root / "product.json").write_text(json.dumps({"method_entrypoints": "run"}), encoding="utf-8")
    assert any("must be a list of dotted names" in f for f in bar_of(root, doc))
    (root / "product.json").write_text(json.dumps({"method_entrypoints": ["pipeline.engine.run"]}), encoding="utf-8")
    assert not any(f.startswith("product.json") for f in bar_of(root, doc))
    (root / "product.json").write_text(json.dumps({"method_entrypoints": []}), encoding="utf-8")  # what instantiate writes: nothing counts yet
    findings = bar_of(root, doc)
    assert any("method cells 0" in f for f in findings) and any("declares no method_entrypoints" in f for f in findings)


def test_nb2_a_chained_constructor_a_factory_and_a_table_of_objects_bind_their_objects(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    tail = ("# predict\ny = model.predict(x)", "# residuals\nr = model.residuals(x, y)", "# score\ns = model.score(x, y)", "# again\nt = model.score(y, x)")
    for build in ("model = fakepkg.Model(k=3).fit(x)", "model = fakepkg.Model.make(k=3)", "model = fakepkg.Model(k=3)"):
        cells = ("# import\nimport fakepkg", f"# build\n{build}", *tail)
        assert len(method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=cells))) == 5, build
    table = ("# import\nimport fakepkg", "# arms\narms = {'a': fakepkg.Model(k=1), 'b': fakepkg.Model(k=2)}",
             *(f"# predict\nv{k} = arms['a'].predict(x)" for k in range(4)))
    assert len(method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=table))) == 5


def test_nb3_short_sentences_and_paragraphs_repeated_are_counted_once(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    doc = bar_doc("en", 2, prose=10)
    doc["cells"][1]["source"] += " " + "Each value here is read from the case on file. " * 120
    findings = bar_of(root, doc)
    assert any("explanatory prose words" in f for f in findings), findings
    assert any("sentences occur more than twice inside the notebook" in f for f in findings), findings
    para = bar_doc("en", 2, prose=10)
    para["cells"][1]["source"] += "\n\n" + "\n\n".join(["A paragraph of eleven words that comes back again and again."] * 60)
    assert any("sentences occur more than twice inside the notebook" in f for f in bar_of(root, para))


def test_nb4_only_declared_artifacts_are_committed_results_whatever_the_call_form(tmp_path: Path) -> None:
    """Residuals against measured data are the lesson; only a committed artifact of the product is a reproduction check."""
    root = review_root(tmp_path)
    cells = ("# import\nimport fakepkg", "# measurements\nobs = fakepkg.load_holdout(protocol='2012')", "# predict\npred = fakepkg.predict(obs)",
             "# residual\nresidual = obs - pred", "# bias\nbias = np.mean(pred - obs)", "# rmse\nrmse = np.sqrt(np.mean((pred - obs) ** 2))")
    assert not any("reproduction checks" in f for f in bar_of(root, bar_doc("en", 2, extra_code=cells)))
    for call in ("fakepkg.load_case('EX')", "fakepkg.load_case(name='EX')"):
        extra = ("# import\nimport fakepkg", f"# committed\nref = {call}", "# run\nsim = fakepkg.run(1)", "# check\nprint(sim - ref)",
                 "# check again\nprint(ref - sim)")
        assert any("reproduction checks" in f for f in bar_of(root, bar_doc("en", 2, extra_code=extra))), call


def test_n1_an_unconsumed_generator_and_utility_packages_earn_no_method_cell(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    cells = ("# import\nimport fakepkg", "# a generator nobody consumes\ng = (fakepkg.run(x) for x in [])")
    assert method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=cells)) == []
    assert "tqdm" not in CHECK.method_modules(root, {"packages": ["numpy==2.4.6", "tqdm==4.66.0"]}, 3, BAR)


def test_n3_the_answer_is_matched_by_magnitude_and_a_bare_exponent_is_no_answer() -> None:
    assert CHECK.answer_matches("It falls by 0.12 here.", "delta -0.12")[0]
    assert CHECK.answer_matches("2133 people at the peak.", "peak 2133.4")[0]
    assert not CHECK.answer_matches("About 1e2 cases.", "count 57")[0]
    assert not CHECK.answer_matches("It falls by +0.12 here.", "delta -0.12")[0]


def test_n4_a_head_and_a_display_of_what_was_read_are_input_output_cells(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    cells = ("# read\nd = pd.read_csv('../../../data/derived/x.csv')", "# look\nd.head()", "# look again\ndisplay(pd.DataFrame(d))",
             "# read more\ne = pd.read_csv('../../../data/derived/y.csv')", "# look\ne.tail()")
    assert any("setup and input/output cells" in f for f in bar_of(root, bar_doc("en", 2, extra_code=cells)))


def test_n5_an_input_check_and_a_selector_with_a_reduction_are_no_reproduction_checks(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    cells = ("# monotone time\nassert np.all(np.diff(t) > 0)", "# monotone again\nassert np.all(np.diff(u) > 0)",
             "# the peak\nidx = np.isclose(r, r.max()).argmax()", "# the peak again\njdx = np.isclose(q, q.max()).argmax()")
    assert not any("reproduction checks" in f for f in bar_of(root, bar_doc("en", 2, extra_code=cells)))


# ---------------------------------------------------------------- the second re-review (2026-10-27): R2-1, R2-2 and r1 to r4

def test_r21_a_short_sentence_repeated_is_counted_once_and_more_than_twice_is_a_finding(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    doc = bar_doc("en", 2, prose=10)
    doc["cells"][1]["source"] += " " + "The value is read. " * 200
    findings = bar_of(root, doc)
    assert any("explanatory prose words" in f for f in findings), findings
    assert any("sentences occur more than twice inside the notebook" in f for f in findings), findings
    twice = bar_doc("en", 2)
    twice["cells"][1]["source"] += " The value is read. The value is read."
    assert not any("occur more than twice" in f for f in bar_of(root, twice))
    thrice = bar_doc("en", 2)
    thrice["cells"][1]["source"] += " Look at this figure. Look at this figure. Look at this figure."
    assert any("occur more than twice" in f for f in bar_of(root, thrice))


def test_r22_the_return_value_of_a_function_and_a_container_method_earn_no_method_cell(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    run_once = ("# import\nimport fakepkg", "# one run\nres = fakepkg.simulate(p)", "# a list method\nprint(res.I.index(max(res.I)))",
                "# another\nprint(res.t.count(day))", "# another\nprint(res.t.count(night))", "# another\nprint(res.S.index(low))")
    assert len(method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=run_once))) == 1
    table = ("# import\nimport fakepkg", "# runs\nruns = {k: fakepkg.run(k) for k in ks}", *(f"# look\nprint(runs.get(k{n}))" for n in range(4)))
    assert len(method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=table))) == 1
    cls = ("# import\nimport fakepkg", "# build\nm = fakepkg.Model(k=3)", "# a dict method of the object\nprint(m.items(x))",
           "# a list method\nprint(m.index(x))", "# a real method\ny = m.predict(x)", "# a real method\nz = m.score(x, y)")
    assert len(method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=cls))) == 3
    factory = ("# import\nimport fakepkg", "# a classmethod factory\nm = fakepkg.Model.make(k=3)", "# predict\ny = m.predict(x)")
    assert len(method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=factory))) == 2


def test_r1_an_alias_made_by_assignment_is_followed_and_a_rebound_name_loses_its_alias(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    alias = ("# import\nimport fakepkg", "# the alias\nrun = fakepkg.run", *(f"# call\nv{n} = run(x{n})" for n in range(5)))
    assert len(method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=alias))) == 5
    rebound = ("# import\nimport fakepkg\nimport json", "# rebound\nfakepkg = json", *(f"# call\nv{n} = fakepkg.run(x{n})" for n in range(5)))
    assert method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=rebound)) == []


def test_r2_a_re_export_is_resolved_statically_from_the_package_or_from_the_map(tmp_path: Path) -> None:
    import copy
    # a package of the repository: its __init__ re-exports run from engine
    declared = review_root(tmp_path, declared={"method_entrypoints": ["mypkg.engine.run"]})
    (declared / "data-pipeline" / "mypkg").mkdir()
    (declared / "data-pipeline" / "mypkg" / "__init__.py").write_text("from .engine import run\n", encoding="utf-8")
    (declared / "data-pipeline" / "mypkg" / "engine.py").write_text("def run(x):\n    return x\n", encoding="utf-8")
    calls = tuple(f"# call\nfrom mypkg import run as r{n}\n\nv{n} = r{n}(x)" for n in range(5))
    assert len(method_cells_of(declared, bar_doc("en", 2, methods=0, extra_code=calls))) == 5
    reverse = review_root(tmp_path / "r", declared={"method_entrypoints": ["mypkg.run"]})
    (reverse / "data-pipeline" / "mypkg").mkdir()
    (reverse / "data-pipeline" / "mypkg" / "__init__.py").write_text("from .engine import run\n", encoding="utf-8")
    deep = tuple(f"# call\nfrom mypkg.engine import run as r{n}\n\nv{n} = r{n}(x)" for n in range(5))
    assert len(method_cells_of(reverse, bar_doc("en", 2, methods=0, extra_code=deep))) == 5
    # a package that is not in the repository: the static map of notebook_bar.json
    outside = review_root(tmp_path / "o", declared={"method_entrypoints": ["fakepkg.core.score"]})
    bar = copy.deepcopy(BAR)
    bar["reexports"] = {"fakepkg.score": "fakepkg.core.score"}
    shorts = ("# import\nimport fakepkg", *(f"# call\nv{n} = fakepkg.score(x{n})" for n in range(5)))
    doc = bar_doc("en", 2, methods=0, extra_code=shorts)
    assert method_cells_of(outside, doc) == []
    assert len(CHECK.Reading(doc, "en", outside, bar).method_cells) == 5


def test_r3_a_comprehension_over_an_empty_literal_never_runs(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    cells = ("# import\nimport fakepkg", *(f"# nothing\nys{n} = [fakepkg.run(x) for x in []]" for n in range(3)),
             "# nothing\nzs = {k: fakepkg.run(k) for k in ()}")
    assert method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=cells)) == []


# ---------------------------------------------------------------- the third re-review (2026-10-27): M3-1 to M3-3

def test_m31_a_heading_a_label_and_a_short_pointer_may_come_back(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    doc = bar_doc("en", 2)
    doc["cells"][1]["source"] += ("\n\n### What to look for\n\nA step.\n\n### What to look for\n\nA step.\n\n### What to look for\n\nA step."
                                  "\n\n- Units: days.\n- Units: days.\n- Units: days.\n\nSee the figure. See the figure. See the figure.")
    assert not any("occur more than twice" in f for f in bar_of(root, doc))
    four = bar_doc("en", 2)
    four["cells"][1]["source"] += " Look at this figure. Look at this figure. Look at this figure."
    assert any("occur more than twice" in f for f in bar_of(root, four))


def test_m32_a_declared_factory_builds_a_method_object(tmp_path: Path) -> None:
    cells = ("# import\nimport fakepkg", "# build\nmodel = fakepkg.make_model(k=3)", "# fit\nmodel.fit(x)", "# predict\ny = model.predict(x)",
             "# score\ns = model.score(x, y)", "# again\nt = model.score(y, x)")
    undeclared = review_root(tmp_path / "a")
    assert len(method_cells_of(undeclared, bar_doc("en", 2, methods=0, extra_code=cells))) == 1  # make_model is an entry point, its result is data
    declared = review_root(tmp_path / "b", declared={"method_factories": ["fakepkg.make_model"]})
    assert len(method_cells_of(declared, bar_doc("en", 2, methods=0, extra_code=cells))) == 5
    assert len(method_cells_of(declared, bar_doc("en", 2, methods=0, extra_code=cells[:2]))) == 1  # the factory call itself is a method call


def test_m33_a_method_of_an_attribute_of_the_object_is_not_a_method_of_the_object(tmp_path: Path) -> None:
    root = review_root(tmp_path)
    cells = ("# import\nimport fakepkg", "# build\nm = fakepkg.Model(k=3)", "# look\nprint(m.curve.mean(axis=ax))", "# look\nprint(m.weights.round(digits))",
             "# look\nprint(m.weights.round(places))", "# look\nprint(m.curve[0].sum(axis=ax))")
    assert len(method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=cells))) == 1
    chain = ("# import\nimport fakepkg", "# build\nm = fakepkg.Model(k=3)", "# fit and predict\ny = m.fit(x).predict(z)", "# a table item\narms = {'a': m}\nv = arms['a'].score(x, y)")
    assert len(method_cells_of(root, bar_doc("en", 2, methods=0, extra_code=chain))) == 2
