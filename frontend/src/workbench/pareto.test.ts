// V6, the Pareto view: the cell it opens on, the method it recommends and why, the nearest cell that has rows, and the seed intervals it draws.
// Every number is read from a planted benchmark document; nothing is typed.
import { describe, expect, it } from 'vitest';
import type { BenchmarkResults, BenchmarkRow } from '../lib/contract.types';
import { pickRows } from '../content/benchmark/data';
import { SERIES_COLORS, cellWithRows, closestGeometry, EFF_WINDOW, intervalDots, openingCell, recommend, recommendationText } from './pareto';

const stat = (m: number, spread = 0.01) => ({ median: m, q1: m - spread, q3: m + spread });
const row = (method: string, geometry: string, eff: number, std: number, over: Partial<BenchmarkRow> = {}): BenchmarkRow =>
  ({
    method,
    geometry,
    device: 'ideal',
    budget_kind: 'iterations',
    budget: 100,
    params: 'default',
    n_seeds: 3,
    efficiency: stat(eff),
    uniformity: stat(1 - std / 100),
    rel_std_pct: stat(std, 0.2),
    time_s: stat(1),
    iterations: stat(100),
    ...over,
  }) as BenchmarkRow;

const doc = (rows: BenchmarkRow[]): BenchmarkResults =>
  ({
    schema: 'dinhot.benchmark/v1',
    engine_version: 'test',
    protocol: {},
    geometries: [
      { id: 'G1', name: { en: 'Square 10 x 10', es: 'Cuadrada 10 x 10' }, n_traps: 100, dims: 2 },
      { id: 'G2', name: { en: 'Ring of 36 traps', es: 'Anillo de 36 trampas' }, n_traps: 36, dims: 2 },
      { id: 'G5', name: { en: '3D lattice 5 x 5 x 3', es: 'Red 3D 5 x 5 x 3' }, n_traps: 75, dims: 3 },
      { id: 'G7', name: { en: 'Shaped fields', es: 'Campos con forma' }, n_traps: 0, dims: 2 },
    ],
    rows,
    pareto: [],
    skipped: [],
  }) as unknown as BenchmarkResults;

describe('the cell the view opens on', () => {
  const res = doc([row('M07', 'G1', 0.8, 5)]);
  it('is the geometry of the case dimensions with the trap count closest to the case, at 100 iterations', () => {
    expect(closestGeometry(res, 2, 9)?.id).toBe('G2');
    expect(closestGeometry(res, 2, 90)?.id).toBe('G1');
    expect(closestGeometry(res, 3, 27)?.id).toBe('G5');
    expect(closestGeometry(res, 2, 0)?.id).toBe('G7');
  });
  it('takes the device the case models: its own, else the ideal SLM', () => {
    expect(openingCell(res, { dims: 2, nTraps: 100, device: 'device' })).toEqual({ geometry: 'G1', device: 'device', budget: { kind: 'iterations', value: 100 } });
    expect(openingCell(res, { dims: 2, nTraps: 100, device: 'ideal' })?.device).toBe('ideal');
  });
  it('is null when the document holds no geometry of those dimensions', () => {
    expect(openingCell({ ...res, geometries: [] }, { dims: 2, nTraps: 9, device: 'ideal' })).toBeNull();
  });
});

describe('the recommended method', () => {
  const cell = [row('M06', 'G1', 0.82, 6), row('M07', 'G1', 0.8, 1.4), row('M09', 'G1', 0.79, 0.9), row('M04', 'G1', 0.7, 0.1), row('M01', 'G1', 0.5, 30)];
  const picked = pickRows(doc(cell), 'G1', 'ideal', { kind: 'iterations', value: 100 }, 'default');
  it('has the lowest median spread among the methods within five points of the best efficiency', () => {
    const rec = recommend(picked)!;
    expect(EFF_WINDOW).toBe(0.05);
    // M04 is the most uniform of all but 12 points under the best: it does not qualify; M09 is 3 points under it
    expect(rec.pick.method).toBe('M09');
    expect(rec.best.method).toBe('M06');
    expect(rec.next?.method).toBe('M07');
    expect(rec.pointsUnderBest).toBeCloseTo(3, 6);
  });
  it('states both numbers and names the runner-up, in both languages', () => {
    const rec = recommend(picked)!;
    const en = recommendationText(rec, 'en');
    expect(en).toMatch(/0\.90 %/);
    expect(en).toMatch(/79\.0 % efficiency/);
    expect(en).toMatch(/3\.0 points under the best/);
    expect(en).toMatch(/next: .*1\.4 %/);
    expect(recommendationText(rec, 'es')).toMatch(/0,90 %/);
    expect(en).not.toMatch(/\bM\d{2}\b|\bB\d\b/);
  });
  it('says so when the recommended method is the best one', () => {
    const rec = recommend(picked.filter((p) => p.method !== 'M09' && p.method !== 'M07' && p.method !== 'M04'))!;
    expect(rec.pick.method).toBe('M06');
    expect(recommendationText(rec, 'en')).toMatch(/the best efficiency of the cell/);
  });
  it('is null for a cell without rows, never a method typed in', () => {
    expect(recommend([])).toBeNull();
  });
});

describe('a cell without rows', () => {
  const res = doc([row('M07', 'G1', 0.8, 2, { device: 'device', budget: 30 }), row('M06', 'G2', 0.7, 3)]);
  it('offers the nearest cell that has rows: the same geometry first, then the same device, then the budget', () => {
    expect(cellWithRows(res, { geometry: 'G1', device: 'ideal', budget: { kind: 'iterations', value: 100 } })).toEqual({ geometry: 'G1', device: 'device', budget: { kind: 'iterations', value: 30 } });
  });
  it('returns the cell itself when it has rows', () => {
    const c = { geometry: 'G2', device: 'ideal' as const, budget: { kind: 'iterations' as const, value: 100 } };
    expect(cellWithRows(res, c)).toEqual(c);
  });
  it('is null when the document holds no row at all', () => {
    expect(cellWithRows(doc([]), { geometry: 'G1', device: 'ideal', budget: { kind: 'iterations', value: 100 } })).toBeNull();
  });
});

describe('the seed interval of each method', () => {
  it('draws the q1 to q3 range on both axes, at the median of the other', () => {
    const picked = pickRows(doc([row('M07', 'G1', 0.8, 2)]), 'G1', 'ideal', { kind: 'iterations', value: 100 }, 'default');
    const d = intervalDots(picked, 5);
    // 5 dots across uniformity at the median efficiency, 5 up efficiency at the median uniformity
    expect(d.x.length).toBe(10);
    expect(d.y.length).toBe(10);
    expect(Math.min(...d.x.slice(0, 5))).toBeCloseTo(0.98 - 0.01, 6);
    expect(Math.max(...d.x.slice(0, 5))).toBeCloseTo(0.98 + 0.01, 6);
    expect(d.y.slice(0, 5).every((v) => v === 0.8)).toBe(true);
    expect(Math.min(...d.y.slice(5))).toBeCloseTo(0.79, 6);
    expect(Math.max(...d.y.slice(5))).toBeCloseTo(0.81, 6);
  });
  it('draws nothing for a method with a single seed or a zero range', () => {
    const one = pickRows(doc([row('M07', 'G1', 0.8, 2, { n_seeds: 1, efficiency: { median: 0.8, q1: 0.8, q3: 0.8 }, uniformity: { median: 0.98, q1: 0.98, q3: 0.98 } })]), 'G1', 'ideal', { kind: 'iterations', value: 100 }, 'default');
    expect(intervalDots(one, 5)).toEqual({ x: [], y: [] });
  });
});

describe('the series of the chart', () => {
  it('each take a colour of their own', () => {
    const colours = Object.values(SERIES_COLORS);
    expect(new Set(colours).size).toBe(colours.length);
  });
});
