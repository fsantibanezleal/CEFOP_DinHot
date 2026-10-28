/**
 * Trap-array metrics, one definition each (algorithms D1.0, Di Leonardo et al. 2007 eq (4); Bianchi and Di Leonardo 2010).
 *
 * Python counterpart: `core/metrics.py`. With `I_m = |V_m|^2` (fraction of the input power in the peak of trap m):
 * efficiency `e = sum I_m`; uniformity `u = 1 - (max - min) / (max + min)` (1 is perfect); relative standard deviation
 * `100 std(I) / mean(I)` in percent (population std). With target weights the intensities of `uniformity` and `relStd`
 * are `I_m / w_m`.
 */
import { type Cx } from './fft';
import { trapBins } from './forward';
import { type Setup, nFft } from './geometry';
import type { TrapSet } from './traps';

function vec(i: ArrayLike<number>, name = 'intensities'): void {
  if (i.length === 0) throw new Error(`${name} must be a non-empty 1D array`);
  for (let k = 0; k < i.length; k++) if (!Number.isFinite(i[k])) throw new Error(`${name} contain NaN or infinite values`);
}

/** `I_m = |V_m|^2` from interleaved complex fields, divided by the weights when given. */
export function trapIntensities(v: Cx, weights?: ArrayLike<number>): Float64Array {
  const n = v.length / 2;
  const out = new Float64Array(n);
  for (let i = 0; i < n; i++) out[i] = v[2 * i] ** 2 + v[2 * i + 1] ** 2;
  if (!weights) return out;
  if (weights.length !== n) throw new Error(`weights shape (${weights.length},) differs from the trap count (${n},)`);
  for (let i = 0; i < n; i++) {
    if (!Number.isFinite(weights[i]) || weights[i] <= 0) throw new Error('weights must be finite and positive');
    out[i] /= weights[i];
  }
  return out;
}

export function efficiency(i: ArrayLike<number>): number {
  vec(i);
  let s = 0;
  for (let k = 0; k < i.length; k++) s += i[k];
  return s;
}

function extrema(i: ArrayLike<number>): [number, number] {
  let lo = Infinity, hi = -Infinity;
  for (let k = 0; k < i.length; k++) {
    if (i[k] < lo) lo = i[k];
    if (i[k] > hi) hi = i[k];
  }
  return [lo, hi];
}

export function uniformity(i: ArrayLike<number>): number {
  vec(i);
  const [lo, hi] = extrema(i);
  const s = hi + lo;
  if (s <= 0) throw new Error('uniformity is undefined when all intensities are zero');
  return 1 - (hi - lo) / s;
}

export function relStd(i: ArrayLike<number>): number {
  vec(i);
  let mean = 0;
  for (let k = 0; k < i.length; k++) mean += i[k];
  mean /= i.length;
  if (mean <= 0) throw new Error('relative standard deviation is undefined when the mean intensity is zero');
  let ss = 0;
  for (let k = 0; k < i.length; k++) ss += (i[k] - mean) ** 2;
  return (100 * Math.sqrt(ss / i.length)) / mean;
}

function checkE(e: Cx, setup: Setup): void {
  const m = nFft(setup);
  if (e.length !== 2 * m * m) throw new Error(`focal field must have shape (${m}, ${m})`);
}

/** Peak fraction at the zero order, `|E[0, 0]|^2 pad^2 / N_pix`. */
export function zeroOrderFraction(e: Cx, setup: Setup): number {
  checkE(e, setup);
  const m = nFft(setup), h = Math.floor(m / 2), o = 2 * (h * m + h);
  return (e[o] ** 2 + e[o + 1] ** 2) * (setup.pad ** 2 / setup.nPix ** 2);
}

export interface PowerBudget {
  traps: number;
  zeroOrder: number;
  ghosts: number;
  remainder: number;
}

/** Where the input power goes, as fractions of `N_pix` (integrated power; discs of `radiusBins`, default `pad`). */
export function powerBudget(e: Cx, setup: Setup, traps: TrapSet, radiusBins?: number): PowerBudget {
  checkE(e, setup);
  const r = radiusBins === undefined ? setup.pad : radiusBins;
  if (!(r > 0)) throw new Error('radius_bins must be positive');
  const m = nFft(setup), h = Math.floor(m / 2);
  const { iy, ix } = trapBins(setup, traps);
  const near = new Uint8Array(m * m);
  const rr = r * r, reach = Math.ceil(r);
  for (let t = 0; t < iy.length; t++) {
    for (let y = Math.max(0, iy[t] - reach); y <= Math.min(m - 1, iy[t] + reach); y++) {
      for (let x = Math.max(0, ix[t] - reach); x <= Math.min(m - 1, ix[t] + reach); x++) {
        if ((y - iy[t]) ** 2 + (x - ix[t]) ** 2 <= rr) near[y * m + x] = 1;
      }
    }
  }
  const n2 = setup.nPix ** 2;
  let total = 0, pTrap = 0, pZero = 0;
  for (let y = 0; y < m; y++) {
    for (let x = 0; x < m; x++) {
      const q = y * m + x;
      const p = (e[2 * q] ** 2 + e[2 * q + 1] ** 2) / n2;
      total += p;
      if (near[q]) pTrap += p;
      else if ((y - h) ** 2 + (x - h) ** 2 <= rr) pZero += p;
    }
  }
  return { traps: pTrap, zeroOrder: pZero, ghosts: total - pTrap - pZero, remainder: 1 - total };
}

export const ghostFraction = (e: Cx, setup: Setup, traps: TrapSet, radiusBins: number): number =>
  powerBudget(e, setup, traps, radiusBins).ghosts;
