// The arithmetic of the Benchmark page and the guards that keep it honest: the recorded acceptance numbers and the thresholds equal the SDD, no
// DinHot figure is typed into a page file, every method of the committed results document is on the ladder, and the selectors, the Pareto
// arithmetic and the verdicts behave on planted documents (a tuned row is never taken for a default one; a cell with no data is never a pass).
import { readFileSync, readdirSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { BenchmarkResults } from '../../lib/contract.types';
import {
  bs5Cells,
  budgetsOf,
  budgetText,
  CRITERIA,
  dominates,
  frontOf,
  hypervolume,
  ladderOf,
  median,
  mostUniform,
  nonDominated,
  orderMethods,
  pickRows,
  ratioCells,
  skippedIn,
  tierOf,
  verdictOf,
} from './data';
import { RECORDED } from './recorded';

const root = new URL('../../../../', import.meta.url);
const sdd = readFileSync(new URL('docs/design/SDD.md', root), 'utf8');
const committed = JSON.parse(readFileSync(new URL('data/derived/benchmark/results.json', root), 'utf8')) as BenchmarkResults;
const fixture = JSON.parse(readFileSync(new URL('docs/contracts/fixtures/data/derived/benchmark/results.json', root), 'utf8')) as BenchmarkResults;

/** The text of one row of the SDD method-ladder table. */
function sddRow(id: string): string {
  const start = sdd.indexOf('## Method ladder');
  const end = sdd.indexOf('\n## ', start + 5);
  const line = sdd
    .slice(start, end)
    .split('\n')
    .find((l) => l.startsWith(`| ${id} |`));
  if (!line) throw new Error(`the SDD ladder has no row ${id}`);
  return line;
}
/** The text of the "Beyond the state of the art" bullet of one row. */
function sddBeyond(id: string): string {
  const start = sdd.indexOf('## Beyond the state of the art');
  const end = sdd.indexOf('\n## ', start + 5);
  const text = sdd.slice(start, end);
  const at = text.indexOf(`- ${id} `);
  if (at < 0) throw new Error(`no bullet for ${id}`);
  const next = text.indexOf('\n- BS-', at + 5);
  return text.slice(at, next < 0 ? undefined : next);
}
const WORDS: Record<number, string> = { 3: 'three', 5: 'five' };

function plant(rows: Partial<BenchmarkResults['rows'][number]>[], extra: Partial<BenchmarkResults> = {}): BenchmarkResults {
  const stat = (m: number) => ({ median: m, q1: m * 0.9, q3: m * 1.1 });
  return {
    schema: 'dinhot.benchmark/v1',
    engine_version: '0.02.000',
    protocol: { grids: [64], seeds: 2, budgets: { iterations: [30], time_s: [1] }, device: { en: 'd', es: 'd' } },
    geometries: [
      { id: 'G1', name: { en: 'one', es: 'uno' }, n_traps: 4, dims: 2 },
      { id: 'G2', name: { en: 'two', es: 'dos' }, n_traps: 4, dims: 2 },
    ],
    rows: rows.map((r) => ({
      method: 'M04', geometry: 'G1', device: 'ideal', budget_kind: 'iterations', budget: 30, params: 'default', n_seeds: 2,
      efficiency: stat(0.8), uniformity: stat(0.5), rel_std_pct: stat(10), time_s: stat(0.1), iterations: stat(30),
      ...r,
    })) as BenchmarkResults['rows'],
    pareto: [],
    skipped: [],
    ...extra,
  } as BenchmarkResults;
}

describe('the recorded acceptance numbers equal the SDD', () => {
  for (const [id, rec] of Object.entries(RECORDED)) {
    it(`${id}: every recorded number is in its ladder row`, () => {
      const row = sddRow(rec.row);
      for (const [key, value] of Object.entries(rec.numbers)) {
        if (key === 'c10LpiLeadsAtEqualFrames') {
          expect(row, key).toMatch(/LPI leads in every seed/);
          expect(value).toBe(1);
          continue;
        }
        const written = String(value);
        // a decimal the SDD writes with trailing zeros (0.910) is the same number as its shortest form (0.91)
        const zeros = written.includes('.') ? '0*' : '';
        const ok = new RegExp(`(^|[^0-9.])${written.replace('.', '\\.')}${zeros}([^0-9]|\\.(?![0-9])|$)`).test(row) || (WORDS[value] !== undefined && row.includes(WORDS[value]));
        expect(ok, `${id}.${key} = ${written} is not in the SDD row ${rec.row}`).toBe(true);
      }
    });
  }

  it('the criteria equal the thresholds the SDD rows state', () => {
    expect(sddRow('BS-1')).toMatch(/at least two times below M07/);
    expect(CRITERIA.bs1.sigmaFactor).toBe(2);
    expect(sddRow('BS-1')).toMatch(/efficiency at most 10 percent lower/);
    expect(CRITERIA.bs1.effRatio).toBeCloseTo(0.9, 12);
    expect(sddRow('BS-4')).toMatch(/at least 1\.25 times below M07/);
    expect(CRITERIA.bs4.sigmaFactor).toBe(1.25);
    expect(sddRow('BS-4')).toMatch(/efficiency at most 10 percent lower/);
    expect(sddBeyond('BS-3') + sddRow('BS-3')).toMatch(/below the 2 times claimed/);
    expect(CRITERIA.bs3.iterationFactor).toBe(2);
    expect(sddRow('BS-2')).toMatch(/at least 0\.9 of its mean/);
    expect(sddRow('BS-5')).toMatch(/M04, M05, M09 and M06/);
  });
});

describe('no DinHot figure is typed into a page file', () => {
  const dir = new URL('./', import.meta.url);
  const files = readdirSync(dir).filter((f) => /\.tsx?$/.test(f) && !/\.test\.|^recorded\.ts$|^data\.ts$/.test(f));
  const pageFile = new URL('../../pages/Benchmark.tsx', import.meta.url);
  for (const f of [...files.map((x) => new URL(x, dir)), pageFile]) {
    it(`${f.pathname.split('/').pop()} writes no measured decimal`, () => {
      const code = readFileSync(f, 'utf8')
        .split('\n')
        .filter((l) => !/^\s*\/\//.test(l))
        .join('\n');
      // a decimal with two or more places is a measurement; the floors of the log axes and the thresholds live in data.ts as named constants
      const found = [...code.matchAll(/(?<![\w.])\d+\.\d{2,}(?![\w])/g)].map((m) => m[0]);
      expect(found, `${f.pathname} holds a typed decimal`).toEqual([]);
    });
  }
});

describe('the committed results document', () => {
  it('names only methods that are on the ladder, and geometries it declares', () => {
    const ids = new Set(committed.geometries.map((g) => g.id));
    for (const r of committed.rows) {
      expect(ladderOf(r.method), r.method).toBeDefined();
      expect(ids.has(r.geometry), r.geometry).toBe(true);
    }
    for (const s of committed.skipped ?? []) expect(ladderOf(s.method), s.method).toBeDefined();
  });
  it('the fixture of the contract is read by the same selectors', () => {
    expect(budgetsOf(fixture).length).toBeGreaterThan(0);
    expect(frontOf(fixture, 'G1').length).toBeGreaterThan(1);
    expect(skippedIn(fixture).length).toBe((fixture.skipped ?? []).length);
  });
});

describe('the tier and the order of a method', () => {
  it('reads the tier from the ladder and the engine id of a beyond method', () => {
    expect(tierOf('M01')).toBe('classical');
    expect(tierOf('M07')).toBe('sota');
    expect(tierOf('B1')).toBe('beyond');
    expect(tierOf('BS-1')).toBe('beyond');
    expect(tierOf('M99')).toBeNull();
  });
  it('orders classical, state of the art, beyond, then by number', () => {
    expect(['B1', 'M10', 'M07', 'M02', 'M01'].sort(orderMethods)).toEqual(['M01', 'M02', 'M07', 'M10', 'B1']);
  });
});

describe('pickRows keeps a tuned row apart from a default one', () => {
  const res = plant([
    { method: 'M05', params: 'default', rel_std_pct: { median: 8, q1: 7, q3: 9 } },
    { method: 'M05', params: 'tuned', rel_std_pct: { median: 2, q1: 1, q3: 3 } },
    { method: 'M04', params: 'default', rel_std_pct: { median: 9, q1: 8, q3: 10 } },
  ]);
  const b = { kind: 'iterations' as const, value: 30 };
  it('the default view takes the default row of every method', () => {
    const rows = pickRows(res, 'G1', 'ideal', b, 'default');
    expect(rows.map((p) => [p.method, p.params, p.noTunedRow])).toEqual([['M04', 'default', false], ['M05', 'default', false]]);
  });
  it('the tuned view takes a tuned row where there is one and labels a default row that stands beside it', () => {
    const rows = pickRows(res, 'G1', 'ideal', b, 'tuned');
    expect(rows.map((p) => [p.method, p.params, p.noTunedRow])).toEqual([['M04', 'default', true], ['M05', 'tuned', false]]);
  });
  it('a cell with no rows gives no rows, and another device is another cell', () => {
    expect(pickRows(res, 'G2', 'ideal', b, 'default')).toEqual([]);
    expect(pickRows(res, 'G1', 'device', b, 'default')).toEqual([]);
  });
  it('mostUniform ignores a method that is uniform by wasting the light', () => {
    const r = plant([
      { method: 'M04', efficiency: { median: 0.9, q1: 0.9, q3: 0.9 }, rel_std_pct: { median: 5, q1: 5, q3: 5 } },
      { method: 'M06', efficiency: { median: 0.2, q1: 0.2, q3: 0.2 }, rel_std_pct: { median: 0.1, q1: 0.1, q3: 0.1 } },
    ]);
    expect(mostUniform(pickRows(r, 'G1', 'ideal', b, 'default'))?.method).toBe('M04');
    expect(mostUniform([])).toBeNull();
  });
});

describe('ratio cells and verdicts', () => {
  const res = plant([
    { method: 'M07', device: 'device', rel_std_pct: { median: 12, q1: 11, q3: 13 }, efficiency: { median: 0.8, q1: 0.8, q3: 0.8 } },
    { method: 'B1', device: 'device', rel_std_pct: { median: 3, q1: 2, q3: 4 }, efficiency: { median: 0.76, q1: 0.76, q3: 0.76 } },
    { method: 'M07', device: 'device', geometry: 'G2', rel_std_pct: { median: 6, q1: 6, q3: 6 }, efficiency: { median: 0.8, q1: 0.8, q3: 0.8 } },
    { method: 'B1', device: 'device', geometry: 'G2', rel_std_pct: { median: 5, q1: 5, q3: 5 }, efficiency: { median: 0.5, q1: 0.5, q3: 0.5 } },
    // a tuned baseline row is never the baseline of a default challenger
    { method: 'M07', device: 'device', geometry: 'G2', params: 'tuned', rel_std_pct: { median: 0.1, q1: 0.1, q3: 0.1 } },
  ]);
  it('divides the baseline by the challenger and compares default with default only', () => {
    const cells = ratioCells(res, 'B1', 'M07', 'device');
    expect(cells.map((c) => [c.geometry, c.sigmaFactor, Number(c.effRatio.toFixed(2))])).toEqual([['G1', 4, 0.95], ['G2', 1.2, 0.63]]);
  });
  it('a pair with a missing side is left out, never a pass', () => {
    expect(ratioCells(res, 'B4', 'M07', 'device')).toEqual([]);
    expect(verdictOf([])).toBe('no-data');
  });
  it('the verdict is all, some or none of the cells', () => {
    const t = CRITERIA.bs1;
    const ok = (c: { sigmaFactor: number; effRatio: number }) => c.sigmaFactor >= t.sigmaFactor && c.effRatio >= t.effRatio;
    const cells = ratioCells(res, 'B1', 'M07', 'device');
    expect(verdictOf(cells.map(ok))).toBe('partly');
    expect(verdictOf([true, true])).toBe('supported');
    expect(verdictOf([false, false])).toBe('not-supported');
  });
  it('median of an even and an odd list', () => {
    expect(median([3, 1, 2])).toBe(2);
    expect(median([4, 1, 2, 3])).toBe(2.5);
    expect(median([])).toBeNull();
  });
});

describe('the Pareto arithmetic', () => {
  it('dominance needs one strict improvement', () => {
    expect(dominates({ e: 0.9, u: 0.9 }, { e: 0.8, u: 0.9 })).toBe(true);
    expect(dominates({ e: 0.9, u: 0.9 }, { e: 0.9, u: 0.9 })).toBe(false);
    expect(nonDominated([{ e: 0.9, u: 0.1 }, { e: 0.1, u: 0.9 }, { e: 0.05, u: 0.05 }])).toHaveLength(2);
  });
  it('the hypervolume of two points is the area of the union of their rectangles', () => {
    // (1, 0.5) and (0.5, 1): 1 x 0.5 + 0.5 x 0.5 = 0.75
    expect(hypervolume([{ e: 1, u: 0.5 }, { e: 0.5, u: 1 }])).toBeCloseTo(0.75, 12);
    expect(hypervolume([{ e: 0.4, u: 0.5 }])).toBeCloseTo(0.2, 12);
    expect(hypervolume([])).toBe(0);
    // a dominated point adds nothing
    expect(hypervolume([{ e: 1, u: 1 }, { e: 0.5, u: 0.5 }])).toBeCloseTo(1, 12);
  });
  it('bs5Cells compares the front with the four classical points and lists the missing ones', () => {
    const res = plant(
      [
        { method: 'M04', efficiency: { median: 0.8, q1: 0, q3: 1 }, uniformity: { median: 0.5, q1: 0, q3: 1 } },
        { method: 'M06', efficiency: { median: 0.7, q1: 0, q3: 1 }, uniformity: { median: 0.9, q1: 0, q3: 1 } },
      ],
      { pareto: [{ geometry: 'G1', method: 'B5', points: [{ lambda: 0, efficiency: 0.85, uniformity: 0.95 }, { lambda: 1, efficiency: 0.9, uniformity: 0.6 }] }] },
    );
    const cells = bs5Cells(res, { kind: 'iterations', value: 30 });
    expect(cells).toHaveLength(1);
    expect(cells[0].hvFront).toBeGreaterThan(cells[0].hvClassical);
    expect(cells[0].dominated.sort()).toEqual(['M04', 'M06']);
    expect(cells[0].missing.sort()).toEqual(['M05', 'M09']);
  });
});

describe('the words of a budget', () => {
  it('iterations, milliseconds, seconds and the converged cap, in both languages', () => {
    expect(budgetText({ kind: 'iterations', value: 30 })).toEqual({ en: '30 iterations', es: '30 iteraciones' });
    expect(budgetText({ kind: 'time', value: 0.05 }).en).toBe('50 ms');
    expect(budgetText({ kind: 'time', value: 1 }).es).toBe('1 s');
    expect(budgetText({ kind: 'converged', value: 60 })).toEqual({ en: 'converged (cap 60 s)', es: 'convergido (tope 60 s)' });
  });
});
