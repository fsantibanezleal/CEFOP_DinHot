"""The opt-out of Windows power throttling (EcoQoS) of every worker process of the bake and the benchmark (BL-056, BK-018, BM-018):
the call, its read-back, its no-op elsewhere and the two pools that pass it as their initializer."""
from __future__ import annotations

import sys
from concurrent.futures import Future
from pathlib import Path

import pytest

from pipeline import pipeline as bake_pipeline
from pipeline.benchmark import protocol
from pipeline.core import power

WINDOWS = sys.platform == "win32"


@pytest.mark.skipif(not WINDOWS, reason="process power throttling is a Windows setting")
def test_on_windows_the_opt_out_is_set_and_read_back():
    assert power.opt_out_of_power_throttling() is True
    state = power.read_power_throttling()
    assert state is not None
    control, mask = state
    assert control & 1 == 1       # PROCESS_POWER_THROTTLING_EXECUTION_SPEED is controlled by this process
    assert mask & 1 == 0          # and its state is off: the process is not throttled


@pytest.mark.skipif(not WINDOWS, reason="process power throttling is a Windows setting")
def test_the_opt_out_is_idempotent():
    assert power.opt_out_of_power_throttling() is True
    assert power.opt_out_of_power_throttling() is True
    assert power.read_power_throttling() == (1, 0)


def test_on_another_system_the_opt_out_does_nothing_and_never_raises(monkeypatch):
    monkeypatch.setattr(power.sys, "platform", "linux")
    assert power.opt_out_of_power_throttling() is False
    assert power.read_power_throttling() is None


def test_a_failing_call_returns_false_instead_of_raising(monkeypatch):
    def boom(*a, **k):
        raise OSError("no such API")

    monkeypatch.setattr(power, "_set_execution_speed_throttling", boom, raising=False)
    monkeypatch.setattr(power.sys, "platform", "win32")
    assert power.opt_out_of_power_throttling() is False


class _FakePool:
    """Stands in for ``ProcessPoolExecutor``: records its keyword arguments, runs the work in this process."""
    made: list[dict] = []

    def __init__(self, **kw):
        type(self).made.append(kw)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def map(self, fn, it):
        return map(fn, it)

    def submit(self, fn, *args):
        f: Future = Future()
        f.set_result(fn(*args))
        return f


@pytest.fixture
def fake_pool(monkeypatch):
    _FakePool.made = []
    monkeypatch.setattr(bake_pipeline, "ProcessPoolExecutor", _FakePool)
    monkeypatch.setattr(protocol, "ProcessPoolExecutor", _FakePool)
    return _FakePool


@pytest.fixture
def opt_out_calls(monkeypatch):
    calls: list[int] = []
    monkeypatch.setattr(bake_pipeline, "opt_out_of_power_throttling", lambda: calls.append(1) or True)
    monkeypatch.setattr(protocol, "opt_out_of_power_throttling", lambda: calls.append(1) or True)
    return calls


def _echo(job):
    return job


def test_the_bake_pool_is_built_with_the_initializer_and_the_calling_process_opts_out(fake_pool, opt_out_calls):
    out = bake_pipeline.bake_jobs([1, 2, 3], workers=2, fn=_echo)
    assert out == [1, 2, 3]
    assert len(fake_pool.made) == 1
    assert callable(fake_pool.made[0]["initializer"])
    assert opt_out_calls == [1]


def test_the_pool_initializers_are_the_real_function(fake_pool, groups, tmp_path):
    bake_pipeline.bake_jobs([1, 2], workers=2, fn=_echo)
    protocol.run(tmp_path, seeds=2, workers=2, reduced=True, geometries=["G1"], methods=["M04"])
    assert [kw["initializer"] for kw in fake_pool.made] == [power.opt_out_of_power_throttling] * 2


def test_the_sequential_bake_opts_out_in_the_calling_process(fake_pool, opt_out_calls):
    assert bake_pipeline.bake_jobs([1, 2, 3], workers=1, fn=_echo) == [1, 2, 3]
    assert bake_pipeline.bake_jobs([7], workers=4, fn=_echo) == [7]
    assert fake_pool.made == []
    assert opt_out_calls == [1, 1]


def _stub_groups(monkeypatch):
    from pipeline.model.holo import methods
    previous = methods._base
    methods.reload(None)
    monkeypatch.setattr(protocol, "run_group", lambda t: {"refused": {"method": t["method"], "geometry": t["geometry"],
                                                                      "reason": {"en": "x", "es": "x"}}})
    return methods, previous


@pytest.fixture
def groups(monkeypatch):
    methods, previous = _stub_groups(monkeypatch)
    try:
        yield
    finally:
        methods.reload(None if previous == methods.__name__ else previous)


def test_the_benchmark_pool_is_built_with_the_initializer(fake_pool, opt_out_calls, groups, tmp_path):
    protocol.run(tmp_path, seeds=2, workers=2, reduced=True, geometries=["G1"], methods=["M04"])
    assert len(fake_pool.made) == 1
    assert fake_pool.made[0]["initializer"] is protocol.opt_out_of_power_throttling
    assert opt_out_calls == [1]


def test_the_sequential_benchmark_opts_out_in_the_calling_process(fake_pool, opt_out_calls, groups, tmp_path):
    protocol.run(tmp_path, seeds=2, workers=1, reduced=True, geometries=["G1"], methods=["M04"])
    assert fake_pool.made == []
    assert opt_out_calls == [1]


# ---- adversarial: the defects the tests above exist to catch, planted and detected -------------------------------------
def _has_initializer(kw: dict) -> bool:
    return kw.get("initializer") is power.opt_out_of_power_throttling


def _pool_without_initializer(**kw):
    kw.pop("initializer", None)
    return _FakePool(**kw)


def test_adversarial_a_bake_pool_without_the_initializer_is_detected(monkeypatch, fake_pool):
    bake_pipeline.bake_jobs([1, 2], workers=2, fn=_echo)
    assert _has_initializer(fake_pool.made[-1])
    monkeypatch.setattr(bake_pipeline, "ProcessPoolExecutor", _pool_without_initializer)
    fake_pool.made = []
    bake_pipeline.bake_jobs([1, 2], workers=2, fn=_echo)
    assert not _has_initializer(fake_pool.made[-1])     # the defect the pool tests fail on


def test_adversarial_a_benchmark_pool_without_the_initializer_is_detected(monkeypatch, fake_pool, groups, tmp_path):
    protocol.run(tmp_path / "a", seeds=2, workers=2, reduced=True, geometries=["G1"], methods=["M04"])
    assert _has_initializer(fake_pool.made[-1])
    monkeypatch.setattr(protocol, "ProcessPoolExecutor", _pool_without_initializer)
    fake_pool.made = []
    protocol.run(tmp_path / "b", seeds=2, workers=2, reduced=True, geometries=["G1"], methods=["M04"])
    assert not _has_initializer(fake_pool.made[-1])


def test_adversarial_an_opt_out_that_raises_is_swallowed_and_the_sequential_path_still_runs(monkeypatch):
    def boom():
        raise PermissionError("denied")

    monkeypatch.setattr(power, "_set_execution_speed_throttling", lambda throttled: boom())
    monkeypatch.setattr(power.sys, "platform", "win32")
    assert power.opt_out_of_power_throttling() is False
    assert bake_pipeline.bake_jobs([1, 2], workers=1, fn=_echo) == [1, 2]
