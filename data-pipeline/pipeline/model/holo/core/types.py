"""The method interface: budget, target, result and method description (implemented by units E2 and E3, ported by T1).

A method module exposes ``SPEC = MethodSpec(...)`` and
``run(setup, target, *, device=None, budget, rng, init=None) -> Result``; ``device=None`` means the ideal device,
``init`` is an optional starting phase (None: the method's own start, drawn through ``rng``), and ``rng`` is the only
source of randomness (ADR-0054).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np

from .traps import TrapSet

LANES = ("live", "baked", "both")
TARGET_KINDS = ("traps", "field")
HISTORY_KEYS = ("iteration", "efficiency", "uniformity", "rel_std", "time_s")
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class Budget:
    """Iteration cap and an optional wall-clock cap in seconds (``None``: iterations only)."""

    iterations: int
    time_s: float | None = None

    def __post_init__(self) -> None:
        if isinstance(self.iterations, bool) or not isinstance(self.iterations, int) or self.iterations < 1:
            raise ValueError(f"iterations must be a positive integer, got {self.iterations!r}")
        if self.time_s is not None and not (math.isfinite(self.time_s) and self.time_s > 0):
            raise ValueError(f"time_s must be finite and positive or None, got {self.time_s!r}")


@dataclass(frozen=True)
class Target:
    """Either a ``TrapSet`` (point traps) or a shaped field: ``amplitude`` on the FFT grid and a boolean signal ``mask``."""

    traps: TrapSet | None = None
    amplitude: np.ndarray | None = None
    mask: np.ndarray | None = None

    def __post_init__(self) -> None:
        shaped = self.amplitude is not None or self.mask is not None
        if (self.traps is None) == (not shaped):
            raise ValueError("a target is either traps or (amplitude and mask), exactly one")
        if shaped:
            if self.amplitude is None or self.mask is None:
                raise ValueError("a shaped-field target needs both amplitude and mask")
            amp = np.asarray(self.amplitude, dtype=np.float64)
            mask = np.asarray(self.mask, dtype=bool)
            if amp.ndim != 2 or amp.shape != mask.shape or amp.shape[0] != amp.shape[1]:
                raise ValueError("amplitude and mask must be square arrays of the same shape")
            if not np.all(np.isfinite(amp)) or np.any(amp < 0):
                raise ValueError("amplitude must be finite and non-negative")
            if not mask.any():
                raise ValueError("the signal region (mask) is empty")
            object.__setattr__(self, "amplitude", amp)
            object.__setattr__(self, "mask", mask)

    @property
    def kind(self) -> str:
        return "traps" if self.traps is not None else "field"

    @classmethod
    def from_traps(cls, traps: TrapSet) -> Target:
        return cls(traps=traps)

    @classmethod
    def from_field(cls, amplitude: np.ndarray, mask: np.ndarray) -> Target:
        return cls(amplitude=amplitude, mask=mask)


@dataclass
class Result:
    """Outcome of a run: the phase (float64, ``n_pix x n_pix``), the per-iteration ``history``, the final ``fields``.

    Each history entry is a dict with at least ``iteration, efficiency, uniformity, rel_std, time_s``. ``fields`` is the
    final trap fields ``V_m`` (traps) or the focal field (shaped target). ``meta`` is free.
    """

    phi: np.ndarray
    history: list
    fields: np.ndarray
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.phi = np.asarray(self.phi, dtype=np.float64)
        if self.phi.ndim != 2 or self.phi.shape[0] != self.phi.shape[1]:
            raise ValueError("phi must be a square 2D array")
        if not np.all(np.isfinite(self.phi)):
            raise ValueError("phi contains NaN or infinite values")
        if not isinstance(self.history, list):
            raise ValueError("history must be a list of dicts")
        for k, h in enumerate(self.history):
            if not isinstance(h, dict) or any(key not in h for key in HISTORY_KEYS):
                raise ValueError(f"history[{k}] must be a dict with the keys {HISTORY_KEYS}")
        self.fields = np.asarray(self.fields)


@dataclass(frozen=True)
class MethodSpec:
    """Static description of a method: ``lane`` is ``live``, ``baked`` or ``both``; ``dims`` a subset of {2, 3}."""

    id: str
    name: str
    family: str
    lane: str
    targets: tuple
    dims: tuple

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not _ID.match(self.id):
            raise ValueError(f"id must match {_ID.pattern}, got {self.id!r}")
        for name in ("name", "family"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if self.lane not in LANES:
            raise ValueError(f"lane must be one of {LANES}, got {self.lane!r}")
        if not self.targets or any(t not in TARGET_KINDS for t in self.targets):
            raise ValueError(f"targets must be a non-empty subset of {TARGET_KINDS}, got {self.targets!r}")
        if not self.dims or any(d not in (2, 3) for d in self.dims):
            raise ValueError(f"dims must be a non-empty subset of (2, 3), got {self.dims!r}")
