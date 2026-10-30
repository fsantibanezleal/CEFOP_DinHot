"""Volume accuracy of a mask on the three planes of M17 (numpy; no ``SPEC``: the registry skips this module)."""
from __future__ import annotations

import numpy as np

from ...core.forward import fft_focal_field

Z_PLANES = (-8.0, 0.0, 8.0)   # SLM-limited Rayleigh ranges, learned/torch_forward.Z_PLANES


def plane_accuracy(amps: np.ndarray, phi: np.ndarray, setup, z_planes=Z_PLANES) -> float:
    """The mean over the planes of ``AC = 2 sum(T I) / (sum T^2 + sum I^2)`` with unit-sum plane intensities ``T`` (target) and ``I``
    (mask); the plane field is the engine's focal field of ``phi`` minus the plane's lens phase ``Z (cx^2 + cy^2) / (N/2)^2``, which
    is the point-trap delay of a trap at that depth. DeepCGH's own accuracy formula was not read (UNVERIFIED)."""
    n = setup.n_pix
    c = np.arange(n) - (n - 1) / 2.0
    q = (c[None, :] ** 2 + c[:, None] ** 2) / (n / 2.0) ** 2
    ac = []
    for a, z in zip(amps, z_planes):
        i = np.abs(fft_focal_field(phi - z * q, setup)) ** 2
        i = i / i.sum()
        t = np.asarray(a, dtype=np.float64) ** 2
        t = t / t.sum()
        ac.append(2.0 * np.sum(t * i) / (np.sum(t**2) + np.sum(i**2)))
    return float(np.mean(ac))
