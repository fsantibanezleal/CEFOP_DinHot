"""Volume accuracy of a mask on the three planes of M17 (numpy; no ``SPEC``: the registry skips this module)."""
from __future__ import annotations

import numpy as np

from ...core.forward import fft_focal_field

Z_PLANES = (-8.0, 0.0, 8.0)   # SLM-limited Rayleigh ranges, learned/torch_forward.Z_PLANES


def _plane_q(n: int) -> np.ndarray:
    c = np.arange(n) - (n - 1) / 2.0
    return (c[None, :] ** 2 + c[:, None] ** 2) / (n / 2.0) ** 2


def plane_accuracy(amps: np.ndarray, phi: np.ndarray, setup, z_planes=Z_PLANES) -> float:
    """DinHot's accuracy: the mean over the planes of ``AC = 2 sum(T I) / (sum T^2 + sum I^2)`` with unit-sum plane intensities
    ``T`` (target) and ``I`` (mask); the plane field is the engine's focal field of ``phi`` minus the plane's lens phase
    ``Z (cx^2 + cy^2) / (N/2)^2``, which is the point-trap delay of a trap at that depth. The network is trained with this form.
    DeepCGH's own definition is ``cosine_volume_accuracy``; both are reported by the evaluation."""
    q = _plane_q(setup.n_pix)
    ac = []
    for a, z in zip(amps, z_planes):
        i = np.abs(fft_focal_field(phi - z * q, setup)) ** 2
        i = i / i.sum()
        t = np.asarray(a, dtype=np.float64) ** 2
        t = t / t.sum()
        ac.append(2.0 * np.sum(t * i) / (np.sum(t**2) + np.sum(i**2)))
    return float(np.mean(ac))


def cosine_similarity(target: np.ndarray, recon: np.ndarray) -> float:
    """Cosine similarity of two volumes flattened to one vector each (all planes jointly): ``sum(I J) / sqrt(sum I^2 sum J^2)``;
    0 when either volume is all zero (no division error)."""
    t = np.asarray(target, dtype=np.float64).ravel()
    i = np.asarray(recon, dtype=np.float64).ravel()
    den = np.sqrt(np.sum(t * t) * np.sum(i * i))
    return float(np.sum(t * i) / den) if den > 0.0 else 0.0


def cosine_volume_accuracy(amps: np.ndarray, phi: np.ndarray, setup, z_planes=Z_PLANES) -> float:
    """The accuracy in the definition of DeepCGH (Eybposh et al. 2020, Opt. Express 28, 26636, Eq. 3):
    ``AC = sum_{x,y,z} I Ihat / sqrt(sum I^2 sum Ihat^2)`` over every voxel of the volume, ``I`` the target intensity and ``Ihat``
    the reconstruction, here the unit-sum plane intensities of ``plane_accuracy`` (the same normalisation, so the two accuracies differ
    only in the form of the overlap: one cosine over the whole volume, against a Dice-type overlap averaged over the planes)."""
    q = _plane_q(setup.n_pix)
    ts, rs = [], []
    for a, z in zip(amps, z_planes):
        i = np.abs(fft_focal_field(phi - z * q, setup)) ** 2
        t = np.asarray(a, dtype=np.float64) ** 2
        rs.append(i / i.sum())
        ts.append(t / t.sum() if t.sum() > 0.0 else t)
    return cosine_similarity(np.stack(ts), np.stack(rs))
