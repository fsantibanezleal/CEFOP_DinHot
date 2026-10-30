"""Run product tests twice in child pytest processes: untouched (the control, which must pass) and with a defect planted in the
product's code around each test (which must fail). A requirement whose named test passes with the requirement broken has no gate.

``run_cases`` takes ``{requirement id: (test node id, [plants])}``, runs one control child and one planted child for the whole
table (the start-up of the product's test session is the larger cost), and returns a ``Cases`` object whose ``refuted(id)``
asserts one requirement."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def _child(nodeids: list[str], plants: dict, base: Path, tag: str) -> dict:
    report = base / f"{tag}.json"
    env = dict(os.environ, DINHOT_PLANTS=json.dumps(plants), DINHOT_PLANT_REPORT=str(report),
               PYTHONPATH=os.pathsep.join([str(HERE), os.environ.get("PYTHONPATH", "")]))
    cmd = [sys.executable, "-m", "pytest", *nodeids, "-p", "no:cacheprovider", "-W", "ignore", "-q", "--basetemp", str(base / tag),
           "-p", "plant_plugin"]
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", cwd=ROOT, env=env, timeout=1500)
    assert report.is_file(), f"the {tag} child wrote no report (exit {r.returncode}):\n{r.stdout[-1200:]}\n{r.stderr[-600:]}"
    return json.loads(report.read_text(encoding="utf-8"))


class Cases:
    def __init__(self, table: dict, control: dict | None, planted: dict) -> None:
        self.table, self.control, self.planted = table, control, planted

    @staticmethod
    def _outcomes(report: dict, nodeid: str) -> dict:
        return {k: v for k, v in report.items() if k == nodeid or k.startswith(nodeid + "[")}

    def refuted(self, rid: str, *, asserted: bool = False) -> None:
        """The named test passes untouched (when a control ran) and fails planted; ``asserted``: it fails on an assertion of the
        requirement, not on an error that the stand-in defect itself raised."""
        nodeid, plants = self.table[rid][:2]
        after = self._outcomes(self.planted, nodeid)
        if self.control is not None:
            before = self._outcomes(self.control, nodeid)
            assert before, f"{rid}: the control run found no test {nodeid}"
            assert all(v.get("outcome") == "passed" for v in before.values()), f"{rid}: {nodeid} must pass untouched: {before}"
        assert after, f"{rid}: the planted run found no test {nodeid}"
        for k, v in after.items():
            assert "plant_error" not in v, f"{rid}: the plant could not be applied to {k}: {v['plant_error']}"
            assert v.get("applied") == [p["target"] for p in plants], f"{rid}: the plant was not applied to {k}: {v}"
        failed = [v for v in after.values() if v.get("outcome") == "failed"]
        assert failed, f"{rid}: planting {[p['target'] for p in plants]} did not make {nodeid} fail: {after}"
        if asserted:
            assert any(v["crash"].lstrip().startswith(("assert", "AssertionError", "Failed: DID NOT RAISE")) for v in failed), (
                f"{rid}: the planted test failed on an error and not on an assertion of the requirement: {failed}")


def run_cases(table: dict, base: Path, *, control: bool = True) -> Cases:
    """``table``: ``{id: (node id, plants)}`` or ``{id: (node id, plants, True)}`` for a test whose module-scoped fixture is built
    under its plants and so needs a planted child of its own."""
    shared = {k: v for k, v in table.items() if len(v) < 3}
    alone = {k: v for k, v in table.items() if len(v) >= 3}
    nodeids = sorted({v[0] for v in table.values()})
    base.mkdir(parents=True, exist_ok=True)
    before = _child(nodeids, {}, base, "control") if control else None
    planted: dict = {}
    if shared:
        planted.update(_child(sorted({v[0] for v in shared.values()}), {v[0]: v[1] for v in shared.values()}, base, "planted"))
    for rid, v in alone.items():
        planted.update(_child([v[0]], {v[0]: v[1]}, base, "planted-" + rid.lower()))
    return Cases(table, before, planted)
