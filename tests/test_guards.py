"""The base guards fail on what they exist to catch, and pass on what they must allow (ADR-0078: the base validates
itself). Each test builds a throwaway tree, plants the case, and runs the real script on it."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
# instantiate.py runs only in the template, whose sentinel it deletes: in a product the test has nothing to run on
TEMPLATE_ONLY = pytest.mark.skipif(not (ROOT / ".template-source").exists(),
                                   reason="instantiate runs only in the template repository (.template-source)")


def _run(script: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, cwd=cwd)


def _put(root: Path, rel: str, doc) -> int:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    data = doc if isinstance(doc, str) else json.dumps(doc)
    p.write_bytes(data.encode("utf-8"))
    return p.stat().st_size


def _git_tree(tmp: Path) -> Path:
    tree = tmp / "tree"
    tree.mkdir()
    for i in range(10):
        _put(tree, f"filler{i}.txt", f"filler {i}\n")
    subprocess.run(["git", "init", "-q"], cwd=tree, check=True)
    return tree


REQ = """# Requirements: a unit not built yet

{status}

| ID | Requirement | Gate |
|---|---|---|
| UX-001 | THE unit SHALL do its job. | `tests/test_not_written_yet.py::test_its_job` |
"""


def test_doc_paths_skips_the_gates_of_planned_requirements_only(tmp_path):
    tree = _git_tree(tmp_path)
    _put(tree, "tests/test_exists.py", "def test_x():\n    pass\n")
    _put(tree, "docs/design/features/unit/requirements.md", REQ.format(status="Status: planned"))
    ok = _run("check_doc_paths.py", str(tree))
    assert ok.returncode == 0, ok.stdout
    _put(tree, "docs/design/features/unit/requirements.md", REQ.format(status="Status: live"))
    bad = _run("check_doc_paths.py", str(tree))
    assert bad.returncode == 1 and "names tests/test_not_written_yet.py" in bad.stdout
    # a planned file anywhere else is not exempt
    _put(tree, "docs/design/features/unit/requirements.md", REQ.format(status="Status: planned"))
    _put(tree, "docs/notes.md", "See `tests/test_missing.py`.\n\nStatus: planned\n")
    other = _run("check_doc_paths.py", str(tree))
    assert other.returncode == 1 and "docs/notes.md:1: names tests/test_missing.py" in other.stdout


def test_doc_paths_judge_the_repository_as_git_sees_it_never_the_disk(tmp_path):
    tree = _git_tree(tmp_path)
    _put(tree, ".gitignore", "web/out/\n")
    _put(tree, "web/index.md", "The site.\n")
    # an output the tools write, ignored on purpose and absent here, as on a fresh CI checkout: the guard used to
    # pass it only where the folder existed (CAOS_Contraste's frontend/gate-output/shots)
    _put(tree, "docs/a.md", "The gate writes its screenshots to `web/out/shots`; see [the folder](../web/out/).\n")
    ok = _run("check_doc_paths.py", str(tree))
    assert ok.returncode == 0, ok.stdout
    # neither in the repository nor ignored
    _put(tree, "docs/b.md", "Read `web/report.txt`.\n")
    bad = _run("check_doc_paths.py", str(tree))
    assert bad.returncode == 1 and "docs/b.md:1: names web/report.txt" in bad.stdout
    # a link that leaves the repository names nothing the repository holds
    _put(tree, "docs/b.md", "See [elsewhere](../../elsewhere.md).\n")
    away = _run("check_doc_paths.py", str(tree))
    assert away.returncode == 1 and "outside the repository" in away.stdout


def test_residue_marker_flags_the_placeholder_name_and_not_the_plugin_name():
    sys.path.insert(0, str(SCRIPTS))
    import check_template_residue as r

    marker = dict(r.MARKERS)["the placeholder product name"]
    assert marker.search('"name": "caos-product-frontend"')
    assert marker.search("npm run build in caos-product")
    assert marker.search('"name": "CAOS Product"')
    assert not marker.search("name: 'caos-product-html',")
    assert not marker.search('"name": "contraste-frontend"')


def test_residue_marker_flags_the_example_variants_and_not_a_hyphenated_id():
    sys.path.insert(0, str(SCRIPTS))
    import check_template_residue as r

    marker = dict(r.MARKERS)["the example immunisation variants"]
    assert marker.search("export const COVERAGE = [")
    assert marker.search("import { COVERAGE, type Selection } from './model';")
    assert marker.search("return COVERAGE.map((v) => ({ v }));")
    assert marker.search("the herd threshold is 1 - 1/R0")
    assert not marker.search('{"id": "F-SCALED-COVERAGE", "severity": "S3"}')
    assert not marker.search("COVERAGE-LEVELS")
    assert not marker.search("UNCONDITIONAL_COVERAGE = 0.99")


def test_residue_marker_flags_the_example_executive_view_and_not_a_product_own():
    sys.path.insert(0, str(SCRIPTS))
    import check_template_residue as r

    marker = dict(r.MARKERS)["the example executive view"]
    assert marker.search('"en": "Hospital capacity in respiratory seasons"')
    assert marker.search('"es": "Capacidad hospitalaria en las temporadas respiratorias"')
    assert marker.search("https://www.nao.org.uk/wp-content/uploads/2026/09/Managing-the-flow-of-patients-through-hospital-from-AE-Summary.pdf")
    assert not marker.search('"title": { "en": "Provisioning for commercial loans in Chile" }')


def test_residue_guard_scans_the_helper_scripts_and_skips_its_own_tests(tmp_path):
    tree = _git_tree(tmp_path)
    _put(tree, "scripts/precompute.ps1", "# E.g.:  ./scripts/precompute.ps1 EX02_epidemic --seed 7\n")
    _put(tree, "scripts/precompute.sh", "# the tiny teaching engine\n")
    # the guard's own tests must name the placeholder they look for
    _put(tree, "tests/test_guards.py", "assert marker.search('\"name\": \"caos-product-frontend\"')\n")
    res = _run("check_template_residue.py", str(tree))
    assert res.returncode == 1, res.stdout
    assert "scripts/precompute.ps1:1: an example case id" in res.stdout
    assert "scripts/precompute.sh:1: prose about the example engine" in res.stdout
    assert "tests/test_guards.py" not in res.stdout


def _instantiate_a_copy(tmp_path: Path) -> tuple[Path, subprocess.CompletedProcess]:
    """A copy of the template, instantiated with --no-run: the copy and the script's result."""
    copy = tmp_path / "product"
    ignore = shutil.ignore_patterns(".git", "node_modules", ".venv*", "dist", "public/data", "__pycache__",
                                    ".pytest_cache", ".ruff_cache", "gate-output")
    shutil.copytree(ROOT, copy, ignore=ignore)
    # the script resolves its root from its own location: run the COPY's script, never this repository's
    res = subprocess.run([sys.executable, str(copy / "scripts" / "instantiate.py"), "--slug", "probe", "--name", "Probe",
                          "--repo", "CAOS_Probe", "--deploy", "pages", "--visibility", "public", "--tagline-en",
                          "A probe.", "--tagline-es", "Una sonda.", "--no-run"], capture_output=True, text=True, cwd=copy)
    assert res.returncode == 0, res.stdout + res.stderr
    return copy, res


@TEMPLATE_ONLY
def test_adversarial_instantiate_removes_the_template_own_tests_and_says_so(tmp_path):
    """EX-015: tests/template/ holds the base guards' tests that need the example; a product has none of them."""
    assert (ROOT / "tests" / "template").is_dir(), "the template's own tests are the thing instantiate must remove"
    copy, res = _instantiate_a_copy(tmp_path)
    assert not (copy / "tests" / "template").exists()
    assert "removed tests/template" in res.stdout, res.stdout
    assert (copy / "tests" / "test_guards.py").is_file() and (copy / "tests" / "adversarial").is_dir()  # the rest stays
    # the template's CI runs the moved plants too; the product's workflow names no path that no longer exists
    assert "tests/template" in (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "tests/template" not in (copy / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    # no feature row names a test that is gone, so the product's SDD guard is green from the first run (a feature left with
    # no requirement is removed with them)
    named = [f.as_posix() for f in (copy / "docs" / "design" / "features").rglob("*.md") if "tests/template/" in f.read_text(encoding="utf-8")]
    assert named == [], named
    schema = ROOT / "frontend" / "node_modules" / "@fasl-work" / "caos-app-shell" / "src" / "content" / "executive.schema.json"
    if schema.is_file():  # check_sdd validates the executive view against the shell's schema, which npm ci installs
        (copy / schema.relative_to(ROOT)).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(schema, copy / schema.relative_to(ROOT))
        sdd = subprocess.run([sys.executable, str(copy / "scripts" / "check_sdd.py")], capture_output=True, text=True, cwd=copy)
        # from 0.13.000 the one thing a new product owes its SDD at once is the method tiers: the example claims nothing beyond the
        # state of the art, which holds only for the template (guide 09); every other check is green from the first run
        findings = [ln for ln in sdd.stdout.splitlines() if ln.startswith("  - ")]
        assert findings and all("method-tiers-and-manuscripts.md" in ln for ln in findings), sdd.stdout
        assert any("no beyond method" in ln for ln in findings) and any("None claimed" in ln for ln in findings), sdd.stdout


@TEMPLATE_ONLY
def test_instantiate_renames_the_lockfile_and_drops_the_template_guide(tmp_path):
    copy, _ = _instantiate_a_copy(tmp_path)
    lock = json.loads((copy / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["name"] == "probe-frontend" and lock["version"] == "0.1.0"
    assert lock["packages"][""]["name"] == "probe-frontend" and lock["packages"][""]["version"] == "0.1.0"
    assert "caos-product" not in (copy / "frontend" / "package-lock.json").read_text(encoding="utf-8")
    assert not (copy / "docs" / "guides" / "00_instantiate.md").exists()
    assert "00_instantiate" not in (copy / "docs" / "guides.md").read_text(encoding="utf-8")
    assert not (copy / ".template-source").exists()


def _template_only_offenders(tests_root: Path) -> list[str]:
    """Test functions that run instantiate.py or remove the template's sentinel without the TEMPLATE_ONLY marker. Such a
    test needs the template's own tree, so in every instantiated product it fails instead of skipping (BD-1: two did, found
    on CAOS_ChancaDEM's re-instantiation, 2026-10-26)."""
    import ast

    offenders: list[str] = []
    for path in sorted(tests_root.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            body = ast.unparse(node)
            runs_instantiate = "instantiate.py" in body and "subprocess" in body
            drops_sentinel = ".template-source" in body and ".unlink(" in body
            marked = any("TEMPLATE_ONLY" in ast.unparse(d) for d in node.decorator_list)
            if (runs_instantiate or drops_sentinel) and not marked:
                offenders.append(f"{path.relative_to(tests_root).as_posix()}::{node.name}")
    return offenders


def test_every_test_that_needs_the_template_tree_is_template_only():
    assert _template_only_offenders(ROOT / "tests") == []


def test_adversarial_an_unmarked_template_only_test_is_named(tmp_path):
    planted = tmp_path / "tests" / "test_planted.py"
    planted.parent.mkdir(parents=True)
    # the planted source is spelled in pieces, so this test's own body never holds the tokens the guard looks for
    script, sentinel, drop = "instan" + "tiate.py", ".template" + "-source", ".un" + "link("
    planted.write_text(
        "import subprocess, sys\n\n\ndef test_runs_it(tmp_path):\n"
        f"    subprocess.run([sys.executable, 'scripts/{script}', '--no-run'])\n\n\n"
        f"def test_drops_it(repo):\n    (repo / '{sentinel}'){drop})\n",
        encoding="utf-8",
    )
    assert _template_only_offenders(tmp_path / "tests") == ["test_planted.py::test_runs_it", "test_planted.py::test_drops_it"]


# What the content-based residue guard cannot see in a test: the example's rows, notebook paths and guide,
# named by id or path. Its own MARKERS (the model, the case ids, the references ...) are imported, never copied (BD-3).
EXAMPLE_NAMES = (
    ("an example requirement id", re.compile(r"\bEX-\d{3}\b")),
    ("an example notebook", re.compile(r"\b02-threshold-and-final-size\b|01-getting-started/0[12]-the-(?:problem-and-the-data|method-step-by-step)")),
    ("the template's own guide", re.compile(r"00_instantiate\.md")),
    ("the example catalog history row", re.compile(r"\|\s*surrogate-model\s*\|\s*1\.0\.0\s*\|\s*2026-10-11\s*\|")),
)
# a test module exercises a base guard or tool when it names one: a check_*.py script, the notebook runner, instantiate, the gate
BASE_TOOL = re.compile(r"\bcheck_[a-z_]+\b|\brun_notebooks\b|\binstantiate\.py\b|\bgate\.mjs\b")


def _example_bound_offenders(tests_root: Path) -> list[str]:
    """Test modules outside tests/template/ that exercise a base guard or tool AND hold a string the residue guard treats as
    example residue (its MARKERS, or one of EXAMPLE_NAMES). Such a module plants into or reads the template's example, so in a
    product that replaced the example it fails for that reason alone, and the product's residue guard lists it (BD-3: found on
    CAOS_ChancaDEM, 2026-10-27, 102 failures). The base guards are taken verbatim and tested in the template, so those tests
    belong in tests/template/, which instantiate.py removes. A module that builds a synthetic tree in tmp_path must not spell the
    example's names either (use a neutral name): the product's residue guard reads the module, not the tree it builds. This
    file is exempt like the residue guard's own SELF set, because it must name what it looks for."""
    sys.path.insert(0, str(SCRIPTS))
    import check_template_residue as r

    patterns = [*r.MARKERS, *EXAMPLE_NAMES]
    offenders: list[str] = []
    for path in sorted(tests_root.rglob("test_*.py")):
        rel = path.relative_to(tests_root).as_posix()
        if rel.startswith("template/") or f"tests/{rel}" in r.SELF:
            continue
        text = path.read_text(encoding="utf-8")
        if not BASE_TOOL.search(text):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            hit = next((name for name, pat in patterns if pat.search(line)), None)
            if hit:
                offenders.append(f"{rel}:{n}: {hit}")
                break
    return offenders


def test_no_example_bound_test_of_a_base_guard_is_left_outside_tests_template():
    assert _example_bound_offenders(ROOT / "tests") == []


def test_adversarial_an_example_bound_guard_test_outside_tests_template_is_named(tmp_path):
    tests = tmp_path / "tests"
    # the planted sources are spelled in pieces, so this file never holds the strings the guard looks for
    topic, nb = "01-getting" + "-started", "01-the-problem" + "-and-the-data.ipynb"
    planted = {
        "adversarial/test_planted_notebook.py": (
            "from planting import guard\n\n\ndef test_it(repo):\n"
            f"    edit(repo, 'notebooks/en/{topic}/{nb}', 'a', 'b')\n    guard(repo, 'check_notebooks.py')\n"),
        "test_planted_case.py": "import subprocess\n\n\ndef test_it():\n    subprocess.run(['check_artifacts.py', 'EX0" + "1_subcritical'])\n",
        "test_planted_row.py": "def test_it():\n    run('check_sdd.py', 'EX" + "-001')\n",
        # controls: the same strings in tests/template/, an example test that runs no guard, and a clean guard test
        "template/adversarial/test_kept.py": f"def test_it(repo):\n    guard(repo, 'check_notebooks.py', '{topic}')\n",
        "test_example_only.py": "def test_it():\n    assert precompute('EX0" + "2_epidemic')\n",
        "test_clean.py": "def test_it(tmp_path):\n    run('check_sdd.py', str(tmp_path))\n",
        # BD-4: a product names its own first topic and its own workbench feature, as ChancaDEM does
        "test_product_names.py": "def test_it(repo):\n    guard(repo, 'check_notebooks.py', 'notebooks/en/01-getting" + "-started/01-first-run.ipynb', 'docs/design/features/workbench')\n",
    }
    for rel, body in planted.items():
        (tests / rel).parent.mkdir(parents=True, exist_ok=True)
        (tests / rel).write_text(body, encoding="utf-8")
    found = _example_bound_offenders(tests)
    assert [f.split(":")[0] for f in found] == ["adversarial/test_planted_notebook.py", "test_planted_case.py", "test_planted_row.py"], found
    assert "an example notebook" in found[0] and "an example case id" in found[1] and "an example requirement id" in found[2]


def _version_tree(tmp: Path) -> Path:
    root = tmp / "repo"
    _put(root, "VERSION", "0.03.000\n")
    _put(root, "frontend/package.json", {"name": "p", "version": "0.3.0"})
    _put(root, "CHANGELOG.md", "# Changelog\n\n## [0.03.000] - 2026-10-07\n")
    return root


def test_version_guard_reads_code_not_history(tmp_path):
    """CAOS_PRODUCT_TEMPLATE#19: a version in a comment or a docstring is history and passes; one in code fails."""
    root = _version_tree(tmp_path)
    _put(root, "data-pipeline/pipeline/a.py", '"""Until 0.02.004 the guard read comments."""\n'
         "# measured at 0.01.000\nX = 1  # since 0.02.000\n")
    _put(root, "frontend/src/a.ts", "// until 0.02.003\n/* history: 0.01.000\n and 0.02.000 */\nexport const u = 'https://x.org/a'; // 0.02.001\n")
    # the documentation pages are prose: a release they cite is history
    _put(root, "frontend/src/pages/Implementation.tsx", "export const p = 'Measured at 0.02.000 between Windows and Linux.';\n")
    ok = _run("check_version_coherence.py", str(root))
    assert ok.returncode == 0, ok.stdout
    _put(root, "data-pipeline/pipeline/b.py", '__version__ = "0.02.004"\n')
    _put(root, "frontend/src/b.tsx", "export const v = '0.02.004';\n")
    bad = _run("check_version_coherence.py", str(root))
    assert bad.returncode == 1
    assert "data-pipeline/pipeline/b.py:1: a version literal in code" in bad.stdout
    assert "frontend/src/b.tsx:1: a version literal in code" in bad.stdout
    assert "a.py" not in bad.stdout and "a.ts" not in bad.stdout


def _web_tree(tmp: Path, pin: str, app_css: str) -> Path:
    root = tmp / "repo"
    shell = "frontend/node_modules/@fasl-work/caos-app-shell"
    _put(root, f"{shell}/styles.css", ":root { --color-fg: #000; }\n.chip { color: red; }\n.chip.on { color: blue; }\n.tablist { display: flex; }\n")
    _put(root, f"{shell}/chart.css", ".caos-chart { width: 100%; }\n")
    _put(root, f"{shell}/reserved-classes.json", {"components": ["caos-chart", "chip", "tablist"], "modifiers": ["on"], "classes": ["caos-chart", "chip", "on", "tablist"]})
    _put(root, f"{shell}/package.json", {"name": "@fasl-work/caos-app-shell", "version": "0.8.0"})
    _put(root, "frontend/package.json", {"name": "p", "version": "0.3.0", "dependencies": {"@fasl-work/caos-app-shell": pin}})
    _put(root, "frontend/src/app.css", app_css)
    _put(root, "frontend/src/main.tsx", "export const x = 1;\n")
    return root


def test_web_baseline_judges_the_subject_of_each_rule(tmp_path):
    """Shell 0.8.0: a modifier joined to the app's own class passes; a shell component or a lone modifier fails."""
    good = _web_tree(tmp_path / "a", "0.8.0", ".my-row.on { color: var(--color-fg); }\n.chip-host .my-label { color: red; }\n@media (max-width: 760px) { .my-row { display: none; } }\n")
    ok = _run("check_web_baseline.py", str(good))
    assert ok.returncode == 0, ok.stdout
    bad = _web_tree(tmp_path / "b", "0.8.0", ".my-panel .chip { color: red; }\n.on { color: blue; }\n@media (max-width: 760px) { .tablist { flex-wrap: wrap; } }\n")
    res = _run("check_web_baseline.py", str(bad))
    assert res.returncode == 1
    assert "restyles the shell component .chip" in res.stdout
    assert "styles the shell modifier .on on its own" in res.stdout
    assert "restyles the shell component .tablist" in res.stdout


def test_web_baseline_requires_an_exact_shell_pin(tmp_path):
    """CAOS_PRODUCT_TEMPLATE#19: a range lets an instantiated product float to a shell it never gated."""
    caret = _run("check_web_baseline.py", str(_web_tree(tmp_path / "a", "^0.8.0", ".my-row { color: red; }\n")))
    assert caret.returncode == 1 and "pin it exactly" in caret.stdout
    stale = _run("check_web_baseline.py", str(_web_tree(tmp_path / "b", "0.7.2", ".my-row { color: red; }\n")))
    assert stale.returncode == 1 and "the installed shell is 0.8.0, the pin is 0.7.2" in stale.stdout


def test_web_baseline_requires_the_stylesheet_of_every_shell_entry_it_imports(tmp_path):
    """CAOS_PRODUCT_TEMPLATE#22: a product drew the shell's chart without chart.css, and the chart had no height."""
    shell = "@fasl-work/caos-app-shell"
    bare = _web_tree(tmp_path / "a", "0.8.0", ".my-row { color: red; }\n")
    _put(bare, "frontend/src/main.tsx", f"import {{ AppShell }} from '{shell}';\nimport {{ UPlotChart }} from '{shell}/chart';\n")
    res = _run("check_web_baseline.py", str(bare))
    assert res.returncode == 1
    assert f"imports {shell} and never '{shell}/styles.css'" in res.stdout
    assert f"imports {shell}/chart and never '{shell}/chart.css'" in res.stdout
    styled = _web_tree(tmp_path / "b", "0.8.0", f"@import '{shell}/chart.css';\n.my-row {{ color: red; }}\n")
    _put(styled, "frontend/src/main.tsx", f"import {{ AppShell }} from '{shell}';\nimport '{shell}/styles.css';\n")
    _put(styled, "frontend/src/views.tsx", f"import {{ UPlotChart }} from '{shell}/chart';\n")
    ok = _run("check_web_baseline.py", str(styled))
    assert ok.returncode == 0, ok.stdout
    # the shell alone, with no chart entry, needs no chart stylesheet
    plain = _web_tree(tmp_path / "c", "0.8.0", ".my-row { color: red; }\n")
    _put(plain, "frontend/src/main.tsx", f"import {{ AppShell }} from '{shell}';\nimport '{shell}/styles.css';\n")
    assert _run("check_web_baseline.py", str(plain)).returncode == 0
