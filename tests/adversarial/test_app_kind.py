"""Adversarial checks of the App's kind (0.09.000, requirements WB-014 and WB-015): `product.json` says whether the App is a
workbench or a surface, and whether a surface waives Focus mode; `scripts/check_sdd.py` and the gate runner hold the same
rules. Each test plants one defect in a throwaway copy and runs the real guard, or the real runner against a stub shell gate."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from planting import add_schema, drop_row, guard, make_tree

NODE = shutil.which("node")
INPUTS = ("scripts/*.py", "docs/design", "tests", "data", "frontend/src/**/*.test.ts", "frontend/src/**/*.test.tsx", "frontend/scripts",
          "requirements*.txt", "data-pipeline/requirements.txt", "content", "frontend/public/executive", "product.json", "deploy/TARGET")
SDD = "docs/design/SDD.md"
VALIDATION = "docs/design/features/web/validation.md"
REASON = "this hub only links to studies and runs no simulation or dynamic synthetic scenario"
OTHER = "this console has an engine view that simulates a policy over the task families"
OK = "check_sdd: OK"


@pytest.fixture
def app_repo(tmp_path: Path) -> Path:
    return add_schema(make_tree(tmp_path / "repo", *INPUTS))


def set_product(repo: Path, **fields: object) -> None:
    path = repo / "product.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc.update(fields)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def set_row(repo: Path, rule: str | None) -> None:
    """Replace the rule cell of the SDD's ADR-0070 row (None: remove the row)."""
    path = repo / SDD
    out: list[str] = []
    for line in path.read_bytes().decode("utf-8").split("\n"):
        if line.startswith("| ADR-0070 |"):
            if rule is not None:
                out.append(f"| ADR-0070 | {rule} | `npm run gate` without `--require-focus` (G18) |")
            continue
        out.append(line)
    path.write_bytes("\n".join(out).encode("utf-8"))


def waive(repo: Path, reason: str = REASON, row: str | None = None) -> None:
    set_product(repo, app="surface", focus=False, focus_reason=reason)
    set_row(repo, f"not applicable: {row if row is not None else reason}")


def sdd(repo: Path) -> subprocess.CompletedProcess:
    return guard(repo, "check_sdd.py")


def runner(repo: Path, *extra: str) -> tuple[subprocess.CompletedProcess, list[str] | None]:
    """Run frontend/scripts/gate.mjs of the copy against a stub shell gate that records its arguments."""
    frontend = repo / "frontend"
    shell = frontend / "node_modules" / "@fasl-work" / "caos-app-shell"
    (shell / "bin").mkdir(parents=True, exist_ok=True)
    (shell / "package.json").write_text('{"name":"@fasl-work/caos-app-shell","version":"0.0.0"}', encoding="utf-8")
    (shell / "bin" / "caos-shell-gate.mjs").write_text(
        "import { writeFileSync } from 'node:fs';\nwriteFileSync(process.env.STUB_OUT, JSON.stringify(process.argv.slice(2)));\n", encoding="utf-8")
    out = repo / "stub-args.json"
    out.unlink(missing_ok=True)
    r = subprocess.run([NODE, str(frontend / "scripts" / "gate.mjs"), *extra], capture_output=True, encoding="utf-8", errors="replace",
                       cwd=frontend, env={**os.environ, "STUB_OUT": str(out)})
    return r, (json.loads(out.read_text(encoding="utf-8")) if out.is_file() else None)


def test_the_template_example_is_a_workbench_with_focus_and_passes(app_repo: Path) -> None:
    r = guard(app_repo, "check_sdd.py", ok_marker=OK)
    assert r.returncode == 0, r.stdout


def test_a_surface_with_focus_passes(app_repo: Path) -> None:
    set_product(app_repo, app="surface")
    r = guard(app_repo, "check_sdd.py", ok_marker=OK)
    assert r.returncode == 0, r.stdout


def test_a_surface_with_a_confirmed_waiver_passes(app_repo: Path) -> None:
    waive(app_repo)
    r = guard(app_repo, "check_sdd.py", ok_marker=OK)
    assert r.returncode == 0, r.stdout


def test_an_unknown_app_value_fails(app_repo: Path) -> None:
    set_product(app_repo, app="console")
    r = sdd(app_repo)
    assert r.returncode == 1 and "product.json" in r.stdout and '"app"' in r.stdout and "workbench" in r.stdout, r.stdout


def test_a_waiver_on_a_workbench_fails(app_repo: Path) -> None:
    set_product(app_repo, focus=False, focus_reason=REASON)
    set_row(app_repo, f"not applicable: {REASON}")
    r = sdd(app_repo)
    assert r.returncode == 1 and '"focus": false' in r.stdout and "workbench" in r.stdout, r.stdout


def test_a_waiver_on_a_workbench_that_names_itself_fails(app_repo: Path) -> None:
    set_product(app_repo, app="workbench", focus=False, focus_reason=REASON)
    set_row(app_repo, f"not applicable: {REASON}")
    assert sdd(app_repo).returncode == 1


def test_a_waiver_without_a_reason_fails(app_repo: Path) -> None:
    set_product(app_repo, app="surface", focus=False)
    set_row(app_repo, f"not applicable: {REASON}")
    r = sdd(app_repo)
    assert r.returncode == 1 and "focus_reason" in r.stdout, r.stdout


@pytest.mark.parametrize("reason", ["a hub of links", "TODO write the reason for the waiver of this view here", "tbd tbd tbd tbd tbd tbd tbd tbd tbd"])
def test_a_waiver_with_a_short_or_placeholder_reason_fails(app_repo: Path, reason: str) -> None:
    waive(app_repo, reason)
    r = sdd(app_repo)
    assert r.returncode == 1 and "focus_reason" in r.stdout, r.stdout


def test_a_waiver_without_its_sdd_row_fails(app_repo: Path) -> None:
    set_product(app_repo, app="surface", focus=False, focus_reason=REASON)  # the row still describes the Focus mode of the example
    r = sdd(app_repo)
    assert r.returncode == 1 and "ADR-0070" in r.stdout and "not applicable" in r.stdout, r.stdout


def test_a_waiver_whose_sdd_has_no_adr_0070_row_fails(app_repo: Path) -> None:
    set_product(app_repo, app="surface", focus=False, focus_reason=REASON)
    set_row(app_repo, None)
    r = sdd(app_repo)
    assert r.returncode == 1 and "ADR-0070" in r.stdout, r.stdout


def test_a_reason_that_differs_from_the_sdd_row_fails(app_repo: Path) -> None:
    waive(app_repo, REASON, row=OTHER)
    r = sdd(app_repo)
    assert r.returncode == 1 and "differs" in r.stdout and "focus_reason" in r.stdout, r.stdout


def test_an_sdd_row_that_says_not_applicable_with_no_waiver_fails(app_repo: Path) -> None:
    set_row(app_repo, f"not applicable: {REASON}")
    r = sdd(app_repo)
    assert r.returncode == 1 and "product.json" in r.stdout and "no waiver" in r.stdout, r.stdout


def test_focus_that_is_not_a_boolean_fails(app_repo: Path) -> None:
    set_product(app_repo, app="surface", focus="no")
    r = sdd(app_repo)
    assert r.returncode == 1 and '"focus"' in r.stdout and "true or false" in r.stdout, r.stdout


def test_a_reason_without_a_waiver_fails(app_repo: Path) -> None:
    set_product(app_repo, app="surface", focus_reason=REASON)
    r = sdd(app_repo)
    assert r.returncode == 1 and "focus_reason" in r.stdout, r.stdout


def test_requirement_wb_014_without_its_adversarial_row_fails(app_repo: Path) -> None:
    drop_row(app_repo, VALIDATION, "WB-014")
    r = sdd(app_repo)
    assert r.returncode == 1 and "WB-014" in r.stdout, r.stdout


def test_requirement_wb_015_without_its_adversarial_row_fails(app_repo: Path) -> None:
    drop_row(app_repo, VALIDATION, "WB-015")
    r = sdd(app_repo)
    assert r.returncode == 1 and "WB-015" in r.stdout, r.stdout


# ---------------------------------------------------------------- the gate runner, with a stub shell gate

needs_node = pytest.mark.skipif(NODE is None, reason="needs node")


@needs_node
def test_the_runner_passes_the_arguments_of_each_kind(app_repo: Path) -> None:
    r, args = runner(app_repo)
    assert r.returncode == 0 and args and "--require-focus" in args and "--workbench" not in args, (r.stderr, args)
    set_product(app_repo, app="surface")
    r, args = runner(app_repo)
    assert r.returncode == 0 and args[args.index("--workbench") + 1] == "" and "--require-focus" in args, (r.stderr, args)
    waive(app_repo)
    r, args = runner(app_repo)
    assert r.returncode == 0 and args[args.index("--workbench") + 1] == "" and "--require-focus" not in args, (r.stderr, args)


@needs_node
def test_a_surface_app_without_focus_keeps_the_requirement_for_every_extra_argument(app_repo: Path) -> None:
    """A surface with no waiver is measured with --require-focus however the run is started: an App with no focusable view
    cannot pass the shell gate, and nothing a run adds can lift the requirement."""
    set_product(app_repo, app="surface")
    for extra in ([], ["--url", "https://example.org"], ["--sizes", "1280x800"]):
        r, args = runner(app_repo, *extra)
        assert r.returncode == 0 and "--require-focus" in args, (extra, r.stderr, args)


@needs_node
def test_the_runner_refuses_a_waiver_without_its_sdd_row(app_repo: Path) -> None:
    set_product(app_repo, app="surface", focus=False, focus_reason=REASON)
    r, args = runner(app_repo)
    assert r.returncode != 0 and args is None and "focus_reason" in r.stderr and "ADR-0070" in r.stderr, (r.stdout, r.stderr)


@needs_node
def test_the_runner_refuses_a_waiver_on_a_workbench(app_repo: Path) -> None:
    set_product(app_repo, focus=False, focus_reason=REASON)
    set_row(app_repo, f"not applicable: {REASON}")
    r, args = runner(app_repo)
    assert r.returncode != 0 and args is None and '"focus"' in r.stderr, (r.stdout, r.stderr)


@needs_node
def test_the_runner_refuses_a_reason_that_differs_from_the_sdd_row(app_repo: Path) -> None:
    waive(app_repo, REASON, row=OTHER)
    r, args = runner(app_repo)
    assert r.returncode != 0 and args is None and "focus_reason" in r.stderr, (r.stdout, r.stderr)
