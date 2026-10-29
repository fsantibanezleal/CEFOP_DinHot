// The yz cut by transposition (cuts.ts) equals the engine's own yz cut (forward.axialCut with x given), with and without an aberration.
import { describe, expect, it } from 'vitest';
import type { ParamsRecord } from '../lib/contract.types';
import { axialCutOf, setupOf } from '../engine/holo/engine';
import { axialCut } from '../engine/holo/forward';
import { phaseFromCoeffs } from '../engine/holo/zernike';
import { cutRequest, transpose } from './cuts';

const N = 32;

function params(aberration: boolean, beam: 'gaussian' | 'flat' = 'gaussian'): ParamsRecord {
  return {
    case_id: 'T',
    setup: { wavelength_nm: 1064, focal_mm: 2.4, na: 1.2, n_imm: 1.33, n_pix: N, pitch_um: 10, pad: 2, beam: beam === 'flat' ? { kind: 'flat' } : { kind: 'gaussian', waist_frac: 0.8 } },
    device: null,
    target: {
      kind: 'traps',
      traps: [
        { id: 0, x_um: 6, y_um: -3, z_um: 0, weight: 1, charge: 0 },
        { id: 1, x_um: -9, y_um: 4.5, z_um: 5, weight: 1, charge: 0 },
      ],
    },
    aberration: aberration ? { noll: { '4': 0.2, '7': -0.15, '8': 0.1 } } : null,
    methods: ['M04'],
    reference_method: 'M04',
    budget: { iterations: 5, time_s: null },
    seed: 1,
    feedback: null,
    dynamics: null,
    rearrangement: null,
    expect: {},
  } as unknown as ParamsRecord;
}

function phase(): Float64Array {
  const p = new Float64Array(N * N);
  // asymmetric on purpose: a plane wave tilt, a quadratic term in x only and a bump, so x and y are not interchangeable
  for (let iy = 0; iy < N; iy++) for (let ix = 0; ix < N; ix++) p[iy * N + ix] = (0.31 * ix + 0.07 * iy + 0.004 * ix * ix + Math.sin(ix * 0.5) * Math.cos(iy * 0.3)) % (2 * Math.PI);
  return p;
}

describe('the yz cut by transposition', () => {
  it.each([
    ['no aberration', false, 'gaussian' as const],
    ['with an aberration', true, 'gaussian' as const],
    ['a flat beam', false, 'flat' as const],
  ])('equals the engine yz cut (%s)', (_name, ab, beam) => {
    const p = params(ab, beam);
    const ph = phase();
    for (const trapId of [0, 1]) {
      const req = cutRequest('yz', ph, N, p, trapId, 24);
      const got = axialCutOf(req.params, req.phase, req.trapId, req.nz);
      // the engine's direct yz cut: the same z range, the plane at the trap's x
      const s = setupOf(p);
      const trap = (p.target as { traps: { id: number; x_um: number; z_um: number }[] }).traps.find((t) => t.id === trapId)!;
      const halfZ = Math.max((5 * s.wavelengthM * s.nImm) / s.na ** 2, 1.5 * Math.max(...(p.target as { traps: { z_um: number }[] }).traps.map((t) => Math.abs(t.z_um * 1e-6))));
      const ab2 = p.aberration ? phaseFromCoeffs([0, 0, 0, 0.2, 0, 0, -0.15, 0.1], s) : null;
      const phi = ab2 ? ph.map((v, i) => v + ab2[i]) : ph;
      const direct = axialCut(phi, s, { xM: trap.x_um * 1e-6, zRangeM: [-halfZ, halfZ], nz: 24 });
      expect(got.nx).toBe(direct.nLateral);
      let worst = 0;
      let peak = 0;
      for (let i = 0; i < direct.intensity.length; i++) {
        worst = Math.max(worst, Math.abs(got.xz[i] - direct.intensity[i]));
        peak = Math.max(peak, direct.intensity[i]);
      }
      expect(peak).toBeGreaterThan(0);
      // the test is not vacuous: the xz cut of this trap is a different picture, so a missing transposition would be caught
      const xz = cutRequest('xz', ph, N, p, trapId, 24);
      const other = axialCutOf(xz.params, xz.phase, xz.trapId, xz.nz);
      let differ = 0;
      for (let i = 0; i < direct.intensity.length; i++) differ = Math.max(differ, Math.abs(other.xz[i] - direct.intensity[i]));
      expect(differ / peak).toBeGreaterThan(1e-3);
      expect(worst / peak).toBeLessThan(1e-6);
    }
  });

  it('the xz request is the engine request unchanged, and transposing twice is the identity', () => {
    const p = params(false);
    const ph = phase();
    const req = cutRequest('xz', ph, N, p, 0, 16);
    expect(req.params).toBe(p);
    expect(Array.from(req.phase)).toEqual(Array.from(ph));
    expect(Array.from(transpose(transpose(ph, N), N))).toEqual(Array.from(ph));
  });

  it('a record without traps has no axial cut', () => {
    const p = { ...params(false), target: { kind: 'shaped' } } as unknown as ParamsRecord;
    expect(() => cutRequest('yz', phase(), N, p, 0, 8)).toThrow(/trap target/);
  });
});
