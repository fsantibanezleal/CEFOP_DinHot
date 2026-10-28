"""Adversarial checks for requirements whose gate is a script, a hook or a measured run rather than a test of their own
(0.05.000): each test plants the defect the requirement names in a throwaway copy and runs the real mechanism on it.

Tests that need Node (the web build scripts) or numpy (the root test sandbox) skip when the tool or the installed
packages are absent: CI's checks job installs neither, and the web job runs the same scripts on the real tree
(`npm run build`); locally they run after `npm ci`."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from planting import NODE, NODE_MODULES, edit, guard, link_node_modules, unlink_node_modules

needs_web = pytest.mark.skipif(NODE is None or not (NODE_MODULES / "@fasl-work").is_dir(),
                               reason="needs node and `npm ci` in frontend/")


def test_a_test_that_writes_a_committed_artifact_fails_the_session(repo: Path) -> None:
    pytest.importorskip("numpy")
    plant = repo / "tests" / "test_plant_writes_data.py"
    plant.write_text("from pathlib import Path\n\n\ndef test_writes():\n"
                     "    Path(__file__).resolve().parents[1].joinpath('data', 'derived', 'planted.txt').write_text('x')\n",
                     encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/test_plant_writes_data.py", "-v", "-p", "no:cacheprovider"],
                       capture_output=True, encoding="utf-8", errors="replace", cwd=repo, timeout=120)
    assert "1 passed" in r.stdout, r.stdout  # the planted test itself passes: only the session guard can fail the run
    assert r.returncode != 0 and "changed committed artifacts" in r.stdout and "data/derived/planted.txt" in r.stdout, r.stdout


def test_a_version_stated_twice_and_disagreeing_fails_the_coherence_guard(repo: Path) -> None:
    ok = guard(repo, "check_version_coherence.py")
    assert ok.returncode in (0, 1), ok.stdout  # the copy has no git history: the tag comparison may complain, nothing else
    before = ok.stdout
    current = json.loads((repo / "frontend" / "package.json").read_text(encoding="utf-8"))["version"]  # the version of the release under test
    edit(repo, "frontend/package.json", f'"version": "{current}"', '"version": "9.9.9"')
    r = guard(repo, "check_version_coherence.py")
    assert r.returncode == 1 and "9.9.9" in r.stdout and r.stdout != before, r.stdout


@needs_web
def test_a_build_without_the_routes_or_the_theme_script_fails(repo: Path) -> None:
    link_node_modules(repo / "frontend")
    try:
        dist = repo / "frontend" / "dist"
        script = repo / "frontend" / "scripts" / "materialize-routes.mjs"
        r = subprocess.run([NODE, str(script)], capture_output=True, encoding="utf-8", errors="replace", cwd=repo / "frontend")
        assert r.returncode == 1 and "dist/index.html is missing" in r.stderr, r.stderr
        dist.mkdir()
        (dist / "build.json").write_text("{}", encoding="utf-8")
        (dist / "index.html").write_text("<html><body>no theme script</body></html>", encoding="utf-8")
        r = subprocess.run([NODE, str(script)], capture_output=True, encoding="utf-8", errors="replace", cwd=repo / "frontend")
        assert r.returncode == 1 and "no pre-paint theme script" in r.stderr, r.stderr
        (dist / "index.html").write_text('<html data-theme="light"><body>app</body></html>', encoding="utf-8")
        r = subprocess.run([NODE, str(script)], capture_output=True, encoding="utf-8", errors="replace", cwd=repo / "frontend")
        assert r.returncode == 0 and "routes and 404.html written" in r.stdout, r.stderr
        routes = sorted(p.parent.name for p in dist.glob("*/index.html"))
        assert routes and (dist / "404.html").is_file(), "every standard route is its own page and 404.html is the app"
    finally:
        unlink_node_modules(repo / "frontend")


@needs_web
def test_a_schema_change_without_regenerated_types_fails_the_build_check(repo: Path) -> None:
    link_node_modules(repo / "frontend")
    try:
        script = repo / "frontend" / "scripts" / "gen-contract-types.mjs"
        clean = subprocess.run([NODE, str(script), "--check"], capture_output=True, encoding="utf-8", errors="replace", cwd=repo / "frontend")
        assert clean.returncode == 0 and "contract types: current" in clean.stdout, clean.stderr
        schema = repo / "docs" / "contracts" / "schemas" / "trace.schema.json"
        doc = json.loads(schema.read_text(encoding="utf-8"))
        doc["properties"]["planted_field"] = {"type": "number"}
        schema.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        r = subprocess.run([NODE, str(script), "--check"], capture_output=True, encoding="utf-8", errors="replace", cwd=repo / "frontend")
        assert r.returncode == 1 and "not current" in r.stderr, r.stderr
    finally:
        unlink_node_modules(repo / "frontend")


@pytest.mark.skipif(NODE is None, reason="needs node")
def test_the_gate_runner_fails_with_the_shell_gates_status_and_measures_the_products_own_name(repo: Path) -> None:
    """The measured gate (G4 deep links, G6 drawing area, G9 selection key) is the shell's; this runner must hand it
    the product's brand and the built site, and must not swallow its failure. A stub gate that exits 3 stands in."""
    frontend = repo / "frontend"
    shell = frontend / "node_modules" / "@fasl-work" / "caos-app-shell"
    (shell / "bin").mkdir(parents=True)
    (shell / "package.json").write_text('{"name":"@fasl-work/caos-app-shell","version":"0.0.0"}', encoding="utf-8")
    (shell / "bin" / "caos-shell-gate.mjs").write_text(
        "import { writeFileSync } from 'node:fs';\nwriteFileSync(process.env.STUB_OUT, JSON.stringify(process.argv.slice(2)));\n"
        "process.exit(Number(process.env.STUB_EXIT));\n", encoding="utf-8")
    out = repo / "stub-args.json"
    env = {**os.environ, "STUB_OUT": str(out), "STUB_EXIT": "3"}
    r = subprocess.run([NODE, str(frontend / "scripts" / "gate.mjs")], capture_output=True, encoding="utf-8", errors="replace", cwd=frontend, env=env)
    assert out.is_file(), "the runner never started the shell gate"
    args = json.loads(out.read_text(encoding="utf-8"))
    name = json.loads((repo / "product.json").read_text(encoding="utf-8"))["name"]
    assert r.returncode == 3, "the runner swallowed the gate's failure"
    assert args[args.index("--expect-brand") + 1] == name and args[args.index("--serve") + 1].endswith("dist"), args
    r = subprocess.run([NODE, str(frontend / "scripts" / "gate.mjs")], capture_output=True, encoding="utf-8", errors="replace", cwd=frontend,
                       env={**env, "STUB_EXIT": "0"})
    assert r.returncode == 0
