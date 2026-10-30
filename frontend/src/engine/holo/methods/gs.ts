/**
 * The Gerchberg-Saxton iteration shared by M04 to M08, M12, M14, M15 and M16.
 *
 * Python counterpart: `methods/baseline/_gs.py`. `runTraps` is the point-trap iteration: the trap fields `V_m` of the current
 * hologram map to the focal coefficients `c_m` (the rule of the method), are back-projected to the SLM and the phase is
 * kept; `runField` is the FFT-form iteration for a shaped target with mixed-region amplitude freedom (`mixing = 1` is plain
 * GS). The rules `gs`, `gaa`, `gsw` and `wgsFixed` are the ones the Python docstrings state (Di Leonardo et al. 2007, Kim
 * et al. 2019, Pasienski and DeMarco 2008).
 */
import type { Cx } from '../fft';
import { PointPlan, fftFocalField, fftInverse, slmField } from '../forward';
import { type Setup, focalBinM, inputAmplitude, nFft, slmAxis } from '../geometry';
import type { Rng } from '../rng';
import type { TrapSet } from '../traps';
import type { Budget, HistoryEntry, MethodRun, Result, Target } from '../types';
import { Recorder, ampTargets, angle, fftBackproject, fftFields, now, phasor, startPhase } from './common';

export const FORMS = ['point', 'fft'] as const;
export type Form = (typeof FORMS)[number];

export function checkForm(form: string): Form {
  if (!(FORMS as readonly string[]).includes(form)) throw new Error(`form must be one of [${FORMS.map((f) => `'${f}'`).join(', ')}], got '${form}'`);
  return form as Form;
}

/** The FFT form samples the focal field at bins: traps must sit on bins with z = 0 and no vortex. */
export function checkOnBins(setup: Setup, traps: TrapSet): void {
  const b = focalBinM(setup);
  let bad = false;
  for (let i = 0; i < traps.length; i++) {
    const fx = traps.xM[i] / b, fy = traps.yM[i] / b;
    const off = Math.abs(fx - Math.round(fx)) + Math.abs(fy - Math.round(fy));
    if (off > 1e-6 || traps.zM[i] !== 0 || traps.charge[i] !== 0) bad = true;
  }
  if (bad) throw new Error("the fft form needs traps on FFT bins with z = 0 and no vortex (use form='point')");
}

/** `{fwd, back}`: `fwd(phi) -> V_m` and `back(c) -> complex SLM field` for the chosen form. */
export function makeEngine(setup: Setup, traps: TrapSet, form: Form): { fwd: (phi: ArrayLike<number>) => Cx; back: (c: Cx) => Cx } {
  checkForm(form);
  const amp = inputAmplitude(setup);
  if (form === 'fft') {
    checkOnBins(setup, traps);
    return { fwd: (phi) => fftFields(phi, setup, traps, amp).v, back: (c) => fftBackproject(c, setup, traps) };
  }
  const plan = new PointPlan(setup, traps); // the x and y factors are computed once for the whole run
  return { fwd: (phi) => plan.project(slmField(phi, setup, amp)), back: (c) => plan.backproject(c) };
}

/** Rule state: target amplitudes `a`, weights `w`, and the keywords of the rule. */
export interface RuleState {
  a: Float64Array;
  w: Float64Array;
  alpha?: number;
  scale?: string;
  nFix?: number;
  psi?: Float64Array | null;
  psiLast?: Float64Array | null;
}

export type Rule = (state: RuleState, v: Cx, k: number) => Cx;

const scaleBy = (ph: Cx, f: ArrayLike<number>): Cx => {
  const out = new Float64Array(ph.length);
  for (let i = 0; i < f.length; i++) {
    out[2 * i] = ph[2 * i] * f[i];
    out[2 * i + 1] = ph[2 * i + 1] * f[i];
  }
  return out;
};

const ratio = (v: Cx, a: ArrayLike<number>): Float64Array => Float64Array.from(a, (ai, i) => Math.max(Math.hypot(v[2 * i], v[2 * i + 1]) / ai, 1e-300));
const meanOf = (a: ArrayLike<number>): number => {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += a[i];
  return s / a.length;
};

export const ruleGs: Rule = (state, v) => scaleBy(phasor(v), state.a);

/** GAA (R2 D3.4, Eq. 16): `c_m = a_m V_m/|V_m| [(1 - alpha) + alpha / r_m]`, `r_m = |V_m|/a_m` (scale 'mean': divided by its mean). */
export const ruleGaa: Rule = (state, v) => {
  const { a } = state;
  const alpha = state.alpha as number;
  let r = ratio(v, a);
  if (state.scale === 'mean') {
    const m = meanOf(r);
    r = r.map((x) => x / m);
  }
  return scaleBy(phasor(v), a.map((ai, i) => ai * (1 - alpha + alpha / r[i])));
};

/** `w_m <- w_m <r> / r_m`, `c_m = w_m V_m/|V_m|` (R2 D3.4, Eq. 18). The field of the start hologram is projected with the initial weights (k = 1 is plain GS), as the Python rule and slmsuite's WGS-Leonardo do. */
export const ruleGsw: Rule = (state, v, k) => {
  if (k > 1) {
    const r = ratio(v, state.a);
    const m = meanOf(r);
    state.w = state.w.map((w, i) => w * (m / r[i]));
  }
  return scaleBy(phasor(v), state.w);
};

/** Kim 2019: `g_i = (<B>/B_m) g_{i-1}`, `g_0 = 1`, `c_m = g_m a_m e^{i psi_i}`, `psi_i = psi_N` for `i >= N`. The field of the start hologram is projected with `g_0 = 1` (k = 1 is plain GS). */
export const ruleWgsFixed: Rule = (state, v, k) => {
  const { a } = state;
  if (k > 1) {
    const b = ratio(v, a);
    const m = meanOf(b);
    state.w = state.w.map((w, i) => w * (m / b[i]));
  }
  let psi: Float64Array;
  if (k < (state.nFix as number)) psi = angle(v);
  else if (k === state.nFix) psi = state.psi = angle(v);
  else psi = state.psi as Float64Array;
  state.psiLast = psi;
  const out = new Float64Array(v.length);
  for (let i = 0; i < psi.length; i++) {
    const mag = state.w[i] * a[i];
    out[2 * i] = mag * Math.cos(psi[i]);
    out[2 * i + 1] = mag * Math.sin(psi[i]);
  }
  return out;
};

/** Iterate `rule` from the SR start (or `init`) until the budget is spent; one history entry per iteration. */
export function* runTraps(
  mid: string, setup: Setup, traps: TrapSet, budget: Budget, rng: Rng, init: Float64Array | null, form: Form, rule: Rule,
  state: Partial<RuleState>, meta: Record<string, unknown> = {},
): MethodRun {
  const { fwd, back } = makeEngine(setup, traps, form);
  const rec = new Recorder(budget, traps.weight);
  let phi = startPhase(setup, traps, rng, init);
  let v = fwd(phi);
  const a = state.a ?? ampTargets(traps);
  const st: RuleState = { ...state, a, w: state.w ?? (rule === ruleGsw ? Float64Array.from(a) : new Float64Array(traps.length).fill(1)) };
  let k = 0;
  for (;;) {
    k++;
    phi = angle(back(rule(st, v, k)));
    v = fwd(phi);
    yield rec.add(k, v);
    if (rec.done(k)) break;
  }
  const result: Result = { phi, history: rec.history, fields: v, meta: { method: mid, form, iterations: k, ...meta } };
  result.meta.state = st;
  return result;
}

// ---- shaped targets (FFT form, mixed-region amplitude freedom) ----

/** Pixels where the shape is evaluated: `T > 0` inside the signal mask, eroded by one resolution cell (`pad` bins, periodic). */
export function measureRegion(setup: Setup, target: Extract<Target, { kind: 'field' }>): Uint8Array {
  const n = nFft(setup);
  const region = new Uint8Array(n * n);
  for (let i = 0; i < region.length; i++) region[i] = target.mask[i] && target.amplitude[i] > 0 ? 1 : 0;
  const r = setup.pad;
  const pass = (src: Uint8Array, horizontal: boolean): Uint8Array => {
    const out = new Uint8Array(n * n).fill(1);
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        for (let d = -r; d <= r; d++) {
          const yy = horizontal ? y : (((y - d) % n) + n) % n;
          const xx = horizontal ? (((x - d) % n) + n) % n : x;
          if (!src[yy * n + xx]) {
            out[y * n + x] = 0;
            break;
          }
        }
      }
    }
    return out;
  };
  const eroded = pass(pass(region, true), false);
  if (!eroded.some((v) => v)) throw new Error(`the shape is thinner than the resolution cell (${r} bins on each side of every pixel)`);
  return eroded;
}

/** Signal-region error `eta = sqrt(mean(((s I - T^2) / T^2)^2))` over the measure region, `s = sum T^2 / sum I`. */
export function fieldError(e: Cx, target: Extract<Target, { kind: 'field' }>, region: Uint8Array): number {
  let st = 0, si = 0;
  for (let q = 0; q < region.length; q++) {
    if (!region[q]) continue;
    st += target.amplitude[q] ** 2;
    si += e[2 * q] ** 2 + e[2 * q + 1] ** 2;
  }
  const s = st / Math.max(si, 1e-300);
  let acc = 0, cnt = 0;
  for (let q = 0; q < region.length; q++) {
    if (!region[q]) continue;
    const t2 = target.amplitude[q] ** 2;
    acc += ((s * (e[2 * q] ** 2 + e[2 * q + 1] ** 2) - t2) / t2) ** 2;
    cnt++;
  }
  return Math.sqrt(acc / cnt);
}

export const START_WAVES = 20;

/** `init` if given; else a Fresnel-lens phase of `startWaves` waves at the aperture edge; `null` waves: uniform random phase. */
export function startPhaseField(setup: Setup, rng: Rng, init: Float64Array | null, startWaves: number | null): Float64Array {
  const n = setup.nPix;
  if (init !== null) {
    if (init.length !== n * n || !init.every(Number.isFinite)) throw new Error(`init must be a finite array of shape (${n}, ${n})`);
    return Float64Array.from(init);
  }
  if (startWaves === null) return rng.phases(n * n);
  const c = slmAxis(setup);
  const r0 = (n * setup.pitchM) / 2;
  const out = new Float64Array(n * n);
  for (let iy = 0; iy < n; iy++) for (let ix = 0; ix < n; ix++) out[iy * n + ix] = (2 * Math.PI * startWaves * (c[ix] ** 2 + c[iy] ** 2)) / r0 ** 2;
  return out;
}

/** MRAF iteration (Pasienski and DeMarco 2008, Eq. (1)); `mixing = 1` reduces to GS. */
export function* runField(
  mid: string, setup: Setup, target: Extract<Target, { kind: 'field' }>, budget: Budget, rng: Rng, init: Float64Array | null,
  mixing: number, startWaves: number | null = START_WAVES,
): MethodRun {
  if (!(mixing > 0 && mixing <= 1)) throw new Error(`mixing must be in (0, 1], got ${mixing}`);
  const n = nFft(setup);
  if (target.mask.length !== n * n) throw new Error(`the shaped target must be ${n} x ${n} (the FFT grid), got ${Math.sqrt(target.mask.length)}`);
  const sig = target.mask;
  const t = new Float64Array(n * n);
  let st2 = 0;
  for (let q = 0; q < t.length; q++) {
    t[q] = sig[q] ? target.amplitude[q] : 0;
    st2 += t[q] ** 2;
  }
  if (!t.some((v) => v > 0)) throw new Error('the target amplitude is zero in the whole signal region');
  const k0 = Math.sqrt(setup.nPix ** 2 / st2);
  for (let q = 0; q < t.length; q++) t[q] *= k0;
  const nPix2 = setup.nPix ** 2;
  let phi = startPhaseField(setup, rng, init, startWaves);
  let e = fftFocalField(phi, setup);
  const t0 = now();
  const history: HistoryEntry[] = [];
  const region = measureRegion(setup, target);
  const idx: number[] = [];
  for (let q = 0; q < region.length; q++) if (region[q]) idx.push(q);
  let k = 0;
  for (;;) {
    k++;
    const g = new Float64Array(2 * n * n);
    const ph = phasor(e);
    for (let q = 0; q < n * n; q++) {
      const amp = sig[q] ? mixing * t[q] : (1 - mixing) * Math.hypot(e[2 * q], e[2 * q + 1]);
      g[2 * q] = amp * ph[2 * q];
      g[2 * q + 1] = amp * ph[2 * q + 1];
    }
    phi = angle(fftInverse(g, setup));
    e = fftFocalField(phi, setup);
    let sum = 0, lo = Infinity, hi = -Infinity;
    const ratios = new Float64Array(idx.length);
    idx.forEach((q, j) => {
      const r = (e[2 * q] ** 2 + e[2 * q + 1] ** 2) / t[q] ** 2;
      ratios[j] = r;
      sum += r;
      lo = Math.min(lo, r);
      hi = Math.max(hi, r);
    });
    const mean = sum / ratios.length;
    let ss = 0;
    for (const r of ratios) ss += (r - mean) ** 2;
    let eff = 0;
    for (let q = 0; q < n * n; q++) if (sig[q]) eff += e[2 * q] ** 2 + e[2 * q + 1] ** 2;
    const entry: HistoryEntry = {
      iteration: k,
      efficiency: eff / nPix2,
      uniformity: 1 - (hi - lo) / (hi + lo),
      relStd: (100 * Math.sqrt(ss / ratios.length)) / mean,
      timeS: now() - t0,
      error: fieldError(e, target, region),
    };
    history.push(entry);
    yield entry;
    if (k >= budget.iterations || (budget.timeS !== null && entry.timeS >= budget.timeS)) break;
  }
  return { phi, history, fields: e, meta: { method: mid, mixing, iterations: k } };
}

