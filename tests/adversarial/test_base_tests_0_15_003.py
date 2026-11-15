"""Plants of template 0.15.003 (CAOS_ChancaDEM's adoption of 0.15.001, 2026-11-07): the tests under frontend/src that test a base
script are taken verbatim by every product. They say so, which is what CAOS_MANAGE tools/git/template_adopt.py reads to adopt them
as base files instead of leaving them behind as product content (ChancaDEM kept the 0.15.000 copy of gate-script.test.ts and never
received the two story-route tests of 0.15.001), and they pass for a product that declares its own story steps (the copy named the
example's four routes, so a product declaring other steps had to edit a verbatim file)."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
from planting import NODE, NODE_MODULES, link_node_modules, unlink_node_modules

ROOT = Path(__file__).resolve().parents[2]
MARK = "A product takes this file verbatim"
# A base script is a frontend/scripts/*.mjs that is not a product module (*.product.mjs, 0.15.005): a test of the latter is the product's.
SCRIPT_IMPORT = re.compile(r"""(?:from\s+|new URL\(\s*)['"](?:\.\./)+scripts/[^'"]+(?<!\.product)\.mjs['"]""")
needs_web = pytest.mark.skipif(NODE is None or not (NODE_MODULES / "@fasl-work").is_dir(),
                               reason="needs node and `npm ci` in frontend/")


def base_script_tests(root: Path) -> list[Path]:
    return sorted(p for p in (root / "frontend" / "src").rglob("*.test.ts*")
                  if SCRIPT_IMPORT.search(p.read_text(encoding="utf-8")))


def test_every_frontend_test_of_a_base_script_says_it_is_taken_verbatim() -> None:
    found = base_script_tests(ROOT)
    rels = [p.relative_to(ROOT).as_posix() for p in found]
    assert {"frontend/src/gate-script.test.ts", "frontend/src/lib/declared.test.ts"} <= set(rels), rels
    unmarked = [r for p, r in zip(found, rels) if MARK not in p.read_text(encoding="utf-8")]
    assert not unmarked, f"a base test under frontend/src that does not say it is taken verbatim: {unmarked}"


@needs_web
def test_the_gate_runner_test_passes_for_a_product_with_its_own_story_steps(repo: Path) -> None:
    product = json.loads((repo / "product.json").read_text(encoding="utf-8"))
    product["showcase"] = {"story_routes": ["/story/measure", "/story/inside", "/story/solve"]}
    (repo / "product.json").write_text(json.dumps(product, indent=2), encoding="utf-8")
    link_node_modules(repo / "frontend")
    try:
        r = subprocess.run([NODE, str(NODE_MODULES / "vitest" / "vitest.mjs"), "run", "src/gate-script.test.ts"],
                           cwd=repo / "frontend", capture_output=True, encoding="utf-8", errors="replace", timeout=900)
    finally:
        unlink_node_modules(repo / "frontend")
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
    assert "failed" not in r.stdout.split("Test Files")[-1].split("\n")[0], r.stdout[-2000:]
