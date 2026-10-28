"""Adversarial checks of the shell 0.14.0 rules the template enforces (0.08.000): an animated SVG without its reduced-motion
block fails the guard script, and the gate runner always passes `--require-focus` to the shell gate, so an App without Focus
mode cannot pass. Each test plants the defect in a throwaway copy and runs the real script on it.

They need node (the guard reuses the shell's JavaScript analysis) and the installed shell; they skip when either is absent,
the same way as the web-script tests of ``test_requirements_refuted.py`` (CI's checks job runs ``npm ci`` first)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from planting import ROOT, add_gate_module, guard

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None or not (ROOT / "frontend" / "node_modules" / "@fasl-work").is_dir(),
                                reason="needs node and `npm ci` in frontend/")
OK = "check_svg_animation: OK"

ANIMATED = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50"><style>.a{animation:fade 4s ease-in-out infinite}'
            '@keyframes fade{0%{opacity:0}100%{opacity:1}}@@REDUCED@@</style><rect class="a" x="0" y="0" width="10" height="10" fill="var(--color-fg)"/></svg>')
REDUCED = "@media (prefers-reduced-motion: reduce){.a{animation:none;opacity:1}}"


def plant_svg(repo: Path, name: str, body: str) -> None:
    add_gate_module(repo)
    (repo / "frontend" / "public" / name).write_text(body, encoding="utf-8")


@needs_node
def test_the_guard_passes_the_clean_copy_and_counts_the_animated_example(repo: Path) -> None:
    add_gate_module(repo)
    r = guard(repo, "check_svg_animation.py", ok_marker=OK)
    assert r.returncode == 0 and OK in r.stdout, r.stdout
    animated = int(re.search(r"(\d+) animated", r.stdout).group(1))
    assert animated >= 1, f"the example must carry an animated illustration: {r.stdout}"


@needs_node
def test_an_animated_svg_with_its_reduced_motion_block_passes(repo: Path) -> None:
    plant_svg(repo, "planted-good.svg", ANIMATED.replace('@@REDUCED@@', REDUCED))
    r = guard(repo, "check_svg_animation.py")
    assert r.returncode == 0 and "planted-good.svg" not in r.stdout, r.stdout


@needs_node
def test_an_animated_svg_without_its_reduced_motion_block_fails(repo: Path) -> None:
    plant_svg(repo, "planted-bad.svg", ANIMATED.replace('@@REDUCED@@', ''))
    r = guard(repo, "check_svg_animation.py")
    assert r.returncode == 1 and "planted-bad.svg" in r.stdout and "prefers-reduced-motion" in r.stdout, r.stdout


@needs_node
def test_a_reduced_motion_block_that_does_not_stop_the_animation_fails(repo: Path) -> None:
    plant_svg(repo, "planted-weak.svg", ANIMATED.replace('@@REDUCED@@', '@media (prefers-reduced-motion: reduce){.a{opacity:1}}'))
    r = guard(repo, "check_svg_animation.py")
    assert r.returncode == 1 and "planted-weak.svg" in r.stdout and "animation: none" in r.stdout, r.stdout


@needs_node
def test_an_animation_longer_than_ten_seconds_fails(repo: Path) -> None:
    plant_svg(repo, "planted-slow.svg", (ANIMATED.replace('@@REDUCED@@', REDUCED)).replace("4s ease", "14s ease"))
    r = guard(repo, "check_svg_animation.py")
    assert r.returncode == 1 and "planted-slow.svg" in r.stdout and "limit is 10 s" in r.stdout, r.stdout


@needs_node
def test_an_animated_svg_in_the_example_that_loses_its_block_fails(repo: Path) -> None:
    add_gate_module(repo)
    path = repo / "frontend" / "public" / "executive" / "pain.svg"
    text = path.read_text(encoding="utf-8")
    stripped = re.sub(r"@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*?\}\s*\}", "", text)
    assert stripped != text, "the example pain.svg carries no reduced-motion block to remove"
    path.write_text(stripped, encoding="utf-8")
    r = guard(repo, "check_svg_animation.py")
    assert r.returncode == 1 and "executive/pain.svg" in r.stdout, r.stdout


def test_the_guard_without_the_shell_analysis_fails_instead_of_passing(repo: Path) -> None:
    r = guard(repo, "check_svg_animation.py")
    assert r.returncode == 1 and "npm ci" in r.stdout, r.stdout


@pytest.mark.skipif(NODE is None, reason="needs node")
def test_the_gate_runner_always_passes_require_focus_to_the_shell_gate(repo: Path) -> None:
    """A stub gate records its arguments: `--require-focus` is there with the default run and with a run that passes
    `--url` or its own flags, so no invocation of `npm run gate` measures an App that may lack Focus mode."""
    frontend = repo / "frontend"
    shell = frontend / "node_modules" / "@fasl-work" / "caos-app-shell"
    (shell / "bin").mkdir(parents=True)
    (shell / "package.json").write_text('{"name":"@fasl-work/caos-app-shell","version":"0.0.0"}', encoding="utf-8")
    (shell / "bin" / "caos-shell-gate.mjs").write_text(
        "import { writeFileSync } from 'node:fs';\nwriteFileSync(process.env.STUB_OUT, JSON.stringify(process.argv.slice(2)));\n", encoding="utf-8")
    out = repo / "stub-args.json"
    env = {**os.environ, "STUB_OUT": str(out)}
    for extra in ([], ["--url", "https://example.org"], ["--sizes", "1280x800", "--themes", "light"]):
        out.unlink(missing_ok=True)
        r = subprocess.run([NODE, str(frontend / "scripts" / "gate.mjs"), *extra], capture_output=True, encoding="utf-8", errors="replace", cwd=frontend, env=env)
        assert r.returncode == 0 and out.is_file(), r.stderr
        assert "--require-focus" in json.loads(out.read_text(encoding="utf-8")), (extra, out.read_text(encoding="utf-8"))

