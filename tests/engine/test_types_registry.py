from __future__ import annotations

import importlib
import sys
import textwrap

import numpy as np
import pytest

from pipeline.model.holo import methods
from pipeline.model.holo.core.traps import Trap, TrapSet
from pipeline.model.holo.core.types import Budget, MethodSpec, Result, Target

TS = TrapSet((Trap(0, 0.0, 0.0),))


# ---- types -----------------------------------------------------------------------------------------------------

def test_budget():
    assert Budget(10).time_s is None and Budget(10, 2.5).time_s == 2.5
    for bad in (dict(iterations=0), dict(iterations=1.5), dict(iterations=3, time_s=0.0),
                dict(iterations=3, time_s=float("nan"))):
        with pytest.raises(ValueError):
            Budget(**bad)


def test_target_exactly_one_form():
    assert Target.from_traps(TS).kind == "traps"
    amp = np.ones((8, 8))
    mask = np.zeros((8, 8), dtype=bool)
    mask[2:5, 2:5] = True
    t = Target.from_field(amp, mask)
    assert t.kind == "field" and t.mask.dtype == bool
    with pytest.raises(ValueError):
        Target(traps=TS, amplitude=amp, mask=mask)
    with pytest.raises(ValueError):
        Target()
    with pytest.raises(ValueError):
        Target.from_field(amp, np.ones((4, 4), dtype=bool))
    with pytest.raises(ValueError):
        Target.from_field(amp, np.zeros((8, 8), dtype=bool))          # empty signal region
    bad = amp.copy()
    bad[0, 0] = -1
    with pytest.raises(ValueError):
        Target.from_field(bad, mask)


def good_history():
    return [dict(iteration=0, efficiency=0.5, uniformity=0.4, rel_std=30.0, time_s=0.01)]


def test_result_validation():
    r = Result(phi=np.zeros((4, 4)), history=good_history(), fields=np.ones(3, dtype=complex), meta={"a": 1})
    assert r.phi.dtype == np.float64 and r.meta == {"a": 1}
    for bad_hist in ([dict(iteration=0)], "x", [dict(iteration=0, efficiency=0.5, uniformity=0.4, rel_std=1.0)]):
        with pytest.raises(ValueError):
            Result(phi=np.zeros((4, 4)), history=bad_hist, fields=np.ones(3, dtype=complex))
    with pytest.raises(ValueError):
        Result(phi=np.zeros(4), history=good_history(), fields=np.ones(3, dtype=complex))
    with pytest.raises(ValueError):
        Result(phi=np.full((4, 4), np.nan), history=good_history(), fields=np.ones(3, dtype=complex))


def test_method_spec_validation():
    s = MethodSpec("m06-gsw", "Weighted GS", "GS", "live", ("traps",), (2, 3))
    assert s.id == "m06-gsw"
    for kw in (dict(id="bad id"), dict(id=""), dict(lane="fast"), dict(targets=()), dict(targets=("blob",)),
               dict(dims=(4,)), dict(dims=()), dict(family=""), dict(name="")):
        args = dict(id="m1", name="n", family="f", lane="live", targets=("traps",), dims=(2,))
        args.update(kw)
        with pytest.raises(ValueError):
            MethodSpec(**args)


# ---- registry --------------------------------------------------------------------------------------------------

def plant(tmp_path, monkeypatch, name, files):
    for rel, body in files.items():
        p = tmp_path / name / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body))
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()


MOD = """
    from pipeline.model.holo.core.types import MethodSpec
    SPEC = MethodSpec("{id}", "{id} name", "analytic", "live", ("traps",), (2,))
    def run(setup, target, *, device=None, budget, rng, init=None):
        return "{id}"
"""


@pytest.fixture
def cleanup():
    before = set(sys.modules)
    yield
    for k in set(sys.modules) - before:
        del sys.modules[k]


def test_default_registry_lists_unique_specs_and_refuses_unknown_ids():
    methods.reload()
    ids = [s.id for s in methods.all_specs()]
    assert len(ids) == len(set(ids))
    with pytest.raises(KeyError):
        methods.get("not-a-method")


def test_discovers_recursively_and_tolerates_missing_subpackages(tmp_path, monkeypatch, cleanup):
    plant(tmp_path, monkeypatch, "tmp_reg_a", {
        "__init__.py": "",
        "baseline/__init__.py": "",
        "baseline/m_one.py": MOD.format(id="m01"),
        "optim/__init__.py": "",
        "optim/deep/__init__.py": "",
        "optim/deep/m_two.py": MOD.format(id="m02"),
        "optim/deep/helper.py": "X = 1\n",                      # a module without SPEC is ignored
        # control and beyond are absent on purpose
    })
    found = methods.discover("tmp_reg_a")
    assert [m.spec.id for m in found] == ["m01", "m02"]
    assert found[0].run(None, None, budget=None, rng=None) == "m01"


def test_other_subpackage_names_are_not_scanned(tmp_path, monkeypatch, cleanup):
    plant(tmp_path, monkeypatch, "tmp_reg_b", {
        "__init__.py": "", "misc/__init__.py": "", "misc/m.py": MOD.format(id="m99"),
    })
    assert methods.discover("tmp_reg_b") == []


def test_module_without_run_is_an_error(tmp_path, monkeypatch, cleanup):
    plant(tmp_path, monkeypatch, "tmp_reg_c", {
        "__init__.py": "", "beyond/__init__.py": "",
        "beyond/m.py": "from pipeline.model.holo.core.types import MethodSpec\n"
                       "SPEC = MethodSpec('b1', 'n', 'f', 'live', ('traps',), (2,))\n",
    })
    with pytest.raises(ValueError, match="run"):
        methods.discover("tmp_reg_c")


def test_duplicate_ids_are_an_error(tmp_path, monkeypatch, cleanup):
    plant(tmp_path, monkeypatch, "tmp_reg_d", {
        "__init__.py": "", "baseline/__init__.py": "", "control/__init__.py": "",
        "baseline/a.py": MOD.format(id="dup"), "control/b.py": MOD.format(id="dup"),
    })
    with pytest.raises(ValueError, match="dup"):
        methods.discover("tmp_reg_d")


def test_broken_method_import_is_not_swallowed(tmp_path, monkeypatch, cleanup):
    plant(tmp_path, monkeypatch, "tmp_reg_e", {
        "__init__.py": "", "baseline/__init__.py": "", "baseline/bad.py": "import not_a_real_module_xyz\n",
    })
    with pytest.raises(ModuleNotFoundError):
        methods.discover("tmp_reg_e")


def test_get_and_all_specs_use_the_default_package(tmp_path, monkeypatch, cleanup):
    plant(tmp_path, monkeypatch, "tmp_reg_f", {
        "__init__.py": "", "baseline/__init__.py": "", "baseline/m.py": MOD.format(id="zz1"),
    })
    methods.reload("tmp_reg_f")
    try:
        assert [s.id for s in methods.all_specs()] == ["zz1"]
        assert methods.get("zz1").spec.id == "zz1"
    finally:
        methods.reload()
    assert "zz1" not in {s.id for s in methods.all_specs()}
