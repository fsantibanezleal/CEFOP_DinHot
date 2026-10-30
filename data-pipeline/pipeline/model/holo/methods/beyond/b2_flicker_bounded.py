r"""B2 flicker-bounded phase-continuous hologram sequence for moving traps (algorithms dossier D5.1 B2, SDD BS-2).

Gap: linear phase interpolation (LPI; arXiv 2501.01391, dossier D3.2) interpolates the position, amplitude and optical
phase of every tweezer between two endpoint holograms and inverts the Fourier transform at each step, so the
intermediate holograms are never individually optimised: their trap intensities are uneven and the interference of
the transient spots makes the intensity dip ("at 11 kHz sampling the WGS spot nearly vanished several times, the LPI
spot stayed above 70 percent").

Method. For a trajectory ``x_m(s)``, ``s = 0..S`` and trap phases ``theta_m(s)`` that are smooth in ``s``, every frame
is the phase-fixed weighted GS of Kim et al. 2019 (dossier D1.3) with the trap phases *locked* to the trajectory,

.. math::
    c_m = w_m\, a_m\, e^{i\theta_m(s)},\quad w_m \leftarrow w_m \langle r\rangle / r_m,\quad
    \phi_j = \arg \sum_m c_m e^{+i\Delta_j^m(x_m(s))},

started from the previous frame's hologram and weights (warm start: a few iterations per frame). The positions follow
the minimal-jerk profile ``x_m(s) = x_m(0) + (x_m(S) - x_m(0))\,(10\tau^3 - 15\tau^4 + 6\tau^5)``, ``tau = s / S``. The
phases are ``theta_m(s) = theta_m(0) + \mathrm{wrap}(\theta_m^{end} - \theta_m(0))\,h(\tau)`` with the same ``h`` (default:
``theta^{end} = theta(0)``, phases held), and ``run`` raises ``ValueError`` if the phase step per frame exceeds
``phase_velocity_max`` (default 0.3 rad; LPI paper: slips of several tenths of pi barely mattered, near pi lost atoms).
Frame 0 is a cold phase-fixed WGS of ``budget.iterations`` iterations; later frames use ``frame_iterations`` (default 10).
The optimization drops the penalty form of the dossier's loss (``lambda sum (arg V - theta)^2``) for the hard lock,
which is its ``lambda -> infinity`` limit.

Transient intensity (UNVERIFIED model: the dossier gives the LPI paper's measurement, not its transient equation).
Between frames ``s`` and ``s+1`` the displayed SLM field is modelled as the blend ``f_a = A\,[(1-a) e^{i\phi_s} + a
e^{i\phi_{s+1}}]``, ``a`` in [0, 1] (the liquid crystal relaxing between the two holograms), and the trap ``m`` is
read at its trajectory point ``x_m(s + a)``: ``I_m(s, a) = |V_m(f_a; x_m(s+a))|^2``. ``transient_min_ratio`` returns for
each trap ``min_{s,a} I_m(s, a) / mean_s I_m(s)``. Both B2 and the LPI baseline of the tests are scored by the same
function. Not modelled: SLM refresh rate, the temporal response of the device.

Limit of the claim (measured, case C10, ``frames_for_move``). The blend model has a closed form for a pattern that shifts by
``delta`` Fourier units (``lambda f / (n_pix p)``) between two frames: with a flat input, the trap read half way has the amplitude
``sinc(delta / 2)``, so its intensity falls to ``sinc^2(delta / 2)`` of the frame's (0.9 at ``delta`` = 0.35 Fourier units); the
minimal-jerk profile moves fastest by ``PEAK_JERK = 15/8`` times the mean step, so the frames needed grow with the move: ``frames - 1 >=
PEAK_JERK L / delta`` for a move of ``L`` Fourier units. That is an upper bound, and the lowest moving trap measured 0.03 to
0.07 below it (frame-to-frame changes of the other traps). The acceptance task moves 4 bins (2 Fourier units at padding 2) in the
default 13 frames, a peak step of 0.31 Fourier units, and meets 0.9. The sort of C10, on M16's own plan, moves 16 of its 36 traps by up to 29 bins
(14.5 Fourier units) with the end phases of the final hologram given (``end_phases``; held phases dim the moving traps to 0.177 on seed 1, the phases that
make the traps equal at the end of a long move are other ones), and the lowest moving trap measured, over frames (seed 1, 10
iterations per frame; more iterations per frame change nothing):

    frames       25     49     97    129
    peak step    1.13   0.57   0.28  0.21   Fourier units per frame
    lowest       0.333  0.741  0.883 0.905

So BS-2 (at least 0.9) holds for a move only when the peak step per frame is at most ``CLAIM_STEP_FU`` = 0.2 Fourier units, which the
13-frame default allows for moves of about 1.3 Fourier units on that calibration (the acceptance task meets it at 2); ``frames_for_move``
gives the frames a move needs (137 for the longest move of C10).
Against LPI on the same assignment (one Hungarian assignment at alpha 1.0, 17 moving traps, the same transient model; LPI is the
test module's two independent phase-fixed WGS endpoints, interpolated linearly) the lowest moving trap measured:

    C10 sort on M16's plan (16 moving traps), seeds 1 to 6
                                 25 frames        137 frames
    LPI                          0.320 to 0.594   0.360 to 0.690
    B2 (end phases given)        0.205 to 0.391   0.902 to 0.917 on 5 of 6 seeds (median 0.911); seed 2 collapses to 0.155
    acceptance task (13 frames, seeds 1 to 3): B2 0.916 to 0.926, LPI 0.551 to 0.709.

So B2 leads LPI on the acceptance task and on the long sort only with enough frames (about 137); at 25 frames LPI leads B2
on the long sort in every seed, and at 137 frames on every seed but one. BS-2 (0.9) holds for B2 when the peak step per frame is at most 0.2 Fourier units and the end
phases are given, on most seeds and not on all: on the acceptance lattice with two columns moved 12 or 20 bins (8 seeds,
``frames_for_move`` frames) the median lowest moving trap is 0.933 and 0.936 and 6 of 8 seeds reach 0.9; the other seeds stay
below with twice the frames as well (0.023 and 0.768 at 12 bins, 0.584 and 0.847 at 20), so their limit is the phase path the
end phases prescribe and not the frame count. LPI does not reach 0.9 in any row. Measured 2026-10-29 after the GS family was
made the ladder methods' own rules (``optim/_gs_family.py``); the transient model is unverified in absolute terms.

``run(setup, target, ..., destination=None, frames=13)``: ``target`` holds the initial traps, ``destination`` the final
positions with the same ids (``None``: the traps hold still, a static sequence). 13 holograms are the dossier's
6x6 to 4x4 sort. Point-trap form (any trap position, not only bins), ideal device.
"""
from __future__ import annotations

import math
import time
from dataclasses import replace

import numpy as np

from ...core.forward import point_trap_backproject, point_trap_projection, slm_field
from ...core.geometry import Setup, focal_bin_m, input_amplitude
from ...core.rng import Rng
from ...core.traps import TrapSet
from ...core.types import Budget, MethodSpec, Result, Target
from ..optim import _common as C
from ..optim._gs_family import weighted_gs

SPEC = MethodSpec(id="B2", name="Flicker-bounded phase-continuous sequence", family="beyond", lane="baked",
                  targets=("traps",), dims=(2, 3))
DEFAULT_FRAMES = 13
DEFAULT_FRAME_ITERATIONS = 10
DEFAULT_PHASE_VELOCITY_MAX = 0.3
PEAK_JERK = 15.0 / 8.0       # peak velocity of the minimal-jerk profile in units of the mean velocity: d/dtau (10 t^3 - 15 t^4 + 6 t^5) at 1/2
CLAIM_STEP_FU = 0.2          # peak step per frame, in Fourier units, at which the lowest moving trap of C10's sort measured 0.9 (docstring)


def min_jerk(tau: np.ndarray | float) -> np.ndarray | float:
    """Minimal-jerk time profile ``10 tau^3 - 15 tau^4 + 6 tau^5`` (0 at 0, 1 at 1, zero velocity and acceleration at both)."""
    tau = np.clip(tau, 0.0, 1.0)
    return 10.0 * tau**3 - 15.0 * tau**4 + 6.0 * tau**5


def move_fourier_units(setup: Setup, start: TrapSet, end: TrapSet | None) -> float:
    """The longest lateral move of any trap, in Fourier units ``lambda f / (n_pix p)`` (a focal bin is ``1 / pad`` of one)."""
    if end is None or len(end) == 0:
        return 0.0
    longest = max(math.hypot(e.x_m - t.x_m, e.y_m - t.y_m) for t, e in zip(start, end))
    return longest / (focal_bin_m(setup) * setup.pad)


def peak_step_fu(setup: Setup, start: TrapSet, end: TrapSet | None, frames: int) -> float:
    """The largest shift between two consecutive frames, in Fourier units: ``PEAK_JERK`` times the mean step of the longest move."""
    if frames < 2:
        raise ValueError("frames must be >= 2")
    return PEAK_JERK * move_fourier_units(setup, start, end) / (frames - 1)


def frames_for_move(setup: Setup, start: TrapSet, end: TrapSet | None, step_fu: float = CLAIM_STEP_FU,
                    minimum: int = DEFAULT_FRAMES) -> int:
    """The fewest frames (at least ``minimum``) whose peak step per frame is at most ``step_fu`` Fourier units (module docstring)."""
    if not step_fu > 0:
        raise ValueError("step_fu must be positive")
    need = PEAK_JERK * move_fourier_units(setup, start, end) / step_fu
    return max(int(minimum), int(math.ceil(need - 1e-9)) + 1)


def wrap_pi(x: np.ndarray) -> np.ndarray:
    """Wrap to (-pi, pi]."""
    return -np.mod(-np.asarray(x, dtype=np.float64) + math.pi, 2.0 * math.pi) + math.pi


def trajectory(start: TrapSet, end: TrapSet | None, frames: int, profile=min_jerk):
    """Trap sets at fractional frame positions: returns ``at(s)`` for ``s`` in ``[0, frames - 1]`` (frames - 1 = S)."""
    if frames < 2:
        raise ValueError("frames must be >= 2")
    if end is not None and (len(end) != len(start) or not np.array_equal(end.ids, start.ids)):
        raise ValueError("the destination must hold the same trap ids in the same order")
    s_total = frames - 1

    def at(s: float) -> TrapSet:
        if end is None:
            return start
        h = float(profile(s / s_total))
        return TrapSet(replace(t, x_m=t.x_m + (e.x_m - t.x_m) * h, y_m=t.y_m + (e.y_m - t.y_m) * h,
                               z_m=t.z_m + (e.z_m - t.z_m) * h) for t, e in zip(start, end))

    return at


def transient_min_ratio(setup: Setup, phis: list, at, substeps: int = 10) -> np.ndarray:
    """Per-trap ``min_{s,a} I_m(s, a) / mean_s I_m(s)`` for the sequence ``phis`` along ``at(s)`` (module docstring).

    ``at(s)`` returns the trap set at the (fractional) frame ``s``; ``substeps`` sub-frames per frame interval
    (``a = j / substeps``, ``j = 0..substeps``).
    """
    amp = input_amplitude(setup)
    e = [np.exp(1j * p) for p in phis]
    frame_i = np.array([np.abs(point_trap_projection(amp * e[s], setup, at(float(s)))) ** 2
                        for s in range(len(phis))])
    low = frame_i.min(axis=0)
    for s in range(len(phis) - 1):
        for j in range(1, substeps):
            a = j / substeps
            v = point_trap_projection(amp * ((1.0 - a) * e[s] + a * e[s + 1]), setup, at(s + a))
            low = np.minimum(low, np.abs(v) ** 2)
    return low / frame_i.mean(axis=0)


def run(setup: Setup, target: Target, *, device=None, budget: Budget, rng: Rng, init: np.ndarray | None = None,
        destination: TrapSet | None = None, frames: int = DEFAULT_FRAMES,
        frame_iterations: int = DEFAULT_FRAME_ITERATIONS, end_phases: np.ndarray | None = None,
        phase_velocity_max: float = DEFAULT_PHASE_VELOCITY_MAX, n_fix: int = 12) -> Result:
    """The sequence of ``frames`` holograms; ``Result.phi`` is the last frame, ``meta['frames']`` all of them."""
    if target.kind != "traps":
        raise ValueError("B2 supports trap targets only (targets: 'traps'); got a shaped field")
    start = target.traps
    at = trajectory(start, destination, frames)
    t0 = time.perf_counter()
    deadline = C.deadline_of(budget.time_s)
    a = np.sqrt(start.weight / np.mean(start.weight))
    # frame 0: cold phase-fixed WGS on the initial traps
    phi0, _ = weighted_gs(setup, start, budget.iterations, rng, variant="pfwgs", n_fix=min(n_fix, budget.iterations),
                          init=init)
    v0 = point_trap_projection(slm_field(phi0, setup), setup, start)
    theta0 = np.angle(v0)
    theta_end = theta0 if end_phases is None else np.asarray(end_phases, dtype=np.float64)
    if theta_end.shape != theta0.shape:
        raise ValueError(f"end_phases must have one phase per trap ({len(start)})")
    dtheta = wrap_pi(theta_end - theta0)
    steps = np.abs(np.diff(np.array([dtheta * float(min_jerk(s / (frames - 1))) for s in range(frames)]), axis=0))
    if steps.size and steps.max() > phase_velocity_max:
        raise ValueError(f"the phase step per frame reaches {steps.max():.3f} rad, above phase_velocity_max "
                         f"{phase_velocity_max}; use more frames or closer end phases")
    phis = [phi0]
    history = [C.trap_history(1, v0, start.weight, t0)]
    w = np.ones(len(start))
    phi, v = phi0, v0
    for s in range(1, frames):
        if C.expired(deadline):
            break
        traps_s = at(float(s))
        theta = np.exp(1j * (theta0 + dtheta * float(min_jerk(s / (frames - 1)))))
        for _ in range(frame_iterations):
            v = point_trap_projection(slm_field(phi, setup), setup, traps_s)
            r = np.maximum(np.abs(v), 1e-300) / a
            w = w * np.mean(r) / r
            phi = np.angle(point_trap_backproject(w * a * theta, setup, traps_s))
        v = point_trap_projection(slm_field(phi, setup), setup, traps_s)
        phis.append(np.mod(phi, 2.0 * math.pi))
        history.append(C.trap_history(s + 1, v, start.weight, t0))
    ratio = transient_min_ratio(setup, phis, at)
    moving = np.array([bool(np.hypot(e.x_m - t.x_m, e.y_m - t.y_m) > 0) for t, e in
                       zip(start, destination if destination is not None else start)])
    return Result(phi=phis[-1], history=history, fields=v,
                  meta={"frames": np.array(phis), "transient_ratio": ratio, "moving": moving,
                        "theta0": theta0, "frame_iterations": frame_iterations, "n_frames": len(phis)})
