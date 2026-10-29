"""Baselines of the two model slots (catalog rows cgh-net and warmstart-model): what answers behind the same contract while
no released model exists, and the other side of the swap tests.

- ``cgh_net_baseline``: the volumetric 3D Gerchberg-Saxton (M19, ladder row M19) for 30 iterations on the same three-plane
  target as the network, through the method registry (it needs the engine's M19 module); M17 measures itself against it.
- ``warmstart_baseline``: the random trap phases of the portable RNG, the start of the random-superposition method (M02) and
  of every method that draws its own start, so the model's warm start is measured against exactly this.

Neither needs a released model or a library beyond numpy.
"""
from __future__ import annotations

import numpy as np

from .holo import methods
from .holo.core.geometry import Setup
from .holo.core.rng import Rng
from .holo.core.types import Budget, Target

GS_ITERATIONS = 30
GS_METHOD = "M19"


def cgh_net_baseline(setup: Setup, target: Target, seed: int, device=None) -> np.ndarray:
    """The M19 phase mask (``n_pix x n_pix``, radians) for ``target``; ``LookupError`` if M19 is not registered."""
    try:
        method = methods.get(GS_METHOD)
    except KeyError as exc:
        raise LookupError(f"the cgh-net baseline needs method {GS_METHOD}, which is not registered") from exc
    return method.run(setup, target, device=device, budget=Budget(GS_ITERATIONS), rng=Rng(seed), init=None).phi


def warmstart_baseline(n_traps: int, seed: int) -> np.ndarray:
    """Random trap phases in ``[0, 2 pi)`` from the portable RNG (float64, length ``n_traps``)."""
    return np.asarray(Rng(seed).phases(n_traps), dtype=np.float64)
