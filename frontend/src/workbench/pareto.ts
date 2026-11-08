// V6, the Pareto view: which benchmark cell it opens on, which method it recommends and why, and the seed intervals it draws. Pure functions
// of the benchmark document (`benchmark-results`) and of the case, so the view shows whatever the document holds and a test can plant one.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { nameOf, type Budget, type Device, type Picked } from '../content/benchmark/data';
import type { BenchmarkResults } from '../lib/contract.types';

type Lang = 'en' | 'es';

/** A method is a candidate for the recommendation when its median efficiency is within this fraction of the cell's best (5 percentage points). */
export const EFF_WINDOW = 0.05;

/** The budget the view opens on: 100 iterations, the longest iteration budget of the protocol. */
export const OPENING_BUDGET: Budget = { kind: 'iterations', value: 100 };

/** One colour per series of the view (shell tokens), none repeated: the benchmark's methods, the front, this case's methods and the recommendation are told apart by colour and size. */
export const SERIES_COLORS = {
  published: '--color-accent',
  proposed: '--color-accent-2',
  front: '--color-good',
  case: '--color-warn',
  recommended: '--color-magenta',
  spread: '--color-fg-subtle',
} as const;

export interface Cell {
  geometry: string;
  device: Device;
  budget: Budget;
}

/** A cell as the run state holds it: `geometry|device|kind|value`. */
export const cellKey = (c: Cell): string => `${c.geometry}|${c.device}|${c.budget.kind}|${c.budget.value}`;

/** The cell a key names, or null for a key that does not parse (the view then opens on the case's own cell). */
export function cellFromKey(key: string | null | undefined): Cell | null {
  if (!key) return null;
  const [geometry, device, kind, value] = key.split('|');
  const v = Number(value);
  if (!geometry || (device !== 'ideal' && device !== 'device') || !kind || !Number.isFinite(v)) return null;
  return { geometry, device, budget: { kind: kind as Budget['kind'], value: v } };
}

/**
 * The benchmark geometry of the case's dimensions whose trap count is closest to the case's (the lower id on a tie); null when none has those
 * dimensions. A case with traps is never matched to the geometry of shaped fields (no traps), nor a shaped case to an array of traps.
 */
export function closestGeometry(res: BenchmarkResults, dims: number, nTraps: number) {
  const same = res.geometries.filter((g) => g.dims === dims && (g.n_traps > 0) === (nTraps > 0));
  return same.reduce<(typeof same)[number] | null>((best, g) => (best === null || Math.abs(g.n_traps - nTraps) < Math.abs(best.n_traps - nTraps) ? g : best), null);
}

/** The cell the view opens on for a case: the closest geometry, the case's device kind, 100 iterations, default parameters. */
export function openingCell(res: BenchmarkResults, c: { dims: number; nTraps: number; device: Device }): Cell | null {
  const g = closestGeometry(res, c.dims, c.nTraps);
  return g ? { geometry: g.id, device: c.device, budget: OPENING_BUDGET } : null;
}

const sameBudget = (a: Budget, b: Budget): boolean => a.kind === b.kind && a.value === b.value;

/**
 * The cell itself when the document has default rows for it, else the nearest cell that has some: the same geometry first, then the same
 * device, then the same kind of budget, then the closest budget, then the closest trap count. Null when the document holds no row.
 */
export function cellWithRows(res: BenchmarkResults, want: Cell): Cell | null {
  const cells = new Map<string, Cell>();
  for (const r of res.rows) {
    if (r.params !== 'default') continue;
    cells.set(`${r.geometry}|${r.device}|${r.budget_kind}|${r.budget}`, { geometry: r.geometry, device: r.device as Device, budget: { kind: r.budget_kind, value: r.budget } });
  }
  const list = [...cells.values()];
  const own = list.find((c) => c.geometry === want.geometry && c.device === want.device && sameBudget(c.budget, want.budget));
  if (own) return own;
  const traps = (id: string) => res.geometries.find((g) => g.id === id)?.n_traps ?? 0;
  const score = (c: Cell): number[] => [c.geometry === want.geometry ? 0 : 1, c.device === want.device ? 0 : 1, c.budget.kind === want.budget.kind ? 0 : 1, Math.abs(c.budget.value - want.budget.value), Math.abs(traps(c.geometry) - traps(want.geometry))];
  const cmp = (a: number[], b: number[]) => {
    for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] - b[i];
    return 0;
  };
  return list.sort((a, b) => cmp(score(a), score(b)) || a.geometry.localeCompare(b.geometry))[0] ?? null;
}

export interface Recommendation {
  /** The method recommended: the lowest median spread among those within `EFF_WINDOW` of the best efficiency. */
  pick: Picked;
  /** The method with the best median efficiency of the cell. */
  best: Picked;
  /** The next candidate by spread, or null when the pick is the only one within the window. */
  next: Picked | null;
  /** How far under the best median efficiency the pick sits, in percentage points. */
  pointsUnderBest: number;
}

/** The recommended method of a cell (see EFF_WINDOW), or null when the cell has no rows. Computed from the rows, never typed. */
export function recommend(rows: readonly Picked[]): Recommendation | null {
  if (!rows.length) return null;
  const best = rows.reduce((a, b) => (b.row.efficiency.median > a.row.efficiency.median ? b : a));
  const inside = rows.filter((p) => best.row.efficiency.median - p.row.efficiency.median <= EFF_WINDOW + 1e-12).sort((a, b) => a.row.rel_std_pct.median - b.row.rel_std_pct.median);
  const pick = inside[0];
  return { pick, best, next: inside[1] ?? null, pointsUnderBest: (best.row.efficiency.median - pick.row.efficiency.median) * 100 };
}

/** "Lowest spread, 0.9 %, at 79.0 % efficiency, 3.0 points under the best; next: ..., 1.4 %." with the method names, never ids. */
export function recommendationText(r: Recommendation, lang: Lang): string {
  const f = (v: number) => formatNumber(v, lang, { decimals: 1 });
  // a spread under 1 % is written to two decimals, so that 0.04 % does not read as 0.0 %
  const fs = (v: number) => formatNumber(v, lang, { decimals: v < 0.1 ? 3 : v < 1 ? 2 : 1 });
  const spread = r.pick.row.rel_std_pct.median;
  const eff = r.pick.row.efficiency.median * 100;
  const gap =
    r.pick.method === r.best.method
      ? lang === 'es'
        ? 'la mejor eficiencia de la celda'
        : 'the best efficiency of the cell'
      : lang === 'es'
        ? `${f(r.pointsUnderBest)} puntos bajo la mejor`
        : `${f(r.pointsUnderBest)} points under the best`;
  const next = r.next ? (lang === 'es' ? `; sigue: ${nameOf(r.next.method, lang)}, ${fs(r.next.row.rel_std_pct.median)} %` : `; next: ${nameOf(r.next.method, lang)}, ${fs(r.next.row.rel_std_pct.median)} %`) : '';
  return lang === 'es' ? `Menor dispersión, ${fs(spread)} %, con ${f(eff)} % de eficiencia, ${gap}${next}.` : `Lowest spread, ${fs(spread)} %, at ${f(eff)} % efficiency, ${gap}${next}.`;
}

/**
 * The q1 to q3 interval of every method's point on both axes, as dots of a series on x values of its own: `k` dots along the interval of
 * uniformity at the median efficiency, then `k` along the interval of efficiency at the median uniformity. A method with one seed, or with a
 * zero range on an axis, gets no dots on that axis.
 */
export function intervalDots(rows: readonly Picked[], k = 9): { x: number[]; y: number[] } {
  const x: number[] = [];
  const y: number[] = [];
  const sweep = (lo: number, hi: number, at: (v: number) => void) => {
    for (let i = 0; i < k; i++) at(lo + ((hi - lo) * i) / (k - 1));
  };
  for (const p of rows) {
    if (p.row.n_seeds < 2) continue;
    const u = p.row.uniformity;
    const e = p.row.efficiency;
    if (u.q3 - u.q1 > 1e-12) sweep(u.q1, u.q3, (v) => (x.push(v), y.push(e.median)));
    if (e.q3 - e.q1 > 1e-12) sweep(e.q1, e.q3, (v) => (x.push(u.median), y.push(v)));
  }
  return { x, y };
}
