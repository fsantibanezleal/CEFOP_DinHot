// The trace encodings, the device display maths and the Zernike port, held to the engine's definitions and to the committed trace.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { Trace } from '../lib/contract.types';
import {
  apertureEnvelopeAtEdge,
  b64ToU8,
  crosstalkWeights,
  dbFromU8,
  decodeRle,
  fillFactorEfficiency,
  gratingPeriodPx,
  levelOf,
  linearToDb,
  phaseDifference,
  phaseFromU8,
  quantizationEfficiency,
  quantizePhase,
  separableBlur,
  stagePhase,
  TWO_PI,
} from './decode';
import { lutRgb, INTENSITY_LUT, PHASE_LUT } from './colormaps';
import { coeffArray, nollToNm, rmsWaves, strehl, wavefrontWaves, zernike, zernikeName } from './zernike';

const trace = JSON.parse(readFileSync(new URL('../../../docs/contracts/fixtures/data/derived/FX01_fixture/trace.json', import.meta.url), 'utf8')) as Trace;

describe('the trace encodings', () => {
  it('decodes the fixture phase to n_pix squared bytes and the focal map to size squared', () => {
    const n = trace.grid.n_pix;
    expect(b64ToU8(trace.reference.phase_u8).length).toBe(n * n);
    expect(b64ToU8(trace.reference.focal.intensity_db_u8).length).toBe(trace.reference.focal.size ** 2);
  });
  it('maps bytes to radians over [0, 2 pi) and to dB between the floor and 0', () => {
    const p = phaseFromU8(Uint8Array.of(0, 128, 255));
    expect(p[0]).toBe(0);
    expect(p[1]).toBeCloseTo(Math.PI, 6);
    expect(p[2]).toBeLessThan(TWO_PI);
    const d = dbFromU8(Uint8Array.of(0, 255), -40);
    expect(d[0]).toBe(-40);
    expect(d[1]).toBeCloseTo(0, 9);
  });
  it('expands a run-length mask, false first, and refuses a mask that does not cover the crop', () => {
    expect([...decodeRle([2, 3, 1], 6)]).toEqual([0, 0, 1, 1, 1, 0]);
    expect([...decodeRle([0, 2], 2)]).toEqual([1, 1]);
    expect(() => decodeRle([2, 3], 6)).toThrow(/covers 5 cells/);
    expect(() => decodeRle([-1], 1)).toThrow(/not a count/);
  });
  it('converts a linear focal map to dB against a reference, floored and capped at 0', () => {
    const d = linearToDb([1, 0.1, 1e-9, 5], 1, -40);
    expect(d[0]).toBeCloseTo(0, 9);
    expect(d[1]).toBeCloseTo(-10, 6);
    expect(d[2]).toBe(-40);
    expect(d[3]).toBe(0);
  });
});

describe('the device display', () => {
  it('quantizes to the nearest of 2^b levels and reports the level', () => {
    expect(levelOf(0, 2)).toBe(0);
    expect(levelOf(Math.PI, 2)).toBe(2);
    expect(levelOf(TWO_PI - 0.01, 2)).toBe(0); // rounds up to level 4, which is level 0
    const q = quantizePhase(Float32Array.of(0.1, 1.7, 3.2), 2);
    expect([...q].map((v) => Math.round(v / (Math.PI / 2)))).toEqual([0, 1, 2]);
  });
  it('the crosstalk weights are symmetric, sum to 1 and spread wider for a larger sigma-of-the-kernel (smaller sigma_per_px)', () => {
    const w = crosstalkWeights(1.24, 1.8, 3, 64);
    const r = (w.length - 1) / 2;
    for (let d = 1; d <= r; d++) expect(w[r + d]).toBeCloseTo(w[r - d], 12);
    expect(w.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 12);
    const wide = crosstalkWeights(0.5, 1.8, 3, 64);
    expect(wide[r]).toBeLessThan(w[r]); // a lower cut-off spreads the pixel more
  });
  it('a blur keeps a constant map and spreads a step', () => {
    const w = crosstalkWeights(0.8, 1.8, 3, 16);
    const flat = new Float32Array(16 * 16).fill(2);
    expect(Math.max(...separableBlur(flat, 16, w).map((v) => Math.abs(v - 2)))).toBeLessThan(1e-5);
    const step = new Float32Array(16 * 16);
    for (let y = 0; y < 16; y++) for (let x = 8; x < 16; x++) step[y * 16 + x] = 1;
    const b = separableBlur(step, 16, w);
    expect(b[8]).toBeGreaterThan(0.05); // the first pixel of the plateau lost light to its neighbour
    expect(b[8]).toBeLessThan(0.99);
  });
  it('stagePhase leaves an ideal device alone, quantizes at the quantized stage and blurs at the crosstalk stage', () => {
    const n = 16;
    const phase = new Float32Array(n * n).map((_, i) => ((i * 0.37) % TWO_PI));
    const device = { bit_depth: 2, crosstalk: { sigma_per_px: 1.24, q: 1.8 }, upsample: 3, fill_factor: 1, flicker_rad: 0, lut_gamma: 1 };
    expect(stagePhase(phase, n, null, 'crosstalk')).toBe(phase);
    expect(stagePhase(phase, n, device, 'ideal')).toBe(phase);
    const q = stagePhase(phase, n, device, 'quantized');
    expect(new Set([...q].map((v) => Math.round(v / (Math.PI / 2)))).size).toBeLessThanOrEqual(4);
    const x = stagePhase(phase, n, device, 'crosstalk');
    expect(x).not.toEqual(q);
    expect(phaseDifference(phase, q).every((v) => Math.abs(v) <= Math.PI / 4 + 1e-6)).toBe(true);
  });
  it('the grating period of a ramp of 2 pi per 8 pixels is 8 pixels; a flat patch has none', () => {
    const n = 16;
    const ramp = new Float32Array(n * n).map((_, i) => (((i % n) * TWO_PI) / 8) % TWO_PI);
    expect(gratingPeriodPx(ramp, n, 3, 2)).toBeCloseTo(8, 5);
    expect(gratingPeriodPx(new Float32Array(n * n), n, 0, 0)).toBe(Infinity);
  });
  it('the closed forms match the sources: sinc^2(1/N) gives 0.405 for N = 2 and 0.684 for N = 3, f^2 for the fill factor', () => {
    expect(quantizationEfficiency(2)).toBeCloseTo(0.405, 3);
    expect(quantizationEfficiency(3)).toBeCloseTo(0.684, 3);
    expect(quantizationEfficiency(16)).toBeCloseTo(0.987, 3);
    expect(fillFactorEfficiency(0.87)).toBeCloseTo(0.757, 3);
    expect(apertureEnvelopeAtEdge(1)).toBeCloseTo(0.405, 2);
  });
});

describe('the colormaps', () => {
  it('are 256 RGB entries; the phase map is cyclic (first and last entries are close) and inferno runs dark to light', () => {
    expect(PHASE_LUT.length).toBe(768);
    expect(INTENSITY_LUT.length).toBe(768);
    const a = lutRgb(PHASE_LUT, 0);
    const b = lutRgb(PHASE_LUT, 1);
    expect(Math.max(...a.map((v, i) => Math.abs(v - b[i])))).toBeLessThan(12);
    const lo = lutRgb(INTENSITY_LUT, 0);
    const hi = lutRgb(INTENSITY_LUT, 1);
    expect(lo[0] + lo[1] + lo[2]).toBeLessThan(20);
    expect(hi[0] + hi[1] + hi[2]).toBeGreaterThan(600);
  });
});

describe('Zernike (port of core/zernike.py)', () => {
  it('orders j = 1..11 as the engine does and names them in both languages', () => {
    expect([2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(nollToNm)).toEqual([[1, 1], [1, -1], [2, 0], [2, -2], [2, 2], [3, -1], [3, 1], [3, -3], [3, 3], [4, 0]]);
    expect(nollToNm(12)[0]).toBe(4);
    expect(zernikeName(4)).toEqual({ en: 'defocus', es: 'desenfoque' });
    expect(zernikeName(15).en).toBe('Z(4,-4)');
    expect(() => nollToNm(0)).toThrow();
    expect(() => nollToNm(22)).toThrow();
  });
  it('is orthonormal over the disc: unit rms for a single mode and zero overlap between modes', () => {
    const n = 128;
    const wave = (j: number) => wavefrontWaves(coeffArray({ [String(j)]: 1 }), n);
    const dot = (a: Float32Array, b: Float32Array) => {
      let s = 0;
      let cnt = 0;
      for (let i = 0; i < a.length; i++) if (!Number.isNaN(a[i])) { s += a[i] * b[i]; cnt++; }
      return s / cnt;
    };
    for (const j of [4, 6, 8, 11]) expect(dot(wave(j), wave(j))).toBeCloseTo(1, 1);
    expect(Math.abs(dot(wave(4), wave(11)))).toBeLessThan(0.05);
    expect(Math.abs(dot(wave(5), wave(6)))).toBeLessThan(0.05);
  });
  it('rms is the root sum of squares without piston and the Strehl is the Marechal exponential (0.8 near 1/14 wave)', () => {
    const c = coeffArray({ '4': 0.03, '6': 0.04 });
    expect(rmsWaves(c)).toBeCloseTo(0.05, 12);
    expect(strehl(c)).toBeCloseTo(Math.exp(-((2 * Math.PI * 0.05) ** 2)), 12);
    expect(strehl(coeffArray({ '4': 1 / 14 }))).toBeGreaterThan(0.79);
    expect(strehl(coeffArray({ '1': 3 }))).toBe(1); // piston does not blur
    expect(zernike(4, 2, 0)).toBe(0); // outside the disc
  });
});
