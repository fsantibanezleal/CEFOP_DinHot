"""Plants of template 0.15.005 (CEFOP_DinHot's adoption of 0.15.004, 2026-11-08).

A product that serves further files beyond its index (a benchmark document, model metrics, released model cards) adapted
``frontend/scripts/copy-data.mjs``, and then its test of that script was refused by the 0.15.003 plant, which counted every
``frontend/src`` test that imports any ``scripts/*.mjs`` as a base test. Since 0.15.005 the product puts that logic in an optional
module ``frontend/scripts/copy-data.product.mjs`` that the base script calls (cases of ``frontend/src/lib/copy-data.test.ts``, a base
test taken verbatim, run here through vitest), and a base script is a ``frontend/scripts/*.mjs`` that is not a ``*.product.mjs``."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from planting import NODE, NODE_MODULES, ROOT
from test_base_tests_0_15_003 import MARK, base_script_tests

needs_web = pytest.mark.skipif(NODE is None or not (NODE_MODULES / "vitest").is_dir(),
                               reason="needs node and `npm ci` in frontend/")

CASES = ("without a hook module", "lands the file a hook copies", "calls the hook once", "passes null as readiness",
         "absent path the hook declares", "stops the build with the hook problems", "when the hook throws",
         "no default function", "does not run the hook when a declared file is missing", "rebuilds the overlay from scratch",
         "adversarial: refuses a copied or absent path that leaves the overlay")


@needs_web
def test_the_base_copy_data_test_covers_the_product_hook(tmp_path: Path) -> None:
    # runs in the checkout itself (its real node_modules); never link_node_modules here, which replaces the folder it is given
    r = subprocess.run([NODE, str(NODE_MODULES / "vitest" / "vitest.mjs"), "run", "src/lib/copy-data.test.ts"],
                       cwd=ROOT / "frontend", capture_output=True, encoding="utf-8", errors="replace", timeout=900,
                       env={**os.environ, "CAOS_TEMP_ROOT": str(tmp_path)})
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
    text = (ROOT / "frontend/src/lib/copy-data.test.ts").read_text(encoding="utf-8")
    assert MARK in text
    for case in CASES:
        assert case in text, case


def plant(tmp_path: Path, name: str, body: str) -> Path:
    root = tmp_path / "product"
    path = root / "frontend" / "src" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return root


def test_a_test_of_a_product_script_without_the_mark_is_not_a_base_test(tmp_path: Path) -> None:
    root = plant(tmp_path, "lib/copy-data.product.test.ts", "import hook from '../../scripts/copy-data.product.mjs';\n")
    assert base_script_tests(root) == []
    root = plant(tmp_path, "lib/own.test.ts", "const u = new URL('../../scripts/copy-data.product.mjs', import.meta.url);\n")
    assert base_script_tests(root) == []


def test_adversarial_a_test_of_a_base_script_without_the_mark_is_still_a_base_test(tmp_path: Path) -> None:
    for name, body in (("lib/a.test.ts", "import { x } from '../../scripts/copy-data.mjs';\n"),
                       ("lib/b.test.ts", "const u = new URL('../../scripts/declared.mjs', import.meta.url);\n"),
                       ("c.test.ts", "import { x } from '../scripts/gate-script.mjs';\n")):
        found = base_script_tests(plant(tmp_path / name.replace("/", "_"), name, body))
        assert [p.name for p in found] == [name.split("/")[-1]], name


def test_adversarial_a_test_importing_a_base_and_a_product_script_is_still_a_base_test(tmp_path: Path) -> None:
    root = plant(tmp_path, "lib/both.test.ts",
                 "import a from '../../scripts/copy-data.product.mjs';\nimport b from '../../scripts/copy-data.mjs';\n")
    assert [p.name for p in base_script_tests(root)] == ["both.test.ts"]


def test_the_template_ships_the_base_copy_data_test_with_the_mark() -> None:
    found = {p.relative_to(ROOT).as_posix(): MARK in p.read_text(encoding="utf-8") for p in base_script_tests(ROOT)}
    assert found.get("frontend/src/lib/copy-data.test.ts") is True, found
