"""Unit tests of the spec-area guards (0.05.000): check_sdd (research basis, resources, validation), check_tech_matrix
and check_contract_versions. Each test builds a small throwaway tree, runs the real script on it as a subprocess and
asserts its exit code and message. The whole-repository plants are in tests/adversarial/."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- check_sdd

SECTIONS = ("Problem and non-goals", "Research basis", "Sizing and contracts", "Technology and versions", "Resources",
            "Lanes", "Method ladder", "Cases", "Oracles", "Deploy driver", "Risks and kill criteria", "ADR fit")
RESEARCH = ("- Doe 1927, https://doi.org/10.1098/rspa.1927.0118\n- Miller 2012, doi 10.1007/s11538-012-9749-6\n"
            "- Roe 2000, https://doi.org/10.1137/S0036144500371907\n\nUNVERIFIED: none\n")
RESOURCES = ("| stage | memory | disk | time | where it runs |\n|---|---|---|---|---|\n"
             "| bake | 120 MB | 1 MB | 0.1 s | workstation |\n| tests | 200 MB | 5 MB | 10 s | workstation |\n"
             "| build | 400 MB | 2 MB | 8 s | workstation |\n| deploy payload | 0 | 2 MB | 5 s | CI |\n")


BRIEF = """The executive view of the Introduction is data, kept apart from this document: one file frames the problem space in five
sections, with its headline figures, its three illustrations and the linked source of every figure, in English and
Spanish. It is valid against the shell's schema and rendered by the shell.

Data file: content/executive.json
"""
SCHEMA_REL = "frontend/node_modules/@fasl-work/caos-app-shell/src/content/executive.schema.json"


def sdd_text(research: str = RESEARCH, resources: str = RESOURCES, skip: str = "", brief: str | None = BRIEF,
             brief_after: str = "Problem and non-goals") -> str:
    out = ["# SDD\n"]
    for name in SECTIONS:
        if name == skip:
            continue
        body = {"Research basis": research, "Resources": resources}.get(name, "text\n")
        out.append(f"## {name}\n\n{body}\n")
        if name == brief_after and brief is not None:
            out.append(f"## Executive brief\n\n{brief}\n")
    return "\n".join(out)


REQUIREMENTS = ("| ID | Requirement | Gate |\n|---|---|---|\n"
                "| FX-001 | THE x SHALL a. | `tests/test_x.py::test_a` |\n| FX-002 | THE x SHALL b. | `tests/test_x.py::test_b` |\n")
ADV = "tests/adversarial/test_adv.py"


def put(tmp: Path, rel: str, text: str) -> Path:
    path = tmp / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def sdd_tree(tmp: Path, *, validation: str | None, sdd: str | None = None, requirements: str = REQUIREMENTS,
             files: dict[str, str] | None = None, executive: bool = True) -> Path:
    (tmp / "docs" / "design" / "features" / "f").mkdir(parents=True)
    put(tmp, "docs/limits.md", "limits\n")
    put(tmp, "tests/test_x.py", "def test_a():\n    pass\n\ndef test_b():\n    pass\n")
    put(tmp, ADV, "def test_a():\n    pass\n\ndef test_b():\n    pass\n")
    put(tmp, "docs/design/SDD.md", sdd if sdd is not None else sdd_text())
    put(tmp, "docs/design/features/f/requirements.md", requirements)
    if validation is not None:
        put(tmp, "docs/design/features/f/validation.md", validation)
    for rel, text in (files or {}).items():
        put(tmp, rel, text)
    if executive:
        executive_tree(tmp)
    return tmp


GOOD_VALIDATION = ("| requirement | adversarial check | gate |\n|---|---|---|\n"
                   f"| FX-001 | a NaN parameter is rejected | `{ADV}::test_a` |\n"
                   f"| FX-002 | a planted drift fails | `{ADV}::test_b` |\n")


def test_sdd_clean_tree_passes(tmp_path):
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION)))
    assert r.returncode == 0, r.stdout


def test_sdd_missing_new_section_is_named(tmp_path):
    t = sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=sdd_text(skip="Technology and versions"))
    r = run("check_sdd.py", str(t))
    assert r.returncode == 1 and "Technology and versions" in r.stdout


def test_sdd_old_contracts_section_name_no_longer_counts(tmp_path):
    text = sdd_text().replace("## Sizing and contracts", "## Contracts")
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=text)))
    assert r.returncode == 1 and "Sizing and contracts" in r.stdout


def test_sdd_research_with_two_sources_fails(tmp_path):
    two = ("- Doe 1927, 10.1098/rspa.1927.0118\n- Miller 2012, https://doi.org/10.1007/s11538-012-9749-6\n\n"
           "UNVERIFIED: none\n")
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=sdd_text(research=two))))
    assert r.returncode == 1 and "research basis" in r.stdout.lower() and "2" in r.stdout


def test_sdd_research_without_an_unverified_line_fails(tmp_path):
    no = RESEARCH.replace("UNVERIFIED: none", "all fine")
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=sdd_text(research=no))))
    assert r.returncode == 1 and "UNVERIFIED" in r.stdout


def test_sdd_resources_with_an_empty_cell_or_tbd_fails(tmp_path):
    empty = RESOURCES.replace("| 120 MB |", "|  |")
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=sdd_text(resources=empty))))
    assert r.returncode == 1 and "empty" in r.stdout
    tbd = RESOURCES.replace("10 s", "TBD")
    r = run("check_sdd.py", str(sdd_tree(tmp_path / "b", validation=GOOD_VALIDATION, sdd=sdd_text(resources=tbd))))
    assert r.returncode == 1 and "TBD" in r.stdout


def test_sdd_resources_without_the_required_stages_fails(tmp_path):
    short = "\n".join(RESOURCES.splitlines()[:4]) + "\n"  # bake and tests only
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=sdd_text(resources=short))))
    assert r.returncode == 1 and "build" in r.stdout and "deploy" in r.stdout


def test_sdd_feature_without_validation_fails(tmp_path):
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=None)))
    assert r.returncode == 1 and "validation.md" in r.stdout


def test_sdd_validation_missing_a_requirement_fails(tmp_path):
    only_one = "\n".join(GOOD_VALIDATION.splitlines()[:3]) + "\n"
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=only_one)))
    assert r.returncode == 1 and "FX-002" in r.stdout and "no validation row" in r.stdout


def test_sdd_validation_listing_a_requirement_twice_or_an_unknown_one_fails(tmp_path):
    twice = GOOD_VALIDATION + "| FX-001 | again | `tests/test_x.py::test_a` |\n"
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=twice)))
    assert r.returncode == 1 and "FX-001" in r.stdout and "more than once" in r.stdout
    unknown = GOOD_VALIDATION + "| FX-009 | ghost | `tests/test_x.py::test_a` |\n"
    r = run("check_sdd.py", str(sdd_tree(tmp_path / "b", validation=unknown)))
    assert r.returncode == 1 and "FX-009" in r.stdout


def test_sdd_validation_gate_naming_a_renamed_test_fails(tmp_path):
    renamed = GOOD_VALIDATION.replace("test_b", "test_renamed")
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=renamed)))
    assert r.returncode == 1 and "test_renamed" in r.stdout


def test_sdd_validation_gate_without_a_named_test_or_an_empty_check_fails(tmp_path):
    no_test = GOOD_VALIDATION.replace(f"`{ADV}::test_b`", f"`{ADV}`")
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=no_test)))
    assert r.returncode == 1 and "names no test" in r.stdout
    empty = GOOD_VALIDATION.replace("a planted drift fails", " ")
    r = run("check_sdd.py", str(sdd_tree(tmp_path / "b", validation=empty)))
    assert r.returncode == 1 and "adversarial check" in r.stdout


ALLOW = "docs/design/features/.status-allow"


def test_sdd_superseded_and_planned_features_need_no_validation_when_listed_with_a_reason(tmp_path):
    t = sdd_tree(tmp_path, validation=None, files={ALLOW: "# area: reason\nf: replaced by the g feature, kept for history\n"})
    req = t / "docs" / "design" / "features" / "f" / "requirements.md"
    req.write_text("Status: superseded\n\n" + req.read_text(encoding="utf-8"), encoding="utf-8")
    r = run("check_sdd.py", str(t))
    assert r.returncode == 0 and "superseded" in r.stdout, r.stdout
    req.write_text(req.read_text(encoding="utf-8").replace("Status: superseded", "Status: planned"), encoding="utf-8")
    r = run("check_sdd.py", str(t))
    assert r.returncode == 0 and "planned" in r.stdout, r.stdout


def test_sdd_s6_a_status_other_than_live_needs_an_allow_entry_with_a_reason(tmp_path):
    for n, status in enumerate(("superseded", "planned")):
        t = sdd_tree(tmp_path / str(n), validation=None)
        req = t / "docs" / "design" / "features" / "f" / "requirements.md"
        req.write_text(f"Status: {status}\n\n" + req.read_text(encoding="utf-8"), encoding="utf-8")
        r = run("check_sdd.py", str(t))
        assert r.returncode == 1 and ".status-allow" in r.stdout and status in r.stdout, r.stdout
        put(t, ALLOW, "f:\n")  # an entry with no reason is no entry
        r = run("check_sdd.py", str(t))
        assert r.returncode == 1 and ".status-allow" in r.stdout, r.stdout


def test_sdd_s6_an_unknown_status_and_two_status_lines_fail(tmp_path):
    t = sdd_tree(tmp_path, validation=GOOD_VALIDATION)
    req = t / "docs" / "design" / "features" / "f" / "requirements.md"
    req.write_text("Status: finished\n\n" + REQUIREMENTS, encoding="utf-8")
    r = run("check_sdd.py", str(t))
    assert r.returncode == 1 and "Status" in r.stdout, r.stdout
    req.write_text("Status: live\nStatus: live\n\n" + REQUIREMENTS, encoding="utf-8")
    r = run("check_sdd.py", str(t))
    assert r.returncode == 1 and "more than one Status" in r.stdout, r.stdout
    req.write_text("Status: live\n\n" + REQUIREMENTS, encoding="utf-8")
    assert run("check_sdd.py", str(t)).returncode == 0


def test_sdd_s6e_a_feature_folder_without_requirements_fails(tmp_path):
    t = sdd_tree(tmp_path, validation=GOOD_VALIDATION, files={"docs/design/features/g/spec.md": "spec\n"})
    r = run("check_sdd.py", str(t))
    assert r.returncode == 1 and "features/g" in r.stdout and "requirements.md" in r.stdout, r.stdout


# ---- a name is a gate only when it is a live test (F-S1)

def gate_tree(tmp: Path, file: str, text: str, name: str, *, where: str = "requirement") -> subprocess.CompletedProcess:
    """A tree whose FX-001 gate (in requirements.md or in validation.md) names ``file::name``; ``file`` holds ``text``."""
    gate = f"`{file}::{name}`"
    req = REQUIREMENTS.replace("`tests/test_x.py::test_a`", gate if where == "requirement" else "`tests/test_x.py::test_a`")
    val = GOOD_VALIDATION.replace(f"`{ADV}::test_a`", gate if where == "validation" else f"`{ADV}::test_a`")
    t = sdd_tree(tmp, validation=val, requirements=req, files={file: text})
    return run("check_sdd.py", str(t))


PY_FILE = "tests/adversarial/test_ghost.py"
TS_FILE = "frontend/src/ghost.test.ts"
PY_NOT_TESTS = {
    "string": 'DOC = """\ndef test_ghost():\n    pass\n"""\n',
    "comment": "# def test_ghost():\n#     pass\n",
    "nested": "def helper():\n    def test_ghost():\n        pass\n",
    "skip": "import pytest\n\n\n@pytest.mark.skip\ndef test_ghost():\n    assert False\n",
    "skip-reason": 'import pytest\n\n\n@pytest.mark.skip(reason="later")\ndef test_ghost():\n    assert False\n',
    "skipif-true": 'import pytest\n\n\n@pytest.mark.skipif(True, reason="never")\ndef test_ghost():\n    assert False\n',
    "skip-class": "import pytest\n\n\n@pytest.mark.skip\nclass TestGhost:\n    def test_ghost(self):\n        assert False\n",
    "pytestmark": "import pytest\n\npytestmark = pytest.mark.skip\n\n\ndef test_ghost():\n    assert False\n",
    "module-skip": 'import pytest\n\npytest.skip("x", allow_module_level=True)\n\n\ndef test_ghost():\n    assert False\n',
    "body-skip": 'import pytest\n\n\ndef test_ghost():\n    pytest.skip("always")\n    assert False\n',
    "method-of-a-plain-class": "class Helper:\n    def test_ghost(self):\n        pass\n",
    "syntax-error": "def test_ghost(:\n",
}
PY_TESTS = {
    "module-level": "def test_ghost():\n    assert True\n",
    "async": "async def test_ghost():\n    assert True\n",
    "class-method": "class TestThing:\n    def test_ghost(self):\n        assert True\n",
    "conditional skip is not a skip": "import sys\nimport pytest\n\n\n@pytest.mark.skipif(sys.platform == 'none', reason='r')\ndef test_ghost():\n    assert True\n",
    "importorskip is a precondition": "import pytest\n\n\ndef test_ghost():\n    pytest.importorskip('json')\n    assert True\n",
}


@pytest.mark.parametrize("where", ["requirement", "validation"])
@pytest.mark.parametrize("case", sorted(PY_NOT_TESTS))
def test_sdd_s1_a_python_name_that_is_not_a_live_test_fails(tmp_path, case, where):
    r = gate_tree(tmp_path, PY_FILE, PY_NOT_TESTS[case], "test_ghost", where=where)
    assert r.returncode == 1 and "FX-001" in r.stdout, r.stdout
    if case != "syntax-error":
        assert "test_ghost" in r.stdout, r.stdout


@pytest.mark.parametrize("case", sorted(PY_TESTS))
def test_sdd_s1_a_python_live_test_passes(tmp_path, case):
    r = gate_tree(tmp_path, PY_FILE, PY_TESTS[case], "test_ghost")
    assert r.returncode == 0, r.stdout


def test_sdd_s1_a_parametrised_python_name_is_the_function(tmp_path):
    r = gate_tree(tmp_path, PY_FILE, "def test_ghost(x):\n    pass\n", "test_ghost[a-1]")
    assert r.returncode == 0, r.stdout


TS_NOT_TESTS = {
    "line comment": "// it('adversarial: ghost', () => {})\n",
    "block comment": "/* it('adversarial: ghost', () => {}) */\n",
    "string": "const DOC = \"test('adversarial: ghost', () => {})\";\n",
    "template": "const DOC = `\nit('adversarial: ghost', () => {})\n`;\n",
    "another body": "it('real one', () => { const s = \"it('adversarial: ghost'\"; expect(s).toBe(s) })\n",
    "nested": "it('real one', () => {\n  it('adversarial: ghost', () => {})\n})\n",
    "skip": "it.skip('adversarial: ghost', () => {})\n",
    "todo": "it.todo('adversarial: ghost')\n",
    "xit": "xit('adversarial: ghost', () => {})\n",
    "skip option": "it('adversarial: ghost', { skip: true }, () => {})\n",
    "todo option": "test('adversarial: ghost', { todo: true }, () => {})\n",
    "describe": "describe('adversarial: ghost', () => {})\n",
    "empty describe": "describe('adversarial: ghost', () => {})\nit('other', () => {})\n",
}
TS_TESTS = {
    "it": "it('adversarial: ghost', () => {})\n",
    "test": "test('adversarial: ghost', () => {})\n",
    "in a describe": "describe('block', () => {\n  it('adversarial: ghost', () => {\n    expect(1).toBe(1)\n  })\n})\n",
    "backtick": "it(`adversarial: ghost`, () => {})\n",
    "double quote": 'it("adversarial: ghost", () => {})\n',
    "crlf": "it('adversarial: ghost', () => {})\r\n",
    "after a comment": "// the note\nit('adversarial: ghost', () => {}) // trailing\n",
    "skip false": "it('adversarial: ghost', { skip: false }, () => {})\n",
}


@pytest.mark.parametrize("where", ["requirement", "validation"])
@pytest.mark.parametrize("case", sorted(TS_NOT_TESTS))
def test_sdd_s1_a_typescript_name_that_is_not_a_live_test_fails(tmp_path, case, where):
    r = gate_tree(tmp_path, TS_FILE, TS_NOT_TESTS[case], "adversarial: ghost", where=where)
    assert r.returncode == 1 and "adversarial: ghost" in r.stdout, r.stdout


@pytest.mark.parametrize("case", sorted(TS_TESTS))
def test_sdd_s1_a_typescript_live_test_passes(tmp_path, case):
    r = gate_tree(tmp_path, TS_FILE, TS_TESTS[case], "adversarial: ghost")
    assert r.returncode == 0, r.stdout


def test_sdd_s2_a_prefix_of_a_test_name_is_not_the_name(tmp_path):
    r = gate_tree(tmp_path, TS_FILE, "it('adversarial: ghost and more', () => {})\n", "adversarial: gho")
    assert r.returncode == 1, r.stdout
    r = gate_tree(tmp_path / "b", TS_FILE, "it('adversarial: ghost', () => {})\n", "adversarial: ghost and more")
    assert r.returncode == 1, r.stdout


# ---- a gate is a test or a script, never a document (F-S2)

@pytest.mark.parametrize("cell", [
    "`docs/limits.md::test_anything`", "`README.md::x`", "`scripts/tool.py::main`", "`README.md`", "`docs/limits.md`",
    "`data/index.json`", "`../outside.py`", "`tests/test_x.py::test_a` and `README.md`",
])
def test_sdd_s2_a_gate_that_is_not_a_test_or_a_script_fails(tmp_path, cell):
    req = REQUIREMENTS.replace("`tests/test_x.py::test_a`", cell)
    t = sdd_tree(tmp_path / "t", validation=GOOD_VALIDATION, requirements=req,
                 files={"README.md": "r\n", "scripts/tool.py": "def main():\n    pass\n", "data/index.json": "{}\n"})
    (tmp_path / "outside.py").write_text("x = 1\n", encoding="utf-8")
    r = run("check_sdd.py", str(t))
    assert r.returncode == 1 and "FX-001" in r.stdout, r.stdout


@pytest.mark.parametrize("cell", ["`scripts/tool.py`", "`frontend/scripts/tool.mjs`", "`tests/conftest.py`",
                                  "`scripts/tool.py`, run by `npm test`"])
def test_sdd_s2_a_script_or_a_test_file_is_a_gate_for_a_requirement(tmp_path, cell):
    req = REQUIREMENTS.replace("`tests/test_x.py::test_a`", cell)
    t = sdd_tree(tmp_path, validation=GOOD_VALIDATION, requirements=req,
                 files={"scripts/tool.py": "x = 1\n", "frontend/scripts/tool.mjs": "export {}\n", "tests/conftest.py": "x = 1\n"})
    r = run("check_sdd.py", str(t))
    assert r.returncode == 0, r.stdout


# ---- rows that vanish (F-S3)

def row_edit(tmp_path, make):
    row = "| FX-002 | THE x SHALL b. | `tests/test_x.py::test_b` |"
    req = REQUIREMENTS.replace(row, make(row))
    val = "\n".join(ln for ln in GOOD_VALIDATION.splitlines() if "FX-002" not in ln) + "\n"
    return run("check_sdd.py", str(sdd_tree(tmp_path, validation=val, requirements=req)))


@pytest.mark.parametrize("case,make", [
    ("split row", lambda row: row.replace("SHALL b.", "SHALL b\nand c.")),
    ("indented row", lambda row: "  " + row),
    ("row without a gate cell", lambda row: "| FX-002 | THE x SHALL b. |"),
    ("lower-case ID", lambda row: row.replace("FX-002", "fx-002")),
    ("bullet outside the table", lambda row: "- FX-002: THE x SHALL b."),
    ("two cells only", lambda row: "| FX-002 |"),
    ("empty ID", lambda row: row.replace("FX-002", "")),
])
def test_sdd_s3_a_requirement_row_that_vanishes_is_a_finding(tmp_path, case, make):
    r = row_edit(tmp_path, make)
    assert r.returncode == 1 and ("FX-002" in r.stdout or "fx-002" in r.stdout or "malformed" in r.stdout), r.stdout


def test_sdd_s3_a_duplicate_id_across_features_fails(tmp_path):
    t = sdd_tree(tmp_path, validation=GOOD_VALIDATION)
    put(t, "docs/design/features/g/requirements.md", REQUIREMENTS)
    put(t, "docs/design/features/g/validation.md", GOOD_VALIDATION)
    r = run("check_sdd.py", str(t))
    assert r.returncode == 1 and "duplicate" in r.stdout, r.stdout


# ---- the SDD outline (F-S5)

def test_sdd_s5_headings_inside_a_fence_or_a_comment_do_not_count(tmp_path):
    body = "text\n"
    fenced = ("# SDD\n\n```\n" + "".join(f"## {n}\n{body}" for n in SECTIONS) + "```\n\n## Research basis\n\n" + RESEARCH
              + "\n## Resources\n\n" + RESOURCES)
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=fenced)))
    assert r.returncode == 1 and "Lanes" in r.stdout and "no section" in r.stdout, r.stdout
    commented = sdd_text().replace("## Lanes", "<!--\n## Lanes\n-->")
    r = run("check_sdd.py", str(sdd_tree(tmp_path / "b", validation=GOOD_VALIDATION, sdd=commented)))
    assert r.returncode == 1 and "Lanes" in r.stdout, r.stdout


def test_sdd_s5_one_heading_naming_ten_sections_fails(tmp_path):
    names = [n for n in SECTIONS if n not in ("Research basis", "Resources")]
    text = f"# SDD\n\n## Resources\n\n{RESOURCES}\n## {', '.join(names)}\n\nnothing\n\n## Research basis\n\n{RESEARCH}\n"
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=text)))
    assert r.returncode == 1 and "Lanes" in r.stdout, r.stdout


def test_sdd_s5_a_heading_that_only_contains_the_name_does_not_count(tmp_path):
    text = sdd_text().replace("## Lanes", "## Lanes and everything else")
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=text)))
    assert r.returncode == 1 and "'Lanes'" in r.stdout, r.stdout


def test_sdd_s5_an_empty_section_and_an_out_of_order_one_fail(tmp_path):
    empty = sdd_text().replace("## Lanes\n\ntext\n", "## Lanes\n\n")
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=empty)))
    assert r.returncode == 1 and "'Lanes'" in r.stdout and "empty" in r.stdout, r.stdout
    swapped = sdd_text().replace("## Lanes", "## @@").replace("## Cases", "## Lanes").replace("## @@", "## Cases")
    r = run("check_sdd.py", str(sdd_tree(tmp_path / "b", validation=GOOD_VALIDATION, sdd=swapped)))
    assert r.returncode == 1 and "out of order" in r.stdout, r.stdout


def test_sdd_s5_numbered_headings_are_accepted(tmp_path):
    numbered = sdd_text().replace("## Lanes", "## 6. Lanes")
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=numbered)))
    assert r.returncode == 0, r.stdout


# ---- research basis and resources (F-S6)

def research_run(tmp_path, research):
    return run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=sdd_text(research=research))))


def test_sdd_s6_placeholder_urls_do_not_count_as_sources(tmp_path):
    r = research_run(tmp_path, "- http://a.example\n- http://b.example\n- http://c.example\n\nUNVERIFIED: none\n")
    assert r.returncode == 1 and "cites 0 sources" in r.stdout, r.stdout
    r = research_run(tmp_path / "b", "- https://example.com/a\n- https://example.org/b\n- http://localhost/c\n\nUNVERIFIED: none\n")
    assert r.returncode == 1 and "cites 0 sources" in r.stdout, r.stdout


def test_sdd_s6_one_work_cited_three_ways_is_one_source(tmp_path):
    doi = "10.1098/rspa.1927.0118"
    r = research_run(tmp_path, f"- {doi}\n- https://doi.org/{doi}\n- http://dx.doi.org/{doi}\n- doi:{doi}\n\nUNVERIFIED: none\n")
    assert r.returncode == 1 and "cites 1 source" in r.stdout, r.stdout


def test_sdd_s6_unverified_must_be_a_line_of_its_own(tmp_path):
    r = research_run(tmp_path, RESEARCH.replace("UNVERIFIED: none", "Nothing here is UNVERIFIED-free."))
    assert r.returncode == 1 and "UNVERIFIED:" in r.stdout, r.stdout
    r = research_run(tmp_path / "b", RESEARCH.replace("UNVERIFIED: none", "- UNVERIFIED: what each work says beyond its title"))
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("cell", ["-", "?", "TODO", "unknown", "n/a", "N/A", "todo"])
def test_sdd_s6_placeholder_resource_cells_fail(tmp_path, cell):
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=sdd_text(resources=RESOURCES.replace("120 MB", cell)))))
    assert r.returncode == 1 and "Resources" in r.stdout, r.stdout


def test_sdd_s6_one_row_for_four_stages_fails(tmp_path):
    one = ("| stage | memory | disk | time | where it runs |\n|---|---|---|---|---|\n"
           "| bake, tests, build, deploy | 1 MB | 1 MB | 1 s | workstation |\n")
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=sdd_text(resources=one))))
    assert r.returncode == 1 and "no row for the bake" in r.stdout, r.stdout


# ---- validation rows are plants (F-S7)

def test_sdd_s7_a_validation_gate_must_be_an_adversarial_test(tmp_path):
    ordinary = GOOD_VALIDATION.replace(f"`{ADV}::test_b`", "`tests/test_x.py::test_b`")
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=ordinary)))
    assert r.returncode == 1 and "FX-002" in r.stdout and "adversarial" in r.stdout, r.stdout


def test_sdd_s7_a_test_named_adversarial_counts_anywhere(tmp_path):
    named = GOOD_VALIDATION.replace(f"`{ADV}::test_b`", "`tests/test_y.py::test_adversarial_b`")
    t = sdd_tree(tmp_path, validation=named, files={"tests/test_y.py": "def test_adversarial_b():\n    pass\n"})
    assert run("check_sdd.py", str(t)).returncode == 0
    ts = GOOD_VALIDATION.replace(f"`{ADV}::test_b`", "`frontend/src/y.test.ts::adversarial: b`")
    t = sdd_tree(tmp_path / "b", validation=ts, files={"frontend/src/y.test.ts": "it('adversarial: b', () => {})\n"})
    assert run("check_sdd.py", str(t)).returncode == 0


def test_sdd_s7_a_check_that_names_no_plant_and_a_readme_gate_fail(tmp_path):
    bad = GOOD_VALIDATION.replace("a planted drift fails", "it works").replace(f"`{ADV}::test_b`", "`README.md::x`")
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=bad, files={"README.md": "r\n"})))
    assert r.returncode == 1 and "FX-002" in r.stdout, r.stdout


def test_sdd_s7_a_skipped_validation_gate_fails(tmp_path):
    skipped = "import pytest\n\n\n@pytest.mark.skip\ndef test_b():\n    assert False\n"
    val = GOOD_VALIDATION.replace(f"`{ADV}::test_b`", "`tests/adversarial/test_skipped.py::test_b`")
    r = run("check_sdd.py", str(sdd_tree(tmp_path, validation=val, files={"tests/adversarial/test_skipped.py": skipped})))
    assert r.returncode == 1 and "FX-002" in r.stdout and "test_b" in r.stdout, r.stdout


def test_sdd_crlf_in_every_file_still_passes(tmp_path):
    t = sdd_tree(tmp_path, validation=GOOD_VALIDATION)
    for path in list((t / "docs").rglob("*.md")) + list((t / "tests").rglob("*.py")):
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    r = run("check_sdd.py", str(t))
    assert r.returncode == 0, r.stdout


# ---------------------------------------------------------------- check_sdd: the executive view (problem-context-first, schema 2.0.0, 0.07.000)

GUIDE = "docs/guides/06_executive-brief.md"
EXEC = "content/executive.json"
DELETE = object()
ILLUSTRATIONS = ("pain", "situation", "proposal")


def example_data() -> dict:
    return json.loads((ROOT / EXEC).read_text(encoding="utf-8"))


def executive_tree(tmp: Path, data: dict | None = None, *, schema: bool = True, svgs: bool = True) -> Path:
    """The executive view of a throwaway tree: the example's file (or ``data``), its three SVG files under
    frontend/public/ and the shell's schema as npm ci installs it."""
    data = example_data() if data is None else data
    put(tmp, EXEC, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    if svgs:
        for ill in example_data()["illustrations"].values():
            target = tmp / "frontend" / "public" / ill["file"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / "frontend" / "public" / ill["file"]).read_bytes())
    if schema:
        src = ROOT / SCHEMA_REL
        assert src.is_file(), f"{SCHEMA_REL} is absent: run npm ci in frontend/ (the shell's schema is the contract under test)"
        (tmp / SCHEMA_REL).parent.mkdir(parents=True, exist_ok=True)
        (tmp / SCHEMA_REL).write_bytes(src.read_bytes())
    return tmp


def view_tree(tmp_path, data: dict | None = None, brief: str | None = BRIEF, *, sdd: str | None = None, **kw) -> Path:
    tree = sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=sdd if sdd is not None else sdd_text(brief=brief), executive=False)
    return executive_tree(tree, data, **kw)


def view_run(tmp_path, data: dict | None = None, brief: str | None = BRIEF, **kw):
    return run("check_sdd.py", str(view_tree(tmp_path, data, brief, **kw)))


def changed(path: list, value) -> dict:
    """The example's data with one field replaced (DELETE removes it)."""
    data = example_data()
    node = data
    for key in path[:-1]:
        node = node[key]
    if value is DELETE:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return data


def words(n: int) -> str:
    return " ".join(["word"] * n)


def test_view_the_example_passes(tmp_path):
    r = view_run(tmp_path)
    assert r.returncode == 0, r.stdout


def test_view_the_real_repository_passes():
    r = run("check_sdd.py", str(ROOT))
    assert r.returncode == 0 and "check_sdd: OK" in r.stdout, r.stdout


def test_view_the_example_is_a_frame_of_the_problem_space_with_sourced_links():
    data = example_data()
    assert set(data["illustrations"]) == set(ILLUSTRATIONS)
    assert [c["c"]["en"] for c in data["proposal"]["four_cs"]] == ["Choice", "Context", "Cost", "Control"]
    assert len(data["sources"]) >= 8
    assert all(s["url"].startswith("https://") for s in data["sources"])
    for old in ("executive", "organisation", "initiative", "why_now", "vision", "outcomes", "dialogue", "four_cs"):
        assert old not in data, old


def test_view_missing_file_fails_naming_it_and_the_guide(tmp_path):
    tree = sdd_tree(tmp_path, validation=GOOD_VALIDATION, executive=False)
    r = run("check_sdd.py", str(tree))
    assert r.returncode == 1 and EXEC in r.stdout and "missing" in r.stdout and GUIDE in r.stdout, r.stdout


def test_view_a_file_that_is_not_json_fails(tmp_path):
    tree = view_tree(tmp_path)
    put(tree, EXEC, "{ not json")
    r = run("check_sdd.py", str(tree))
    assert r.returncode == 1 and EXEC in r.stdout and "not valid JSON" in r.stdout, r.stdout


def test_view_without_the_shell_schema_fails_instead_of_passing(tmp_path):
    r = view_run(tmp_path, schema=False)
    assert r.returncode == 1 and "executive.schema.json" in r.stdout and "npm ci" in r.stdout, r.stdout


def test_view_a_schema_of_the_old_version_is_refused(tmp_path):
    tree = view_tree(tmp_path)
    schema = tree / SCHEMA_REL
    doc = json.loads(schema.read_text(encoding="utf-8"))
    doc["title"] = doc["title"].replace("2.0.0", "1.0.0")
    schema.write_text(json.dumps(doc), encoding="utf-8")
    r = run("check_sdd.py", str(tree))
    assert r.returncode == 1 and "2.0.0" in r.stdout and "npm ci" in r.stdout, r.stdout


@pytest.mark.parametrize("path,value,expected", [
    (["pain", "bearers", 1, "cost"], DELETE, "pain.bearers[1].cost"),
    (["pain", "bearers", 0, "who", "es"], DELETE, "pain.bearers[0].who.es"),
    (["title"], "A title with no language", "title"),
    (["key_statement"], {"en": "", "es": "x"}, "key_statement.en"),
    (["headline_figures"], [], "headline_figures"),
    (["pain", "causes"], [], "pain.causes"),
    (["context", "forces", 0, "direction"], "sideways", "context.forces[0].direction"),
    (["trends", "items", 0, "horizon"], "tomorrow", "trends.items[0].horizon"),
    (["trends", "items", 0, "confidence"], DELETE, "trends.items[0].confidence"),
    (["situation", "status"], DELETE, "situation.status"),
    (["proposal", "four_cs"], [], "proposal.four_cs"),
    (["illustrations", "situation"], DELETE, "illustrations.situation"),
    (["illustrations", "initiative"], {"file": "executive/x.svg", "caption": {"en": "a", "es": "b"}}, "illustrations.initiative"),
    (["invented_field"], "x", "invented_field"),
    (["executive"], {"en": "Chief Operating Officer", "es": "Director de Operaciones"}, "executive"),
])
def test_view_a_file_that_breaks_the_schema_names_the_field_path(tmp_path, path, value, expected):
    r = view_run(tmp_path, changed(path, value))
    assert r.returncode == 1 and EXEC in r.stdout and expected in r.stdout, r.stdout


@pytest.mark.parametrize("path,floor", [
    (["pain", "paragraphs"], 2), (["pain", "bearers"], 3), (["pain", "figures"], 2), (["pain", "causes"], 3),
    (["context", "forces"], 3), (["situation", "roles"], 3), (["situation", "state_of_the_art"], 3),
    (["trends", "items"], 3), (["proposal", "actions"], 3),
])
def test_view_a_sub_tab_below_its_floor_fails(tmp_path, path, floor):
    data = example_data()
    node = data
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = node[path[-1]][:floor - 1]
    r = view_run(tmp_path, data)
    assert r.returncode == 1 and ".".join(path) in r.stdout, r.stdout


@pytest.mark.parametrize("name", ILLUSTRATIONS)
def test_view_a_missing_illustration_file_is_named(tmp_path, name):
    tree = view_tree(tmp_path)
    (tree / "frontend" / "public" / example_data()["illustrations"][name]["file"]).unlink()
    r = run("check_sdd.py", str(tree))
    assert r.returncode == 1 and f"illustrations.{name}.file" in r.stdout and "does not exist" in r.stdout, r.stdout


def test_view_an_illustration_per_language_is_checked_for_each_language(tmp_path):
    data = changed(["illustrations", "pain", "file"], {"en": "executive/pain.svg", "es": "executive/pain-es.svg"})
    r = view_run(tmp_path, data)
    assert r.returncode == 1 and "illustrations.pain.file.es" in r.stdout, r.stdout


def test_view_an_illustration_that_is_not_an_svg_with_a_viewbox_fails(tmp_path):
    tree = view_tree(tmp_path)
    (tree / "frontend" / "public" / "executive" / "proposal.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
    r = run("check_sdd.py", str(tree))
    assert r.returncode == 1 and "illustrations.proposal.file" in r.stdout and "viewBox" in r.stdout, r.stdout


def test_view_an_illustration_path_that_leaves_the_site_fails(tmp_path):
    r = view_run(tmp_path, changed(["illustrations", "pain", "file"], "../../outside.svg"))
    assert r.returncode == 1 and "illustrations.pain.file" in r.stdout, r.stdout


# ---- the sources are links, each cited, each cited id real

def test_view_a_figure_citing_an_unknown_source_fails(tmp_path):
    r = view_run(tmp_path, changed(["headline_figures", 0, "source"], "nobody"))
    assert r.returncode == 1 and "headline_figures[0].source" in r.stdout and "nobody" in r.stdout and "not the id of any source" in r.stdout, r.stdout


def test_view_a_source_that_nothing_cites_fails(tmp_path):
    data = example_data()
    data["sources"].append({"id": "orphan", "title": {"en": "A report nobody cites", "es": "Un informe que nadie cita"}, "url": "https://example.org/report"})
    r = view_run(tmp_path, data)
    assert r.returncode == 1 and "sources[" in r.stdout and "orphan" in r.stdout and "cited by no" in r.stdout, r.stdout


def test_view_two_sources_with_one_id_fail(tmp_path):
    data = example_data()
    data["sources"].append(dict(data["sources"][0]))
    r = view_run(tmp_path, data)
    assert r.returncode == 1 and "already the id" in r.stdout, r.stdout


@pytest.mark.parametrize("url", ["http://example.org/insecure", "report.pdf", "file 7", "", "ftp://example.org/x"])
def test_view_a_source_that_is_not_an_https_link_fails(tmp_path, url):
    r = view_run(tmp_path, changed(["sources", 0, "url"], url))
    assert r.returncode == 1 and "sources[0].url" in r.stdout, r.stdout


def test_view_a_source_without_a_url_fails(tmp_path):
    r = view_run(tmp_path, changed(["sources", 0, "url"], DELETE))
    assert r.returncode == 1 and "sources[0].url" in r.stdout and "required" in r.stdout, r.stdout


@pytest.mark.parametrize("title", ["Annex file 7 of the report", "Archivo 3 del informe", "The report.pdf", "Published on 3 May"])
def test_view_a_source_that_cites_a_file_in_place_of_its_link_fails(tmp_path, title):
    r = view_run(tmp_path, changed(["sources", 0, "title"], {"en": title, "es": title}))
    assert r.returncode == 1 and "sources[0].title" in r.stdout and "link" in r.stdout, r.stdout


# ---- the rules a schema cannot say

def test_view_the_causes_weights_over_one_hundred_fail(tmp_path):
    data = example_data()
    for cause in data["pain"]["causes"]:
        cause["weight"] = 60
    r = view_run(tmp_path, data)
    assert r.returncode == 1 and "pain.causes" in r.stdout and "at most 100" in r.stdout, r.stdout


def test_view_an_action_whose_owner_is_not_a_role_of_the_situation_fails(tmp_path):
    r = view_run(tmp_path, changed(["proposal", "actions", 0, "owner"], {"en": "A role nobody has", "es": "Un rol que nadie tiene"}))
    assert r.returncode == 1 and "proposal.actions[0].owner" in r.stdout and "roles of the current situation" in r.stdout, r.stdout


def test_view_the_four_cs_out_of_order_fail(tmp_path):
    data = example_data()
    data["proposal"]["four_cs"].reverse()
    r = view_run(tmp_path, data)
    assert r.returncode == 1 and "proposal.four_cs[0].c" in r.stdout, r.stdout


@pytest.mark.parametrize("path,value,expected", [
    (["pain", "key_message", "en"], words(31) + ".", "pain.key_message.en"),
    (["pain", "key_message", "es"], "Una frase. Y otra frase.", "pain.key_message.es"),
    (["key_statement", "en"], "One. Two. Three.", "key_statement.en"),
    (["pain", "paragraphs", 0, "en"], "Too short to be a paragraph.", "pain.paragraphs[0].en"),
    (["context", "evidence", 0, "statement", "en"], "A statement with $x^2$ in it.", "context.evidence[0].statement.en"),
    (["context", "evidence", 0, "statement", "en"], "A statement with an inline citation [1] in it.", "context.evidence[0].statement.en"),
    (["proposal", "actions", 0, "action", "en"], "Buy the product now.", "proposal.actions[0].action.en"),
    (["proposal", "actions", 0, "action", "es"], "Comprar el producto ahora.", "proposal.actions[0].action.es"),
    (["proposal", "risks", 0, "en"], "Our client has a price for it.", "proposal.risks[0].en"),
    (["trends", "items", 0, "effect", "en"], "Contact us for the offer.", "trends.items[0].effect.en"),
    (["illustrations", "pain", "caption", "en"], "One caption. And a second one.", "illustrations.pain.caption.en"),
])
def test_view_the_writing_limits_fail_with_the_field_path(tmp_path, path, value, expected):
    r = view_run(tmp_path, changed(path, value))
    assert r.returncode == 1 and EXEC in r.stdout and expected in r.stdout, r.stdout


# ---- the SDD section names the file and restates nothing


def test_brief_missing_section_fails_and_points_at_the_guide(tmp_path):
    r = view_run(tmp_path, brief=None)
    assert r.returncode == 1 and "Executive brief" in r.stdout and GUIDE in r.stdout


def test_brief_at_the_end_of_the_sdd_fails(tmp_path):
    r = view_run(tmp_path, sdd=sdd_text(brief=BRIEF, brief_after="ADR fit"))
    assert r.returncode == 1 and "right after" in r.stdout


def test_brief_after_another_section_fails(tmp_path):
    r = view_run(tmp_path, sdd=sdd_text(brief=BRIEF, brief_after="Research basis"))
    assert r.returncode == 1 and "right after" in r.stdout


def test_brief_without_the_data_file_line_fails(tmp_path):
    r = view_run(tmp_path, brief=BRIEF.replace("Data file: content/executive.json", "The data is somewhere."))
    assert r.returncode == 1 and "Data file: content/executive.json" in r.stdout, r.stdout


def test_brief_naming_another_file_fails(tmp_path):
    r = view_run(tmp_path, brief=BRIEF.replace("content/executive.json", "docs/executive.json"))
    assert r.returncode == 1 and "Data file: content/executive.json" in r.stdout, r.stdout


@pytest.mark.parametrize("plant", [
    "\n### Initiative\n\nA unit owns a problem.\n",
    "\n- one bullet that lists a part of the view\n",
    "\n| capability | outcome |\n|---|---|\n| a | b |\n",
    "\n1. a numbered list of outcomes\n",
])
def test_brief_that_restates_the_view_in_structure_fails(tmp_path, plant):
    r = view_run(tmp_path, brief=BRIEF + plant)
    assert r.returncode == 1 and "restates" in r.stdout and GUIDE in r.stdout, r.stdout


@pytest.mark.parametrize("lang", ["en", "es"])
def test_brief_that_copies_a_sentence_of_the_file_fails(tmp_path, lang):
    r = view_run(tmp_path, brief=BRIEF + "\n" + example_data()["key_statement"][lang].split(". ")[0] + "\n")
    assert r.returncode == 1 and "restates" in r.stdout, r.stdout


def test_brief_that_is_long_prose_fails(tmp_path):
    r = view_run(tmp_path, brief=BRIEF + "\n" + "A word that says nothing new about the file. " * 30 + "\n")
    assert r.returncode == 1 and "restates" in r.stdout and "words" in r.stdout, r.stdout


def test_brief_a_heading_inside_a_code_fence_does_not_count(tmp_path):
    r = view_run(tmp_path, brief=BRIEF + "\n```\n### Initiative\n```\n")
    assert r.returncode == 0, r.stdout


def test_brief_the_data_line_inside_a_code_fence_does_not_count(tmp_path):
    r = view_run(tmp_path, brief=BRIEF.replace("Data file: content/executive.json", "```\nData file: content/executive.json\n```"))
    assert r.returncode == 1 and "Data file: content/executive.json" in r.stdout, r.stdout


def test_brief_crlf_and_trailing_spaces_pass(tmp_path):
    tree = view_tree(tmp_path, sdd=sdd_text().replace("## Executive brief", "## Executive brief  "))
    sdd = tree / "docs" / "design" / "SDD.md"
    sdd.write_bytes(sdd.read_bytes().replace(b"\n", b"\r\n"))
    r = run("check_sdd.py", str(tree))
    assert r.returncode == 0, r.stdout


def test_brief_numbered_headings_in_place_pass(tmp_path):
    text = sdd_text().replace("## Problem and non-goals", "## 1. Problem and non-goals").replace("## Executive brief", "## 2. Executive brief")
    assert view_run(tmp_path, sdd=text).returncode == 0


def test_brief_two_executive_brief_sections_fail(tmp_path):
    text = sdd_text().replace("## Research basis", "## Executive brief\n\n" + BRIEF + "\n## Research basis")
    r = view_run(tmp_path, sdd=text)
    assert r.returncode == 1 and "more than one" in r.stdout, r.stdout


def test_brief_the_four_old_parts_are_not_a_valid_brief(tmp_path):
    old = ("### Initiative\n\nSome owner and initiative.\n\n### Outcomes\n\nSome outcomes.\n\n### Positioning\n\nSome value.\n\n"
           "### Credibility\n\nSome questions.\n\nData file: content/executive.json\n")
    r = view_run(tmp_path, brief=old)
    assert r.returncode == 1 and "restates" in r.stdout, r.stdout


# ---- a validation gate that skips for lack of a tool counts as not run (Q1), and the adversarial name is a prefix (M9c)

CONDITIONAL = {
    "an alias of skipif": "import pytest\n\nneeds = pytest.mark.skipif(1 + 1 == 3, reason='needs a tool')\n\n\n@needs\ndef test_adversarial_x():\n    assert True\n",
    "skipif on the test": "import shutil\nimport pytest\n\n\n@pytest.mark.skipif(shutil.which('node') is None, reason='needs node')\ndef test_adversarial_x():\n    assert True\n",
    "skipif in a pytestmark": "import pytest\n\npytestmark = pytest.mark.skipif(1 + 1 == 3, reason='r')\n\n\ndef test_adversarial_x():\n    assert True\n",
    "importorskip of a tool the repository does not pin": "import pytest\n\n\ndef test_adversarial_x():\n    pytest.importorskip('nosuchtool')\n    assert True\n",
    "module-level importorskip": "import pytest\n\npytest.importorskip('nosuchtool')\n\n\ndef test_adversarial_x():\n    assert True\n",
    "a skip in the body": "import pytest\n\n\ndef test_adversarial_x():\n    if 1 + 1 == 3:\n        pytest.skip('no tool')\n    assert True\n",
}


@pytest.mark.parametrize("case", sorted(CONDITIONAL))
def test_rereview_s3d_a_validation_gate_that_skips_for_lack_of_a_tool_fails(tmp_path, case):
    r = gate_tree(tmp_path, ADV, CONDITIONAL[case], "test_adversarial_x", where="validation")
    assert r.returncode == 1 and "FX-001" in r.stdout and "skips" in r.stdout, r.stdout


def test_rereview_s3d_a_second_gate_that_runs_in_the_same_row_passes(tmp_path):
    val = GOOD_VALIDATION.replace(f"`{ADV}::test_a` |", f"`tests/adversarial/test_cond.py::test_adversarial_x` and `{ADV}::test_a` |", 1)
    t = sdd_tree(tmp_path, validation=val, files={"tests/adversarial/test_cond.py": CONDITIONAL["skipif on the test"]})
    r = run("check_sdd.py", str(t))
    assert r.returncode == 0, r.stdout


def test_rereview_s3d_the_same_conditional_test_as_a_requirement_gate_is_still_a_precondition(tmp_path):
    r = gate_tree(tmp_path, "tests/test_cond.py", CONDITIONAL["skipif on the test"], "test_adversarial_x", where="requirement")
    assert r.returncode == 0, r.stdout


def test_rereview_s3d_an_importorskip_of_a_pinned_package_is_a_precondition_of_the_documented_setup(tmp_path):
    text = "import pytest\n\npytest.importorskip('pytest')\n\n\ndef test_adversarial_x():\n    assert True\n"
    val = GOOD_VALIDATION.replace(f"`{ADV}::test_a` |", "`tests/adversarial/test_cond.py::test_adversarial_x` |", 1)
    t = sdd_tree(tmp_path, validation=val, files={"tests/adversarial/test_cond.py": text, "requirements-dev.txt": "pytest==9.1.1\n"})
    r = run("check_sdd.py", str(t))
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("file,text,name", [
    ("tests/test_other.py", "def test_adversarialish_x():\n    assert True\n", "test_adversarialish_x"),
    ("tests/test_other.py", "def test_adversarial():\n    assert True\n", "test_adversarial"),
    ("frontend/src/other.test.ts", "it('adversarialish works', () => { expect(1).toBe(1) })\n", "adversarialish works"),
    ("frontend/src/other.test.ts", "it('adversarial works', () => { expect(1).toBe(1) })\n", "adversarial works"),
])
def test_rereview_m9c_a_name_that_only_starts_with_the_word_is_not_adversarial(tmp_path, file, text, name):
    r = gate_tree(tmp_path, file, text, name, where="validation")
    assert r.returncode == 1 and "not adversarial" in r.stdout, r.stdout


@pytest.mark.parametrize("file,text,name", [
    ("tests/test_other.py", "def test_adversarial_x():\n    assert True\n", "test_adversarial_x"),
    ("frontend/src/other.test.ts", "it('adversarial: works', () => { expect(1).toBe(1) })\n", "adversarial: works"),
])
def test_rereview_m9c_the_two_forms_of_the_name_pass(tmp_path, file, text, name):
    r = gate_tree(tmp_path, file, text, name, where="validation")
    assert r.returncode == 0, r.stdout


def local_only_tree(tmp: Path, note: str) -> Path:
    val = GOOD_VALIDATION.replace(f"| a NaN parameter is rejected | `{ADV}::test_a` |",
                                  f"| a NaN parameter is rejected {note} | `tests/adversarial/test_cond.py::test_adversarial_x` |", 1)
    assert val != GOOD_VALIDATION
    return sdd_tree(tmp, validation=val, files={"tests/adversarial/test_cond.py": CONDITIONAL["skipif on the test"]})


def test_rereview_s3d_a_local_only_row_with_a_reason_is_a_reviewed_exception(tmp_path):
    t = local_only_tree(tmp_path, "(local-only: needs node and the installed frontend, which the checks job lacks)")
    r = run("check_sdd.py", str(t))
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("note", ["", "(local-only: needs node)", "(local-only: TBD TBD TBD TBD TBD)", "(locally only needs node and the frontend)"])
def test_rereview_s3d_a_local_only_marker_without_a_reason_is_no_exception(tmp_path, note):
    r = run("check_sdd.py", str(local_only_tree(tmp_path, note)))
    assert r.returncode == 1 and "skips when a tool is missing" in r.stdout, r.stdout


# ---- check_ci_budget: what YAML reads is what is judged (F-B2, F-B3)

def ci_raw(tmp: Path, steps: str, top: str = "") -> Path:
    """A workflow whose steps are the given YAML text (a step starts at six spaces)."""
    (tmp / ".github" / "workflows").mkdir(parents=True)
    (tmp / "data-pipeline").mkdir()
    (tmp / ".github" / "workflows" / "ci.yml").write_text(
        "name: CI\non:\n  push:\n    branches: [main, develop]\nconcurrency:\n  group: g\n" + top
        + "jobs:\n  checks:\n    runs-on: ubuntu-latest\n    timeout-minutes: 10\n    steps:\n" + steps, encoding="utf-8")
    return tmp


FOLDED_FAIL = {
    "m10a a plain scalar continued on the next line": "      - name: s\n        run: python -m pytest tests/adversarial\n          tests/\n",
    "m10b a folded block": "      - name: s\n        run: >\n          python -m pytest tests/adversarial\n          tests/\n",
    "m10b a folded block with a strip indicator": "      - name: s\n        run: >-\n          python -m pytest tests/adversarial\n          tests/\n",
    "m10c a literal block indented by nine spaces": "      - name: s\n        run: |\n         pip install pytest==9.1.1\n         python -m pytest -q\n",
    "m10c a literal block with the whole suite": "      - name: s\n        run: |\n          python -m pytest -q\n",
    "a step that is a list item with run on the dash line": "      - run: |\n          python -m pytest -q\n",
    "a double-quoted scalar on two lines": "      - name: s\n        run: \"python -m pytest tests/adversarial\n          tests/\"\n",
    "a second pytest after a blank line of a block": "      - name: s\n        run: |\n          python -m pytest tests/adversarial -q\n\n          python -m pytest -q\n",
}


@pytest.mark.parametrize("case", sorted(FOLDED_FAIL))
def test_rereview_m10_a_command_is_read_as_yaml_reads_it(tmp_path, case):
    r = run("check_ci_budget.py", str(ci_raw(tmp_path, FOLDED_FAIL[case])))
    assert r.returncode == 1 and "tests run locally" in r.stdout, r.stdout


FOLDED_PASS = {
    "a folded block of exactly the allowance": "      - name: s\n        run: >\n          python -m pytest tests/adversarial -q\n",
    "a plain scalar continued into exactly the allowance": "      - name: s\n        run: pip install pytest==9.1.1 &&\n          python -m pytest tests/adversarial\n",
    "a literal block nine spaces deep, install then allowance": "      - name: s\n        run: |\n         pip install pytest==9.1.1\n         python -m pytest tests/adversarial -q\n",
    "a step after the block is not part of it": "      - name: s\n        run: |\n          python -m pytest tests/adversarial -q\n      - name: t\n        run: echo done\n",
}


@pytest.mark.parametrize("case", sorted(FOLDED_PASS))
def test_rereview_m10_the_allowance_in_other_yaml_forms_passes(tmp_path, case):
    r = run("check_ci_budget.py", str(ci_raw(tmp_path, FOLDED_PASS[case])))
    assert r.returncode == 0 and "ci budget: OK" in r.stdout, r.stdout


ALLOWED_RUN = "        run: python -m pytest tests/adversarial\n"


@pytest.mark.parametrize("steps,top", [
    ("      - name: s\n        env:\n          PYTEST_ADDOPTS: \"tests --override-ini=addopts=\"\n" + ALLOWED_RUN, ""),
    ("      - name: s\n" + ALLOWED_RUN, "env:\n  PYTEST_ADDOPTS: tests\n"),
    ("      - name: s\n        env:\n          PYTEST_PLUGINS: x\n" + ALLOWED_RUN, ""),
    ("      - name: s\n        env:\n          PYTEST_CONFIG: x\n" + ALLOWED_RUN, ""),
    ("      - name: s\n        run: export PYTEST_ADDOPTS=tests && python -m pytest tests/adversarial\n", ""),
    ("      - name: s\n        run: PYTEST_ADDOPTS=tests python -m pytest tests/adversarial\n", ""),
    ("      - name: s\n        run: |\n          export PYTEST_ADDOPTS=tests\n          python -m pytest tests/adversarial\n", ""),
])
def test_rereview_m10d_a_pytest_environment_variable_widens_the_allowance(tmp_path, steps, top):
    r = run("check_ci_budget.py", str(ci_raw(tmp_path, steps, top)))
    assert r.returncode == 1 and "PYTEST_" in r.stdout, r.stdout


def test_rereview_m10d_a_comment_that_names_the_variable_is_not_a_setting(tmp_path):
    r = run("check_ci_budget.py", str(ci_raw(tmp_path, "      # PYTEST_ADDOPTS would widen the suite\n      - name: s\n" + ALLOWED_RUN)))
    assert r.returncode == 0, r.stdout


# ---------------------------------------------------------------- check_tech_matrix

TABLE_HEAD = "| component | package | version | use | alternative considered |\n|---|---|---|---|---|\n"


def tech_tree(tmp: Path, rows: list[tuple[str, str]]) -> Path:
    (tmp / "docs" / "design").mkdir(parents=True)
    (tmp / "data-pipeline").mkdir()
    (tmp / "frontend").mkdir()
    (tmp / "requirements-precompute.txt").write_text("-r data-pipeline/requirements.txt\n", encoding="utf-8")
    (tmp / "requirements-dev.txt").write_text(
        "# comment\npytest==9.1.1\ninterpret-core[required]==0.7.9\n"
        "riskvalidation @ git+https://example.org/r.git@v1.2.3\n", encoding="utf-8")
    (tmp / "data-pipeline" / "requirements.txt").write_text("numpy==2.4.6\n", encoding="utf-8")
    (tmp / "frontend" / "package.json").write_text(json.dumps(
        {"dependencies": {"react": "19.3.0", "katex": "^0.16.47"}, "devDependencies": {"vite": "8.3.2"}}),
        encoding="utf-8")
    (tmp / "frontend" / "package-lock.json").write_text(json.dumps({"packages": {
        "": {"dependencies": {"react": "19.3.0", "katex": "^0.16.47"}, "devDependencies": {"vite": "8.3.2"}},
        "node_modules/katex": {"version": "0.16.47"}, "node_modules/react": {"version": "19.3.0"},
        "node_modules/vite": {"version": "8.3.2"}}}), encoding="utf-8")
    table = TABLE_HEAD + "".join(f"| c | `{p}` | `{v}` | u | a |\n" for p, v in rows)
    (tmp / "docs" / "design" / "SDD.md").write_text(f"## Technology and versions\n\n{table}\n## Resources\n",
                                                     encoding="utf-8")
    return tmp


GOOD_ROWS = [("pytest", "9.1.1"), ("interpret-core", "0.7.9"), ("riskvalidation", "v1.2.3"), ("numpy", "2.4.6"),
             ("react", "19.3.0"), ("katex", "0.16.47"), ("vite", "8.3.2")]


def test_tech_matrix_clean_tree_passes(tmp_path):
    r = run("check_tech_matrix.py", str(tech_tree(tmp_path, GOOD_ROWS)))
    assert r.returncode == 0 and "7 pinned" in r.stdout, r.stdout


def test_tech_matrix_a_pin_changed_only_in_requirements_fails(tmp_path):
    t = tech_tree(tmp_path, GOOD_ROWS)
    (t / "data-pipeline" / "requirements.txt").write_text("numpy==2.5.0\n", encoding="utf-8")
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1 and "numpy" in r.stdout and "2.5.0" in r.stdout and "2.4.6" in r.stdout


def test_tech_matrix_a_pin_missing_from_the_table_and_a_row_not_pinned_fail(tmp_path):
    rows = [r for r in GOOD_ROWS if r[0] != "vite"] + [("scipy", "1.0.0")]
    r = run("check_tech_matrix.py", str(tech_tree(tmp_path, rows)))
    assert r.returncode == 1 and "vite" in r.stdout and "scipy" in r.stdout


def test_tech_matrix_an_unpinned_python_requirement_fails(tmp_path):
    t = tech_tree(tmp_path, GOOD_ROWS)
    (t / "data-pipeline" / "requirements.txt").write_text("numpy>=2.0\n", encoding="utf-8")
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1 and "numpy" in r.stdout and "unpinned" in r.stdout


def test_tech_matrix_a_range_the_lock_does_not_resolve_fails(tmp_path):
    t = tech_tree(tmp_path, GOOD_ROWS)
    (t / "frontend" / "package-lock.json").write_text(json.dumps({"packages": {"": {}}}), encoding="utf-8")
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1 and "katex" in r.stdout and "unpinned" in r.stdout


def test_tech_matrix_a_missing_table_fails(tmp_path):
    t = tech_tree(tmp_path, GOOD_ROWS)
    (t / "docs" / "design" / "SDD.md").write_text("## Resources\n", encoding="utf-8")
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1 and "Technology and versions" in r.stdout

def edit_pkg(t: Path, fn) -> None:
    path = t / "frontend" / "package.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


def edit_lock(t: Path, fn) -> None:
    path = t / "frontend" / "package-lock.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_tech_t1_every_requirements_file_at_the_root_and_pyproject_are_read(tmp_path):
    t = tech_tree(tmp_path, GOOD_ROWS)
    (t / "requirements-api.txt").write_text("# api\nuvicorn==0.54.0\n", encoding="utf-8")
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1 and "uvicorn" in r.stdout and "absent from the SDD" in r.stdout, r.stdout
    (t / "requirements-api.txt").unlink()
    (t / "pyproject.toml").write_text('[project]\nname = "x"\ndependencies = ["tomli==2.0.1", "pyyaml>=6"]\n', encoding="utf-8")
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1 and "tomli" in r.stdout and "pyyaml" in r.stdout and "unpinned" in r.stdout, r.stdout


def test_tech_t2_the_same_package_pinned_twice_with_different_versions_fails(tmp_path):
    t = tech_tree(tmp_path, GOOD_ROWS)
    (t / "requirements-precompute.txt").write_text("numpy==2.4.7\n-r data-pipeline/requirements.txt\n", encoding="utf-8")
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1 and "numpy" in r.stdout and "2.4.7" in r.stdout and "2.4.6" in r.stdout, r.stdout
    (t / "requirements-precompute.txt").write_text("numpy==2.4.6\n-r data-pipeline/requirements.txt\n", encoding="utf-8")
    assert run("check_tech_matrix.py", str(t)).returncode == 0  # the same pin twice is not a conflict


@pytest.mark.parametrize("line", ["-e git+https://example.org/u.git#egg=unpinned", "--editable ./local", "https://example.org/u.zip",
                                  "git+https://example.org/u.git", "numpy==2.*", "numpy==2.4.*", "numpy==2.4.6,<3", "numpy===2.4.6.*"])
def test_tech_t3_editable_url_and_wildcard_requirements_fail(tmp_path, line):
    t = tech_tree(tmp_path, GOOD_ROWS)
    (t / "data-pipeline" / "requirements.txt").write_text(f"{line}\n", encoding="utf-8")
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1, r.stdout


def test_tech_t3_a_git_ref_pin_and_an_exact_pin_with_a_marker_still_pass(tmp_path):
    t = tech_tree(tmp_path, GOOD_ROWS)
    (t / "data-pipeline" / "requirements.txt").write_text('numpy==2.4.6 ; python_version >= "3.12"\n', encoding="utf-8")
    assert run("check_tech_matrix.py", str(t)).returncode == 0


def test_tech_t4_the_lock_must_record_the_package_json_spec(tmp_path):
    t = tech_tree(tmp_path, GOOD_ROWS)
    edit_pkg(t, lambda d: d["dependencies"].update(katex="^0.16.0"))  # the lock's root spec is ^0.16.47
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1 and "katex" in r.stdout and "^0.16.0" in r.stdout and "^0.16.47" in r.stdout, r.stdout


@pytest.mark.parametrize("spec", [">=0.16.47", "0.x", "*", "^1.0.0", "~0.15.0", "latest", "1.x || 2.x"])
def test_tech_t4_a_range_that_the_locked_version_does_not_satisfy_or_that_is_no_range_fails(tmp_path, spec):
    t = tech_tree(tmp_path, GOOD_ROWS)
    edit_pkg(t, lambda d: d["dependencies"].update(katex=spec))
    edit_lock(t, lambda d: d["packages"][""]["dependencies"].update(katex=spec))
    r = run("check_tech_matrix.py", str(t))
    if spec in (">=0.16.47", "0.x", "*"):  # satisfied by 0.16.47, so only the SDD version decides
        assert r.returncode == 0, r.stdout
    else:
        assert r.returncode == 1 and "katex" in r.stdout, r.stdout


@pytest.mark.parametrize("spec,locked,ok", [
    ("^0.16.47", "0.16.47", True), ("^0.16.47", "0.16.99", True), ("^0.16.47", "0.17.0", False), ("^1.2.3", "1.9.0", True),
    ("^1.2.3", "2.0.0", False), ("~5.9.3", "5.9.9", True), ("~5.9.3", "5.10.0", False), ("19.x", "19.3.0", True),
    ("19", "19.3.0", True), ("19.3", "19.3.5", True), (">=8.0.0", "8.3.2", True), (">8.3.2", "8.3.2", False),
    ("<9", "8.3.2", True), ("1.2.3 - 2.0.0", "1.5.0", True), (">=1 <2", "1.5.0", True), (">=1 <2", "2.0.0", False),
    ("^0.0.3", "0.0.3", True), ("^0.0.3", "0.0.4", False), ("^1.0.0-beta.1", "1.0.0-beta.2", True), ("^1.0.0", "1.1.0-beta.1", False),
    ("1.2.3", "1.2.3", True), ("1.2.3", "1.2.4", False), ("=1.2.3", "1.2.3", True), ("^8.3.2 || ^9", "9.0.1", True),
])
def test_tech_t4_the_range_satisfaction_follows_npm_semver(tmp_path, spec, locked, ok):
    t = tech_tree(tmp_path, [(p, v) for p, v in GOOD_ROWS if p != "katex"] + [("katex", locked)])
    edit_pkg(t, lambda d: d["dependencies"].update(katex=spec))
    edit_lock(t, lambda d: (d["packages"][""]["dependencies"].update(katex=spec),
                            d["packages"].update({"node_modules/katex": {"version": locked}})))
    r = run("check_tech_matrix.py", str(t))
    assert (r.returncode == 0) is ok, r.stdout


def test_tech_t4_the_sdd_version_is_the_locked_version_not_the_range(tmp_path):
    rows = [(p, "0.16.0" if p == "katex" else v) for p, v in GOOD_ROWS]
    r = run("check_tech_matrix.py", str(tech_tree(tmp_path, rows)))
    assert r.returncode == 1 and "katex" in r.stdout and "0.16.0" in r.stdout and "0.16.47" in r.stdout, r.stdout


def test_tech_t4_a_package_json_with_no_lock_fails(tmp_path):
    t = tech_tree(tmp_path, GOOD_ROWS)
    (t / "frontend" / "package-lock.json").unlink()
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1 and "package-lock.json" in r.stdout, r.stdout


@pytest.mark.parametrize("section", ["optionalDependencies", "peerDependencies"])
def test_tech_t5_other_dependency_sections_are_read(tmp_path, section):
    t = tech_tree(tmp_path, GOOD_ROWS)
    edit_pkg(t, lambda d: d.update({section: {"left-pad": "1.3.0"}}))
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1 and "left-pad" in r.stdout, r.stdout


def test_tech_t5_overrides_are_pins_too(tmp_path):
    t = tech_tree(tmp_path, GOOD_ROWS)
    edit_pkg(t, lambda d: d.update(overrides={"left-pad": "1.3.0"}))
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1 and "left-pad" in r.stdout, r.stdout
    edit_pkg(t, lambda d: d.update(overrides={"react": "19.3.1"}))
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1 and "react" in r.stdout and "19.3.1" in r.stdout, r.stdout
    edit_pkg(t, lambda d: d.update(overrides={"react": "^19.3.0"}))
    r = run("check_tech_matrix.py", str(t))
    assert r.returncode == 1 and "react" in r.stdout, r.stdout


# ---------------------------------------------------------------- check_contract_versions

CAT_HEAD = "| id | version | owner | schema file | example |\n|---|---|---|---|---|\n"
HIST_HEAD = "## History\n\n| contract | version | date | change | kind |\n|---|---|---|---|---|\n"
FIRST = "| a | 1.0.0 | 2026-10-11 | first | initial |\n| b | 1.0.0 | 2026-10-11 | first | initial |\n"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def versions_tree(tmp: Path, *, version: str = "1.0.0", lock_version: str = "1.0.0",
                  history: str | None = None) -> Path:
    (tmp / "docs" / "contracts" / "schemas").mkdir(parents=True)
    schema = tmp / "docs" / "contracts" / "schemas" / "a.schema.json"
    schema.write_bytes(b'{\n  "type": "object"\n}\n')
    (tmp / "docs" / "contracts" / "catalog.md").write_text(
        "## Contracts\n\n" + CAT_HEAD + f"| a | {version} | o | docs/contracts/schemas/a.schema.json | e |\n"
        "| b | 1.0.0 | o | - | e |\n\n" + (history if history is not None else HIST_HEAD + FIRST), encoding="utf-8")
    (tmp / "docs" / "contracts" / "versions.lock.json").write_text(json.dumps(
        {"a": {"version": lock_version, "schema": "docs/contracts/schemas/a.schema.json",
               "sha256": digest(schema)}}), encoding="utf-8")
    return tmp


def test_versions_clean_tree_passes_and_a_row_without_schema_is_skipped(tmp_path):
    r = run("check_contract_versions.py", "--repo-root", str(versions_tree(tmp_path)))
    assert r.returncode == 0, r.stdout


def test_versions_a_schema_edit_without_a_bump_fails(tmp_path):
    t = versions_tree(tmp_path)
    (t / "docs" / "contracts" / "schemas" / "a.schema.json").write_bytes(b'{"type": "string"}\n')
    r = run("check_contract_versions.py", "--repo-root", str(t))
    assert r.returncode == 1 and "without a version bump" in r.stdout and "a" in r.stdout
    assert run("check_contract_versions.py", "--repo-root", str(t), "--update").returncode == 1  # bump first


def test_versions_a_bump_without_updating_the_lock_fails_and_update_fixes_it(tmp_path):
    t = versions_tree(tmp_path, version="1.1.0", history=HIST_HEAD + FIRST + "| a | 1.1.0 | 2026-10-12 | field | minor |\n")
    (t / "docs" / "contracts" / "schemas" / "a.schema.json").write_bytes(b'{"type": "string"}\n')
    r = run("check_contract_versions.py", "--repo-root", str(t))
    assert r.returncode == 1 and "--update" in r.stdout
    u = run("check_contract_versions.py", "--repo-root", str(t), "--update")
    assert u.returncode == 0 and "1.0.0" in u.stdout and "1.1.0" in u.stdout, u.stdout
    assert run("check_contract_versions.py", "--repo-root", str(t)).returncode == 0


def test_versions_a_lowered_version_fails_and_update_refuses(tmp_path):
    t = versions_tree(tmp_path, version="1.0.0", lock_version="1.2.0")
    r = run("check_contract_versions.py", "--repo-root", str(t))
    assert r.returncode == 1 and "goes down" in r.stdout
    assert run("check_contract_versions.py", "--repo-root", str(t), "--update").returncode == 1


def test_versions_a_row_without_a_history_entry_for_its_version_fails(tmp_path):
    t = versions_tree(tmp_path, history=HIST_HEAD + "| b | 1.0.0 | 2026-10-11 | first | initial |\n")
    r = run("check_contract_versions.py", "--repo-root", str(t))
    assert r.returncode == 1 and "no History entry" in r.stdout and "a" in r.stdout


def test_versions_an_empty_or_missing_history_fails(tmp_path):
    r = run("check_contract_versions.py", "--repo-root", str(versions_tree(tmp_path, history=HIST_HEAD)))
    assert r.returncode == 1 and "History" in r.stdout
    r = run("check_contract_versions.py", "--repo-root", str(versions_tree(tmp_path / "b", history="")))
    assert r.returncode == 1 and "History" in r.stdout


def test_versions_a_missing_lock_says_to_run_update(tmp_path):
    t = versions_tree(tmp_path)
    (t / "docs" / "contracts" / "versions.lock.json").unlink()
    r = run("check_contract_versions.py", "--repo-root", str(t))
    assert r.returncode == 1 and "--update" in r.stdout
    assert run("check_contract_versions.py", "--repo-root", str(t), "--update").returncode == 0


def test_versions_the_digest_ignores_line_endings(tmp_path):
    t = versions_tree(tmp_path)
    schema = t / "docs" / "contracts" / "schemas" / "a.schema.json"
    schema.write_bytes(schema.read_bytes().replace(b"\n", b"\r\n"))
    assert b"\r\n" in schema.read_bytes()
    r = run("check_contract_versions.py", "--repo-root", str(t))
    assert r.returncode == 0, r.stdout


def test_versions_a_catalog_row_missing_from_the_lock_or_a_stale_lock_row_fails(tmp_path):
    t = versions_tree(tmp_path)
    lock = t / "docs" / "contracts" / "versions.lock.json"
    good = json.loads(lock.read_text(encoding="utf-8"))
    lock.write_text("{}", encoding="utf-8")
    r = run("check_contract_versions.py", "--repo-root", str(t))
    assert r.returncode == 1 and "not in the lock" in r.stdout
    lock.write_text(json.dumps({**good, "ghost": {"version": "1.0.0", "schema": "x", "sha256": "0"}}), encoding="utf-8")
    r = run("check_contract_versions.py", "--repo-root", str(t))
    assert r.returncode == 1 and "ghost" in r.stdout

# ---- --base: the schema against the base ref, the lock no longer the only witness (F-C1, F-C2, F-C3)

GIT = ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", "-c", "core.autocrlf=false"]


def commit(t: Path) -> str:
    if not (t / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=t, check=True)
    subprocess.run(["git", "add", "-A"], cwd=t, check=True, capture_output=True)
    subprocess.run([*GIT, "commit", "-q", "-m", "c"], cwd=t, check=True, capture_output=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=t, check=True, capture_output=True, text=True).stdout.strip()


SCHEMA = {"type": "object", "additionalProperties": False, "required": ["x"],
          "properties": {"x": {"type": ["string", "null"], "maxLength": 10, "enum": ["a", "b"]}, "y": {"type": "integer", "minimum": 0}}}


def schema_tree(tmp: Path, schema: dict | None = None) -> tuple[Path, str]:
    """A repository holding contract a (schema SCHEMA, 1.0.0) and its lock, committed: returns it and its base SHA."""
    t = versions_tree(tmp)
    path = t / "docs" / "contracts" / "schemas" / "a.schema.json"
    path.write_text(json.dumps(schema or SCHEMA, indent=2) + "\n", encoding="utf-8", newline="\n")
    (t / "docs" / "contracts" / "versions.lock.json").unlink()  # this schema is the tree's first: write the lock anew
    assert run("check_contract_versions.py", "--repo-root", str(t), "--update").returncode == 0
    return t, commit(t)


def bump(t: Path, doc: dict, version: str, kind: str, *, update: bool = True) -> None:
    (t / "docs" / "contracts" / "schemas" / "a.schema.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    cat = t / "docs" / "contracts" / "catalog.md"
    text = re.sub(r"\| a \| \d+\.\d+\.\d+ \| o \|", f"| a | {version} | o |", cat.read_text(encoding="utf-8"))
    cat.write_text(text + f"| a | {version} | 2026-10-12 | change | {kind} |\n", encoding="utf-8")
    if update:  # --update writes the lock, then reports the findings: a wrong History kind makes it exit 1 after writing
        run("check_contract_versions.py", "--repo-root", str(t), "--update")


def vrun(t: Path, base: str, *extra: str):
    return run("check_contract_versions.py", "--repo-root", str(t), "--base", base, *extra)


def narrowed(doc: dict, fn) -> dict:
    out = json.loads(json.dumps(doc))
    fn(out)
    return out


def test_versions_base_a_tree_equal_to_its_base_passes(tmp_path):
    t, base = schema_tree(tmp_path)
    r = vrun(t, base)
    assert r.returncode == 0, r.stdout


def test_versions_base_c4_the_lock_edited_by_hand_to_match_a_schema_change_fails(tmp_path):
    t, base = schema_tree(tmp_path)
    path = t / "docs" / "contracts" / "schemas" / "a.schema.json"
    path.write_text(path.read_text(encoding="utf-8").replace('"maxLength": 10', '"maxLength": 12'), encoding="utf-8", newline="\n")
    lock = t / "docs" / "contracts" / "versions.lock.json"
    doc = json.loads(lock.read_text(encoding="utf-8"))
    doc["a"]["sha256"] = digest(path)
    lock.write_text(json.dumps(doc), encoding="utf-8")
    assert run("check_contract_versions.py", "--repo-root", str(t)).returncode == 0  # offline: the lock alone, the known limit
    r = vrun(t, base)
    assert r.returncode == 1 and "a: " in r.stdout and "base" in r.stdout and "bump" in r.stdout, r.stdout


def test_versions_base_a_version_lower_than_the_base_fails_even_with_the_schema_unchanged(tmp_path):
    t, base = schema_tree(tmp_path)
    cat = t / "docs" / "contracts" / "catalog.md"
    cat.write_text(cat.read_text(encoding="utf-8").replace("| a | 1.0.0 | o |", "| a | 0.9.0 | o |")
                   + "| a | 0.9.0 | 2026-10-12 | x | patch |\n", encoding="utf-8")
    r = vrun(t, base)
    assert r.returncode == 1 and "goes down" in r.stdout, r.stdout


BREAKING = {
    "a removed property": lambda d: d["properties"].pop("y"),
    "a property newly required": lambda d: d["required"].append("y"),
    "a removed enum value": lambda d: d["properties"]["x"]["enum"].remove("b"),
    "a narrowed type": lambda d: d["properties"]["y"].update(type="boolean"),
    "a type list narrowed": lambda d: d["properties"]["x"].update(type=["string"]),
    "a tightened maxLength": lambda d: d["properties"]["x"].update(maxLength=4),
    "an added maxLength": lambda d: d["properties"]["y"].update(maxLength=4),
    "a raised minimum": lambda d: d["properties"]["y"].update(minimum=1),
    "an added maximum": lambda d: d["properties"]["y"].update(maximum=9),
    "an added pattern": lambda d: d["properties"]["x"].update(pattern="^a"),
    "additionalProperties turned false on a nested object": lambda d: d["properties"]["n"].update(additionalProperties=False),
    "a const changed": lambda d: d["properties"]["x"].update(const="a"),
}


@pytest.mark.parametrize("case", sorted(BREAKING))
def test_versions_base_c3_a_breaking_change_needs_a_major_bump(tmp_path, case):
    start = narrowed(SCHEMA, lambda d: d["properties"].update(n={"type": "object"}))  # a nested object, open at the base
    t, base = schema_tree(tmp_path, start)
    doc = narrowed(start, BREAKING[case])
    bump(t, doc, "1.1.0", "minor")
    r = vrun(t, base)
    assert r.returncode == 1 and "major" in r.stdout and "a: " in r.stdout, r.stdout
    bump(t, doc, "2.0.0", "major")
    r = vrun(t, base)
    assert r.returncode == 0, r.stdout


COMPATIBLE = {
    "a new optional property": lambda d: d["properties"].update(w={"type": "string"}),
    "a description": lambda d: d["properties"]["x"].update(description="what x is"),
    "a widened enum": lambda d: d["properties"]["x"]["enum"].append("c"),
    "a relaxed maxLength": lambda d: d["properties"]["x"].update(maxLength=20),
    "a lowered minimum": lambda d: d["properties"]["y"].update(minimum=-5),
    "integer widened to number": lambda d: d["properties"]["y"].update(type="number"),
    "a removed constraint on required": lambda d: d.update(required=[]),
    "additionalProperties opened": lambda d: d.update(additionalProperties=True),
    "an example": lambda d: d.update(examples=[{"x": "a"}]),
}


@pytest.mark.parametrize("case", sorted(COMPATIBLE))
def test_versions_base_c3_a_compatible_change_passes_as_minor(tmp_path, case):
    t, base = schema_tree(tmp_path)
    bump(t, narrowed(SCHEMA, COMPATIBLE[case]), "1.1.0", "minor")
    r = vrun(t, base)
    assert r.returncode == 0, r.stdout


def test_versions_base_the_history_kind_must_be_the_semver_step(tmp_path):
    t, base = schema_tree(tmp_path)
    bump(t, narrowed(SCHEMA, COMPATIBLE["a new optional property"]), "1.1.0", "patch")
    r = vrun(t, base)
    assert r.returncode == 1 and "kind" in r.stdout and "minor" in r.stdout, r.stdout
    t2, base2 = schema_tree(tmp_path / "b")
    bump(t2, narrowed(SCHEMA, COMPATIBLE["a new optional property"]), "2.0.0", "minor")
    r = vrun(t2, base2)
    assert r.returncode == 1 and "kind" in r.stdout and "major" in r.stdout, r.stdout


def test_versions_the_history_kind_is_checked_offline_too(tmp_path):
    t = versions_tree(tmp_path, version="1.1.0", history=HIST_HEAD + FIRST + "| a | 1.1.0 | 2026-10-12 | field | major |\n")
    run("check_contract_versions.py", "--repo-root", str(t), "--update")  # writes the lock, then reports the History kind
    r = run("check_contract_versions.py", "--repo-root", str(t))
    assert r.returncode == 1 and "kind" in r.stdout and "minor" in r.stdout, r.stdout


def test_versions_base_a_schema_removed_needs_a_major_history_row(tmp_path):
    t, base = schema_tree(tmp_path)
    cat = t / "docs" / "contracts" / "catalog.md"
    cat.write_text(cat.read_text(encoding="utf-8").replace("| docs/contracts/schemas/a.schema.json |", "| - |"), encoding="utf-8")
    lock = t / "docs" / "contracts" / "versions.lock.json"
    lock.write_text("{}", encoding="utf-8")
    r = vrun(t, base)
    assert r.returncode == 1 and "a: " in r.stdout and "major" in r.stdout and "removed" in r.stdout, r.stdout
    cat.write_text(cat.read_text(encoding="utf-8").replace("| a | 1.0.0 | o |", "| a | 2.0.0 | o |")
                   + "| a | 2.0.0 | 2026-10-12 | the schema is removed | major |\n", encoding="utf-8")
    r = vrun(t, base)
    assert r.returncode == 0, r.stdout


def test_versions_base_a_contract_row_removed_from_the_catalog_needs_a_major_history_row(tmp_path):
    t, base = schema_tree(tmp_path)
    cat = t / "docs" / "contracts" / "catalog.md"
    lines = [ln for ln in cat.read_text(encoding="utf-8").splitlines(keepends=True) if not ln.startswith("| a | 1.0.0 | o |")]
    cat.write_text("".join(lines), encoding="utf-8")
    (t / "docs" / "contracts" / "versions.lock.json").write_text("{}", encoding="utf-8")
    r = vrun(t, base)
    assert r.returncode == 1 and "a: " in r.stdout and "removed" in r.stdout, r.stdout


def test_versions_base_a_new_contract_is_a_first_release_and_needs_no_base_version(tmp_path):
    t, base = schema_tree(tmp_path)
    (t / "docs" / "contracts" / "schemas" / "c.schema.json").write_text('{"type": "object"}\n', encoding="utf-8")
    cat = t / "docs" / "contracts" / "catalog.md"
    text = cat.read_text(encoding="utf-8").replace("| b | 1.0.0 | o | - | e |\n", "| b | 1.0.0 | o | - | e |\n| c | 1.0.0 | o | docs/contracts/schemas/c.schema.json | e |\n")
    cat.write_text(text + "| c | 1.0.0 | 2026-10-12 | first | initial |\n", encoding="utf-8")
    assert run("check_contract_versions.py", "--repo-root", str(t), "--update").returncode == 0
    r = vrun(t, base)
    assert r.returncode == 0, r.stdout


def test_versions_base_a_base_without_a_catalog_means_every_contract_is_a_first_release(tmp_path):
    t = versions_tree(tmp_path / "t")
    (t / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=t, check=True)
    subprocess.run(["git", "add", "README.md"], cwd=t, check=True)
    subprocess.run([*GIT, "commit", "-q", "-m", "c"], cwd=t, check=True, capture_output=True)
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=t, check=True, capture_output=True, text=True).stdout.strip()
    r = vrun(t, base)
    assert r.returncode == 0, r.stdout


def test_versions_base_a_ref_that_cannot_be_resolved_fails_naming_fetch_depth(tmp_path):
    t, _ = schema_tree(tmp_path)
    r = vrun(t, "origin/develop")
    assert r.returncode == 1 and "origin/develop" in r.stdout and "fetch-depth: 0" in r.stdout, r.stdout


def test_versions_base_in_a_directory_that_is_not_a_git_repository_fails(tmp_path):
    t = versions_tree(tmp_path)
    r = vrun(t, "HEAD")
    assert r.returncode == 1 and "fetch-depth: 0" in r.stdout, r.stdout


def test_versions_base_crlf_in_the_working_tree_against_an_lf_base_is_no_change(tmp_path):
    t, base = schema_tree(tmp_path)
    path = t / "docs" / "contracts" / "schemas" / "a.schema.json"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    r = vrun(t, base)
    assert r.returncode == 0, r.stdout


# ---------------------------------------------------------------- check_ci_budget (the one suite CI may run)

def ci_tree(tmp: Path, step: str) -> Path:
    (tmp / ".github" / "workflows").mkdir(parents=True)
    (tmp / "data-pipeline").mkdir()
    (tmp / ".github" / "workflows" / "ci.yml").write_text(
        "name: CI\non:\n  push:\n    branches: [main, develop]\nconcurrency:\n  group: g\njobs:\n  checks:\n"
        f"    runs-on: ubuntu-latest\n    timeout-minutes: 10\n    steps:\n      - name: s\n        run: {step}\n", encoding="utf-8")
    return tmp


def test_ci_budget_allows_the_adversarial_suite_and_nothing_else_of_pytest(tmp_path):
    ok = run("check_ci_budget.py", str(ci_tree(tmp_path / "a", "pip install pytest==9.1.1 && python -m pytest tests/adversarial -q")))
    assert ok.returncode == 0, ok.stdout
    bad = run("check_ci_budget.py", str(ci_tree(tmp_path / "b", "python -m pytest tests -q")))
    assert bad.returncode == 1 and "runs the test suite in CI" in bad.stdout


ALLOWED_STEP = "pip install pytest==9.1.1 && python -m pytest tests/adversarial -q"


def ci_block(tmp: Path, lines: list[str]) -> Path:
    """A workflow whose step is a ``run: |`` block of the given lines."""
    (tmp / ".github" / "workflows").mkdir(parents=True)
    (tmp / "data-pipeline").mkdir()
    body = "".join(f"          {ln}\n" for ln in lines)
    (tmp / ".github" / "workflows" / "ci.yml").write_text(
        "name: CI\non:\n  push:\n    branches: [main, develop]\nconcurrency:\n  group: g\njobs:\n  checks:\n"
        f"    runs-on: ubuntu-latest\n    timeout-minutes: 10\n    steps:\n      - name: s\n        run: |\n{body}", encoding="utf-8")
    return tmp


@pytest.mark.parametrize("command", [
    ALLOWED_STEP,
    "python -m pytest tests/adversarial",
    "pip install pytest==9.1.1 && python -m pytest tests/adversarial",
    "pip install pytest==9.1.1 && python -m pytest tests/adversarial tests/template/adversarial -q",  # the template's own (BD-3)
])
def test_ci_budget_b6_the_allowance_in_its_exact_forms_passes(tmp_path, command):
    r = run("check_ci_budget.py", str(ci_tree(tmp_path, command)))
    assert r.returncode == 0 and "ci budget: OK" in r.stdout, r.stdout


@pytest.mark.parametrize("command", [
    "pip install pytest==9.1.1 && python -m pytest tests/adversarial tests/ -q",            # B-1
    "pip install pytest==9.1.1 && python -m pytest tests/adversarial/.. -q",                 # B-2
    "python -m pytest tests/adversarial -q; python -m pytest -q",                            # B-3
    "python -m pytest tests/adversarial tests/test_pipeline_smoke.py -q",                    # B-4
    "pip install pytest==9.1.1 && python -m pytest tests/adversarial -q --rootdir=. --override-ini=testpaths=tests "
    "-c pyproject.toml tests/test_pipeline_smoke.py",                                        # B-8
    "python -m pytest tests/adversarial -c pyproject.toml",
    "python -m pytest tests/adversarial --rootdir=.",
    "python -m pytest tests/adversarial -o testpaths=tests",
    "python -m pytest tests/adversarial --override-ini testpaths=tests",
    "python -m pytest tests/adversarial -p no:cacheprovider",
    "python -m pytest tests/adversarial --pyargs pipeline",
    "python -m pytest tests/adversarial && python -m pytest tests",
    "python -m pytest tests/adversarial | tee out.txt",
    "python -m pytest tests/adversarial -q # and more",
    "python -m pytest tests/adversarial -k a or b",
    "pytest -q",
    "python -m pytest",
    "python -m pytest tests/adversarialx",
    "pip install pytest==9.1.1 && cd data-pipeline && python -m pytest tests/adversarial",
    "pip install pytest && python -m pytest tests/adversarial -q",
    "pip install pytest==9.1.1 numpy && python -m pytest tests/adversarial -q",
    "echo ok; python -m pytest tests/adversarial -q",
])
def test_ci_budget_an_allowance_broader_than_the_adversarial_suite_fails(tmp_path, command):
    r = run("check_ci_budget.py", str(ci_tree(tmp_path, command)))
    assert r.returncode == 1 and "tests run locally" in r.stdout, (command, r.stdout)


def test_ci_budget_b7_a_line_continuation_adds_what_the_line_does_not_show(tmp_path):
    r = run("check_ci_budget.py", str(ci_block(tmp_path, ["pip install pytest==9.1.1 && python -m pytest tests/adversarial \\", "tests/"])))
    assert r.returncode == 1 and "tests run locally" in r.stdout, r.stdout
    r = run("check_ci_budget.py", str(ci_block(tmp_path / "b", ["python -m pytest \\", "tests/adversarial"])))
    assert r.returncode == 0, r.stdout  # joined, it is exactly the allowed command


def test_ci_budget_a_pytest_install_on_a_line_of_its_own_is_not_a_test_run(tmp_path):
    r = run("check_ci_budget.py", str(ci_block(tmp_path, ["pip install pytest==9.1.1", "python -m pytest tests/adversarial -q"])))
    assert r.returncode == 0, r.stdout
    r = run("check_ci_budget.py", str(ci_block(tmp_path / "b", ["pip install pytest==9.1.1", "python -m pytest tests -q"])))
    assert r.returncode == 1 and "tests run locally" in r.stdout, r.stdout


def test_ci_budget_a_second_line_of_a_block_is_judged_too(tmp_path):
    r = run("check_ci_budget.py", str(ci_block(tmp_path, ["python -m pytest tests/adversarial -q", "python -m pytest -q"])))
    assert r.returncode == 1 and "tests run locally" in r.stdout, r.stdout
