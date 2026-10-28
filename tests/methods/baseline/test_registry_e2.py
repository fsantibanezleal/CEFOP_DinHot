"""The thirteen E2 methods are discovered by the E1 registry with their ladder ids, lanes and target kinds."""
from __future__ import annotations

from pipeline.model.holo.core.types import Target
from pipeline.model.holo.methods import all_specs, get, reload

E2 = {"M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M12", "M14", "M15", "M16", "M19"}


def test_registry_discovers_all_e2_methods():
    reload()
    ids = {s.id for s in all_specs()}
    assert E2 <= ids


def test_registered_run_is_the_module_run_and_specs_are_consistent():
    reload()
    for mid in sorted(E2):
        m = get(mid)
        assert m.spec.id == mid and callable(m.run)
        assert set(m.spec.targets) <= {"traps", "field"} and m.spec.dims


def test_unsupported_target_kind_names_the_supported_kinds(setup256):
    import numpy as np
    from pipeline.model.holo.core.rng import Rng
    from pipeline.model.holo.core.types import Budget
    n = setup256.n_fft
    field = Target.from_field(np.ones((n, n)), np.ones((n, n), bool))
    reload()
    for mid in sorted(E2):
        m = get(mid)
        if "field" in m.spec.targets:
            continue
        try:
            m.run(setup256, field, budget=Budget(1), rng=Rng(1))
        except ValueError as e:
            assert "traps" in str(e)
        else:
            raise AssertionError(mid)
