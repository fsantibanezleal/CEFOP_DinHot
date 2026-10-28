// T12: the TypeScript live engine against the traces the Python engine baked. The trace keeps 200 points of the
// trajectory rounded to two decimals (pipeline/core/trace.py); the TS run, taken at the same points, must match to
// that rounding. This is the one place the two engines meet, so it is where they are held together.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { CaseIndex, CaseManifest, Trace } from '../lib/contract.types';
import { atTimes, finalSize, simulate } from './sir';

const derived = new URL('../../../data/derived/', import.meta.url);
const read = <T>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const index = read<CaseIndex>('manifests/index.json');

describe('the live engine reproduces every baked case', () => {
  for (const entry of index.cases) {
    it(entry.case_id, () => {
      const m = read<CaseManifest>(entry.manifest_path);
      const trace = read<Trace>(m.artifact.path);
      const run = simulate(m.params);
      const at = atTimes(run, trace.t);
      const worst = Math.max(...(['S', 'I', 'R'] as const).flatMap((k) => at[k].map((v, i) => Math.abs(v - trace[k][i]))));
      expect(worst).toBeLessThanOrEqual(0.0051);
      expect(Math.abs(run.peakI - trace.summary.peak_I)).toBeLessThanOrEqual(0.0051);
      expect(Math.abs(run.tPeak - trace.summary.t_peak)).toBeLessThanOrEqual(0.0051);
      expect(Math.abs(run.attackRate - trace.summary.attack_rate)).toBeLessThanOrEqual(0.00005);
    });
  }
});

describe('the final-size relation', () => {
  it('solves z = 1 - exp(-R0 z), and is zero at or below the threshold', () => {
    for (const r0 of [1.2, 2, 2.75, 6]) {
      const z = finalSize(r0);
      expect(Math.abs(z - (1 - Math.exp(-r0 * z)))).toBeLessThan(1e-12);
      expect(z).toBeGreaterThan(0);
    }
    expect(finalSize(0.72)).toBe(0);
    expect(finalSize(1)).toBe(0);
    expect(finalSize(2)).toBeCloseTo(0.796812130, 8);
  });
  it('the engine converges to the final size at first order, as the Methodology page states', () => {
    // A long run (the epidemic ends well inside the horizon) from a vanishing seed; halving the step halves the
    // gap to the final size, the signature of a first-order scheme.
    const gap = (dt: number) => Math.abs(simulate({ beta: 0.5, gamma: 0.2, N: 1e6, I0: 1, days: 1200 }, dt).attackRate - finalSize(2.5));
    const [g1, g2, g3] = [gap(0.25), gap(0.125), gap(0.0625)];
    expect(g2 / g1).toBeGreaterThan(0.4);
    expect(g2 / g1).toBeLessThan(0.6);
    expect(g3 / g2).toBeGreaterThan(0.4);
    expect(g3 / g2).toBeLessThan(0.6);
    expect(g3).toBeLessThan(g1);
  });
});
