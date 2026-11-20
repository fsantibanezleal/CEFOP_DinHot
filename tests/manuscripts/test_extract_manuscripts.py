"""``scripts/extract_manuscripts.py`` runs every reader of the bake and the benchmark in the order their inputs require.

The report reads the device-aware paper's ``beyond.json`` and imports its and the continuation paper's macros, ``extract.py`` reads
``acceptance.json``, and ``extract_methods.py`` reads the ``studio.json`` that ``extract.py`` writes. A reader left out or run before
its input leaves a paper printing the numbers of an earlier bake (review finding N-B2 of 2026-11-15).
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location("extract_manuscripts_under_test", ROOT / "scripts" / "extract_manuscripts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def em():
    return load()


def test_every_step_script_exists(em):
    for name, script, _args, _engine in em.STEPS:
        assert (ROOT / script).is_file(), (name, script)


def test_the_order_respects_the_inputs(em):
    order = [s[0] for s in em.STEPS]
    assert order.index("device-aware") < order.index("report")
    assert order.index("efficiency-uniformity") < order.index("report")
    assert order.index("report-acceptance") < order.index("report") < order.index("report-methods")


def test_every_reader_of_the_benchmark_or_the_bake_is_a_step(em):
    """A manuscript data script that opens the benchmark results or the bake manifests is a step (the learned warm-start paper reads
    only its model record and checks it itself, see the script's docstring; a script that only applies the benchmark's win rule to
    its own runs, as the flicker-bounded paper's does, reads no benchmark file)."""
    steps = {s[1] for s in em.STEPS}
    readers = set()
    for f in (ROOT / "manuscripts").glob("*/data/*.py"):
        text = f.read_text(encoding="utf-8")
        if re.search(r"results\.json|[\"']manifests[\"']|read_manifests|[\"']benchmark[\"']\s*/", text) and "def main" in text:
            readers.add(f.relative_to(ROOT).as_posix())
    readers.discard("manuscripts/learned-warm-start/data/measure.py")
    assert readers <= steps, sorted(readers - steps)


def test_skip_engine_and_only(em):
    names = [n for n, _ in em.plan(skip_engine=True)]
    assert "report-acceptance" not in names and names[-1] == "report-methods"
    assert [n for n, _ in em.plan(only=["report", "device-aware"])] == ["device-aware", "report"]
    with pytest.raises(SystemExit):
        em.plan(only=["nope"])


def test_dry_run_runs_nothing(em, capsys):
    assert em.main(["--dry-run"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert [line.split(":")[0] for line in out] == [s[0] for s in em.STEPS]
    assert 'measure.py --parts ""' in out[0]
