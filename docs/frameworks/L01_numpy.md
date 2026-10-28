# L01, numpy (the canonical engine's only numerical dependency)

## What and why

numpy 2.4.6 is the array library of the whole Python engine: the FFT (`numpy.fft`), the linear algebra of the optimizers, the random-number-free numerics of the forward models and the scorer. The engine of DinHot depends on
numpy and on nothing else numerical (ADR-0057: the product declares no package of its own, and the engine in `data-pipeline/pipeline/model/holo/` is a module tree, not a distribution). `scipy.fft` was considered and rejected: a second
heavy dependency for the same transforms. The lane gate treats numpy as the one wheel an engine may use and still be live-eligible (`LIVE_WHEELS`, `data-pipeline/pipeline/core/gate.py`), because the live lane is a TypeScript port of
exactly this numerical content.

## Install (exact, verified)

```
pip install numpy==2.4.6      # pinned in data-pipeline/requirements.txt, through requirements-precompute.txt
```

The same pin is used by the notebooks (`notebooks/requirements.txt`). `./scripts/setup.sh` builds the pipeline environment with it ([guide 01](../guides/01_precompute-pipeline.md)).

## Usage

```python
import numpy as np
from pipeline.model.holo.core.geometry import Setup
from pipeline.model.holo.core.forward import fft_focal_field

setup = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=64, pitch_m=12.5e-6, pad=2)
phi = np.zeros((64, 64))                  # a flat hologram: all the light goes to the zero order
e = fft_focal_field(phi, setup)           # centred, zero-padded, orthonormal FFT: shape (128, 128)
print(float(np.sum(np.abs(e) ** 2)))      # Parseval: equals n_pix squared = 4096
```

## Applying it here

Modules: all of `core/` ([P01](P01_forward-models-and-metrics.md) to [P07](P07_portable-rng.md)) and every method. The FFT convention (centred, zero-padded, orthonormal, with the linear phase that puts the origin on the optical axis) is
the engine's own and is what the TypeScript port reproduces; the random numbers do not come from `numpy.random` but from the portable generator, because the browser cannot reproduce numpy's streams.

## Caveats and licence

Floating-point rounding differs between platforms and between numpy builds at the level of 1e-12 relative, which is why the parity tolerances are stated per quantity. The licence of numpy is carried by the package and was not
re-read for this card (UNVERIFIED here); see [ATTRIBUTION](../../ATTRIBUTION.md) for the policy on dependencies.
