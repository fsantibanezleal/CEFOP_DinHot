// The dense kernels of vortex traps are computed once per PointPlan (the cache): the result must be the same to the bit as the
// per-call computation, on repeated calls, with plain and vortex traps mixed, and the cache must stay off above its bound.
import { describe, expect, it } from 'vitest';
import { DENSE_CACHE_MAX, PointPlan } from './forward';
import { makeSetup } from './geometry';
import { TrapSet } from './traps';

const setup = makeSetup({ wavelengthM: 1064e-9, focalM: 2.4e-3, na: 1.2, nImm: 1.33, nPix: 48, pitchM: 10e-6 });
const um = 1e-6;
const traps = new TrapSet([
  { id: 1, xM: 8 * um, yM: 0, zM: 0, charge: 1 },
  { id: 2, xM: -6 * um, yM: 5 * um, zM: 2 * um, charge: -2 },
  { id: 3, xM: 0, yM: -9 * um, zM: -1 * um, charge: 3 },
  { id: 4, xM: 4 * um, yM: 4 * um },
  { id: 5, xM: -3 * um, yM: -2 * um, zM: 1.5 * um },
]);

/** A deterministic complex field and coefficient vector (no RNG dependency). */
const field = Float64Array.from({ length: 2 * setup.nPix * setup.nPix }, (_, i) => Math.sin(0.37 * i) + 0.25 * Math.cos(0.011 * i * i));
const coeffs = Float64Array.from({ length: 2 * traps.length }, (_, i) => Math.cos(1.3 * i + 0.2));

describe('PointPlan dense kernels of vortex traps', () => {
  it('projects and back-projects to the bit as the per-call computation, on every call', () => {
    const cached = new PointPlan(setup, traps);
    const plain = new PointPlan(setup, traps, 0); // bound 0: no cache, the kernels are recomputed per call
    for (let call = 0; call < 3; call++) {
      expect(Array.from(cached.project(field))).toEqual(Array.from(plain.project(field)));
      expect(Array.from(cached.backproject(coeffs))).toEqual(Array.from(plain.backproject(coeffs)));
    }
  });

  it('keeps the plain traps on the separable path and the vortex traps on the dense one (adjointness holds)', () => {
    const plan = new PointPlan(setup, traps);
    // <P f, c> = (1 / N_pix) <f, P* c> for the projection P and its adjoint P* (back-projection without 1 / N_pix)
    const v = plan.project(field);
    const b = plan.backproject(coeffs);
    let lr = 0, li = 0, rr = 0, ri = 0;
    for (let m = 0; m < traps.length; m++) {
      lr += v[2 * m] * coeffs[2 * m] + v[2 * m + 1] * coeffs[2 * m + 1];
      li += v[2 * m + 1] * coeffs[2 * m] - v[2 * m] * coeffs[2 * m + 1];
    }
    const n2 = setup.nPix * setup.nPix;
    for (let i = 0; i < n2; i++) {
      rr += field[2 * i] * b[2 * i] + field[2 * i + 1] * b[2 * i + 1];
      ri += field[2 * i + 1] * b[2 * i] - field[2 * i] * b[2 * i + 1];
    }
    expect(lr).toBeCloseTo(rr / n2, 10);
    expect(li).toBeCloseTo(ri / n2, 10);
  });

  it('bounds the cache: the default keeps a vortex case of 256 x 256 pixels and refuses one past the bound', () => {
    expect(16 * 256 * 256).toBeLessThanOrEqual(DENSE_CACHE_MAX); // case C06: sixteen vortex traps on 256 x 256 pixels
    const small = new PointPlan(setup, traps, 3 * setup.nPix * setup.nPix - 1); // one value short of the three vortex kernels
    const plain = new PointPlan(setup, traps, 0);
    expect(Array.from(small.project(field))).toEqual(Array.from(plain.project(field)));
  });
});
