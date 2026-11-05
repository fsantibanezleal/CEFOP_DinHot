import { describe, expect, it } from 'vitest';
import * as tp from './trapphys';

describe('Rayleigh bead medium factor (Harada and Asakura 1996)', () => {
  const r = 0.1e-6, nP = 1.59, nM = 1.33;
  const m = nP / nM, lm = (m ** 2 - 1) / (m ** 2 + 2);

  it('the polarizability carries n_m^2', () => {
    const a = tp.rayleighPolarizabilityFm2(r, nP, nM);
    expect(a / (4 * Math.PI * tp.EPS0_F_PER_M * nM ** 2 * r ** 3 * lm)).toBeCloseTo(1, 12);
    expect(tp.rayleighPolarizabilityFm2(50e-9, 1.2, 1.33)).toBeLessThan(0);
  });

  it('the stiffness equals (2 pi n_m r^3 / c) L(m) (-d2I/dx2)', () => {
    const a = tp.rayleighPolarizabilityFm2(r, nP, nM);
    const curv = -3.0e22;
    const k = tp.gradientStiffnessNPerM(a, curv, nM);
    expect(k / (((2 * Math.PI * nM * r ** 3) / tp.C_M_PER_S) * lm * -curv)).toBeCloseTo(1, 12);
    expect(k / tp.gradientStiffnessNPerM(a, curv)).toBeCloseTo(1 / nM, 12);
  });

  it('vacuum (the default) is the old form', () => {
    const a = 3.3e-33;
    expect(tp.gradientStiffnessNPerM(a, -4.4e22)).toBe((-a / (2 * tp.C_M_PER_S * tp.EPS0_F_PER_M)) * -4.4e22);
    expect(tp.gaussianStiffnessNPerM(a, 2.1e10, 0.7e-6)).toBe((2 * a * 2.1e10) / (tp.C_M_PER_S * tp.EPS0_F_PER_M * 0.7e-6 ** 2));
  });

  it('the Gaussian stiffness and the stiffness map divide by n_m', () => {
    const a = tp.rayleighPolarizabilityFm2(50e-9, nP, nM);
    const w = 0.5e-6, dx = 0.02e-6, n = 121;
    const map = new Float64Array(n * n);
    for (let iy = 0; iy < n; iy++) for (let ix = 0; ix < n; ix++) {
      const x = (ix - 60) * dx, y = (iy - 60) * dx;
      map[iy * n + ix] = Math.exp((-2 * (x * x + y * y)) / w ** 2);
    }
    const i0 = tp.gaussianPeakIntensityWPerM2(1e-3, w);
    const vac = tp.stiffnessMap(map, n, n, dx, i0, a);
    const med = tp.stiffnessMap(map, n, n, dx, i0, a, nM);
    expect(med[0][60 * n + 60] / vac[0][60 * n + 60]).toBeCloseTo(1 / nM, 12);
    expect(med[0][60 * n + 60] / tp.gaussianStiffnessNPerM(a, i0, w, nM)).toBeCloseTo(1, 2);
    expect(tp.gaussianStiffnessNPerM(a, i0, w, nM) / tp.gaussianStiffnessNPerM(a, i0, w)).toBeCloseTo(1 / nM, 12);
  });

  it('refuses a non-positive medium index', () => {
    expect(() => tp.gradientStiffnessNPerM(1e-33, -1e22, 0)).toThrow('n_medium');
    expect(() => tp.gaussianStiffnessNPerM(1e-33, 1e10, 1e-6, NaN)).toThrow('n_medium');
  });
});
