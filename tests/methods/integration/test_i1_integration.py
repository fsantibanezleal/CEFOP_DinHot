"""I1: the interfaces between the bake and the real methods (form auto-selection, case inputs, shaped-target metrics, the
atom driver, the tuning grid, the disordered set, the parallel bake). Each test reproduces a failure of the first sandbox
bake (2026-10-28) or states the contract that fixes it. They use the real registry, never the planted one."""
from __future__ import annotations

import inspect
import json
import math
from pathlib import Path

import numpy as np
import pytest

from pipeline import pipeline, ranges
from pipeline.bake import bake_case
from pipeline.benchmark import geometries as G
from pipeline.benchmark import protocol
from pipeline.cases import build, library
from pipeline.core import expect as expectations
from pipeline.core import score as scoring
from pipeline.model.holo import methods
from pipeline.model.holo.core.geometry import Setup, focal_bin_m
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import Trap, TrapSet
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.baseline import _gs, m04_gs, m05_gaa, m06_gsw, m07_phase_fixed_wgs
from pipeline.stages import dynamics, export, infer

ROOT = Path(__file__).resolve().parents[3]
SETUP64 = {"wavelength_nm": 850, "focal_mm": 1.5, "na": 0.5, "n_imm": 1.0, "n_pix": 64, "pitch_um": 20, "pad": 2,
           "beam": {"kind": "gaussian", "waist_frac": 1.0}}


@pytest.fixture
def real_registry():
    prev = methods._base
    methods.reload(None)
    yield
    methods.reload(None if prev == methods.__name__ else prev)


def rec64(traps, methods_=("M06",), **over):
    rec = {"case_id": "C95_mini", "setup": dict(SETUP64), "device": None, "target": {"kind": "traps", "traps": traps},
           "aberration": None, "methods": list(methods_), "reference_method": methods_[0],
           "budget": {"iterations": 6, "time_s": None}, "seed": 20261028, "feedback": None, "dynamics": None,
           "rearrangement": None, "expect": {"efficiency": [0.0, 1.0]}}
    rec.update(over)
    return rec


def bin_grid(n, spacing_bins, setup=SETUP64):
    return library._grid(n, n, spacing_bins * library._bin_um(setup))


def trapset(setup: Setup, bins, z=0.0, charge=0):
    b = focal_bin_m(setup)
    return TrapSet(Trap(i, x * b, y * b, z, 1.0, charge) for i, (x, y) in enumerate(bins))


@pytest.fixture(scope="module")
def setup64():
    return build.setup_of(rec64(bin_grid(3, 6)))


def case_record(cid):
    return next(c for c in library.CASES if c.id == cid).record


# ---- F1: the form is chosen from the traps -------------------------------------------------------------------------

@pytest.mark.parametrize("module", [m04_gs, m05_gaa, m06_gsw, m07_phase_fixed_wgs])
def test_auto_form_is_fft_on_bins_and_point_off_bins(module, setup64):
    on = Target.from_traps(trapset(setup64, [(-6, -6), (6, -6), (0, 6), (-6, 0)]))
    off = Target.from_traps(trapset(setup64, [(-6.5, -6), (6, -6), (0, 6.25), (-6, 0)]))
    r_on = module.run(setup64, on, budget=Budget(4), rng=Rng(1))
    r_off = module.run(setup64, off, budget=Budget(4), rng=Rng(1))
    assert r_on.meta["form"] == "fft" and r_off.meta["form"] == "point"


@pytest.mark.parametrize("kw", [{"z": 3e-6}, {"charge": 1}])
def test_auto_form_is_point_for_3d_and_vortex_traps(kw, setup64):
    t = Target.from_traps(trapset(setup64, [(-6, -6), (6, -6), (0, 6)], **kw))
    assert m07_phase_fixed_wgs.run(setup64, t, budget=Budget(3), rng=Rng(2)).meta["form"] == "point"


def test_auto_form_equals_the_explicit_form_on_bins(setup64):
    t = Target.from_traps(trapset(setup64, [(-6, -6), (6, -6), (0, 6), (-6, 0)]))
    a = m07_phase_fixed_wgs.run(setup64, t, budget=Budget(8), rng=Rng(3))
    b = m07_phase_fixed_wgs.run(setup64, t, budget=Budget(8), rng=Rng(3), form="fft")
    assert np.array_equal(a.phi, b.phi)


def test_an_explicit_fft_form_still_refuses_off_bin_traps(setup64):
    t = Target.from_traps(trapset(setup64, [(-6.5, -6), (6, -6), (0, 6)]))
    with pytest.raises(ValueError, match="fft form"):
        m07_phase_fixed_wgs.run(setup64, t, budget=Budget(2), rng=Rng(1), form="fft")


@pytest.mark.parametrize("cid", ["C01_square_grid", "C02_grid_feedback", "C03_large_array", "C12_calibration"])
def test_grid_cases_sit_on_fft_bins(cid):
    """F8 and the C12 failure: case coordinates are rounded to 1e-4 um (1e-4 bin) and the tolerance was 1e-6 bin."""
    ctx = infer.case_context(case_record(cid))
    assert _gs.on_bins(ctx["setup"], ctx["target"].traps)


@pytest.mark.parametrize("cid", ["C05_multiplane_vortices", "C06_vortex_ring_line", "C10_rearrangement"])
def test_3d_vortex_and_rearrangement_cases_keep_their_off_bin_traps(cid):
    ctx = infer.case_context(case_record(cid))
    assert not _gs.on_bins(ctx["setup"], ctx["target"].traps)


# ---- F5: case inputs at the boundary -------------------------------------------------------------------------------

def test_b4_is_not_given_the_case_wavefront(real_registry):
    """B4 takes an ``aberration`` float (rms of residual aberrations); the driver passed it the Noll list (TypeError)."""
    rec = rec64(bin_grid(2, 6), ("B4",), aberration={"noll": {"4": 0.08, "5": 0.07}})
    out = infer.run_method(rec, "B4", budget=Budget(2))
    assert out.phi.shape == (64, 64)


def test_m14_is_given_the_case_wavefront_as_the_injected_system(real_registry):
    rec = rec64(bin_grid(2, 6), ("M14",), aberration={"noll": {"4": 0.08, "5": 0.07}})
    assert infer.case_inputs(rec, "M14", methods.get("M14").run) == {"injected": [0.0, 0.0, 0.0, 0.08, 0.07]}
    assert infer.case_inputs(rec, "B4", methods.get("B4").run) == {}


def rearr_rec():
    return rec64(bin_grid(4, 6), ("M16",), rearrangement={"loading_p": 0.8, "target_ids": [5, 6, 9, 10], "alpha": 1.5,
                                                          "steps_per_move": 4})


def test_m16_is_given_the_loaded_atoms_and_the_target_sites(real_registry):
    rec = rearr_rec()
    kw = infer.case_inputs(rec, "M16", methods.get("M16").run)
    assert {int(i) for i in kw["atoms"].ids} == set(library.random_loading(rec))
    assert {int(i) for i in infer.rearrangement_target(rec).traps.ids} == {5, 6, 9, 10}
    out = infer.run_method(rec, "M16", budget=Budget(4))
    assert out.meta["crossings"] == 0 and out.phi.shape == (64, 64)


def test_a_sorting_method_needs_a_rearrangement_block(real_registry):
    with pytest.raises(ValueError, match="no rearrangement"):
        infer.run_method(rec64(bin_grid(3, 6), ("M16",)), "M16", budget=Budget(2))


# ---- F2: a shaped target is judged by the signal region -------------------------------------------------------------

def shaped_rec():
    return rec64([], ("M08", "M04"), target={"kind": "shaped", "shape": "disc", "radius_um": 8.0, "signal_margin_bins": 2})


def test_shaped_score_carries_the_signal_metrics_and_no_trap_metric(real_registry):
    rec = shaped_rec()
    sc = infer.run_method(rec, "M08", budget=Budget(10), ctx=infer.case_context(rec)).score
    assert sc["signal_rms_error_pct"] > 0 and 0 < sc["signal_efficiency"] <= 1
    assert sc["rel_std_pct"] == pytest.approx(min(sc["signal_rms_error_pct"], scoring.REL_STD_CAP))
    assert sc["uniformity"] == pytest.approx(max(0.0, 1.0 - sc["signal_rms_error_pct"] / 100.0))
    assert sc["trap_intensity"] == []


def test_signal_error_agrees_with_the_methods_own_history(real_registry):
    rec = shaped_rec()
    out = infer.run_method(rec, "M08", budget=Budget(10), ctx=infer.case_context(rec))
    assert out.score["signal_rms_error_pct"] == pytest.approx(100.0 * out.history[-1]["error"], rel=1e-6)


def test_shaped_bake_flags_the_two_slots_and_summarises_the_signal_error(real_registry, tmp_path):
    rec = shaped_rec()
    rec["expect"] = {"M08.signal_rms_error_pct": [0.0, 1000.0], "M08.signal_efficiency": [0.0, 1.0]}
    manifest, fails = bake_case(rec, derived_dir=tmp_path, manifests_dir=tmp_path / "m", models_dir=tmp_path / "models")
    assert not fails, fails
    text = " ".join(f["flag"] for f in manifest["flags"])
    assert "signal_rms_error_pct" in text and "not trap metrics" in text
    trace = json.loads((tmp_path / manifest["artifact"]["path"]).read_text(encoding="utf-8"))
    assert "signal-region RMS error" in trace["summary"]["notes"]["en"]
    hist = trace["methods"]["M08"]["history"]
    assert all(0.0 <= p["uniformity"] <= 1.0 and 0.0 <= p["rel_std_pct"] <= 1000.0 for p in hist)


def test_summary_names_the_trap_metric_for_traps_and_the_signal_error_for_shapes():
    rows = {"M04": {"efficiency": 0.9, "rel_std_pct": 3.0}}
    assert "relative standard deviation" in export.summary(rows)["notes"]["en"]
    assert "signal-region RMS error" in export.summary(rows, shaped=True)["notes"]["en"]


def test_signal_metrics_are_known_to_the_expectation_check():
    assert expectations.parse_key("M10.signal_rms_error_pct") == ("M10", "signal_rms_error_pct")
    assert expectations.parse_key("signal_efficiency") == (None, "signal_efficiency")


# ---- F4: the atom ---------------------------------------------------------------------------------------------------

def one_trap_c03():
    rec = case_record("C03_large_array")
    return dict(rec, target={"kind": "traps", "traps": [t for t in rec["target"]["traps"] if t["id"] == 528]},
                methods=["M06"], feedback=None, budget={"iterations": 20, "time_s": None})


def test_the_atom_stays_in_the_map_and_oscillates_at_the_predicted_frequency(real_registry):
    """Oracle: the spectral peak of the simulated position against ``omega_r = sqrt(U |d2 I_hat| / m)`` of the same map."""
    rec = one_trap_c03()
    ctx = infer.case_context(rec)
    out = infer.run_method(rec, "M06", ctx=ctx)
    trace, metrics = dynamics.run(rec, out.phi, ctx["setup"])
    reach = max(math.hypot(x, y) for x, y in zip(trace["x_um"], trace["y_um"]))
    assert reach < dynamics.HALF_BINS * focal_bin_m(ctx["setup"]) * 1e6
    assert 0.8 <= metrics["fc_ratio"] <= 1.2, metrics
    assert trace["depth"]["unit"] == "uK"


def test_the_driver_refuses_a_hologram_that_does_not_trap_the_atom(real_registry):
    rec = one_trap_c03()
    ctx = infer.case_context(rec)
    with pytest.raises(ValueError):
        dynamics.run(rec, np.zeros((256, 256)), ctx["setup"])   # a flat phase: all the light in the zero order


# ---- F7 -------------------------------------------------------------------------------------------------------------

def test_every_fallback_tuning_key_is_a_keyword_of_its_method(real_registry):
    for mid, grid in protocol.FALLBACK_TUNING.items():
        params = inspect.signature(methods.get(mid).run).parameters
        for cand in grid:
            assert set(cand) <= set(params), (mid, cand, list(params))


def test_no_method_file_names_a_coordination_path():
    root = ROOT / "data-pipeline" / "pipeline" / "model" / "holo" / "methods"
    texts = {p: p.read_text(encoding="utf-8") for p in root.rglob("*.py")}
    bad = [str(p.relative_to(ROOT)) for p, t in texts.items() if "wip/" in t or "CAOS_MANAGE" in t]
    assert not bad, bad


def test_disordered_set_is_seeded_on_bins_and_spaced():
    s = library.ATOM
    a = library.disordered_set(30, 20, 5, 7, s)
    assert a == library.disordered_set(30, 20, 5, 7, s) and a != library.disordered_set(30, 20, 5, 8, s)
    b = library._bin_um(s)
    xy = np.array([(t["x_um"] / b, t["y_um"] / b) for t in a])
    assert np.allclose(xy, np.rint(xy), atol=2e-3) and np.abs(xy).max() <= 20 + 2e-3
    d = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1]) + np.eye(len(a)) * 1e9
    assert d.min() >= 5 - 1e-3


def test_the_819_set_fits_its_window():
    a = library.disordered_set(s=library.ATOM, **library.DISORDERED_819)
    assert len(a) == 819 and len({t["id"] for t in a}) == 819


def test_disordered_set_that_cannot_fit_is_an_error():
    with pytest.raises(ValueError, match="fit"):
        library.disordered_set(500, 5, 4, 1, library.ATOM)


def test_g6_pools_the_lattice_and_the_disordered_set_by_seed_parity():
    even = G.record("G6", device=False, seed=0)
    odd = G.record("G6", device=False, seed=1)
    assert len(even["target"]["traps"]) == 1024 and len(odd["target"]["traps"]) == 819
    ctx = infer.case_context(odd)
    assert _gs.on_bins(ctx["setup"], ctx["target"].traps)
    assert len(G.record("G6", device=False, seed=1, reduced=True)["target"]["traps"]) == 20


# ---- F6 and the manifest being a pure function of the inputs ----------------------------------------------------------

def two_cases():
    a = rec64(bin_grid(2, 6), ("M04", "M06"), case_id="C96_a")
    b = rec64(bin_grid(3, 6), ("M06", "M07"), case_id="C97_b", reference_method="M07")
    for r in (a, b):
        r["expect"] = {f"{r['reference_method']}.efficiency": [0.0, 1.0]}
    return [a, b]


def jobs_for(root: Path, recs):
    return [{"rec": r, "root": str(root), "manifests": str(root / "manifests"), "models": str(root / "models"),
             "allow_missing": False, "flags": []} for r in recs]


def comparable(doc: dict) -> dict:
    """A manifest or trace without what timing may change (the lane verdict and the bytes that carry it)."""
    doc = json.loads(json.dumps(doc))
    for k in ("gate", "lane"):
        doc.pop(k, None)
    doc.get("artifact", {}).pop("bytes", None)
    return doc


def test_parallel_bake_writes_the_same_artifacts_as_a_sequential_bake(real_registry, tmp_path):
    recs = two_cases()
    seq = pipeline.bake_jobs(jobs_for(tmp_path / "seq", recs), workers=1)
    par = pipeline.bake_jobs(jobs_for(tmp_path / "par", recs), workers=2)
    assert [r["case_id"] for r in par] == [r["case_id"] for r in seq] == ["C96_a", "C97_b"]
    assert all(not r["failures"] for r in par + seq) and all(r["peak_mb"] >= 0 for r in par)
    for cid in ("C96_a", "C97_b"):
        for rel in (f"manifests/{cid}.json", f"{cid}/trace.json"):
            a = json.loads((tmp_path / "seq" / rel).read_text(encoding="utf-8"))
            b = json.loads((tmp_path / "par" / rel).read_text(encoding="utf-8"))
            assert comparable(a) == comparable(b), rel


def test_two_bakes_of_the_same_inputs_give_the_same_manifest(real_registry, tmp_path):
    rec = two_cases()[0]
    outs = []
    for k in range(2):
        root = tmp_path / f"r{k}"
        m, fails = bake_case(dict(rec), derived_dir=root, manifests_dir=root / "manifests", models_dir=root / "models")
        assert not fails
        outs.append(comparable(m))
    assert outs[0] == outs[1]


def test_peak_memory_is_reported():
    assert pipeline.peak_memory_mb() > 0


# ---- measured ranges --------------------------------------------------------------------------------------------------

def test_range_rule_is_the_wider_of_ten_percent_and_the_seed_spread():
    assert ranges.propose([1.0, 1.0, 1.0], "rel_std_pct") == [0.9, 1.1]
    assert ranges.propose([1.0, 1.4, 1.2], "rel_std_pct") == [0.8, 1.6]
    assert ranges.propose([0.95, 0.96, 0.97], "uniformity")[1] == 1.0
    assert ranges.propose([0.0, 0.0, 0.0], "rel_std_pct") == [0.0, 0.0]


def test_a_measured_provisional_case_replaces_its_bands_and_an_anchor_case_keeps_them(monkeypatch):
    monkeypatch.setattr(library, "_measured_ranges", lambda: {"C01_square_grid": {"M06.efficiency": [0.5, 0.9]},
                                                              "C12_calibration": {"M06.efficiency": [0.1, 0.2],
                                                                                  "M02.rel_std_pct": [1.0, 2.0]}})
    cases = {c.id: c for c in library._with_measured(library._build())}
    assert cases["C01_square_grid"].record["expect"] == {"M06.efficiency": [0.5, 0.9]}
    c12 = cases["C12_calibration"].record["expect"]
    assert c12["M06.efficiency"] == [0.8, 1.0] and c12["M02.rel_std_pct"] == [1.0, 2.0]


def test_the_manifest_flags_the_form_each_method_chose(real_registry, tmp_path):
    on = rec64(bin_grid(3, 6), ("M06", "M07"))
    off = rec64(library._grid(3, 3, 3.1), ("M06", "M07"), case_id="C98_off")
    for rec, want in ((on, "M06=fft, M07=fft"), (off, "M06=point, M07=point")):
        rec["expect"] = {"M06.efficiency": [0.0, 1.0]}
        m, fails = bake_case(rec, derived_dir=tmp_path, manifests_dir=tmp_path / "m", models_dir=tmp_path / "models")
        assert not fails
        assert any("forward form chosen" in f["flag"] and want in f["flag"] for f in m["flags"]), m["flags"]
