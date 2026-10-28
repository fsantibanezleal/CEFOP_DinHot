/**
 * Helpers shared by the baseline and control methods.
 *
 * Python counterpart: `methods/baseline/_common.py`: `requireKinds`, the history `Recorder`, the superposition-of-random-phase
 * start `srStart`, and the FFT form of the trap projection and of its adjoint (`fftFields`, `fftBackproject`), the pair
 * that makes the FFT form and the point-trap form identical for traps on bins (z = 0, no vortex).
 */
import type { Cx } from '../fft';
import { fftFocalField, fftInverse, pointTrapBackproject, trapBins, trapFieldsFromFft } from '../forward';
import { type Setup, nFft } from '../geometry';
import { efficiency, relStd, trapIntensities, uniformity } from '../metrics';
import type { Rng } from '../rng';
import type { TrapSet } from '../traps';
import type { Budget, HistoryEntry, Target } from '../types';

export const TINY = 1e-300;

export const now = (): number => performance.now() / 1000;

export function requireKinds(target: Target, supported: readonly string[], id: string): void {
  if (!supported.includes(target.kind)) {
    throw new Error(`${id} supports the target kinds [${supported.map((s) => `'${s}'`).join(', ')}], got '${target.kind}'`);
  }
}

export function trapsOf(target: Target): TrapSet {
  if (target.kind !== 'traps') throw new Error('this method needs a trap target');
  return target.traps;
}

/** `v / |v|` per element of an interleaved complex vector, the phasor 1 where `v` is zero. */
export function phasor(v: Cx): Cx {
  const out = new Float64Array(v.length);
  for (let i = 0; i < v.length; i += 2) {
    const a = Math.hypot(v[i], v[i + 1]);
    if (a > TINY) {
      const d = Math.max(a, TINY);
      out[i] = v[i] / d;
      out[i + 1] = v[i + 1] / d;
    } else {
      out[i] = 1;
    }
  }
  return out;
}

/** `np.angle` of an interleaved complex array. */
export function angle(c: Cx): Float64Array {
  const out = new Float64Array(c.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = Math.atan2(c[2 * i + 1], c[2 * i]);
  return out;
}

export const modulus = (c: Cx): Float64Array => Float64Array.from({ length: c.length / 2 }, (_, i) => Math.hypot(c[2 * i], c[2 * i + 1]));

/** A real vector as an interleaved complex one. */
export function toCx(re: ArrayLike<number>): Cx {
  const out = new Float64Array(2 * re.length);
  for (let i = 0; i < re.length; i++) out[2 * i] = re[i];
  return out;
}

/** `amp * exp(i ph)` as an interleaved complex vector. */
export function polar(amp: ArrayLike<number>, ph: ArrayLike<number>): Cx {
  const out = new Float64Array(2 * ph.length);
  for (let i = 0; i < ph.length; i++) {
    out[2 * i] = amp[i] * Math.cos(ph[i]);
    out[2 * i + 1] = amp[i] * Math.sin(ph[i]);
  }
  return out;
}

export const ampTargets = (traps: TrapSet): Float64Array => Float64Array.from(traps.weight, Math.sqrt);

export function mean(a: ArrayLike<number>): number {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += a[i];
  return s / a.length;
}

/** `arg sum_m sqrt(w_m) exp(i (Delta^m + theta_m))` with `theta_m` uniform: the SR hologram. */
export function srStart(setup: Setup, traps: TrapSet, rng: Rng): Float64Array {
  const theta = rng.phases(traps.length);
  return angle(pointTrapBackproject(polar(ampTargets(traps), theta), setup, traps));
}

/** `init` (validated shape) when given, else the SR start. */
export function startPhase(setup: Setup, traps: TrapSet, rng: Rng, init: Float64Array | null): Float64Array {
  if (init === null) return srStart(setup, traps, rng);
  if (init.length !== setup.nPix ** 2 || !init.every(Number.isFinite)) {
    throw new Error(`init must be a finite array of shape (${setup.nPix}, ${setup.nPix})`);
  }
  return Float64Array.from(init);
}

/** Focal field `E` and trap fields `V_m = E[bin] pad / n_pix` of the hologram `phi`. */
export function fftFields(phi: ArrayLike<number>, setup: Setup, traps: TrapSet, amp?: Float64Array): { e: Cx; v: Cx } {
  const e = fftFocalField(phi, setup, amp);
  return { e, v: trapFieldsFromFft(e, setup, traps) };
}

/** SLM field from focal deltas `c_m` at the trap bins (adjoint of `fftFields`; the overall scale is irrelevant). */
export function fftBackproject(coeffs: Cx, setup: Setup, traps: TrapSet): Cx {
  const { iy, ix } = trapBins(setup, traps);
  const m = nFft(setup), k = setup.nPix / setup.pad;
  const f = new Float64Array(2 * m * m);
  for (let t = 0; t < traps.length; t++) {
    const o = 2 * (iy[t] * m + ix[t]);
    f[o] += coeffs[2 * t] * k;
    f[o + 1] += coeffs[2 * t + 1] * k;
  }
  return fftInverse(f, setup);
}

/** History recorder for a run: `add(iteration, v)` appends the entry, `done(k)` tells when the budget is spent. */
export class Recorder {
  readonly history: HistoryEntry[] = [];
  private readonly t0 = now();

  constructor(
    readonly budget: Budget,
    readonly weights: ArrayLike<number> | undefined,
  ) {}

  elapsed(): number {
    return now() - this.t0;
  }

  add(iteration: number, v: Cx, extra: Record<string, number> = {}): HistoryEntry {
    const raw = trapIntensities(v);
    const w = trapIntensities(v, this.weights);
    const entry: HistoryEntry = {
      iteration,
      efficiency: efficiency(raw),
      uniformity: uniformity(w),
      relStd: relStd(w),
      timeS: this.elapsed(),
      ...extra,
    };
    this.history.push(entry);
    return entry;
  }

  done(iteration: number): boolean {
    if (iteration >= this.budget.iterations) return true;
    return this.budget.timeS !== null && this.elapsed() >= this.budget.timeS;
  }
}
