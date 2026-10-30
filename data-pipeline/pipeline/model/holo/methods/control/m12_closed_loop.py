r"""M12: closed-loop (camera-in-the-loop) weighted GS on the emulated camera of ``core.camera``.

The camera is an EMULATION (``core/camera.py``): per-trap fixed gain error, additive noise, blur and roll-off. A result here
shows that the loop works against those errors, not against a real instrument (the dossier names a measured hardware loop
as a documented frontier). One feedback iteration: measure the trap intensities $I_m$ of the current hologram, rescale the
target, run ``n_inner`` inner iterations from the current phase, repeat. ``Budget.iterations`` counts feedback iterations.

Variant ``nogrette`` (dossier D3.1, Nogrette et al., Phys. Rev. X 4, 021034, https://arxiv.org/abs/1402.5329): inner
iterations are plain GS (forward FFT, replace the amplitude by the target, inverse FFT, keep the phase); with $\rho_m =
(I_m / w_m) / \langle I / w \rangle$ the measured intensity relative to its target and gain $G$,
$$I'_m = \frac{\bar I}{1 - G\,(1 - I_m/\bar I)}\quad\Longrightarrow\quad w^{\rm T}_m \leftarrow w^{\rm T}_m\,\frac{1}{1 - G(1 - \rho_m)}$$
(the target intensity is multiplied by the factor, so a trap at $\rho = 1$ keeps its target: the dossier prints the update in
terms of the measured intensity; the multiplicative reading is DinHot's, it keeps the memory of earlier corrections and has
the same fixed point $\rho = 1$; UNVERIFIED against the paper). Default $G = 0.7$ (Nogrette: 19 percent rms to 1.4 percent
in 20 iterations).

Variant ``kim`` (dossier D1.3 and D3.1, Kim et al., Opt. Lett. 44, 3178, https://arxiv.org/abs/1903.09286):
$T^{(j)}_m = \sqrt{\langle I \rangle / I_m}\; T^{(j-1)}_m$ (square-root weights, full gain), and the first inner iteration displays
arg F^{-1}[T exp(i psi)] with the focal phase psi frozen at that of the current hologram (no weight
correction on top: the camera factor already is the correction, a second one overshoots and the loop diverges, measured),
later inner iterations (``n_inner > 1``) add the weights g of the phase-fixed WGS of M07, reset to 1 at every step
(paper: 22 percent to 1.59 percent in three steps). ``gain`` is not used.

Start (open loop): ``start='gsw'`` (default) runs ``n_start`` = 30 iterations of the weighted GS of M06 from the SR start, so
the open-loop spread is the camera's; ``start='gs'`` runs plain GS (spread of the algorithm plus the camera's); ``init``
overrides. Camera default: ``EmulatedCamera(seed=<first draw of rng>, gain_rms=0.19, rolloff=False)`` (Nogrette's 19 percent).
History per feedback iteration: ``uniformity`` and ``rel_std`` of the MEASURED $I_m / w_m$ (what the experimenter sees),
``efficiency`` of the true fields, ``rel_std_true`` of the true $|V_m|^2 / w_m$. ``meta['open_loop_rel_std']`` is the measured
spread of the starting hologram. FFT form; traps on bins with z = 0 and no vortex. ``n_inner`` defaults to 1 for ``nogrette``, the measured optimum: with more inner GS iterations the algorithm's own intensity spread is
re-introduced between measurements and the loop settles at 3 to 10 percent instead of 1 to 2 (20 iterations, G = 0.7).
Defaults: ``variant='nogrette'``,
``gain=0.7``, ``n_inner=None`` (1 for nogrette, 3 for kim: step 3 reaches 0.5 to 0.8 percent from 22 to 24, against 3.9 to 5.6 with 1),
``n_start=30``, ``start='gsw'``.
"""
from __future__ import annotations

import time

import numpy as np

from ...core.camera import EmulatedCamera
from ...core.metrics import efficiency, rel_std, trap_intensities, uniformity
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from ..baseline import _gs
from ..baseline._common import amp_targets, fft_backproject, fft_fields, require_kinds, start_phase

SPEC = MethodSpec(id="M12", name="Closed-loop weighted GS on an emulated camera", family="control", lane="live",
                  targets=("traps",), dims=(2,))

VARIANTS = ("nogrette", "kim")


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None, variant: str = "nogrette",
        gain: float = 0.7, camera: EmulatedCamera | None = None, n_inner: int | None = None, n_start: int = 30,
        start: str = "gsw") -> Result:
    require_kinds(target, SPEC.targets, SPEC.id)
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {list(VARIANTS)}, got {variant!r}")
    if not (0.0 < gain <= 1.0):
        raise ValueError(f"gain must be in (0, 1], got {gain!r}")
    if start not in ("gsw", "gs"):
        raise ValueError(f"start must be 'gsw' or 'gs', got {start!r}")
    if n_inner is None:
        n_inner = 1 if variant == "nogrette" else 3
    if n_inner < 1 or n_start < 1:
        raise ValueError("n_inner and n_start must be >= 1")
    traps = target.traps
    _gs.check_on_bins(setup, traps)
    if camera is None:
        camera = EmulatedCamera(seed=rng.next_u32(), gain_rms=0.19, rolloff=False)
    w = traps.weight
    a_base = amp_targets(traps)
    t0 = time.perf_counter()

    # open-loop start
    phi = start_phase(setup, traps, rng, init)
    if init is None:
        rule = _gs.rule_gsw if start == "gsw" else _gs.rule_gs
        state = {"a": a_base.copy(), "w": a_base.copy() if start == "gsw" else np.ones(len(traps))}
        for k in range(1, n_start + 1):
            _, v = fft_fields(phi, setup, traps)
            phi = np.angle(fft_backproject(rule(state, v, k), setup, traps))
    e, v = fft_fields(phi, setup, traps)
    meas = camera.measure(e, setup, traps)
    open_loop = rel_std(meas / w)

    a = a_base.copy()
    history = []
    for k in range(1, budget.iterations + 1):
        rho = np.maximum((meas / w) / np.mean(meas / w), 1e-3)
        if variant == "nogrette":
            a = a * np.sqrt(1.0 / (1.0 - gain * (1.0 - rho)))
            state = {"a": a.copy(), "w": np.ones(len(traps))}
            for j in range(1, n_inner + 1):
                _, v = fft_fields(phi, setup, traps)
                phi = np.angle(fft_backproject(_gs.rule_gs(state, v, j), setup, traps))
        else:
            a = a / np.sqrt(rho)
            g = np.ones(len(traps))
            psi = None
            for j in range(1, n_inner + 1):
                _, v = fft_fields(phi, setup, traps)
                if psi is None:
                    psi = np.angle(v)                       # the focal phase of the current hologram, frozen
                else:                                       # later inner steps: the WGS weights g (reset to 1 per step)
                    b = np.maximum(np.abs(v) / a, 1e-300)
                    g = g * (np.mean(b) / b)
                phi = np.angle(fft_backproject(g * a * np.exp(1j * psi), setup, traps))
        e, v = fft_fields(phi, setup, traps)
        meas = camera.measure(e, setup, traps)
        history.append({
            "iteration": k, "efficiency": efficiency(trap_intensities(v)),
            "uniformity": uniformity(meas / w), "rel_std": rel_std(meas / w),
            "time_s": time.perf_counter() - t0,
            "rel_std_true": rel_std(trap_intensities(v, w)),
        })
        if budget.time_s is not None and history[-1]["time_s"] >= budget.time_s:
            break
    return Result(phi=phi, history=history, fields=v,
                  meta={"method": SPEC.id, "variant": variant, "gain": float(gain), "open_loop_rel_std": open_loop,
                        "camera_seed": camera.seed, "n_inner": n_inner})

