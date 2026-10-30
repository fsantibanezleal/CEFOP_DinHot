/**
 * Elementary phase functions on the SLM grid: vortex, lens (axial offset) and grating (lateral offset).
 *
 * Python counterpart: `core/modes.py`. They are the phase terms of the delay `Delta_j^m` (algorithms D1.0). All outputs are
 * float64 in `[0, 2 pi)`.
 */
import { type Setup, slmAxis, wrapPhase } from './geometry';

function grid(setup: Setup, f: (x: number, y: number) => number): Float64Array {
  const n = setup.nPix, c = slmAxis(setup);
  const out = new Float64Array(n * n);
  for (let iy = 0; iy < n; iy++) for (let ix = 0; ix < n; ix++) out[iy * n + ix] = f(c[ix], c[iy]);
  return wrapPhase(out);
}

/** `charge * atan2(y - cy, x - cx)`; `centre` in metres on the SLM. */
export function vortexPhase(setup: Setup, charge: number, centre: [number, number] = [0, 0]): Float64Array {
  if (!Number.isInteger(charge)) throw new Error(`charge must be an integer, got ${charge}`);
  if (!centre.every(Number.isFinite)) throw new Error('centre must be finite');
  return grid(setup, (x, y) => charge * Math.atan2(y - centre[1], x - centre[0]));
}

/** Fresnel lens term `pi z (x^2 + y^2) / (lambda f^2)`. */
export function lensPhase(setup: Setup, zM: number): Float64Array {
  if (!Number.isFinite(zM)) throw new Error('z_m must be finite');
  const k = (Math.PI * zM) / (setup.wavelengthM * setup.focalM ** 2);
  return grid(setup, (x, y) => k * (x * x + y * y));
}

/** Blazed-grating term `2 pi (x x_m + y y_m) / (lambda f)`. */
export function gratingPhase(setup: Setup, xM: number, yM: number): Float64Array {
  if (!(Number.isFinite(xM) && Number.isFinite(yM))) throw new Error('trap position must be finite');
  const k = (2 * Math.PI) / (setup.wavelengthM * setup.focalM);
  return grid(setup, (x, y) => k * (x * xM + y * yM));
}
