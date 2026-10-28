"""Portable pseudo-random generator: xoshiro128** seeded by SplitMix32 (ADR-0054: no global RNG anywhere).

The TypeScript port reproduces the u32 stream and the uniforms bit for bit (integer arithmetic modulo 2^32 and an
exact division by 2^24); the normals use ``log``, ``cos`` and ``sin`` of float64 and agree to about 1e-15.

References (read on 2026-10-28):
- Blackman and Vigna, "Scrambled linear pseudorandom number generators", ACM TOMS 2021 (arXiv 1805.01407), the
  generator ``xoshiro128**`` 1.1: https://prng.di.unimi.it/xoshiro128starstar.c . State of four uint32 words that must not
  be all zero. Output ``rotl(s[1] * 5, 7) * 9``; update ``t = s[1] << 9; s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2];
  s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 11)``.
- SplitMix32 (the 32-bit mixer derived from the MurmurHash3 ``fmix32`` finalizer, "improved" constants), public domain:
  https://github.com/bryc/code/blob/master/jshash/PRNGs.md . Step ``a += 0x9e3779b9``; ``t = a ^ (a >> 16)``;
  ``t *= 0x21f0aaad``; ``t ^= t >> 15``; ``t *= 0x735a2d97``; output ``t ^ (t >> 15)``. The four state words are the
  first four outputs for the seed.

Draw order is part of the contract (the port draws in the same order): ``uniform`` takes one u32; ``normal`` takes two
uniforms per pair (Box-Muller, ``u1 = 1 - uniform`` so that it is in (0, 1], the cosine value is returned first and the
sine value is cached for the next call); arrays are filled in C order by successive scalar draws.
"""
from __future__ import annotations

import math

import numpy as np

_M = 0xFFFFFFFF
_TWO24 = 16777216.0


def _splitmix32(a: int):
    """Generator of SplitMix32 outputs for the seed ``a`` (uint32)."""
    while True:
        a = (a + 0x9E3779B9) & _M
        t = a ^ (a >> 16)
        t = (t * 0x21F0AAAD) & _M
        t ^= t >> 15
        t = (t * 0x735A2D97) & _M
        yield t ^ (t >> 15)


class Rng:
    """xoshiro128** stream for one integer seed in [0, 2^32). Same seed, same stream, on every platform."""

    __slots__ = ("_s0", "_s1", "_s2", "_s3", "_cache")

    def __init__(self, seed: int):
        if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
            raise ValueError(f"seed must be an integer in [0, 2^32), got {seed!r}")
        seed = int(seed)
        if not 0 <= seed <= _M:
            raise ValueError(f"seed must be an integer in [0, 2^32), got {seed}")
        sm = _splitmix32(seed)
        self._s0, self._s1, self._s2, self._s3 = (next(sm) for _ in range(4))
        if (self._s0 | self._s1 | self._s2 | self._s3) == 0:  # the all-zero state is forbidden by the authors
            self._s0 = 1
        self._cache: float | None = None

    def next_u32(self) -> int:
        s0, s1, s2, s3 = self._s0, self._s1, self._s2, self._s3
        x = (s1 * 5) & _M
        x = ((x << 7) | (x >> 25)) & _M
        result = (x * 9) & _M
        t = (s1 << 9) & _M
        s2 ^= s0
        s3 ^= s1
        s1 ^= s2
        s0 ^= s3
        s2 ^= t
        s3 = ((s3 << 11) | (s3 >> 21)) & _M
        self._s0, self._s1, self._s2, self._s3 = s0, s1, s2, s3
        return result

    def uniform(self) -> float:
        """Uniform in [0, 1): the top 24 bits of a u32 over 2^24 (exact in float32 and float64)."""
        return (self.next_u32() >> 8) / _TWO24

    def normal(self) -> float:
        """Standard normal by Box-Muller; the second value of each pair is cached."""
        if self._cache is not None:
            z, self._cache = self._cache, None
            return z
        u1 = 1.0 - self.uniform()
        u2 = self.uniform()
        r = math.sqrt(-2.0 * math.log(u1))
        a = 2.0 * math.pi * u2
        self._cache = r * math.sin(a)
        return r * math.cos(a)

    def uniform_array(self, n: int) -> np.ndarray:
        n = _count(n)
        out = np.empty(n, dtype=np.float64)
        nxt = self.uniform
        for i in range(n):
            out[i] = nxt()
        return out

    def normal_array(self, n: int) -> np.ndarray:
        n = _count(n)
        out = np.empty(n, dtype=np.float64)
        nxt = self.normal
        for i in range(n):
            out[i] = nxt()
        return out

    def phases(self, n: int) -> np.ndarray:
        """``n`` phases uniform in [0, 2 pi)."""
        return 2.0 * math.pi * self.uniform_array(n)


def _count(n: int) -> int:
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 0:
        raise ValueError(f"count must be a non-negative integer, got {n!r}")
    return int(n)
