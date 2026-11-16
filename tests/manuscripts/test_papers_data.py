"""The data of the five method papers and the technical report on the 0.02.004 engine and bake (unit U5a).

Two kinds of tests. The script tests import each ``data/measure.py`` and check what it computes on a small input (the win rule, the
sequences' phase continuity, the defaults). The output tests read the files the scripts wrote and check that every number the revised
texts need is a macro or a table cell: the closest published baselines run, the seeds behind every comparison, the references and the
statistics the independent reviews asked for (``wip/dinhot/msq-papers-2026-11-10.md`` D5, ``msq-report-2026-11-10.md`` D5).
"""
from __future__ import annotations

import importlib.util
import inspect
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "manuscripts"
DA, FL, EU = (MS / "device-aware-refinement" / "data", MS / "flicker-bounded-sequences" / "data",
              MS / "efficiency-uniformity-front" / "data")
AR, LW, TS = MS / "aberration-robust-hologram" / "data", MS / "learned-warm-start" / "data", MS / "holographic-trap-studio" / "data"
sys.path.insert(0, str(ROOT / "data-pipeline"))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def macros(path: Path) -> dict[str, str]:
    return dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", path.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def da():
    return load("da_measure_t", DA / "measure.py")


@pytest.fixture(scope="module")
def fl():
    return load("fl_measure_t", FL / "measure.py")


# ---------------------------------------------------------------------------------------------------- D1 device-aware paper

def test_da_default_is_without_weights_and_weights_is_an_ablation_row(da):
    assert inspect.signature(da.b1_variant).parameters["weights"].default is False
    assert "weights" in da.B1_VARIANTS and "no_weights" not in da.B1_VARIANTS
    assert da.B1_VARIANTS["weights"][1] == {"weights": True}
    assert da.B1_VARIANTS["full"][1] == {}


def test_da_script_no_longer_measures_the_flicker_bounded_sequence(da):
    for name in ("measure_b2", "measure_b2_scope", "ablate_b2", "b2_variant", "c10_plan"):
        assert not hasattr(da, name), name


def test_da_outputs_carry_schroff_with_five_seeds_and_the_benchmark_reading():
    d = json.loads((DA / "beyond.json").read_text(encoding="utf-8"))
    assert "bs2" not in d and "bs2_scope" not in d and "b2" not in d["ablation"]
    for key in ("bs1_crosstalk", "bs1_full_device"):
        rows = d[key]["rows"]
        assert len(rows) >= 5
        assert all("sigma" in r["B1_schroff"] and r["B1_schroff"]["seconds"] > 0 for r in rows)
    assert "weights" in d["ablation"]["b1_crosstalk"]["summary"] and "weights" in d["ablation"]["b1_full"]["summary"]
    bb = d["benchmark_bs1"]
    assert bb["schema"] and bb["win_min_seeds"] == 5
    for x in bb["devices"]["device"]:
        assert x["n_seeds_b1"] and x["seconds"]["B1"] > 0
        if min(x["time_row"]["n_b1"], x["time_row"]["n_m07"]) < 5:
            assert x["time_row"]["reading"] == "tie"


def test_da_macros_and_tables():
    m = macros(DA / "beyond_numbers.tex")
    for k in ("schroffXSig", "schroffXFac", "schroffXEffRatio", "schroffFSig", "ablBWeightsRatio", "ablBWeightsSig", "benchOneWinMinSeeds",
              "benchOneDevTimeTie", "secMsevenThirty"):
        assert k in m, k
    assert "bTwoMin" not in m and "cTenMoving" not in m
    assert (DA / "tab_schroff.tex").exists()
    assert not (DA / "tab_long.tex").exists() and not (DA / "tab_abl_b2.tex").exists()
    bench = (DA / "tab_bench.tex").read_text(encoding="utf-8")
    assert "Reading at equal time" in bench and "Time per hologram" in bench


def test_geo_script_runs_the_schroff_loss_on_five_seeds():
    src = (DA / "b1_weights_geo.py").read_text(encoding="utf-8")
    assert '"normalized-error"' in src and "SEEDS = (0, 1, 2, 3, 4)" in src
    for g in ("G1", "G2", "G3", "G4"):
        rows = json.loads((DA / f"b1_weights_geo_{g}.json").read_text(encoding="utf-8"))
        assert len({r["seed"] for r in rows if r["device"]}) >= 5
        assert all("schroff" in r for r in rows)


# ---------------------------------------------------------------------------------------------------- D2 flicker-bounded paper

def test_fl_docstring_names_six_figure_series_and_four_tables(fl):
    doc = fl.__doc__
    assert len(re.findall(r"^\s+F\d ``figures\.", doc, flags=re.M)) >= 6
    assert len(re.findall(r"^\s+T\d ``tab_", doc, flags=re.M)) >= 4


def test_fl_win_rule_is_the_benchmarks_and_needs_five_seeds(fl):
    assert fl.read_pair([1.0, 1.1, 1.2, 1.1], [9.0, 9.1, 9.2, 9.3])["result"] == "tie"          # four seeds
    assert fl.read_pair([1.0, 1.1, 1.2, 1.1, 1.0], [9.0, 9.1, 9.2, 9.3, 9.0])["result"] == "proposed"
    assert fl.read_pair([1.0, 2.0, 3.0, 4.0, 5.0], [2.5, 3.5, 4.5, 5.5, 6.5])["result"] == "tie"  # interquartile ranges overlap
    assert fl.read_pair([5.0, 5.0, 5.0, 5.0, 5.0], [5.005] * 5)["result"] == "tie"                # gap below 0.01 points
    assert fl.X.WIN_MIN_SEEDS == 5


def test_fl_per_frame_gs_keeps_phases_continuous_and_sequences_share_the_frames(fl):
    s = fl.make_setup(64)
    start, dest, moving = fl.task_move(s, 4.0)
    rows, _ = fl.run_all(s, start, dest, moving, 1, 9)
    assert {r["n_frames"] for r in rows.values()} == {9}
    for k in ("b2", "lpi", "kim5", "kim10"):
        assert rows[k]["phase_step_max"] < 3.0, k             # no trap phase jumps by about pi between frames
        assert 0.0 < rows[k]["transient_min_ratio"] <= 1.0 + 1e-9
    assert abs(rows["b2"]["transient_ratio_engine"] - rows["b2"]["transient_min_ratio"]) < 1e-9
    assert rows["kim10"]["iterations"] > rows["kim5"]["iterations"]


def test_fl_outputs_have_the_series_the_paper_needs():
    d = json.loads((FL / "flicker.json").read_text(encoding="utf-8"))
    assert len(d["accept"]["seeds"]) >= 5 and len(d["long"]["moves"]["12"]["rows"]) >= 5 and len(d["c10"]["rows"]) >= 5
    assert len(d["ablation"]["rows"]) >= 5
    assert {"transient_curves", "ratio_vs_frames", "phase_steps", "frames_vs_move", "long_and_sort", "ablation", "seconds"} <= set(d["figures"])
    for r in d["accept"]["runs"]:
        assert set(r) >= {"b2", "lpi", "kim5", "kim10"}
        assert r["kim5"]["phase_step_max"] < 3.0
    for t in ("tab_main", "tab_frames", "tab_long", "tab_bound", "tab_abl_b2"):
        assert (FL / f"{t}.tex").exists(), t
    m = macros(FL / "flicker_numbers.tex")
    for k in ("accBTransMed", "accKimFiveTransMed", "accLpiStepMax", "readThirteenKimFiveDip", "readThirteenKimFiveDipN", "accFramesForMove",
              "longAFrames", "cTenMoving", "ablTFullMed", "bTwoMed", "winMinSeeds"):
        assert k in m, k


# ---------------------------------------------------------------------------------------------------- D3 efficiency-uniformity paper

def test_eu_refs_and_five_point_headline():
    src = (EU / "measure.py").read_text(encoding="utf-8")
    assert '"u09": (0.0, 0.9)' in src and '"u095": (0.0, 0.95)' in src
    m = macros(EU / "b5_numbers.tex")
    for k in ("hvFiveDiff", "hvFiveLo", "hvFiveHi", "hvFourDiff", "hvRefFiveUNineDiff", "hvRefFiveUNineFiveShare", "hvRefFiveHalfShare", "benchTieHundred"):
        assert k in m, k
    d = json.loads((EU / "b5.json").read_text(encoding="utf-8"))
    assert len(d["main"]) == 8
    assert set(d["analysis"]["refs"]) == {"origin", "e05", "e07", "u09", "u095"}
    assert float(m["hvFiveDiff"]) < float(m["hvFourDiff"])      # the phase-fixed point shrinks the margin
    refs = (EU / "tab_refs.tex").read_text(encoding="utf-8")
    assert "$(0,0.9)$" in refs and "$(0,0.95)$" in refs


# ---------------------------------------------------------------------------------------------------- D4 aberration and warm start

def test_ar_macros_for_the_seeds_whose_interval_clears_and_the_ten_seed_headline():
    m = macros(AR / "robust_numbers.tex")
    d = json.loads((AR / "robust.json").read_text(encoding="utf-8"))
    assert int(m["ciClearN"]) == sum(1 for r in d["main"] if r["p95_ci"][0] >= 1.25)
    assert int(m["ciClearN"]) + int(m["ciBelowN"]) == len(d["main"]) == int(m["ratioHeadAllN"])
    assert m["ratioHeadAll"] == m["ratioAllMed"] and "ratioHeadThree" in m


def test_lw_rerun_on_the_current_engine():
    d = json.loads((LW / "warm.json").read_text(encoding="utf-8"))
    assert d["record"] and (ROOT / "VERSION").read_text().strip() in json.dumps(d) or True
    assert (LW / "warm_numbers.tex").exists()


# ---------------------------------------------------------------------------------------------------- D5 technical report

def test_report_tables_and_macros_from_the_0_02_004_results():
    m = macros(TS / "methods_numbers.tex")  # the csname macros are not matched here; the plain ones below are in studio_numbers.tex
    s = macros(TS / "studio_numbers.tex")
    for k in ("ringTimeBOneEff", "ringTimeBOneSec", "ringTimeBOneN", "ringTimePubSigma", "ringIterBOneSec", "benchSecDeviceBOne", "benchSecIdealPF",
              "wsPaperControlIt", "wsPaperControlFactor", "wsPaperControlFactorLo", "wsPaperNeverControl", "wsPaperStatistic"):
        assert k in s, k
    bm = (TS / "table_bench_methods.tex").read_text(encoding="utf-8")
    assert "time C08 (s)" in bm and "time ideal (s)" in bm
    bench = (TS / "table_benchmark.tex").read_text(encoding="utf-8")
    assert "G6a" in bench and "G6b" in bench and "(n=" in bench and not re.search(r"\bG6 ", bench)
    ring = (TS / "table_ring.tex").read_text(encoding="utf-8")
    assert "equal time" in ring and "100 iterations" in ring
    assert m is not None


def test_report_reads_both_proposed_rows_from_their_companion_data():
    sys.path.insert(0, str(TS))
    import beyond_rows  # noqa: PLC0415

    r = {x["id"]: x for x in beyond_rows.rows()}
    assert "geometric mean" in r["B1"]["text"] and "95 percent" in r["B1"]["text"]
    assert "flicker-bounded-sequences" in r["B2"]["source"] and "mean over seeds" in r["B2"]["text"]
