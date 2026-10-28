r"""M14: Zernike aberration correction and sensorless modal recovery.

Model (dossier D3.3, Nogrette et al. https://arxiv.org/abs/1402.5329 and Ebadi et al. https://arxiv.org/abs/2012.12281: the
aberration phase is always added to the final SLM phase; the total phase is $\phi + \phi_{\rm blaze} + \phi_{\rm Fresnel} +
\phi_{\rm SH}$): the optical system adds the unknown wavefront $2\pi\,\sum_j c_j Z_j$ to the displayed phase
(``injected``, Noll coefficients in waves, orthonormal modes of ``core.zernike`` over the disc inscribed in the SLM). The
displayed hologram is the base hologram (M06 weighted GS, ``base_iterations`` = 30, or ``init``) minus the correction:
$$\phi_{\rm shown} = \phi_{\rm base} - 2\pi \sum_j \hat c_j Z_j,\qquad E = \mathcal F[A\,e^{\,i(\phi_{\rm shown} + 2\pi \sum_j c_j Z_j)}]$$
``mode='correct'``: ``known`` coefficients are subtracted (exact when ``known == injected``).

``mode='recover'`` (default): sensorless modal search, no wavefront sensor, only the emulated camera (``core.camera``,
default: ideal gains, no noise, no roll-off, seeded from ``rng``). The merit is the summed measured trap intensity
$M(\hat c) = \sum_m I_m$, which the Marechal approximation makes a Gaussian in the residual wavefront rms
($M \propto \exp[-(2\pi\sigma)^2]$, ``core.zernike`` docstring, UNVERIFIED against Noll 1976), so $\ln M$ is a parabola in
each coefficient. One sweep visits the modes in ``modes`` (default Noll 4 to 11, tip, tilt and piston excluded: they
move or do not change the traps) and for each mode evaluates $M$ at $\hat c_j - \delta, \hat c_j, \hat c_j + \delta$
($\delta$ = ``trial_waves`` = 0.06), fits the parabola to $\ln M$ and moves to its vertex (step clipped to $\pm 2\delta$; if
the three points are not concave, to the best of them). The modes are not exactly orthogonal under the Gaussian beam and
the off-axis traps, so the sweep is repeated: ``Budget.iterations`` sweeps (stop early when the largest update falls below
$10^{-4}$ waves). Cost: $3 \times 8 + 1$ camera frames per sweep. ``history`` has one entry per sweep: the ideal trap
fields of the corrected system, plus ``coef_rms_error`` (waves, over the searched modes) when ``injected`` is known.
``meta``: ``coefficients`` (length 21, zeros outside ``modes``), ``base_efficiency`` (no aberration),
``uncorrected_efficiency``. Defaults: ``mode='recover'``, ``modes=range(4, 12)``, ``trial_waves=0.06``.
"""
from __future__ import annotations

import math
import time

import numpy as np

from ...core.camera import EmulatedCamera
from ...core.forward import fft_focal_field, trap_fields_from_fft
from ...core.geometry import wrap_phase
from ...core.metrics import efficiency, trap_intensities
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from ...core.zernike import J_MAX, wavefront_waves
from ..baseline import m06_gsw
from ..baseline._common import Recorder, require_kinds

SPEC = MethodSpec(id="M14", name="Zernike correction and sensorless modal recovery", family="control", lane="live",
                  targets=("traps",), dims=(2, 3))

MODES = tuple(range(4, 12))


def _vector(c, name: str) -> np.ndarray:
    v = np.zeros(J_MAX)
    if c is not None:
        c = np.asarray(c, dtype=np.float64).ravel()
        if c.size > J_MAX:
            raise ValueError(f"{name}: at most {J_MAX} coefficients (Noll j = 1..{J_MAX}), got {c.size}")
        if not np.all(np.isfinite(c)):
            raise ValueError(f"{name}: coefficients must be finite")
        v[: c.size] = c
    return v


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None, mode: str = "recover",
        injected=None, known=None, camera: EmulatedCamera | None = None, modes=MODES, trial_waves: float = 0.06,
        base_iterations: int = 30) -> Result:
    require_kinds(target, SPEC.targets, SPEC.id)
    if mode not in ("recover", "correct"):
        raise ValueError(f"mode must be 'recover' or 'correct', got {mode!r}")
    modes = tuple(int(j) for j in modes)
    if not modes or any(j < 1 or j > J_MAX for j in modes) or len(set(modes)) != len(modes):
        raise ValueError(f"modes must be distinct Noll indices in 1..{J_MAX}, got {modes!r}")
    if not (math.isfinite(trial_waves) and trial_waves > 0):
        raise ValueError("trial_waves must be finite and positive")
    inj = _vector(injected, "injected")
    if mode == "correct" and known is None:
        raise ValueError("mode='correct' needs the known coefficients (known=...)")
    traps = target.traps
    t0 = time.perf_counter()
    # the basis of the modes on the SLM grid, once
    basis = {j: wavefront_waves(np.eye(J_MAX)[j - 1], setup) for j in range(1, J_MAX + 1)
             if inj[j - 1] != 0.0 or j in modes or (known is not None and _vector(known, "known")[j - 1] != 0.0)}
    w_inj = sum((inj[j - 1] * b for j, b in basis.items()), np.zeros((setup.n_pix, setup.n_pix)))

    base = m06_gsw.run(setup, target, budget=Budget(base_iterations), rng=rng, init=init, form="point") \
        if init is None else None
    phi_base = base.phi if base is not None else np.asarray(init, dtype=np.float64)

    def focal(c_hat: np.ndarray) -> np.ndarray:
        w_corr = sum((c_hat[j - 1] * basis[j] for j in modes if c_hat[j - 1] != 0.0), np.zeros_like(w_inj))
        return fft_focal_field(phi_base - 2.0 * math.pi * w_corr + 2.0 * math.pi * w_inj, setup)

    def true_v(c_hat):
        return trap_fields_from_fft(focal(c_hat), setup, traps)

    zero = np.zeros(J_MAX)
    base_eff = efficiency(trap_intensities(trap_fields_from_fft(
        fft_focal_field(phi_base, setup), setup, traps)))
    uncorrected_eff = efficiency(trap_intensities(true_v(zero)))
    rec = Recorder(budget, traps.weight)

    if mode == "correct":
        k_vec = _vector(known, "known")
        c_hat = np.zeros(J_MAX)
        basis_k = {j: basis[j] if j in basis else wavefront_waves(np.eye(J_MAX)[j - 1], setup)
                   for j in range(1, J_MAX + 1) if k_vec[j - 1] != 0.0}
        w_corr = sum((k_vec[j - 1] * b for j, b in basis_k.items()), np.zeros_like(w_inj))
        phi = wrap_phase(phi_base - 2.0 * math.pi * w_corr)
        v = trap_fields_from_fft(fft_focal_field(phi + 2.0 * math.pi * w_inj, setup), setup, traps)
        rec.add(1, v)
        return Result(phi=phi, history=rec.history, fields=v,
                      meta={"method": SPEC.id, "mode": mode, "coefficients": k_vec, "base_efficiency": base_eff,
                            "uncorrected_efficiency": uncorrected_eff})

    if camera is None:
        camera = EmulatedCamera(seed=rng.next_u32(), gain_rms=0.0, rolloff=False)

    def merit(c_hat) -> float:
        return float(np.sum(camera.measure(focal(c_hat), setup, traps)))

    c_hat = np.zeros(J_MAX)
    d = float(trial_waves)
    k = 0
    while True:
        k += 1
        biggest = 0.0
        for j in modes:
            y = []
            for off in (-d, 0.0, d):
                trial = c_hat.copy()
                trial[j - 1] += off
                y.append(math.log(max(merit(trial), 1e-300)))
            curv = y[0] - 2.0 * y[1] + y[2]
            if curv < 0.0:
                step = d * (y[0] - y[2]) / (2.0 * curv)
                step = float(np.clip(step, -2.0 * d, 2.0 * d))
            else:
                step = (-d, 0.0, d)[int(np.argmax(y))]
            c_hat[j - 1] += step
            biggest = max(biggest, abs(step))
        v = true_v(c_hat)
        err = float(np.sqrt(np.sum((c_hat[[j - 1 for j in modes]] - inj[[j - 1 for j in modes]]) ** 2)))
        rec.add(k, v, coef_rms_error=err)
        if rec.done(k) or biggest < 1e-4:
            break
    w_corr = sum((c_hat[j - 1] * basis[j] for j in modes), np.zeros_like(w_inj))
    phi = wrap_phase(phi_base - 2.0 * math.pi * w_corr)
    return Result(phi=phi, history=rec.history, fields=v,
                  meta={"method": SPEC.id, "mode": mode, "coefficients": c_hat, "base_efficiency": base_eff,
                        "uncorrected_efficiency": uncorrected_eff, "sweeps": k,
                        "elapsed_s": time.perf_counter() - t0})
