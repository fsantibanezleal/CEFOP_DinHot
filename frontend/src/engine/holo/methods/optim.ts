/**
 * Optimization methods M10 (conjugate gradient, Harte et al. 2014) and M11 (Wirtinger gradient with Adam, Chakravarthula
 * et al. 2019), with their shared machinery: forward models with exact adjoints, cost functions and optimizers.
 *
 * Python counterparts: `methods/optim/_common.py`, `m10_cg.py`, `m11_wirtinger_adam.py` (conventions, closed-form
 * gradients and sources are documented there). For a real loss `L` of a complex array `Z`, `G = dL/dZ*`; for an intensity
 * loss `G = L'(I) Z`; if `Z = Op(phi)` is linear in the SLM field `f_j = A_j exp(i phi_j)` then
 * `dL/dphi_j = 2 Re(i f_j conj((Op^H G)_j))`. The device's displayed phase is applied in the forward pass and treated as the
 * identity in the backward pass (straight-through); flicker is dropped. Keywords (camelCase) in `ctx.options`: M10 `t`
 * (number or array of stages), `efficiency`; M11 `lr`, `efficiency`. M10 ignores the device (its model is the ideal one).
 */
import { type Device, crosstalk, crosstalkAdjoint, displayedPhase, swapFactor, upsampledWindow, windowIndex, sinc1d } from '../device';
import { type Cx, plan } from '../fft';
import { fftFocalField, fftInverse, pointTrapBackproject, pointTrapProjection, slmField, trapBins } from '../forward';
import { type Setup, inputAmplitude, nFft, pmod, TWO_PI } from '../geometry';
import { efficiency, relStd, trapIntensities, uniformity } from '../metrics';
import type { Rng } from '../rng';
import type { TrapSet } from '../traps';
import type { HistoryEntry, MethodModule, MethodRun, RunContext } from '../types';
import { now } from './common';

/** The starting phase: `init` (validated) or `nPix^2` uniform random phases drawn in C order from `rng`. */
export function startPhaseRandom(setup: Setup, rng: Rng, init: Float64Array | null): Float64Array {
  const n = setup.nPix;
  if (init === null) return rng.phases(n * n);
  if (init.length !== n * n || !init.every(Number.isFinite)) throw new Error(`init must be a finite array of shape (${n}, ${n})`);
  return Float64Array.from(init);
}

const deadlineOf = (timeS: number | null): number | null => (timeS === null ? null : now() + timeS);
const expired = (d: number | null): boolean => d !== null && now() >= d;

/** `dL/dphi = 2 Re(i f conj(h)) = 2 (f_r h_i - f_i h_r)` per pixel. */
function phaseGrad(f: Cx, h: Cx): Float64Array {
  const n = f.length / 2;
  const out = new Float64Array(n);
  for (let i = 0; i < n; i++) out[i] = 2 * (f[2 * i] * h[2 * i + 1] - f[2 * i + 1] * h[2 * i]);
  return out;
}

// ---- forward models with exact adjoints ----

/** `phi -> E` on the centred focal grid with adjoint; `device = null` is the ideal device. */
export class FocalForward {
  private readonly device: Device | null;
  private readonly amp: Float64Array;
  private readonly env: Float64Array | null = null;
  private readonly swap: Float64Array | null = null;

  constructor(readonly setup: Setup, device: Device | null = null) {
    this.device = device === null ? null : { ...device, flickerRad: 0 };
    this.amp = inputAmplitude(setup);
    const d = this.device;
    if (d !== null) {
      this.env = sinc1d(setup, d.fillFactor);
      if (d.crosstalk !== null) this.swap = swapFactor(setup, d);
    }
  }

  private mulOuter(e: Cx, s: Float64Array): void {
    const m = s.length;
    for (let iy = 0; iy < m; iy++) {
      for (let ix = 0; ix < m; ix++) {
        const k = s[iy] * s[ix], o = 2 * (iy * m + ix);
        e[o] *= k;
        e[o + 1] *= k;
      }
    }
  }

  /** `{e, cache}`: the focal field and what the adjoint needs (the complex field that carries the phase). */
  forward(phi: ArrayLike<number>): { e: Cx; cache: Cx } {
    const s = this.setup, d = this.device;
    if (d === null) return { e: fftFocalField(phi, s, this.amp), cache: slmField(phi, s, this.amp) };
    const disp = displayedPhase(phi, d, null);
    if (d.crosstalk === null) {
      const e = fftFocalField(disp, s, this.amp);
      this.mulOuter(e, this.env as Float64Array);
      return { e, cache: slmField(disp, s, this.amp) };
    }
    const n = s.nPix, u = d.upsample, nu = n * u;
    const psi = crosstalk(disp, d);
    const g = new Float64Array(2 * nu * nu);
    for (let iy = 0; iy < nu; iy++) {
      for (let ix = 0; ix < nu; ix++) {
        const a = this.amp[Math.floor(iy / u) * n + Math.floor(ix / u)], q = iy * nu + ix;
        g[2 * q] = a * Math.cos(psi[q]);
        g[2 * q + 1] = a * Math.sin(psi[q]);
      }
    }
    const e = upsampledWindow(g, s, u);
    this.mulOuter(e, this.swap as Float64Array);
    return { e, cache: g };
  }

  /** `dL/dphi` for `gradE = dL/dE*`. */
  adjoint(gradE: Cx, cache: Cx): Float64Array {
    const s = this.setup, d = this.device;
    if (d === null) return phaseGrad(cache, fftInverse(gradE, s));
    if (d.crosstalk === null) {
      const g = Float64Array.from(gradE);
      this.mulOuter(g, this.env as Float64Array);
      return phaseGrad(cache, fftInverse(g, s));
    }
    const n = s.nPix, m = nFft(s), u = d.upsample, mu = m * u, nu = n * u;
    const gc = Float64Array.from(gradE);
    this.mulOuter(gc, this.swap as Float64Array);
    const { idx, wr, wi } = windowIndex(s, u);
    for (let iy = 0; iy < m; iy++) {
      for (let ix = 0; ix < m; ix++) {
        const pr = wr[iy] * wr[ix] - wi[iy] * wi[ix], pi = -(wr[iy] * wi[ix] + wi[iy] * wr[ix]); // conjugate ramp
        const o = 2 * (iy * m + ix);
        const re = gc[o] / u, im = gc[o + 1] / u;
        gc[o] = re * pr - im * pi;
        gc[o + 1] = re * pi + im * pr;
      }
    }
    // s2 = ifft(s1, axis=0, ortho)[:nu, :] where s1 has the rows of gc at idx; then s3 columns at idx; h = ifft(s3, axis=1)[:, :nu]
    const p = plan(mu);
    const tin = new Float64Array(2 * mu), tout = new Float64Array(2 * mu);
    const s2 = new Float64Array(2 * nu * m);
    for (let c = 0; c < m; c++) {
      tin.fill(0);
      for (let r = 0; r < m; r++) {
        tin[2 * idx[r]] = gc[2 * (r * m + c)];
        tin[2 * idx[r] + 1] = gc[2 * (r * m + c) + 1];
      }
      p.inverse(tin, tout);
      for (let r = 0; r < nu; r++) {
        s2[2 * (r * m + c)] = tout[2 * r];
        s2[2 * (r * m + c) + 1] = tout[2 * r + 1];
      }
    }
    const h = new Float64Array(2 * nu * nu);
    for (let r = 0; r < nu; r++) {
      tin.fill(0);
      for (let c = 0; c < m; c++) {
        tin[2 * idx[c]] = s2[2 * (r * m + c)];
        tin[2 * idx[c] + 1] = s2[2 * (r * m + c) + 1];
      }
      p.inverse(tin, tout);
      for (let c = 0; c < nu; c++) {
        h[2 * (r * nu + c)] = tout[2 * c] * mu; // two inverse transforms divided by mu each; ortho wants 1 / mu in total
        h[2 * (r * nu + c) + 1] = tout[2 * c + 1] * mu;
      }
    }
    return crosstalkAdjoint(phaseGrad(cache, h), d);
  }
}

/** `phi -> V_m` with adjoint. Ideal device: the point-trap form; with a device the fields are read from the device's FFT-form focal field. */
export class TrapForward {
  private readonly focal: FocalForward | null = null;
  private iy: Int32Array = new Int32Array(0);
  private ix: Int32Array = new Int32Array(0);
  private readonly scale: number;

  constructor(readonly setup: Setup, readonly traps: TrapSet, device: Device | null = null) {
    this.scale = setup.pad / setup.nPix;
    if (device !== null) {
      if (traps.zM.some((z) => z !== 0) || traps.charge.some((c) => c !== 0)) throw new Error('a device model supports traps with z = 0 and no vortex charge (FFT form)');
      this.focal = new FocalForward(setup, device);
      ({ iy: this.iy, ix: this.ix } = trapBins(setup, traps));
    }
  }

  fields(phi: ArrayLike<number>): { v: Cx; cache: Cx } {
    if (this.focal === null) {
      const f = slmField(phi, this.setup);
      return { v: pointTrapProjection(f, this.setup, this.traps), cache: f };
    }
    const { e, cache } = this.focal.forward(phi);
    const m = nFft(this.setup);
    const v = new Float64Array(2 * this.traps.length);
    for (let t = 0; t < this.traps.length; t++) {
      const o = 2 * (this.iy[t] * m + this.ix[t]);
      v[2 * t] = e[o] * this.scale;
      v[2 * t + 1] = e[o + 1] * this.scale;
    }
    return { v, cache };
  }

  adjoint(gradV: Cx, cache: Cx): Float64Array {
    if (this.focal === null) {
      const h = pointTrapBackproject(gradV, this.setup, this.traps);
      const n2 = this.setup.nPix ** 2;
      for (let i = 0; i < h.length; i++) h[i] /= n2;
      return phaseGrad(cache, h);
    }
    const m = nFft(this.setup);
    const g = new Float64Array(2 * m * m);
    for (let t = 0; t < this.traps.length; t++) {
      const o = 2 * (this.iy[t] * m + this.ix[t]);
      g[o] += gradV[2 * t] * this.scale;
      g[o + 1] += gradV[2 * t + 1] * this.scale;
    }
    return this.focal.adjoint(g, cache);
  }
}

// ---- cost functions ----

export interface CostEval {
  value: number;
  grad: Float64Array;
  aux: Cx;
}

export interface Cost {
  valueGrad(phi: Float64Array): CostEval;
}

/** `C_t = sum_m (I_m - s T_m)^t / sum_m (s T_m)^t` with `T_m = efficiency w_m / sum w` (Harte et al. 2014). */
export class TrapCost implements Cost {
  readonly fwd: TrapForward;
  readonly t: number;
  s: number;
  readonly target: Float64Array;

  constructor(setup: Setup, traps: TrapSet, device: Device | null, o: { t?: number; efficiency?: number; scale?: number } = {}) {
    const t = o.t ?? 2, eff = o.efficiency ?? 0.9;
    if (t < 2 || t % 2) throw new Error(`t must be an even integer >= 2, got ${t}`);
    if (!(eff > 0 && eff <= 1)) throw new Error(`efficiency must be in (0, 1], got ${eff}`);
    this.fwd = new TrapForward(setup, traps, device);
    this.t = t;
    this.s = o.scale ?? 1;
    let sw = 0;
    for (const w of traps.weight) sw += w;
    this.target = Float64Array.from(traps.weight, (w) => (eff * w) / sw);
  }

  valueGrad(phi: Float64Array): CostEval {
    const { v, cache } = this.fwd.fields(phi);
    const M = this.target.length, t = this.t;
    let norm = 0;
    for (let m = 0; m < M; m++) norm += (this.s * this.target[m]) ** t;
    let value = 0;
    const gv = new Float64Array(2 * M);
    for (let m = 0; m < M; m++) {
      const i = v[2 * m] ** 2 + v[2 * m + 1] ** 2;
      const d = i - this.s * this.target[m];
      value += d ** t;
      const gi = (t * d ** (t - 1)) / norm;
      gv[2 * m] = gi * v[2 * m];
      gv[2 * m + 1] = gi * v[2 * m + 1];
    }
    return { value: value / norm, grad: this.fwd.adjoint(gv, cache), aux: v };
  }
}

/** The same cost over the signal region of a focal-field target (Harte et al. 2014 eqs (6) and (10)). */
export class FieldCost implements Cost {
  readonly fwd: FocalForward;
  readonly t: number;
  s: number;
  readonly target: Float64Array;

  constructor(readonly setup: Setup, amplitude: Float64Array, readonly mask: Uint8Array, device: Device | null, o: { t?: number; efficiency?: number; scale?: number } = {}) {
    const m = nFft(setup), t = o.t ?? 2, eff = o.efficiency ?? 0.4;
    if (amplitude.length !== m * m || mask.length !== m * m) throw new Error(`the target must be on the ${m} x ${m} focal grid (n_fft), got ${Math.sqrt(amplitude.length)}`);
    if (t < 2 || t % 2) throw new Error(`t must be an even integer >= 2, got ${t}`);
    if (!(eff > 0 && eff <= 1)) throw new Error(`efficiency must be in (0, 1], got ${eff}`);
    this.fwd = new FocalForward(setup, device);
    this.t = t;
    this.s = o.scale ?? 1;
    const a2 = Float64Array.from(amplitude, (a, q) => (mask[q] ? a * a : 0));
    let sum = 0;
    for (const x of a2) sum += x;
    if (sum <= 0) throw new Error('the signal region carries no target power');
    this.target = a2.map((x) => (eff * setup.nPix ** 2 * x) / sum);
  }

  valueGrad(phi: Float64Array): CostEval {
    const { e, cache } = this.fwd.forward(phi);
    const t = this.t, n = e.length / 2;
    let norm = 0;
    for (let q = 0; q < n; q++) if (this.mask[q]) norm += (this.s * this.target[q]) ** t;
    let value = 0;
    const g = new Float64Array(2 * n);
    for (let q = 0; q < n; q++) {
      if (!this.mask[q]) continue;
      const d = e[2 * q] ** 2 + e[2 * q + 1] ** 2 - this.s * this.target[q];
      value += d ** t;
      const gi = (t * d ** (t - 1)) / norm;
      g[2 * q] = gi * e[2 * q];
      g[2 * q + 1] = gi * e[2 * q + 1];
    }
    return { value: value / norm, grad: this.fwd.adjoint(g, cache), aux: e };
  }
}

// ---- optimizers (generators: one yield per accepted step) ----

export interface OptEvent {
  it: number;
  x: Float64Array;
  f: number;
  aux: Cx;
}

export interface OptResult {
  x: Float64Array;
  f: number;
  iterations: number;
  evaluations: number;
}

const dot = (a: Float64Array, b: Float64Array): number => {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += a[i] * b[i];
  return s;
};

/** Minimizer of the cubic through `(a, fa, ga)` and `(b, fb, gb)` or null (Nocedal and Wright, eq 3.59). */
function cubicMin(a: number, fa: number, ga: number, b: number, fb: number, gb: number): number | null {
  if (a === b || ![fa, ga, fb, gb].every(Number.isFinite)) return null;
  const d1 = ga + gb - (3 * (fa - fb)) / (a - b);
  const rad = d1 * d1 - ga * gb;
  if (rad < 0) return null;
  const d2 = Math.sign(b - a || 1) * Math.sqrt(rad);
  const den = gb - ga + 2 * d2;
  if (den === 0) return null;
  return b - ((b - a) * (gb + d2 - d1)) / den;
}

type Fun = (x: Float64Array) => CostEval;
interface Probe {
  f: number;
  dphi: number;
  g: Float64Array | null;
  aux: Cx | null;
}

/** Strong-Wolfe step along `d`; `step` is null when the search fails. */
function wolfe(fun: Fun, x: Float64Array, d: Float64Array, f0: number, g0: number, a1: number, c1: number, c2: number, maxEvals: number): { step: { a: number; f: number; g: Float64Array; aux: Cx } | null; evals: number } {
  const cache = new Map<number, Probe>([[0, { f: f0, dphi: g0, g: null, aux: null }]]);
  let evals = 0;
  const phi = (a: number): Probe => {
    let p = cache.get(a);
    if (!p) {
      const xa = x.map((xi, i) => xi + a * d[i]);
      const r = fun(xa);
      evals++;
      p = { f: r.value, dphi: dot(r.grad, d), g: r.grad, aux: r.aux };
      cache.set(a, p);
    }
    return p;
  };
  const zoom = (lo0: number, hi0: number): number | null => {
    let lo = lo0, hi = hi0;
    let flo = phi(lo).f, glo = phi(lo).dphi;
    let fhi = phi(hi).f, ghi = phi(hi).dphi;
    for (let it = 0; it < maxEvals; it++) {
      const loB = Math.min(lo, hi), hiB = Math.max(lo, hi);
      if (hiB - loB < 1e-15 * Math.max(hiB, 1e-300)) break;
      let a = cubicMin(lo, flo, glo, hi, fhi, ghi);
      if (a === null || !(loB + 0.1 * (hiB - loB) <= a && a <= hiB - 0.1 * (hiB - loB))) a = 0.5 * (lo + hi);
      const { f: fa, dphi: ga } = phi(a);
      if (!Number.isFinite(fa) || fa > f0 + c1 * a * g0 || fa >= flo) {
        hi = a; fhi = fa; ghi = ga;
      } else {
        if (Math.abs(ga) <= -c2 * g0) return a;
        if (ga * (hi - lo) >= 0) { hi = lo; fhi = flo; ghi = glo; }
        lo = a; flo = fa; glo = ga;
      }
    }
    return lo > 0 && flo < f0 ? lo : null;
  };
  let aPrev = 0, fPrev = f0, a = a1;
  let result: number | null = null;
  let broke = false;
  for (let i = 0; i < maxEvals; i++) {
    const { f: fa, dphi: ga } = phi(a);
    if (!Number.isFinite(fa) || fa > f0 + c1 * a * g0 || (i > 0 && fa >= fPrev)) { result = zoom(aPrev, a); broke = true; break; }
    if (Math.abs(ga) <= -c2 * g0) { result = a; broke = true; break; }
    if (ga >= 0) { result = zoom(a, aPrev); broke = true; break; }
    aPrev = a; fPrev = fa;
    a *= 2;
  }
  if (!broke) result = aPrev > 0 ? aPrev : null;
  if (result === null || result <= 0 || !((cache.get(result)?.f ?? Infinity) < f0)) return { step: null, evals };
  const p = cache.get(result) as Probe;
  return { step: { a: result, f: p.f, g: p.g as Float64Array, aux: p.aux as Cx }, evals };
}

/**
 * Nonlinear conjugate gradient, Fletcher-Reeves, with a strong-Wolfe line search (Nocedal and Wright Algorithms 3.5 and 3.6,
 * `c1 = 1e-4`, `c2 = 0.1`). Yields `{it, x, f, aux}` after every accepted step; the cost value never increases.
 */
export function* cgMinimize(fun: Fun, x0: Float64Array, iterations: number, deadline: number | null = null, c1 = 1e-4, c2 = 0.1, maxLineEvals = 25): Generator<OptEvent, OptResult> {
  let x = Float64Array.from(x0);
  const first = fun(x);
  let f = first.value, g = first.grad, aux = first.aux;
  let evals = 1;
  let d = g.map((v) => -v);
  let fOld: number | null = null;
  let it = 0;
  for (let k = 1; k <= Math.floor(iterations); k++) {
    it = k;
    if (expired(deadline)) { it--; break; }
    let step: ReturnType<typeof wolfe>['step'] = null;
    for (const restart of [false, true]) {
      if (restart || dot(g, d) >= 0) d = g.map((v) => -v);
      const gd = dot(g, d);
      if (!(gd < 0)) break;
      let a0: number;
      if (fOld !== null && f < fOld && !restart) a0 = (2 * (f - fOld)) / gd;
      else {
        let mx = 0;
        for (const v of d) mx = Math.max(mx, Math.abs(v));
        a0 = 0.1 / Math.max(mx, 1e-300);
      }
      const r = wolfe(fun, x, d, f, gd, a0, c1, c2, maxLineEvals);
      evals += r.evals;
      step = r.step;
      if (step !== null) break;
    }
    if (step === null) { it--; break; }
    const { a, f: fn, g: gn, aux: auxn } = step;
    const dOld = d;
    x = x.map((xi, i) => xi + a * dOld[i]);
    const gg = dot(g, g);
    const beta = gg > 0 ? dot(gn, gn) / gg : 0;
    d = gn.map((v, i) => -v + beta * dOld[i]);
    fOld = f; f = fn; g = gn; aux = auxn;
    yield { it, x, f, aux };
  }
  return { x, f, iterations: it, evaluations: evals };
}

/** Adam (Kingma and Ba 2015) on a real array; yields `{it, x, f, aux}` evaluated before the step of iteration `it`. */
export function* adamMinimize(fun: Fun, x0: Float64Array, iterations: number, lr: number, deadline: number | null = null, beta1 = 0.9, beta2 = 0.999, eps = 1e-8): Generator<OptEvent, OptResult> {
  let x = Float64Array.from(x0);
  const m = new Float64Array(x.length), v = new Float64Array(x.length);
  let f = NaN;
  let it = 0;
  for (let k = 1; k <= Math.floor(iterations); k++) {
    it = k;
    if (expired(deadline)) { it--; break; }
    const r = fun(x);
    f = r.value;
    yield { it, x, f, aux: r.aux };
    const g = r.grad;
    const c1 = 1 - beta1 ** it, c2 = 1 - beta2 ** it;
    const nx = new Float64Array(x.length);
    for (let i = 0; i < x.length; i++) {
      m[i] = beta1 * m[i] + (1 - beta1) * g[i];
      v[i] = beta2 * v[i] + (1 - beta2) * g[i] * g[i];
      nx[i] = x[i] - (lr * (m[i] / c1)) / (Math.sqrt(v[i] / c2) + eps);
    }
    x = nx;
  }
  return { x, f, iterations: it, evaluations: it };
}

// ---- history ----

function trapHistory(iteration: number, v: Cx, weights: ArrayLike<number>, t0: number, extra: Record<string, number>): HistoryEntry {
  const iw = trapIntensities(v, weights);
  return { iteration, efficiency: efficiency(trapIntensities(v)), uniformity: uniformity(iw), relStd: relStd(iw), timeS: now() - t0, ...extra };
}

function fieldRegion(amplitude: Float64Array, mask: Uint8Array): number[] {
  const idx: number[] = [];
  for (let q = 0; q < mask.length; q++) if (mask[q] && amplitude[q] > 0) idx.push(q);
  return idx;
}

/** Relative RMS error over the measure region of the intensity shape (both normalised to unit sum in the region). */
export function fieldErrorNormalised(e: Cx, amplitude: Float64Array, mask: Uint8Array): number {
  const idx = fieldRegion(amplitude, mask);
  let si = 0, st = 0;
  for (const q of idx) {
    si += e[2 * q] ** 2 + e[2 * q + 1] ** 2;
    st += amplitude[q] ** 2;
  }
  let acc = 0;
  for (const q of idx) {
    const i = (e[2 * q] ** 2 + e[2 * q + 1] ** 2) / si, t = amplitude[q] ** 2 / st;
    acc += ((i - t) / t) ** 2;
  }
  return Math.sqrt(acc / idx.length);
}

function fieldHistory(iteration: number, e: Cx, amplitude: Float64Array, mask: Uint8Array, t0: number, extra: Record<string, number>): HistoryEntry {
  const idx = fieldRegion(amplitude, mask);
  let inMask = 0, total = 0;
  for (let q = 0; q < mask.length; q++) {
    const p = e[2 * q] ** 2 + e[2 * q + 1] ** 2;
    total += p;
    if (mask[q]) inMask += p;
  }
  const ratio = idx.map((q) => (e[2 * q] ** 2 + e[2 * q + 1] ** 2) / amplitude[q] ** 2);
  const lo = Math.min(...ratio), hi = Math.max(...ratio);
  const mean = ratio.reduce((a, x) => a + x, 0) / ratio.length;
  const sd = Math.sqrt(ratio.reduce((a, x) => a + (x - mean) ** 2, 0) / ratio.length);
  return {
    iteration, efficiency: inMask / total, uniformity: 1 - (hi - lo) / (hi + lo), relStd: (100 * sd) / mean, timeS: now() - t0,
    error: fieldErrorNormalised(e, amplitude, mask), ...extra,
  };
}

// ---- M10 and M11 ----

function stages(t: number | number[] | undefined, kind: string, iterations: number): [number, number][] {
  const ts = t === undefined || t === null ? (kind === 'field' ? [4, 2] : [2]) : Array.isArray(t) ? t : [t];
  if (!ts.length) throw new Error('t must be an even integer >= 2 or a non-empty tuple of them');
  const share = Math.max(1, Math.floor(iterations / ts.length));
  const out: [number, number][] = ts.map((tt) => [Math.trunc(tt), share]);
  out[out.length - 1] = [out[out.length - 1][0], Math.max(1, iterations - share * (ts.length - 1))];
  return out;
}

const modTwoPi = (x: Float64Array): Float64Array => x.map((v) => pmod(v, TWO_PI));

function* m10(ctx: RunContext): MethodRun {
  const { setup, target, budget, rng, init, options: o } = ctx;
  const t0 = now();
  const deadline = deadlineOf(budget.timeS);
  let phi = startPhaseRandom(setup, rng, init);
  const history: HistoryEntry[] = [];
  let done = 0;
  let last: Cx | null = null;
  let cost: Cost | null = null;
  for (const [tt, iters] of stages(o.t, target.kind, budget.iterations)) {
    cost = target.kind === 'traps'
      ? new TrapCost(setup, target.traps, null, { t: tt, efficiency: o.efficiency ?? 0.9 })
      : new FieldCost(setup, target.amplitude, target.mask, null, { t: tt, efficiency: o.efficiency ?? 0.4 });
    const gen = cgMinimize((x) => (cost as Cost).valueGrad(x), phi, iters, deadline);
    let res: OptResult;
    for (;;) {
      const r = gen.next();
      if (r.done) { res = r.value; break; }
      const { it, f, aux } = r.value;
      last = aux;
      const entry = target.kind === 'traps'
        ? trapHistory(done + it, aux, target.traps.weight, t0, { cost: f, t: tt })
        : fieldHistory(done + it, aux, target.amplitude, target.mask, t0, { cost: f, t: tt });
      history.push(entry);
      yield entry;
    }
    phi = res.x;
    done += res.iterations;
    if (expired(deadline)) break;
  }
  if (last === null) last = (cost as Cost).valueGrad(phi).aux; // a zero-iteration run: evaluate the start
  return { phi: modTwoPi(phi), history, fields: last, meta: { method: 'M10', iterations: done, deviceAware: false } };
}

function* m11(ctx: RunContext): MethodRun {
  const { setup, target, device, budget, rng, init, options: o } = ctx;
  const t0 = now();
  const deadline = deadlineOf(budget.timeS);
  const phi0 = startPhaseRandom(setup, rng, init);
  const lr: number = o.lr ?? 1.0;
  const cost: Cost = target.kind === 'traps'
    ? new TrapCost(setup, target.traps, device, { t: 2, efficiency: o.efficiency ?? 0.9 })
    : new FieldCost(setup, target.amplitude, target.mask, device, { t: 2, efficiency: o.efficiency ?? 0.4 });
  const history: HistoryEntry[] = [];
  const gen = adamMinimize((x) => cost.valueGrad(x), phi0, budget.iterations, lr, deadline);
  let res: OptResult;
  for (;;) {
    const r = gen.next();
    if (r.done) { res = r.value; break; }
    const { it, f, aux } = r.value;
    const entry = target.kind === 'traps'
      ? trapHistory(it, aux, target.traps.weight, t0, { loss: f })
      : fieldHistory(it, aux, target.amplitude, target.mask, t0, { loss: f });
    history.push(entry);
    yield entry;
  }
  const fields = cost.valueGrad(res.x).aux;
  return { phi: modTwoPi(res.x), history, fields, meta: { method: 'M11', lr, paperLr: 0.001, deviceAware: device !== null } };
}

export const optimMethods: MethodModule[] = [
  { spec: { id: 'M10', name: 'Conjugate-gradient minimization', family: 'optimization', lane: 'both', targets: ['traps', 'field'], dims: [2, 3] }, run: m10 },
  { spec: { id: 'M11', name: 'Wirtinger gradient descent with Adam', family: 'optimization', lane: 'both', targets: ['traps', 'field'], dims: [2, 3] }, run: m11 },
];
