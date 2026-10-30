"""Oracles: independent solutions the engine and the notebooks are checked against.

An oracle shares no code with the engine (``pipeline/model/``): it states a closed relation the model must agree with, so a
disagreement is a finding about one of the two. The notebooks import it, as they import every method (CAOS_MANAGE
``conventions/product-notebooks.md`` section 1); none defines its own copy. Standard library only.

- Overdamped bead (Tolic-Norrelykke et al. 2006, https://arxiv.org/abs/physics/0603037): the position spectrum is a Lorentzian
  with corner frequency ``kappa / (2 pi gamma)``; its variance is ``k_B T / kappa`` (equipartition).
- Random mask (Di Leonardo et al. 2007, https://doi.org/10.1364/OE.15.001913): a random phase mask sends about ``1 / M`` of the
  power into each of ``M`` traps, so its efficiency is about ``1 / M`` ... of the order of the inverse of the trap count.
- Vortex (Polin et al. 2005): a trap of charge ``l`` winds the SLM phase by ``2 pi l`` around the axis.
- Published calibration rows (Di Leonardo et al. 2007, Table 1, the 10 x 10 task): efficiency and uniformity of the analytic and
  Gerchberg-Saxton methods, to be reproduced within the seed spread of this engine.
- Parseval: total power is conserved by the propagation.
"""
from __future__ import annotations

import math

KB_J_PER_K = 1.380649e-23

DI_LEONARDO_2007 = {   # method -> (efficiency, uniformity), Table 1 as quoted in the SDD
    "M01": (0.29, 0.01), "M02": (0.69, 0.01), "M04": (0.94, 0.60), "M05": (0.93, 0.79), "M06": (0.93, 0.99),
}


def corner_frequency_hz(kappa_n_per_m: float, gamma_ns_per_m: float) -> float:
    """``f_c = kappa / (2 pi gamma)`` of an overdamped bead in a harmonic trap."""
    if kappa_n_per_m <= 0 or gamma_ns_per_m <= 0:
        raise ValueError("kappa and gamma must be positive")
    return kappa_n_per_m / (2.0 * math.pi * gamma_ns_per_m)


def stokes_drag_ns_per_m(viscosity_pa_s: float, radius_m: float) -> float:
    """``gamma = 6 pi eta r``."""
    return 6.0 * math.pi * viscosity_pa_s * radius_m


def equipartition_variance_m2(kappa_n_per_m: float, temperature_k: float) -> float:
    """``<x^2> = k_B T / kappa``."""
    return KB_J_PER_K * temperature_k / kappa_n_per_m


def random_mask_efficiency(n_traps: int) -> float:
    """The order of magnitude of a random mask's efficiency: ``1 / n_traps``."""
    if n_traps < 1:
        raise ValueError("n_traps must be at least 1")
    return 1.0 / n_traps


def vortex_winding_rad(charge: int) -> float:
    """The phase winding of a charge-``l`` vortex around the axis: ``2 pi l``."""
    return 2.0 * math.pi * charge


def parseval_power(samples) -> float:
    """``sum |E|^2`` of a field: the quantity a propagation conserves."""
    return float(sum(abs(v) ** 2 for v in samples))
