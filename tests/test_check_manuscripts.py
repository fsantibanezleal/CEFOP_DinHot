"""The manuscripts gate (scripts/check_manuscripts.py, template 0.13.000; CAOS_MANAGE
``conventions/method-tiers-and-manuscripts.md`` section 2): ``product.json`` declares the product's Zenodo manuscripts, at least
one technical report for a product. Each test builds a throwaway tree and runs the real script on it; the optional online
verification (``--zenodo``) is exercised with a stand-in for the network, never the real one."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_manuscripts.py"
RULE = "method-tiers-and-manuscripts.md"


def rel(minor: int, patch: int = 0) -> str:
    """A release version of the 0.XX.XXX form, built (a literal would be a version literal in code, check_version_coherence.py)."""
    return f"0.{minor:02d}.{patch:03d}"


NOW, BEHIND, AHEAD = rel(13), rel(12), rel(14)

REPORT = {"kind": "technical-report", "concept_doi": "10.5281/zenodo.1234567", "title": "A detailed technical report", "version": NOW,
          "covers": []}
PAPER = {"kind": "manuscript", "concept_doi": "10.5281/zenodo.7654321", "title": "The beyond method, a preprint", "version": rel(1),
         "covers": ["BS-1"]}
SDD = "# SDD\n\n## Beyond the state of the art\n\n- BS-1: the hypothesis, the method and the evaluation.\n- BS-2: another one.\n"


def tree(tmp: Path, manuscripts, *, template: bool = False, version: str = NOW, sdd: str | None = SDD, product: dict | None = None) -> Path:
    doc = dict(product or {"name": "P", "slug": "p"})
    if manuscripts is not None:
        doc["manuscripts"] = manuscripts
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "product.json").write_text(json.dumps(doc), encoding="utf-8")
    (tmp / "VERSION").write_text(version + "\n", encoding="utf-8")
    if sdd is not None:
        (tmp / "docs" / "design").mkdir(parents=True)
        (tmp / "docs" / "design" / "SDD.md").write_text(sdd, encoding="utf-8")
    if template:
        (tmp / ".template-source").write_text("", encoding="utf-8")
    return tmp


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(root), *args], capture_output=True, encoding="utf-8", errors="replace")


def fails(r: subprocess.CompletedProcess, *needles: str) -> bool:
    return r.returncode == 1 and all(n in r.stdout for n in needles)


def test_a_product_with_a_technical_report_passes(tmp_path):
    r = run(tree(tmp_path, [REPORT]))
    assert r.returncode == 0, r.stdout


def test_a_product_with_a_report_and_a_manuscript_on_a_claim_passes(tmp_path):
    r = run(tree(tmp_path, [REPORT, PAPER]))
    assert r.returncode == 0, r.stdout


def test_adversarial_a_product_without_the_field_fails_with_the_rule(tmp_path):
    assert fails(run(tree(tmp_path, None)), "manuscripts", RULE)


def test_adversarial_a_product_with_an_empty_list_fails_with_the_rule(tmp_path):
    assert fails(run(tree(tmp_path, [])), "technical-report", RULE)


def test_a_product_with_only_a_manuscript_fails_it_needs_a_report(tmp_path):
    assert fails(run(tree(tmp_path, [PAPER])), "technical-report", RULE)


def test_the_field_must_be_a_list_of_objects(tmp_path):
    assert fails(run(tree(tmp_path, "10.5281/zenodo.1")), "manuscripts is not a list")
    assert fails(run(tree(tmp_path / "b", ["10.5281/zenodo.1"])), "manuscripts[0]", "not an object")


@pytest.mark.parametrize("change,needle", [
    ({"kind": "preprint"}, "kind"),
    ({"kind": None}, "kind"),
    ({"concept_doi": "10.1234/zenodo.5"}, "concept_doi"),
    ({"concept_doi": "https://doi.org/10.5281/zenodo.5"}, "concept_doi"),
    ({"concept_doi": "10.5281/zenodo.0"}, "concept_doi"),
    ({"concept_doi": "10.5281/zenodo.TBD"}, "concept_doi"),
    ({"concept_doi": ""}, "concept_doi"),
    ({"title": ""}, "title"),
    ({"title": "TBD"}, "title"),
    ({"version": ""}, "version"),
    ({"version": 3}, "version"),
    ({"covers": "BS-1"}, "covers"),
    ({"covers": ["X-1"]}, "covers"),
])
def test_adversarial_a_malformed_entry_fails_naming_the_field(tmp_path, change, needle):
    r = run(tree(tmp_path, [{**REPORT, **change}]))
    assert fails(r, "manuscripts[0]", needle), r.stdout


def test_a_missing_field_of_an_entry_fails_naming_it(tmp_path):
    entry = {k: v for k, v in REPORT.items() if k != "concept_doi"}
    assert fails(run(tree(tmp_path, [entry])), "manuscripts[0]", "concept_doi")


def test_an_unknown_field_of_an_entry_fails(tmp_path):
    assert fails(run(tree(tmp_path, [{**REPORT, "doi": "10.5281/zenodo.1"}])), "manuscripts[0]", "doi")


def test_a_repeated_concept_doi_fails(tmp_path):
    assert fails(run(tree(tmp_path, [REPORT, {**PAPER, "concept_doi": REPORT["concept_doi"]}])), "twice", REPORT["concept_doi"])


def test_adversarial_a_manuscript_that_covers_a_claim_the_sdd_does_not_list_fails(tmp_path):
    r = run(tree(tmp_path, [REPORT, {**PAPER, "covers": ["BS-9"]}]))
    assert fails(r, "BS-9", "Beyond the state of the art")


def test_a_manuscript_is_not_a_report_and_must_cover_a_claim(tmp_path):
    assert fails(run(tree(tmp_path, [REPORT, {**PAPER, "covers": []}])), "manuscripts[1]", "covers")


def test_a_report_version_ahead_of_the_release_fails(tmp_path):
    assert fails(run(tree(tmp_path, [{**REPORT, "version": AHEAD}], version=NOW)), "ahead", "VERSION")


def test_adversarial_a_report_version_behind_the_release_passes_unless_the_release_changes_a_result(tmp_path):
    root = tree(tmp_path, [{**REPORT, "version": BEHIND}], version=NOW)
    assert run(root).returncode == 0
    r = run(root, "--release")
    assert fails(r, "technical report", BEHIND, NOW, "release")


def test_the_release_mode_passes_when_the_report_matches_the_release(tmp_path):
    assert run(tree(tmp_path, [REPORT]), "--release").returncode == 0


def test_a_malformed_product_json_is_a_finding_not_a_crash(tmp_path):
    root = tree(tmp_path, [REPORT])
    (root / "product.json").write_text("{not json", encoding="utf-8")
    assert fails(run(root), "product.json")
    (root / "product.json").write_text("[]", encoding="utf-8")
    assert fails(run(root), "product.json")


def test_a_missing_product_json_is_a_finding(tmp_path):
    tmp_path.mkdir(exist_ok=True)
    assert fails(run(tmp_path), "product.json")


# ---------------------------------------------------------------- the template

def test_adversarial_the_template_may_declare_no_manuscript(tmp_path):
    assert run(tree(tmp_path, None, template=True)).returncode == 0
    assert run(tree(tmp_path / "b", [], template=True)).returncode == 0


def test_the_template_still_validates_what_it_declares(tmp_path):
    assert fails(run(tree(tmp_path, [{**REPORT, "kind": "preprint"}], template=True)), "kind")


# ---------------------------------------------------------------- the online check (opt-in)

def load():
    spec = importlib.util.spec_from_file_location("check_manuscripts", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record(**kw):
    return {"conceptdoi": "10.5281/zenodo.1234567", "metadata": {"version": NOW, "title": "A detailed technical report"}, **kw}


def test_the_online_check_accepts_a_record_that_matches():
    mod = load()
    assert mod.zenodo_findings([REPORT], fetch=lambda n: record()) == []


def test_the_online_check_finds_a_missing_record_and_a_different_concept_doi():
    mod = load()
    assert any("10.5281/zenodo.1234567" in f and "not found" in f for f in mod.zenodo_findings([REPORT], fetch=lambda n: None))
    other = mod.zenodo_findings([REPORT], fetch=lambda n: record(conceptdoi="10.5281/zenodo.9"))
    assert any("concept DOI" in f and "10.5281/zenodo.9" in f for f in other)


def test_adversarial_the_online_check_finds_a_version_behind_the_declared_one():
    mod = load()
    behind = mod.zenodo_findings([REPORT], fetch=lambda n: record(metadata={"version": BEHIND, "title": "x"}))
    assert any(BEHIND in f and NOW in f for f in behind)


def test_adversarial_the_default_run_never_touches_the_network(tmp_path):
    source = SCRIPT.read_text(encoding="utf-8")
    assert "--zenodo" in source
    assert run(tree(tmp_path, [REPORT])).returncode == 0  # offline by construction: the fetcher is only called under --zenodo
