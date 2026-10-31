"""The internal-names gate (scripts/check_internal_names.py, template 0.14.000; CAOS_MANAGE
``conventions/method-tiers-and-manuscripts.md`` section 0): the tier names (classical, state of the art, beyond it, SOTA, BS-<n>)
sort the methods inside the programme and never reach a reader. Each test builds a throwaway tree, plants the names where a
reader sees them, and runs the real script on it; the clean tree is the control."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_internal_names.py"
RULE = "method-tiers-and-manuscripts.md section 0"


def notebook(cells: list[tuple[str, str]], title: str = "RK45 against the engine's Forward Euler", outputs: str = "") -> dict:
    out = []
    for kind, text in cells:
        cell = {"cell_type": kind, "metadata": {}, "source": text.splitlines(keepends=True)}
        if kind == "code":
            cell.update(execution_count=1, outputs=[{"output_type": "stream", "name": "stdout", "text": outputs}] if outputs else [])
        out.append(cell)
    return {"cells": out, "metadata": {"caos": {"language": "en", "level": 3, "title": title}}, "nbformat": 4, "nbformat_minor": 5}


CLEAN_CELLS = [
    ("markdown", "# How does RK45 compare with the engine?\n\n- **Level:** 3, comparison with published methods\n"),
    ("markdown", "## Comparison\n\nDormand and Prince (1980) built the pair behind RK45; SciPy runs it.\n"),
    ("code", "# solve the epidemic case with DOP853 as the truth\nresult = runs[\"sota\"]\nax.set_title(\"RK45 and Euler against DOP853\")\n"),
    ("markdown", "## References\n\n- A. Author (2020). A state-of-the-art review of ODE solvers. https://doi.org/10.1/x\n"),
]
TEX = ("\\documentclass{article}\n\\title{A learned breakage kernel for SAG mill power}\n\\begin{document}\n"
       "\\section{Related work}\nBond's work index and Morrell's SMC model predict the power.\n"
       "\\section{Method}\nThe proposed method couples a discrete element model with a learned kernel.\n"
       "\\begin{thebibliography}{9}\n\\bibitem{a} A. Author, A state-of-the-art review, 2020.\n\\end{thebibliography}\n"
       "\\end{document}\n")


def tree(tmp: Path, *, cells=None, title=None, outputs="", tex=TEX, files: dict[str, str] | None = None,
         manuscript_title="A detailed technical report on mill power") -> Path:
    nb = tmp / "notebooks" / "en" / "01-topic"
    nb.mkdir(parents=True)
    doc = notebook(cells if cells is not None else CLEAN_CELLS, **({"title": title} if title else {}), outputs=outputs)
    (nb / "03-rk45.ipynb").write_text(json.dumps(doc), encoding="utf-8")
    (tmp / "notebooks" / "en" / "README.md").write_text(
        "# Notebooks\n\nLevels: 1 fundamentals, 2 the method in practice, 3 comparison with published methods, 4 proposed methods.\n",
        encoding="utf-8")
    (tmp / "manuscripts" / "report").mkdir(parents=True)
    (tmp / "manuscripts" / "report" / "main.tex").write_text(tex, encoding="utf-8")
    (tmp / "product.json").write_text(json.dumps({"manuscripts": [{"kind": "technical-report", "title": manuscript_title}]}),
                                      encoding="utf-8")
    (tmp / "README.md").write_text("# P\n\nA product that compares RK45 with Forward Euler.\n", encoding="utf-8")
    (tmp / "content").mkdir()
    (tmp / "content" / "executive.json").write_text(json.dumps({"situation": {"state_of_the_art": [
        {"title": "Embedded Runge-Kutta pairs", "body": "Adaptive steps from a local error estimate.", "tier": "sota"}]}}),
        encoding="utf-8")
    (tmp / "frontend" / "src" / "pages").mkdir(parents=True)
    (tmp / "frontend" / "src" / "pages" / "Methodology.tsx").write_text(
        "// the state of the art is RK45 (a comment is code, not text)\n"
        "export const title = t('Runge-Kutta solvers', 'Resolvedores de Runge-Kutta');\nconst kind = 'sota';\n",
        encoding="utf-8")
    for name, text in (files or {}).items():
        (tmp / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp / name).write_text(text, encoding="utf-8")
    return tmp


def run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, encoding="utf-8", errors="replace")


def fails(r: subprocess.CompletedProcess, *needles: str) -> bool:
    return r.returncode == 1 and all(n in r.stdout for n in needles) and RULE in r.stdout


def test_a_product_that_names_its_methods_passes(tmp_path):
    r = run(tree(tmp_path))
    assert r.returncode == 0, r.stdout


def test_the_template_passes():
    r = run(ROOT)
    assert r.returncode == 0, r.stdout


def test_adversarial_a_notebook_heading_or_title_with_a_tier_name_fails(tmp_path):
    for i, heading in enumerate(("## State of the art", "## Estado del arte", "## Beyond the state of the art",
                                 "## Más allá del estado del arte", "## Beyond-SOTA results", "### Classical approach",
                                 "## The three tiers")):
        cells = [CLEAN_CELLS[0], ("markdown", f"{heading}\n\nRK45 against Euler.\n")]
        assert fails(run(tree(tmp_path / str(i), cells=cells)), "03-rk45.ipynb", "cell 2, line 1"), heading
    assert fails(run(tree(tmp_path / "t", title="Classical solvers and RK45")), "caos.title", "classical")


def test_adversarial_a_tier_name_in_notebook_prose_code_or_output_fails(tmp_path):
    planted = {
        "prose": [("markdown", "## Method\n\nWe run the state-of-the-art solver on the epidemic.\n")],
        "wrapped": [("markdown", "## Method\n\nWe run the state of the\nart solver on the epidemic.\n")],
        "no article": [("markdown", "## Method\n\nWe run the state of art solver on the epidemic.\n")],
        "comment": [("code", "# run the SOTA solver\nx = 1\n")],
        "label": [("code", "ax.plot(t, y, label=\"SOTA\")\n")],
        "claim id": [("code", "print(gain)\n")],
    }
    for i, (what, cells) in enumerate(planted.items()):
        outputs = "BS-1 halves the error\n" if what == "claim id" else ""
        assert fails(run(tree(tmp_path / str(i), cells=cells, outputs=outputs)), "03-rk45.ipynb"), what


def test_adversarial_a_file_or_folder_named_by_a_tier_fails(tmp_path):
    clean = json.dumps(notebook(CLEAN_CELLS))
    for i, name in enumerate(('notebooks/en/01-topic/04-state-of-the-art-comparison.ipynb',
                              'notebooks/en/01-topic/05-state-of-art-sliding-window.ipynb',
                              'notebooks/en/02-sota-solvers/01-rk45.ipynb',
                              'notebooks/es/01-topic/06-classical-methods.ipynb')):
        assert fails(run(tree(tmp_path / str(i), files={name: clean})), name, 'file name'), name
    assert fails(run(tree(tmp_path / 'm', files={'manuscripts/beyond-sota-note/notes.md': '# Note\n'})), 'file name')
    assert run(tree(tmp_path / 'ok', files={'notebooks/en/01-topic/04-rk45-against-the-engine.ipynb': clean})).returncode == 0


def test_adversarial_a_cited_title_in_references_a_key_string_a_fence_and_a_marked_line_pass(tmp_path):
    cells = CLEAN_CELLS + [
        ("markdown", "## Results\n\nIn the classical limit the scheme is Euler's.\n\n```bash\npip install sota-tools==1.0\n```\n"),
        ("markdown", "## Classical mechanics <!-- internal-name-ok -->\n\nNewton's laws.\n"),
    ]
    r = run(tree(tmp_path, cells=cells))
    assert r.returncode == 0, r.stdout


def test_adversarial_a_manuscript_with_a_tier_name_fails(tmp_path):
    planted = {
        "section": TEX.replace("\\section{Related work}", "\\section{State of the art}"),
        "caption": TEX.replace("\\end{document}", "\\caption{Classical against measured power}\n\\end{document}"),
        "title": TEX.replace("A learned breakage kernel", "Beyond SOTA: a learned breakage kernel"),
        "wrapped": TEX.replace("predict the power.", "are the state of the\nart in mill power."),
        "claim id": TEX.replace("The proposed method", "BS-1, the proposed method,"),
    }
    for i, (what, tex) in enumerate(planted.items()):
        assert fails(run(tree(tmp_path / str(i), tex=tex)), "manuscripts/report/main.tex"), what
    figures = {"manuscripts/report/fig.svg": "<svg><text x=\"1\">Classical vs SOTA</text></svg>\n",
               "manuscripts/report/make_figs.py": "ax.set_title('Beyond the state of the art')\n",
               "manuscripts/report/notes.md": "# Report\n\n## Classical methods\n\nBond.\n"}
    for i, (name, text) in enumerate(figures.items()):
        assert fails(run(tree(tmp_path / f"f{i}", files={name: text})), name), name


def test_adversarial_an_index_the_readme_or_a_manuscript_title_with_a_tier_name_fails(tmp_path):
    index = {"notebooks/en/README.md": "# Notebooks\n\nLevels: 1 fundamentals, 2 the method, 3 state of the art.\n"}
    assert fails(run(tree(tmp_path / "i", files=index)), "notebooks/en/README.md", "state of the art")
    readme = {"README.md": "# P\n\n## Beyond the state of the art\n\nOur method.\n"}
    assert fails(run(tree(tmp_path / "r", files=readme)), "README.md")
    assert fails(run(tree(tmp_path / "m", manuscript_title="Classical, SOTA and proposed methods for mill power")),
                 "product.json", "manuscripts[0].title")
    refs = {"README.md": "# P\n\nRK45.\n\n## References\n\n- A state-of-the-art review of solvers (2020).\n"}
    assert run(tree(tmp_path / "ok", files=refs)).returncode == 0


def test_adversarial_an_app_string_with_a_tier_name_fails(tmp_path):
    content = {"content/executive.json": json.dumps({"situation": {"approaches": [{"title": "Classical approach"}]}})}
    assert fails(run(tree(tmp_path / "c", files=content)), "content/executive.json", "classical approach")
    tab = {"content/pages.json": json.dumps({"tabs": [{"label": "Classical"}], "body": "plain"})}
    assert fails(run(tree(tmp_path / "l", files=tab)), "content/pages.json", "classical")
    tsx = {"frontend/src/pages/Benchmark.tsx": "const a = t('State of the art', 'Estado del arte');\n",
           "frontend/src/pages/Results.tsx": "export const B = () => <h2>Beyond SOTA</h2>;\n"}
    for i, (name, text) in enumerate(tsx.items()):
        assert fails(run(tree(tmp_path / f"x{i}", files={name: text})), name), name
    multi = {"frontend/src/pages/Tiers.tsx": "export const C = () => (\n  <p>\n    The state of the\n    art solver.\n  </p>\n);\n"}
    assert fails(run(tree(tmp_path / "j", files=multi)), "frontend/src/pages/Tiers.tsx: line 3"), multi
    locale = {"frontend/src/i18n/en.json": json.dumps({"nav": {"title": "Beyond SOTA"}})}
    assert fails(run(tree(tmp_path / "n", files=locale)), "frontend/src/i18n/en.json"), locale
    marked = {"frontend/src/pages/Note.tsx": "const a = 'the SOTA dataset'; // internal-name-ok a dataset's own name\n"}
    assert run(tree(tmp_path / "k", files=marked)).returncode == 0
    tests = {"frontend/src/pages/Benchmark.test.tsx": "it('shows no state of the art', () => {});\n"}
    assert run(tree(tmp_path / "t", files=tests)).returncode == 0
