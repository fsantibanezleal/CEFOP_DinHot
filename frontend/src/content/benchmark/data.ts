// What the Benchmark page computes from the committed documents: the rows of one cell of the protocol, the kind of every method, the
// Pareto and hypervolume arithmetic and the verdict of each proposed-method claim. Pure functions of the benchmark document
// (`data/derived/benchmark/results.json`, catalog row benchmark-results 1.0.0), so a test can plant a document and a page can show
// whatever the document holds: a method, a geometry or a budget that is absent is absent from the page, never typed into it.
import { KIND_NAME, kindOfTier, LADDER, type Kind } from '../methodology/ladder';
import type { BenchmarkResults, BenchmarkRow, Text } from '../../lib/contract.types';

export type Lang = 'en' | 'es';
export type Device = 'ideal' | 'device';
/** `default`: every method with the parameters of its paper; `tuned`: the shared tuning grid, for the methods that declare one. */
export type ParamsView = 'default' | 'tuned';
export type BudgetKind = BenchmarkRow['budget_kind'];
export interface Budget {
  kind: BudgetKind;
  value: number;
}
export type Stat = BenchmarkRow['efficiency'];

export type { Kind };
export const KIND_ORDER: Kind[] = ['published', 'proposed'];
/** What the reader sees for a kind of method, in a table column and a chart key. */
export const KIND_TEXT: Record<Kind, Text> = KIND_NAME;

/** The ladder row of a benchmark method id (M01 to M19, or the engine id B1 to B5 of a proposed method), or undefined off the ladder. */
export function ladderOf(method: string) {
  return LADDER.find((r) => r.engine === method || r.id === method);
}
export const kindOf = (method: string): Kind | null => {
  const row = ladderOf(method);
  return row ? kindOfTier(row.tier) : null;
};
const kindRank = (method: string) => {
  const k = kindOf(method);
  return k === null ? KIND_ORDER.length : KIND_ORDER.indexOf(k);
};
/** The name of a method on the ladder, in a language; the id itself when the ladder does not know it. */
export const nameOf = (method: string, lang: Lang): string => ladderOf(method)?.name[lang] ?? method;
/** The id the reader sees: the engine id of the method (M01 to M19, B1 to B5). */
export function shownId(method: string): string {
  return ladderOf(method)?.engine ?? method;
}
export const orderMethods = (a: string, b: string): number => kindRank(a) - kindRank(b) || a.localeCompare(b, 'en', { numeric: true });

export const budgetId = (b: Budget): string => `${b.kind}:${b.value}`;
export function parseBudget(id: string): Budget {
  const [kind, value] = id.split(':');
  return { kind: kind as BudgetKind, value: Number(value) };
}
const BUDGET_KIND_ORDER: BudgetKind[] = ['iterations', 'time', 'converged'];

/** Every budget the rows carry, iterations then time then converged, each ascending. */
export function budgetsOf(res: BenchmarkResults): Budget[] {
  const seen = new Map<string, Budget>();
  for (const r of res.rows) seen.set(`${r.budget_kind}:${r.budget}`, { kind: r.budget_kind, value: r.budget });
  return [...seen.values()].sort((a, b) => BUDGET_KIND_ORDER.indexOf(a.kind) - BUDGET_KIND_ORDER.indexOf(b.kind) || a.value - b.value);
}

/** The words of a budget: "30 iterations", "50 ms", "1 s", "converged (cap 300 s)". The value is the one the document carries. */
export function budgetText(b: Budget): Text {
  if (b.kind === 'iterations') return { en: `${b.value} iterations`, es: `${b.value} iteraciones` };
  const num = (n: number, lang: Lang) => (lang === 'es' ? String(n).replace('.', ',') : String(n));
  const sec = (lang: Lang) => (b.value < 1 ? `${num(b.value * 1000, lang)} ms` : `${num(b.value, lang)} s`);
  if (b.kind === 'time') return { en: sec('en'), es: sec('es') };
  return { en: `converged (cap ${sec('en')})`, es: `convergido (tope ${sec('es')})` };
}

export const geometryOf = (res: BenchmarkResults, id: string) => res.geometries.find((g) => g.id === id);
export const methodsIn = (res: BenchmarkResults): string[] =>
  [...new Set([...res.rows.map((r) => r.method), ...(res.skipped ?? []).map((s) => s.method)])].sort(orderMethods);

/** One method of one cell, with the row that is shown and what was not. */
export interface Picked {
  method: string;
  kind: Kind | null;
  /** The row shown. */
  row: BenchmarkRow;
  /** The parameters of the row shown. */
  params: 'default' | 'tuned';
  /** The reader asked for the tuned view and this method has no tuned row in this cell: its default row is shown, and labelled so. */
  noTunedRow: boolean;
  /** Whether the method has a tuned row in this cell, whichever is shown. */
  hasTuned: boolean;
}

/**
 * The rows of one cell (geometry, device, budget). `default` shows every method at its paper's parameters. `tuned` shows a method at its
 * tuned row when it has one; a method without one stays at its default row and carries `noTunedRow`, so the page never lets a tuned result
 * stand against an unlabelled default (protocol rule 5). Sorted by kind, then by method.
 */
export function pickRows(res: BenchmarkResults, geometry: string, device: Device, budget: Budget, view: ParamsView): Picked[] {
  const cell = res.rows.filter((r) => r.geometry === geometry && r.device === device && r.budget_kind === budget.kind && r.budget === budget.value);
  const out: Picked[] = [];
  for (const method of [...new Set(cell.map((r) => r.method))].sort(orderMethods)) {
    const def = cell.find((r) => r.method === method && r.params === 'default');
    const tuned = cell.find((r) => r.method === method && r.params === 'tuned');
    const row = view === 'tuned' ? (tuned ?? def) : def;
    if (!row) continue;
    out.push({ method, kind: kindOf(method), row, params: row.params, noTunedRow: view === 'tuned' && !tuned, hasTuned: Boolean(tuned) });
  }
  return out;
}

/** The cells of a geometry the document lists as not run, with the method's reason. */
export const skippedIn = (res: BenchmarkResults, geometry?: string) =>
  (res.skipped ?? []).filter((s) => geometry === undefined || s.geometry === geometry).sort((a, b) => orderMethods(a.method, b.method));

/**
 * The method a cell calls the most uniform: the lowest relative standard deviation among the methods that keep at least half of the best
 * efficiency (the rule the bake's case summary uses, so a method that is uniform by wasting the light does not win).
 */
export function mostUniform(rows: Picked[]): Picked | null {
  if (!rows.length) return null;
  const best = Math.max(...rows.map((p) => p.row.efficiency.median));
  const kept = rows.filter((p) => p.row.efficiency.median >= best / 2);
  return kept.reduce((a, b) => (b.row.rel_std_pct.median < a.row.rel_std_pct.median ? b : a));
}

/** The most uniform method of one kind in a cell, by the rule of `mostUniform` applied inside the kind (efficiency against the kind's own best). */
export const bestOfKind = (rows: Picked[], kind: Kind): Picked | null => mostUniform(rows.filter((p) => p.kind === kind));
/** The strongest published method of a cell: the most uniform row among all the published methods (M01 to M19), the baseline of every proposed method. */
export const bestPublished = (rows: Picked[]): Picked | null => bestOfKind(rows, 'published');

// ---------------------------------------------------------------------------------------------------------------- Pareto arithmetic

export interface Point {
  /** Efficiency and uniformity, both to be maximised. */
  e: number;
  u: number;
}
/** p dominates q when it is at least as good on both and better on one. */
export const dominates = (p: Point, q: Point): boolean => p.e >= q.e && p.u >= q.u && (p.e > q.e || p.u > q.u);
export const nonDominated = (pts: Point[]): Point[] => pts.filter((q) => !pts.some((p) => dominates(p, q)));

/** The area of the union of the rectangles [0, e] x [0, u] over the points: the hypervolume against the reference point (0, 0). */
export function hypervolume(pts: Point[]): number {
  const s = nonDominated(pts).sort((a, b) => a.e - b.e);
  let area = 0;
  let prev = 0;
  for (let i = 0; i < s.length; i++) {
    const top = Math.max(...s.slice(i).map((p) => p.u));
    area += (s[i].e - prev) * top;
    prev = s[i].e;
  }
  return area;
}

/** The front of B5 for a geometry, as points, ordered by lambda; empty when the document has none. */
export function frontOf(res: BenchmarkResults, geometry: string): { lambda: number; e: number; u: number }[] {
  const f = res.pareto.find((p) => p.geometry === geometry && p.method === 'B5');
  return (f?.points ?? []).map((p) => ({ lambda: p.lambda, e: p.efficiency, u: p.uniformity })).sort((a, b) => a.lambda - b.lambda);
}

// ---------------------------------------------------------------------------------------------------------------- claims

/** One geometry and budget at which a challenger and its baseline both have a default row on the same device. */
export interface RatioCell {
  geometry: string;
  budget: Budget;
  /** Baseline relative standard deviation over the challenger's: above 1 means the challenger is more uniform. */
  sigmaFactor: number;
  /** Challenger efficiency over the baseline's. */
  effRatio: number;
  /** The seeds behind both medians (the smaller of the two). */
  seeds: number;
}

/**
 * The challenger against the baseline on one device, at every geometry and budget that both have, default parameters on both sides
 * (a tuned row is never set against a default one). A median of a relative standard deviation that is 0 gives no factor and the cell is left out.
 */
export function ratioCells(res: BenchmarkResults, challenger: string, baseline: string, device: Device): RatioCell[] {
  const out: RatioCell[] = [];
  for (const g of res.geometries) {
    for (const b of budgetsOf(res)) {
      const find = (m: string) => res.rows.find((r) => r.method === m && r.geometry === g.id && r.device === device && r.budget_kind === b.kind && r.budget === b.value && r.params === 'default');
      const c = find(challenger);
      const base = find(baseline);
      if (!c || !base || !(c.rel_std_pct.median > 0) || !(base.efficiency.median > 0)) continue;
      out.push({ geometry: g.id, budget: b, sigmaFactor: base.rel_std_pct.median / c.rel_std_pct.median, effRatio: c.efficiency.median / base.efficiency.median, seeds: Math.min(c.n_seeds, base.n_seeds) });
    }
  }
  return out;
}

export const median = (xs: number[]): number | null => {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

export type Verdict = 'supported' | 'partly' | 'not-supported' | 'no-data';

/** The share of the cells that meet a test decides the verdict: all, some or none; no cells is no data, never a pass. */
export function verdictOf(cells: boolean[]): Verdict {
  if (!cells.length) return 'no-data';
  const ok = cells.filter(Boolean).length;
  return ok === cells.length ? 'supported' : ok === 0 ? 'not-supported' : 'partly';
}

/** The criteria of the SDD ladder rows, as numbers the page tests the measurement against (the test `data.test.ts` keeps them equal to the SDD). */
export const CRITERIA = {
  /** B1: the relative standard deviation at least this many times below M07 on the crosstalk device, efficiency at most this share lower. */
  b1: { sigmaFactor: 2, effRatio: 0.9 },
  /** B3: the median iterations to 1 percent at least this many times below the random start. */
  b3: { iterationFactor: 2 },
  /** B4: the 95th percentile of the relative standard deviation over the aberration ensemble at least this many times below M07, efficiency at most this share lower. */
  b4: { sigmaFactor: 1.25, effRatio: 0.9 },
} as const;

/** The strongest baseline of a proposed method in this benchmark's matrix, by the SDD row that names it (M07 for B1 and B4). */
export const BASELINE_OF: Record<string, string> = { B1: 'M07', B4: 'M07' };

/** The hypervolume test of B5 in one geometry: the front against the union of the published points of the SDD criterion, at one cell. */
export const B5_PUBLISHED = ['M04', 'M05', 'M09', 'M06'] as const;
export interface B5Cell {
  geometry: string;
  hvFront: number;
  hvPublished: number;
  /** The published methods of the criterion whose point is dominated by some front point. */
  dominated: string[];
  /** The methods of the criterion with no row in this cell. */
  missing: string[];
  nFront: number;
}
export function b5Cells(res: BenchmarkResults, budget: Budget, device: Device = 'ideal'): B5Cell[] {
  const out: B5Cell[] = [];
  for (const g of res.geometries) {
    const front = frontOf(res, g.id);
    if (!front.length) continue;
    const rows = pickRows(res, g.id, device, budget, 'default').filter((p) => (B5_PUBLISHED as readonly string[]).includes(p.method));
    const pts = rows.map((p) => ({ m: p.method, e: p.row.efficiency.median, u: p.row.uniformity.median }));
    const fp = front.map((p) => ({ e: p.e, u: p.u }));
    out.push({
      geometry: g.id,
      hvFront: hypervolume(fp),
      hvPublished: hypervolume(pts),
      dominated: pts.filter((q) => fp.some((p) => dominates(p, q))).map((q) => q.m),
      missing: B5_PUBLISHED.filter((m) => !pts.some((q) => q.m === m)),
      nFront: front.length,
    });
  }
  return out;
}
