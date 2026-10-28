/**
 * The method interface of the live engine.
 *
 * Python counterpart: `core/types.py`. A method is a module that exposes `spec` and `run(ctx)`, a generator: it yields one
 * history entry per iteration (or per feedback step, sweep or frame) and returns the `Result`. The generator form is what
 * lets the Web Worker honour `cancel` within one iteration (the driver yields to the event loop between steps) and report
 * progress; `drain` runs it to the end synchronously (tests, Node).
 */
import type { Device } from './device';
import type { Cx } from './fft';
import type { Rng } from './rng';
import type { Setup } from './geometry';
import type { TrapSet } from './traps';

export const LANES = ['live', 'baked', 'both'] as const;
export type Lane = (typeof LANES)[number];
export const HISTORY_KEYS = ['iteration', 'efficiency', 'uniformity', 'relStd', 'timeS'] as const;

export interface Budget {
  iterations: number;
  timeS: number | null;
}

export function makeBudget(iterations: number, timeS: number | null = null): Budget {
  if (!Number.isInteger(iterations) || iterations < 1) throw new Error(`iterations must be a positive integer, got ${iterations}`);
  if (timeS !== null && !(Number.isFinite(timeS) && timeS > 0)) throw new Error(`time_s must be finite and positive or None, got ${timeS}`);
  return { iterations, timeS };
}

/** A trap set (point traps) or a shaped field: `amplitude` on the FFT grid and a signal `mask` (1 = signal region). */
export type Target =
  | { kind: 'traps'; traps: TrapSet }
  | { kind: 'field'; amplitude: Float64Array; mask: Uint8Array };

export interface HistoryEntry {
  iteration: number;
  efficiency: number;
  uniformity: number;
  relStd: number;
  timeS: number;
  [extra: string]: number;
}

export interface Result {
  /** SLM phase, row-major `nPix x nPix`, radians. */
  phi: Float64Array;
  history: HistoryEntry[];
  /** The final trap fields `V_m` (traps, interleaved complex) or the focal field (shaped target). */
  fields: Cx;
  meta: Record<string, unknown>;
}

export interface MethodSpec {
  id: string;
  name: string;
  family: string;
  lane: Lane;
  targets: readonly ('traps' | 'field')[];
  dims: readonly (2 | 3)[];
}

export interface RunContext {
  setup: Setup;
  target: Target;
  /** `null` is the ideal device. */
  device: Device | null;
  budget: Budget;
  rng: Rng;
  /** Starting phase (warm start); `null`: the method's own start. */
  init: Float64Array | null;
  /** Method keywords (the Python keyword arguments, camelCase). */
  options: Record<string, any>;
}

export type MethodRun = Generator<HistoryEntry, Result, void>;

export interface MethodModule {
  spec: MethodSpec;
  run: (ctx: RunContext) => MethodRun;
}

/** Raised for a method that has no live port: the workbench shows "replayed from the bake" (never a silent fallback). */
export class NotLive extends Error {
  constructor(readonly method: string) {
    super(`method ${method} is not live: it is replayed from the bake`);
    this.name = 'NotLive';
  }
}

/** Raised when a run is cancelled (a `cancel` message or a newer run). */
export class AbortError extends Error {
  constructor(message = 'the run was cancelled') {
    super(message);
    this.name = 'AbortError';
  }
}

/** Run a method generator to the end synchronously. */
export function drain(gen: MethodRun, onStep?: (h: HistoryEntry) => void): Result {
  for (;;) {
    const r = gen.next();
    if (r.done) return r.value;
    onStep?.(r.value);
  }
}
