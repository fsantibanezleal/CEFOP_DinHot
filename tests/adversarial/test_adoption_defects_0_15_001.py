"""Plants of the defects that CAOS_ChancaDEM's adoption of template 0.15.000 exposed (issue #102, with #101): each test plants
the defect in a throwaway copy and runs the real guard, the real runner or the real helper, so the fix is caught the day it
regresses. Product-agnostic: every test reads the product it runs in (its own SDD, catalog, workflow and committed bake) or a
planted tree, never the template's example.

- story routes declared by the product (``product.json`` ``showcase.story_routes``), read by the gate runner and the SDD guard;
- stage admission: the readiness provider and the engine come from the product checkout, the stage is only judged;
- prose ``<`` in Markdown is text, not markup, on every Python release;
- the residue guard and the base EARS rows;
- the dependency copy budget of the codegen plant;
- the doc-path guard and the destinations a blueprint names;
- the internal-names guard and the ids of the SDD's Method ladder (#101)."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import planting
import pytest
from planting import ROOT, add_schema, guard, make_tree

NODE = shutil.which("node")
DOC_ROUTES = ["/app", "/introduction", "/methodology", "/implementation", "/experiments", "/benchmark"]
GATE_INPUTS = ("frontend/scripts", "product.json", "deploy/TARGET", "docs/design/SDD.md")


def load_script(name: str):
    """A guard script of this repository as a module (the guards are standard-library scripts, not a package)."""
    spec = importlib.util.spec_from_file_location(f"_plant_{name}", ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def set_product(repo: Path, **fields: object) -> dict:
    path = repo / "product.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    for key, value in fields.items():
        if value is None:
            doc.pop(key, None)
        else:
            doc[key] = value
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc


def git_init(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)


# ---------------------------------------------------------------- BD-8: the story routes come from product.json

def run_gate(repo: Path, *extra: str) -> tuple[subprocess.CompletedProcess, list[str] | None]:
    """The copy's gate runner against a stub shell gate that records its arguments (None: the stub never ran)."""
    frontend = repo / "frontend"
    shell = frontend / "node_modules" / "@fasl-work" / "caos-app-shell"
    (shell / "bin").mkdir(parents=True, exist_ok=True)
    (shell / "package.json").write_text('{"name":"@fasl-work/caos-app-shell","version":"0.0.0"}', encoding="utf-8")
    (shell / "bin" / "caos-shell-gate.mjs").write_text(
        "import { writeFileSync } from 'node:fs';\nwriteFileSync(process.env.STUB_OUT, JSON.stringify(process.argv.slice(2)));\n",
        encoding="utf-8")
    out = repo / "stub-args.json"
    out.unlink(missing_ok=True)
    r = subprocess.run([NODE, str(frontend / "scripts" / "gate.mjs"), *extra], capture_output=True, encoding="utf-8",
                       errors="replace", cwd=frontend, env={**os.environ, "STUB_OUT": str(out)}, timeout=60)
    return r, (json.loads(out.read_text(encoding="utf-8")) if out.is_file() else None)


def routes_of(args: list[str]) -> list[str]:
    return args[args.index("--routes") + 1].split(",")


OTHER_STORY = ["/story/measure", "/story/look-inside", "/story/solve", "/story/compare", "/story/operate"]


@pytest.mark.skipif(NODE is None, reason="needs node")
def test_the_runner_walks_exactly_the_story_routes_the_product_declares(tmp_path: Path) -> None:
    repo = make_tree(tmp_path / "repo", *GATE_INPUTS)
    set_product(repo, showcase={"story_routes": OTHER_STORY})
    r, args = run_gate(repo)
    assert r.returncode == 0 and args is not None, r.stderr
    assert routes_of(args) == DOC_ROUTES + OTHER_STORY, args
    assert "--require-showcase" in args
    # the product's own steps given back to --routes are accepted (the ChancaDEM refusal of 0.15.000)
    r, args = run_gate(repo, "--routes", ",".join(DOC_ROUTES + OTHER_STORY[::-1]))
    assert r.returncode == 0 and args is not None, r.stderr


@pytest.mark.skipif(NODE is None, reason="needs node")
@pytest.mark.parametrize("undeclared", ["/story/context", "/story/extra", "/extra"])
def test_adversarial_an_undeclared_route_given_to_routes_is_refused(tmp_path: Path, undeclared: str) -> None:
    repo = make_tree(tmp_path / "repo", *GATE_INPUTS)
    set_product(repo, showcase={"story_routes": OTHER_STORY})
    r, args = run_gate(repo, "--routes", ",".join(DOC_ROUTES + OTHER_STORY + [undeclared]))
    assert r.returncode != 0 and args is None, (r.stdout, r.stderr)
    assert undeclared in r.stderr and "showcase.story_routes" in r.stderr, r.stderr


@pytest.mark.skipif(NODE is None, reason="needs node")
def test_adversarial_a_route_list_that_leaves_out_a_declared_story_step_is_still_refused(tmp_path: Path) -> None:
    repo = make_tree(tmp_path / "repo", *GATE_INPUTS)
    set_product(repo, showcase={"story_routes": OTHER_STORY})
    r, args = run_gate(repo, "--routes", ",".join(DOC_ROUTES + OTHER_STORY[:-1]))
    assert r.returncode != 0 and args is None
    assert "/story/operate" in r.stderr and "ADR-0082" in r.stderr, r.stderr


@pytest.mark.skipif(NODE is None, reason="needs node")
def test_a_product_without_a_story_is_measured_on_the_app_and_the_documentation_and_told_so(tmp_path: Path) -> None:
    repo = make_tree(tmp_path / "repo", *GATE_INPUTS)
    set_product(repo, showcase=None)
    r, args = run_gate(repo)
    assert r.returncode == 0 and args is not None, r.stderr
    assert routes_of(args) == DOC_ROUTES, args
    assert "no story" in (r.stdout + r.stderr) and "showcase.story_routes" in (r.stdout + r.stderr)
    # the requirement stays: the shell's G21 still runs and fails a product without a story; the runner never drops it
    assert "--require-showcase" in args


@pytest.mark.skipif(NODE is None, reason="needs node")
@pytest.mark.parametrize("declared", [
    "/story/context",                                  # not a list
    ["/story/a", "/story/a", "/story/b"],              # a duplicate
    ["/story/a", "/app", "/story/b"],                  # not a story route
    ["/story/a", "story/b", "/story/c"],               # not a path
    ["/story/a", "/story/b/c", "/story/d"],            # not one step
    ["/story/a", 3, "/story/c"],                       # not a string
])
def test_adversarial_a_malformed_story_declaration_is_refused(tmp_path: Path, declared: object) -> None:
    repo = make_tree(tmp_path / "repo", *GATE_INPUTS)
    set_product(repo, showcase={"story_routes": declared})
    r, args = run_gate(repo)
    assert r.returncode != 0 and args is None, (declared, r.stdout, r.stderr)
    assert "showcase.story_routes" in r.stderr, r.stderr


@pytest.mark.skipif(NODE is None, reason="needs node")
def test_the_runner_prints_its_plan_and_with_plan_never_runs_the_shell_gate(tmp_path: Path) -> None:
    repo = make_tree(tmp_path / "repo", *GATE_INPUTS)
    set_product(repo, showcase={"story_routes": OTHER_STORY[:3]})
    r, args = run_gate(repo, "--plan")
    assert r.returncode == 0 and args is None, (r.stdout, r.stderr)
    assert f"gate: routes {','.join(DOC_ROUTES + OTHER_STORY[:3])}" in r.stdout, r.stdout


def test_adversarial_no_story_route_is_written_in_the_base_runner_or_story_check() -> None:
    """A route list in the runner is the BD-8 defect; an example assertion in the story check is the same defect one file over."""
    for rel in ("frontend/scripts/gate.mjs", "frontend/scripts/check_story_mode.mjs"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "/story/" not in text.replace("'/story/'", "").replace("/story/<step>", ""), rel
        assert "story_routes" in text, f"{rel} does not read product.json showcase.story_routes"
    story = (ROOT / "frontend/scripts/check_story_mode.mjs").read_text(encoding="utf-8")
    for example in ("EX0", "data-system-diagram", "data-phase-plane", "Euler", "Attack rate", "template-story", "case="):
        assert example not in story, f"check_story_mode.mjs holds the example's {example!r}"


SDD_INPUTS = ("scripts/*.py", "docs/design", "tests", "data", "frontend/src/**/*.test.ts", "frontend/src/**/*.test.tsx",
              "frontend/scripts", "requirements*.txt", "data-pipeline/requirements.txt", "content", "frontend/public/executive",
              "product.json", "deploy/TARGET", ".template-source")


@pytest.fixture
def sdd_tree(tmp_path: Path) -> Path:
    return add_schema(make_tree(tmp_path / "repo", *SDD_INPUTS))


def story_findings(repo: Path) -> list[str]:
    r = guard(repo, "check_sdd.py")
    return [ln for ln in r.stdout.splitlines() if "story_routes" in ln]


def test_the_sdd_guard_reads_the_products_story_declaration(sdd_tree: Path) -> None:
    assert story_findings(sdd_tree) == []
    set_product(sdd_tree, showcase={"story_routes": OTHER_STORY})
    assert story_findings(sdd_tree) == []


@pytest.mark.parametrize("declared", [None, {}, {"story_routes": []}, {"story_routes": ["/story/a", "/story/b"]},
                                      {"story_routes": [f"/story/s{i}" for i in range(7)]},
                                      {"story_routes": ["/story/a", "/story/a", "/story/b"]},
                                      {"story_routes": ["/story/a", "/introduction", "/story/b"]}])
def test_adversarial_a_missing_or_invalid_story_fails_the_sdd_guard(sdd_tree: Path, declared: object) -> None:
    """ADR-0082: every App has a guided story of 3 to 6 directly addressable steps; its absence fails here, not in the runner."""
    set_product(sdd_tree, showcase=declared)
    found = story_findings(sdd_tree)
    assert found and all("ADR-0082" in ln for ln in found), (declared, found)


# ---------------------------------------------------------------- BD-2 (#91): stage admission

def stage_of(root: Path, stage: Path) -> Path:
    """What 02_generate-data stages and admits: the metadata it copies (VERSION, the contracts, product.json, the API
    document, the declared authored inputs) and the promoted payload, taken from the product's committed bake."""
    config = json.loads((root / "scripts/local/workflow.json").read_text(encoding="utf-8"))
    stage.mkdir(parents=True)
    shutil.copy2(root / "VERSION", stage / "VERSION")
    shutil.copytree(root / "docs/contracts", stage / "docs/contracts")
    for name in ["product.json", "app/openapi.json", *config.get("stage_inputs", [])]:
        if (root / name).is_file():
            (stage / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / name, stage / name)
    for name in config["promote"]:
        if (root / name).is_dir():
            shutil.copytree(root / name, stage / name)
    return stage


def readiness(script_root: Path, judged: Path | None = None) -> subprocess.CompletedProcess:
    args = [str(judged)] if judged is not None else []
    return subprocess.run([sys.executable, str(script_root / "scripts/check_readiness.py"), *args], capture_output=True,
                          text=True, cwd=script_root, timeout=120)


def test_the_products_checker_admits_a_stage_of_its_committed_bake(tmp_path: Path) -> None:
    """The stage holds no scripts/ and no pipeline: the checker that runs (the product's) judges it with its own provider."""
    shipped = readiness(ROOT)
    assert shipped.returncode == 0, shipped.stdout + shipped.stderr
    stage = stage_of(ROOT, tmp_path / "external stage")
    assert not (stage / "scripts").exists() and not (stage / "data-pipeline").exists()
    judged = readiness(ROOT, stage)
    assert judged.returncode == 0 and judged.stdout.startswith("readiness: current"), judged.stdout + judged.stderr
    assert "No module named" not in judged.stdout


def product_with_provider(root: Path, code: str | None) -> Path:
    (root / "scripts/local").mkdir(parents=True)
    shutil.copy2(ROOT / "scripts/check_readiness.py", root / "scripts/check_readiness.py")
    config = {"readiness_provider": "scripts/local/provider.py"} if code is not None else {}
    (root / "scripts/local/workflow.json").write_text(json.dumps(config), encoding="utf-8")
    if code is not None:
        (root / "scripts/local/provider.py").write_text(code, encoding="utf-8")
    return root


JUDGE = ("def validate(root):\n"
         "    assert not (root / 'scripts').exists(), 'the provider was handed the product, not the stage'\n"
         "    assert (root / 'data/derived/payload.json').is_file(), 'missing complete payload'\n")


def test_a_declared_provider_comes_from_the_product_and_judges_the_stage(tmp_path: Path) -> None:
    product = product_with_provider(tmp_path / "product", JUDGE)
    stage = tmp_path / "stage"
    (stage / "data/derived").mkdir(parents=True)
    (stage / "data/derived/payload.json").write_text("{}", encoding="utf-8")
    r = readiness(product, stage)
    assert r.returncode == 0 and "declared product provider" in r.stdout, r.stdout + r.stderr
    (stage / "data/derived/payload.json").unlink()
    r = readiness(product, stage)
    assert r.returncode == 1 and "missing complete payload" in r.stdout, r.stdout + r.stderr
    assert "Traceback" not in r.stderr


def test_adversarial_a_stage_cannot_bring_its_own_provider_or_engine(tmp_path: Path) -> None:
    """The judged root is data: a provider or a pipeline package planted in it is never loaded."""
    product = product_with_provider(tmp_path / "product", None)
    stage = tmp_path / "stage"
    (stage / "scripts/local").mkdir(parents=True)
    (stage / "scripts/local/workflow.json").write_text(json.dumps({"readiness_provider": "scripts/local/provider.py"}),
                                                       encoding="utf-8")
    (stage / "scripts/local/provider.py").write_text("def validate(root):\n    return True\n", encoding="utf-8")
    (stage / "data-pipeline/pipeline/core").mkdir(parents=True)
    for init in ("data-pipeline/pipeline/__init__.py", "data-pipeline/pipeline/core/__init__.py"):
        (stage / init).write_text("", encoding="utf-8")
    (stage / "data-pipeline/pipeline/core/readiness.py").write_text(
        "def compute(**kw):\n    raise SystemExit(0)\n", encoding="utf-8")
    r = readiness(product, stage)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "declared product provider" not in r.stdout and "readiness: current" not in r.stdout, r.stdout


# ---------------------------------------------------------------- BD-3: prose `<` is text on every Python release

LADDER_SDD = ("# SDD\n\n## Visualization catalog\n\n| id | question |\n|---|---|\n"
              "| V5 | The Neumann series p_n = (I - C) sum_{k<n} (B C)^k f, with i<j and x <y |\n\n"
              "## Method ladder\n\n| id | tier | method | acceptance criterion | gate |\n|---|---|---|---|---|\n"
              "| M-1 | classical | A method | It converges | `tests/test_a.py` |\n"
              "| B-lin | sota | Another method | It agrees | `tests/test_b.py` |\n")


def test_prose_less_than_is_text_and_never_reaches_the_html_parser(monkeypatch) -> None:
    """Python 3.12.11+ hides everything after `<n}` (an unterminated 'tag'); the reader must not depend on how a release's
    HTMLParser treats text that is not a tag: only real tags (CommonMark raw HTML) are fed to it."""
    structural = load_script("check_notebooks")
    fed: list[str] = []
    original = structural._VisibleHTML.feed
    monkeypatch.setattr(structural._VisibleHTML, "feed", lambda self, data: (fed.append(data), original(self, data))[1])
    out = structural.visible_markdown(LADDER_SDD)
    assert "## Method ladder" in out and "| B-lin |" in out and "sum_{k<n}" in out and "i<j" in out and "x <y" in out, out
    assert fed and not any(s in "".join(fed) for s in ("<n}", "<j ", "<y ")), fed


@pytest.mark.parametrize("hidden", ["<div hidden>SECRET</div>", "<span style='display:none'>SECRET</span>",
                                    "<template>SECRET</template>", "<!-- SECRET -->", "<script>SECRET</script>",
                                    "<div hidden>SECRET"])
def test_adversarial_real_hidden_markup_still_earns_nothing(hidden: str) -> None:
    structural = load_script("check_notebooks")
    out = structural.visible_markdown("before k<n} " + hidden + " after\n")
    assert "SECRET" not in out and "before k<n}" in out, out


def test_the_ladder_below_a_prose_less_than_is_read_by_the_content_bar(tmp_path: Path) -> None:
    depth = load_script("check_notebook_depth")
    sdd = tmp_path / "docs/design/SDD.md"
    sdd.parent.mkdir(parents=True)
    sdd.write_text(LADDER_SDD, encoding="utf-8")
    findings: list[str] = []
    assert depth.inventory_table(sdd, "method ladder", "tier", findings, tmp_path) == {"M-1", "B-lin"}
    assert findings == []


# ---------------------------------------------------------------- BD-4: the base EARS rows are not example residue

def residue_tree(repo: Path) -> Path:
    """A product tree the residue guard scans: ten neutral files besides what a test plants, and a git repository."""
    for i in range(10):
        (repo / f"filler{i}.txt").write_text(f"filler {i}\n", encoding="utf-8")
    git_init(repo)
    return repo


def test_the_base_feature_rows_are_not_example_residue(tmp_path: Path) -> None:
    repo = residue_tree(make_tree(tmp_path / "repo", "scripts/check_template_residue.py", "docs/design/features/notebooks"))
    r = guard(repo, "check_template_residue.py")
    assert "files to scan" not in r.stdout, r.stdout  # the guard scanned the tree
    assert "immunisation variants" not in r.stdout, r.stdout


def test_adversarial_the_example_constant_is_still_residue(tmp_path: Path) -> None:
    repo = make_tree(tmp_path / "repo", "scripts/check_template_residue.py")
    (repo / "frontend/src").mkdir(parents=True)
    constant = "COVER" + "AGE"  # assembled, so this test file is not itself example residue
    (repo / "frontend/src/model.ts").write_text(f"export const {constant} = [0, 0.3, 0.6];\n", encoding="utf-8")
    residue_tree(repo)
    r = guard(repo, "check_template_residue.py")
    assert r.returncode == 1 and "immunisation variants" in r.stdout and "frontend/src/model.ts" in r.stdout, r.stdout


# ---------------------------------------------------------------- BD-6: the dependency copy budget follows the install

def fake_install(base: Path, *, size: int, extra_installed: str | None = None) -> Path:
    """A frontend whose node_modules is one package of ``size`` bytes, installed from its lock."""
    frontend = base / "frontend"
    package = frontend / "node_modules" / "heavy-runtime"
    package.mkdir(parents=True)
    with open(package / "runtime.wasm", "wb") as f:
        f.truncate(size)
    (package / "package.json").write_text('{"name":"heavy-runtime","version":"1.0.0"}', encoding="utf-8")
    locked = {"": {"name": "p"}, "node_modules/heavy-runtime": {"version": "1.0.0"}}
    (frontend / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": locked}), encoding="utf-8")
    installed = {"node_modules/heavy-runtime": {"version": "1.0.0"}}
    if extra_installed:
        installed[extra_installed] = {"version": "9.9.9"}
    (frontend / "node_modules" / ".package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": installed}),
                                                                  encoding="utf-8")
    return frontend / "node_modules"


def test_an_install_heavier_than_the_old_fixed_budget_is_copied(tmp_path: Path, monkeypatch) -> None:
    """ChancaDEM's install is 337 MB (onnxruntime-web): the copy is bounded by the drive, not by a number of the template's."""
    monkeypatch.setattr(planting, "NODE_MODULES", fake_install(tmp_path / "source", size=257 * 1024 * 1024))
    dest = tmp_path / "plant" / "frontend"
    dest.mkdir(parents=True)
    planting.copy_node_modules(dest)
    assert (dest / "node_modules/heavy-runtime/runtime.wasm").stat().st_size == 257 * 1024 * 1024


def test_adversarial_a_copy_the_drive_cannot_hold_is_refused(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(planting, "NODE_MODULES", fake_install(tmp_path / "source", size=1024))
    usage = shutil.disk_usage(tmp_path)
    # a drive with 2 GiB and 512 bytes free cannot take a 1 KiB copy and keep its 2 GiB floor
    monkeypatch.setattr(planting.shutil, "disk_usage", lambda _p: usage._replace(free=2 * 1024 ** 3 + 512))
    dest = tmp_path / "plant" / "frontend"
    dest.mkdir(parents=True)
    with pytest.raises(AssertionError, match="copy budget"):
        planting.copy_node_modules(dest)
    assert not (dest / "node_modules").exists()


def test_adversarial_an_install_that_is_not_the_lock_is_refused(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(planting, "NODE_MODULES", fake_install(tmp_path / "source", size=1024,
                                                               extra_installed="node_modules/unlocked"))
    dest = tmp_path / "plant" / "frontend"
    dest.mkdir(parents=True)
    with pytest.raises(AssertionError, match="lock"):
        planting.copy_node_modules(dest)
    assert not (dest / "node_modules").exists()


# ---------------------------------------------------------------- BD-7: a blueprint's destinations are not repository paths

def doc_paths_tree(tmp_path: Path) -> Path:
    # the blueprint README as it stands, with the files its links name (the fixture README as a plain stand-in: its own links
    # are not under test here)
    repo = make_tree(tmp_path / "repo", "scripts/check_doc_paths.py", "templates/manuscripts/README.md",
                     "templates/manuscripts/provenance.json")
    fixture = repo / "tests/fixtures/manuscript-depth/README.md"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("# Historical manuscript examples\n", encoding="utf-8")
    (repo / "manuscripts").mkdir()
    (repo / "manuscripts/README.md").write_text("# Manuscripts\n\nThe product's own sources.\n", encoding="utf-8")
    git_init(repo)
    return repo


def test_the_destinations_a_blueprint_names_are_not_checked(tmp_path: Path) -> None:
    repo = doc_paths_tree(tmp_path)
    assert "manuscripts/shared/base.tex" in (repo / "templates/manuscripts/README.md").read_text(encoding="utf-8")
    r = guard(repo, "check_doc_paths.py")
    assert r.returncode == 0, r.stdout


def test_adversarial_a_product_document_naming_a_missing_path_still_fails(tmp_path: Path) -> None:
    repo = doc_paths_tree(tmp_path)
    (repo / "manuscripts/README.md").write_text("Build `manuscripts/shared/base.tex` first.\n", encoding="utf-8")
    r = guard(repo, "check_doc_paths.py")
    assert r.returncode == 1 and "manuscripts/README.md:1: names manuscripts/shared/base.tex" in r.stdout, r.stdout


def test_adversarial_a_broken_link_in_a_blueprint_still_fails(tmp_path: Path) -> None:
    repo = doc_paths_tree(tmp_path)
    (repo / "templates/manuscripts/provenance.json").unlink()
    r = guard(repo, "check_doc_paths.py")
    assert r.returncode == 1 and "templates/manuscripts/README.md" in r.stdout and "provenance.json" in r.stdout, r.stdout


# ---------------------------------------------------------------- #101: the Method ladder ids never reach a reader

NAMES_INPUTS = ("scripts/check_internal_names.py", "scripts/check_notebook_depth.py", "scripts/check_notebooks.py")


def notebook(cells: list[dict], methods: list[str] | None = None) -> dict:
    return {"cells": cells, "metadata": {"caos": {"title": "How the solver compares", "methods": methods or []}},
            "nbformat": 4, "nbformat_minor": 5}


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text}


def code(text: str, output: str = "") -> dict:
    outputs = [{"output_type": "stream", "name": "stdout", "text": output}] if output else []
    return {"cell_type": "code", "metadata": {}, "source": text, "outputs": outputs, "execution_count": None}


@pytest.fixture
def names_tree(tmp_path: Path) -> Path:
    repo = make_tree(tmp_path / "repo", *NAMES_INPUTS)
    (repo / "docs/design").mkdir(parents=True)
    (repo / "docs/design/SDD.md").write_text(LADDER_SDD, encoding="utf-8")
    nb = repo / "notebooks/en/01-topic/01-lesson.ipynb"
    nb.parent.mkdir(parents=True)
    clean = notebook([md("# How the solver compares\n\nThe Morrell power model against Bond's law; B-linear is a word."),
                      code("label = 'Morrell model'\nprint(label)", "Morrell model\n")], methods=["B-lin", "M-1"])
    nb.write_text(json.dumps(clean), encoding="utf-8")
    (repo / "README.md").write_text("# Product\n\nThe Morrell model and Bond's law.\n", encoding="utf-8")
    return repo


def internal_names(repo: Path) -> subprocess.CompletedProcess:
    return guard(repo, "check_internal_names.py")


def test_a_clean_tree_with_ladder_ids_in_metadata_only_passes(names_tree: Path) -> None:
    r = internal_names(names_tree)
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("surface", ["markdown", "output", "figure label", "caos title", "notebook index", "manuscript",
                                     "readme", "app string", "app json", "manuscript title"])
def test_adversarial_a_ladder_id_on_a_reader_surface_fails(names_tree: Path, surface: str) -> None:
    nb_path = names_tree / "notebooks/en/01-topic/01-lesson.ipynb"
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    expect = "notebooks/en/01-topic/01-lesson.ipynb"
    if surface == "markdown":
        nb["cells"][0]["source"] += "\n\nB-lin is closer to the plant data."
    elif surface == "output":
        nb["cells"][1]["outputs"][0]["text"] = "B-lin: 3.2 kWh/t\n"
    elif surface == "figure label":
        nb["cells"][1]["source"] = "ax.plot(x, y, label='B-lin')"
    elif surface == "caos title":
        nb["metadata"]["caos"]["title"] = "How M-1 compares"
    elif surface == "notebook index":
        (names_tree / "notebooks/README.md").write_text("# Notebooks\n\n- The lesson on M-1.\n", encoding="utf-8")
        expect = "notebooks/README.md"
    elif surface == "manuscript":
        tex = names_tree / "manuscripts/report/main.tex"
        tex.parent.mkdir(parents=True)
        tex.write_text("\\section{Results}\nThe method B-lin agrees with the survey.\n", encoding="utf-8")
        expect = "manuscripts/report/main.tex"
    elif surface == "readme":
        (names_tree / "README.md").write_text("# Product\n\nIt runs M-1 and B-lin.\n", encoding="utf-8")
        expect = "README.md"
    elif surface == "app string":
        src = names_tree / "frontend/src/pages/Page.tsx"
        src.parent.mkdir(parents=True)
        src.write_text("export const title = t('B-lin against the survey', 'B-lin frente al levantamiento');\n", encoding="utf-8")
        expect = "frontend/src/pages/Page.tsx"
    elif surface == "app json":
        doc = names_tree / "content/methods.json"
        doc.parent.mkdir(parents=True)
        doc.write_text(json.dumps({"summary": "We compare M-1 with the survey."}), encoding="utf-8")
        expect = "content/methods.json"
    else:
        (names_tree / "product.json").write_text(json.dumps({"manuscripts": [{"title": "The B-lin power model"}]}),
                                                 encoding="utf-8")
        expect = "product.json"
    nb_path.write_text(json.dumps(nb), encoding="utf-8")
    r = internal_names(names_tree)
    assert r.returncode == 1 and expect in r.stdout and ("B-lin" in r.stdout or "M-1" in r.stdout), (surface, r.stdout)


def test_adversarial_the_ladder_is_read_below_a_prose_less_than(names_tree: Path) -> None:
    """The prose reader fix (BD-3) applies: a `k<n}` above the ladder no longer hides its ids from the guard."""
    (names_tree / "README.md").write_text("# Product\n\nIt runs B-lin.\n", encoding="utf-8")
    r = internal_names(names_tree)
    assert r.returncode == 1 and "README.md" in r.stdout and "B-lin" in r.stdout, r.stdout


def test_a_reviewed_line_and_a_longer_word_are_not_ladder_ids(names_tree: Path) -> None:
    (names_tree / "README.md").write_text("# Product\n\nM-10 and B-linear are other words.\n\nB-lin, reviewed. internal-name-ok\n",
                                          encoding="utf-8")
    r = internal_names(names_tree)
    assert r.returncode == 0, r.stdout
