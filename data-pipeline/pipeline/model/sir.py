"""EXAMPLE engine: a deterministic SIR epidemic, forward Euler at a quarter-day step. It is the reference of the live
lane: frontend/src/engine/sir.ts is a step-for-step TypeScript port, and its parity test holds it to the traces
this engine bakes. Replace with the product's research-chosen engine."""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from ..io.schema import SIRParams, SIRResult


def derivatives(t: float, y: Sequence[float], beta: float, gamma: float, n: float) -> list[float]:
    """The SIR equations (Kermack and McKendrick 1927, https://doi.org/10.1098/rspa.1927.0118): the rates of change
    ``[dS/dt, dI/dt, dR/dt]`` at the state ``y = (S, I, R)`` of a closed population of ``n`` people, with
    ``dS/dt = -beta S I / n``, ``dI/dt = beta S I / n - gamma I`` and ``dR/dt = gamma I``. ``t`` is unused (the system is
    autonomous) and kept so that the function has the signature an ODE solver such as ``scipy.integrate.solve_ivp`` calls.
    ``simulate`` takes its Forward Euler steps from it, so the engine and a reference solver share one statement of the model."""
    s, i, _ = y
    new_infections = ((beta / n) if n > 0 else 0.0) * s * i
    new_recoveries = gamma * i
    return [-new_infections, new_infections - new_recoveries, new_recoveries]


def simulate(p: SIRParams, dt: float = 0.25) -> SIRResult:
    steps = max(1, int(round(p.days / dt)))
    S = float(p.N - p.I0)
    I = float(p.I0)
    R = 0.0
    ts = [0.0]
    Ss = [S]
    Is = [I]
    Rs = [R]
    for k in range(1, steps + 1):
        dS, _, dR = derivatives(0.0, (S, I, R), p.beta, p.gamma, p.N)
        new_inf = -dS * dt
        new_rec = dR * dt
        S = max(0.0, S - new_inf)
        I = max(0.0, I + new_inf - new_rec)
        R = R + new_rec
        ts.append(k * dt)
        Ss.append(S)
        Is.append(I)
        Rs.append(R)
    peak_idx = int(np.argmax(Is))
    return SIRResult(
        case_id=p.case_id,
        t=ts, S=Ss, I=Is, R=Rs,
        peak_I=float(Is[peak_idx]),
        t_peak=float(ts[peak_idx]),
        attack_rate=float(Rs[-1] / p.N) if p.N > 0 else 0.0,
    )
