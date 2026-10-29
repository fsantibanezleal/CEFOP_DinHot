r"""M13 device-aware conjugate gradient with the pixel-crosstalk kernel (Schroff et al. 2023; dossier D3.4).

Source: Schroff, La Rooij, Haller, Kuhr, Sci. Rep. 13, 3252 (2023), https://doi.org/10.1038/s41598-023-30296-6
(arXiv 2212.10507). Forward model: each SLM pixel is upsampled to 3 x 3 computational pixels and the phase is
convolved with a kernel before the Fourier transform,

.. math::
    \tilde\phi = K * \phi_{\uparrow 3},\qquad
    K = \mathcal F^{-1}\left\{\exp\left[-\frac{|\kappa_x|^q + |\kappa_y|^q}{\sigma^q}\right]\right\},\quad
    \sigma = 1.24\ \mathrm{px}^{-1},\ q = 1.80,

and the cost is the squared error over the signal region (the paper: ``C = s sum_S (T~ - I~)^2`` with normalised
``T~, I~`` and Polak-Ribiere CG, gradient by autodiff). Here the cost is Harte's ``C_t`` of M10 (``_common.FieldCost``)
evaluated on the device's focal field, optimised by the same Fletcher-Reeves/strong-Wolfe CG as M10, and the
gradient is the closed form of ``_common.FocalForward.adjoint``: the adjoint of the crosstalk operator is the
convolution with the reversed kernel followed by the sum over each ``3 x 3`` block (``core.device.crosstalk_adjoint``),
so the TypeScript port needs no autodiff.

The model is the ``device`` passed in: crosstalk, the pixel-aperture envelope and the quantizer (straight-through:
quantized in the forward pass, identity in the backward pass; flicker is dropped). With ``device=None`` M13 is M10
(an ideal device has no crosstalk to model). The unit of the kernel's ``k`` (cycles per SLM pixel) is the
UNVERIFIED assumption recorded in ``core/device.py``.

Quantizer and the line search (I3). With a quantizing device (``bit_depth`` not None) the cost is evaluated on the rounded phase
while the backward pass is the identity, so along a search direction the value is a staircase and the gradient is not its slope.
The strong-Wolfe search of M10 then found no step after two or three iterations whatever the budget (measured on case C08: 26
evaluations per search, 5 and 60 iterations both stopped at 3, the same result; with the quantizer removed the same run goes on for 21
iterations). The cause is the search, not a bug of the gradient (the finite-difference test of the crosstalk operator holds). For
such a model M13 runs ``_common.cg_minimize`` under ``staircase_search()``, which takes a ladder of trial steps that asks only for sufficient decrease and, when no trial lowers
the value, walks on to the lowest trial and keeps the best point (the cost reported never rises, and the iteration count follows
the budget: C08 at 5 and 60 iterations now runs 5 and 60, the cost falling from 0.0536 to 0.0527 and to 0.0493). A device without a quantizer keeps the strong-Wolfe search unchanged, and so do M10 and B1 (B1 on C08 has the same stall; it is not changed here).

Schroff's results (their Table 1): large disc 1.9 percent error
with the model against 2.7 percent without, efficiency 28 against 34 percent; run time about 6x longer than without
the model (here the cost per iteration is one 3x3-upsampled FFT pair against one FFT pair).
"""
from __future__ import annotations

import numpy as np

from ...core.device import Device
from ...core.geometry import Setup
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from . import _common as C
from .m10_cg import optimize

SPEC = MethodSpec(id="M13", name="Device-aware CG with pixel crosstalk", family="optimization", lane="baked",
                  targets=("traps", "field"), dims=(2,))
SCHROFF_DEVICE = Device(crosstalk=(1.24, 1.80), upsample=3)


def run(setup: Setup, target: Target, *, device: Device | None = None, budget: Budget, rng: Rng,
        init: np.ndarray | None = None, t=None, efficiency: float | None = None) -> Result:
    """CG on the device's focal field; ``Result.fields`` is the focal field (traps: the trap fields) of the device."""
    if target.kind == "traps" and device is not None and (np.any(target.traps.z_m != 0)
                                                           or np.any(target.traps.charge != 0)):
        raise ValueError("M13 supports traps with z = 0 and no vortex charge on a device (targets: traps, field)")
    with C.staircase_search():          # a quantizing device makes the cost a staircase (module docstring)
        return optimize(setup, target, device=device, budget=budget, rng=rng, init=init, t=t, efficiency=efficiency,
                        label="M13")
