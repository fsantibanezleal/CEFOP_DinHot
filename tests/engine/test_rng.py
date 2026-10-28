"""Tests of the portable RNG (xoshiro128** seeded by SplitMix32) and its reference fixture.

Run this module as a script to regenerate ``tests/fixtures/rng-reference.json`` (the TypeScript port reads it).
"""
from __future__ import annotations

import json
import math
import pathlib

import numpy as np
import pytest

from pipeline.model.holo.core.rng import Rng

FIXTURE = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "rng-reference.json"
SEED = 20261028


def _take(fn, n):
    r = Rng(SEED)
    return [fn(r) for _ in range(n)]


def generate_reference() -> dict:
    """The fixture content: the first 64 u32, 64 uniforms and 64 normals of seed 20261028 (three fresh streams)."""
    return {
        "algorithm": "xoshiro128starstar 1.1 seeded by four SplitMix32 outputs; uniform = (u32 >> 8) / 2^24; "
                     "normal = Box-Muller (u1 = 1 - uniform, cosine value first, sine value cached)",
        "seed": SEED,
        "u32": _take(lambda r: r.next_u32(), 64),
        "uniform": _take(lambda r: r.uniform(), 64),
        "normal": _take(lambda r: r.normal(), 64),
    }


def _independent_u32(seed: int, n: int) -> list[int]:
    """A second implementation (numpy uint32 scalars) used only as a cross-check of the pure-int one."""
    u = np.uint32
    old = np.seterr(over="ignore")
    try:
        a = u(seed)
        s = []
        for _ in range(4):
            a = u(a + u(0x9E3779B9))
            t = u(a ^ (a >> u(16)))
            t = u(t * u(0x21F0AAAD))
            t = u(t ^ (t >> u(15)))
            t = u(t * u(0x735A2D97))
            t = u(t ^ (t >> u(15)))
            s.append(t)

        def rotl(x, k):
            return u((x << u(k)) | (x >> u(32 - k)))

        out = []
        for _ in range(n):
            out.append(int(u(rotl(u(s[1] * u(5)), 7) * u(9))))
            t = u(s[1] << u(9))
            s[2] = u(s[2] ^ s[0])
            s[3] = u(s[3] ^ s[1])
            s[1] = u(s[1] ^ s[2])
            s[0] = u(s[0] ^ s[3])
            s[2] = u(s[2] ^ t)
            s[3] = rotl(s[3], 11)
        return out
    finally:
        np.seterr(**old)


def test_matches_independent_implementation():
    r = Rng(SEED)
    assert [r.next_u32() for _ in range(200)] == _independent_u32(SEED, 200)


def test_matches_fixture_file():
    ref = json.loads(FIXTURE.read_text())
    got = generate_reference()
    assert ref["seed"] == SEED
    assert ref["u32"] == got["u32"]
    assert ref["uniform"] == got["uniform"]
    assert ref["normal"] == pytest.approx(got["normal"], rel=0, abs=1e-15)
    assert len(ref["u32"]) == len(ref["uniform"]) == len(ref["normal"]) == 64


def test_uniform_is_top_24_bits_exact():
    a, b = Rng(7), Rng(7)
    for _ in range(100):
        assert a.uniform() == (b.next_u32() >> 8) / 16777216.0


def test_uniform_range_and_mean():
    u = Rng(1).uniform_array(20000)
    assert u.dtype == np.float64 and u.min() >= 0.0 and u.max() < 1.0
    assert abs(u.mean() - 0.5) < 0.01


def test_normal_moments_and_cache():
    z = Rng(2).normal_array(40000)
    assert abs(z.mean()) < 0.03 and abs(z.std() - 1.0) < 0.03
    r = Rng(3)
    seq = [r.normal() for _ in range(7)]
    assert Rng(3).normal_array(7).tolist() == seq


def test_array_draws_equal_scalar_draws():
    r = Rng(9)
    assert Rng(9).uniform_array(10).tolist() == [r.uniform() for _ in range(10)]


def test_phases_range():
    p = Rng(4).phases(1000)
    assert p.min() >= 0.0 and p.max() < 2 * math.pi
    assert p.tolist() == (2 * math.pi * Rng(4).uniform_array(1000)).tolist()


def test_determinism_and_seed_sensitivity():
    assert Rng(5).uniform_array(50).tolist() == Rng(5).uniform_array(50).tolist()
    assert Rng(5).uniform_array(50).tolist() != Rng(6).uniform_array(50).tolist()


@pytest.mark.parametrize("bad", [-1, 2**32, 1.5, "a", True])
def test_bad_seed(bad):
    with pytest.raises(ValueError):
        Rng(bad)


def test_negative_count():
    with pytest.raises(ValueError):
        Rng(1).uniform_array(-1)


def test_zero_count_is_empty():
    assert Rng(1).normal_array(0).shape == (0,)


if __name__ == "__main__":
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(generate_reference(), indent=1) + "\n")
    print("wrote", FIXTURE)
