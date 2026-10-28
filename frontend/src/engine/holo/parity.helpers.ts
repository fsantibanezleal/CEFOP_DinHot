// Shared by the parity tests: reads the reference documents the Python engine wrote (tests/fixtures/engine/*.json, catalog row
// engine-reference) and compares with a stated tolerance. The reference always comes from the file; nothing here (or in the
// tests) computes an expected value with the TypeScript engine.
import { appendFileSync, existsSync, readFileSync } from 'node:fs';
import { expect } from 'vitest';
import { TrapSet } from './traps';
import { type Setup, TWO_PI, makeSetup } from './geometry';
import { type Device, makeDevice } from './device';

const DIR = new URL('../../../../tests/fixtures/engine/', import.meta.url);

export interface RefArray {
  shape: number[];
  complex: boolean;
  data?: number[];
  b64?: string;
}

export interface RefCase {
  inputs: Record<string, any>;
  outputs: Record<string, any>;
}

export interface RefDoc {
  schema: string;
  engine_version: string;
  function: string;
  tolerance: { abs: number; rel: number };
  cases: RefCase[];
}

/** Load one reference document; a missing file fails the test naming the file (the catalog's missing-data rule). */
export function load(fn: string): RefDoc {
  const url = new URL(`${fn}.json`, DIR);
  if (!existsSync(url)) throw new Error(`engine reference missing: tests/fixtures/engine/${fn}.json (run python -m pipeline.stages.engine_reference)`);
  const doc = JSON.parse(readFileSync(url, 'utf8')) as RefDoc;
  expect(doc.schema).toBe('dinhot.engine-ref/v1');
  expect(doc.function).toBe(fn);
  return doc;
}

/** Decode a reference array (inline numbers or base64 little-endian float64) to a flat Float64Array. */
export function dec(a: RefArray): Float64Array {
  if (a.data) return Float64Array.from(a.data);
  const buf = Buffer.from(a.b64 as string, 'base64');
  const out = new Float64Array(buf.byteLength / 8);
  for (let i = 0; i < out.length; i++) out[i] = buf.readDoubleLE(8 * i);
  return out;
}

const REPORT = process.env.PARITY_REPORT;

/** Worst difference of a comparison, recorded to `PARITY_REPORT` (one JSON line per comparison) when set. */
function record(what: string, maxAbs: number, maxRel: number, tol: { abs: number; rel: number }): void {
  if (REPORT) appendFileSync(REPORT, `${JSON.stringify({ what, maxAbs, maxRel, tol })}\n`);
}

/** `|a - r| <= abs + rel |r|` elementwise; returns the largest absolute difference. */
export function close(actual: ArrayLike<number>, ref: ArrayLike<number>, tol: { abs: number; rel: number }, what: string): number {
  expect(actual.length, `${what}: length`).toBe(ref.length);
  let maxAbs = 0, maxRel = 0, worst = -1;
  for (let i = 0; i < ref.length; i++) {
    const d = Math.abs(actual[i] - ref[i]);
    if (!(d <= tol.abs + tol.rel * Math.abs(ref[i]))) {
      throw new Error(`${what}[${i}]: actual ${actual[i]} vs reference ${ref[i]} (diff ${d}, tolerance abs ${tol.abs} rel ${tol.rel})`);
    }
    if (d > maxAbs) { maxAbs = d; worst = i; }
    if (ref[i] !== 0) maxRel = Math.max(maxRel, d / Math.abs(ref[i]));
  }
  void worst;
  record(what, maxAbs, maxRel, tol);
  return maxAbs;
}

/** Phase comparison modulo 2 pi (a phase of 0 and of 2 pi - 1e-12 are the same hologram). */
export function phaseClose(actual: ArrayLike<number>, ref: ArrayLike<number>, tolAbs: number, what: string): number {
  expect(actual.length, `${what}: length`).toBe(ref.length);
  let maxAbs = 0;
  for (let i = 0; i < ref.length; i++) {
    let d = Math.abs(actual[i] - ref[i]) % TWO_PI;
    d = Math.min(d, TWO_PI - d);
    if (!(d <= tolAbs)) throw new Error(`${what}[${i}]: actual ${actual[i]} vs reference ${ref[i]} (circular diff ${d}, tolerance ${tolAbs})`);
    maxAbs = Math.max(maxAbs, d);
  }
  record(`${what} (circular)`, maxAbs, 0, { abs: tolAbs, rel: 0 });
  return maxAbs;
}

export const setupFrom = (s: any): Setup =>
  makeSetup({ wavelengthM: s.wavelength_m, focalM: s.focal_m, na: s.na, nImm: s.n_imm, nPix: s.n_pix, pitchM: s.pitch_m, pad: s.pad, beam: s.beam, waistFrac: s.waist_frac });

export const trapsFrom = (t: any): TrapSet =>
  new TrapSet(t.ids.map((id: number, i: number) => ({ id, xM: t.x_m[i], yM: t.y_m[i], zM: t.z_m[i], weight: t.weight[i], charge: t.charge[i] })));

export const deviceFrom = (d: any): Device | null =>
  d === null ? null : makeDevice({ bitDepth: d.bit_depth, crosstalk: d.crosstalk, upsample: d.upsample, fillFactor: d.fill_factor, flickerRad: d.flicker_rad, lutGamma: d.lut_gamma });

/** Exact equality of integer streams. */
export const same = (actual: ArrayLike<number>, ref: ArrayLike<number>, what: string): void => {
  expect(Array.from(actual), what).toEqual(Array.from(ref));
};
