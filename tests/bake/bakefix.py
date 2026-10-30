"""Shared fixtures of the producer-side tests: small cases, a planted method registry and a sandbox bake.

The real methods are separate units, so the tests bake small cases (64 x 64 pixels, a few traps, tens of iterations) with the
planted methods of ``planted.py``; every contract, gate and artifact rule is exercised on the output exactly as it is on the
canonical bake. The sandbox lives under pytest's temporary directories, never under ``data/``.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for p in (str(ROOT / "data-pipeline"), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import planted  # noqa: E402

from pipeline.model.holo import methods  # noqa: E402

SETUP = {"wavelength_nm": 850, "focal_mm": 1.5, "na": 0.5, "n_imm": 1.0, "n_pix": 64, "pitch_um": 20, "pad": 2,
         "beam": {"kind": "gaussian", "waist_frac": 1.0}}
WIDE = [0.0, 1.0]


def trap(i, x, y, z=0.0, w=1.0, charge=0):
    return {"id": i, "x_um": x, "y_um": y, "z_um": z, "weight": w, "charge": charge}


def grid(n, spacing):
    return [trap(iy * n + ix, (ix - (n - 1) / 2) * spacing, (iy - (n - 1) / 2) * spacing) for iy in range(n) for ix in range(n)]


def record(case_id="C91_mini", **over) -> dict:
    rec = {"case_id": case_id, "setup": copy.deepcopy(SETUP), "device": None,
           "target": {"kind": "traps", "traps": grid(3, 4.0)}, "aberration": None, "methods": ["M02", "M04", "M06"],
           "reference_method": "M06", "budget": {"iterations": 12, "time_s": None}, "seed": 20261028,
           "feedback": {"gain": 0.7, "steps": 3, "camera": {"gain_rms": 0.15, "noise_rms": 0.0, "blur_bins": 0.0}},
           "dynamics": {"particle": "bead", "trap_id": 4, "power_mw": 10.0, "bead_radius_um": 0.5, "n_particle": 1.59,
                        "viscosity_pa_s": 0.00089, "temperature_k": 295.0, "n_steps": 16384, "dt_s": 5e-5},
           "rearrangement": None, "expect": {"efficiency": [0.2, 1.0], "rel_std_pct": [0.0, 60.0],
                                             "feedback_final_rel_std_pct": [0.0, 60.0], "fc_ratio": [0.4, 1.6]}}
    rec.update(over)
    if "expect" not in over:   # a case metric needs its driver
        if rec["feedback"] is None:
            rec["expect"].pop("feedback_final_rel_std_pct")
        if rec["dynamics"] is None:
            rec["expect"].pop("fc_ratio")
    return rec


def shaped_record() -> dict:
    return record("C92_disc", methods=["M08"], reference_method="M08", feedback=None, dynamics=None,
                  target={"kind": "shaped", "shape": "disc", "radius_um": 8.0, "signal_margin_bins": 2},
                  expect={"efficiency": [0.0, 1.0]})


def rearr_record() -> dict:
    return record("C93_rearr", target={"kind": "traps", "traps": grid(4, 4.0)}, methods=["M06"], reference_method="M06",
                  feedback=None, dynamics=None,
                  rearrangement={"loading_p": 0.7, "target_ids": [5, 6, 9, 10], "alpha": 1.5, "steps_per_move": 4},
                  expect={"efficiency": [0.0, 1.0], "min_transient": [0.0, 5.0], "final_filling": [0.0, 1.0]})


def refused_record() -> dict:
    return record("C94_far", target={"kind": "traps", "traps": [trap(0, 400.0, 0.0)]}, feedback=None, dynamics=None)


def records() -> list[dict]:
    return [record(), shaped_record(), rearr_record(), refused_record()]


def write_cases(path: Path, recs: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(recs), encoding="utf-8")
    return path


class Planted:
    """A planted registry: ``use()`` redirects the method registry to it for the duration of a ``with`` block."""

    def __init__(self, root: Path, ids: tuple[str, ...], name: str = "plantpkg"):
        self.base, self.path = planted.plant(root, ids, name)

    def __enter__(self):
        self.previous = methods._base
        if self.path not in sys.path:
            sys.path.insert(0, self.path)
        methods.reload(self.base)
        return self

    def __exit__(self, *exc):
        methods.reload(None if self.previous == methods.__name__ else self.previous)
        if self.path in sys.path:
            sys.path.remove(self.path)


@pytest.fixture(scope="session")
def planted_registry(tmp_path_factory):
    with Planted(tmp_path_factory.mktemp("planted"), ("M02", "M04", "M06", "M08")) as p:
        yield p


@pytest.fixture(scope="session")
def sandbox_bake(tmp_path_factory, planted_registry):
    """A bake of the small cases into ``<tmp>/derived``: returns ``(derived root, cases.json path, entries)``."""
    from pipeline import pipeline

    base = tmp_path_factory.mktemp("bake")
    cases = write_cases(base / "cases.json", records())
    entries = pipeline.run_all(output_root=base / "derived", cases_path=cases)
    return base / "derived", cases, entries
