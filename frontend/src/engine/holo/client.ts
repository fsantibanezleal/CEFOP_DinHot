/**
 * The typed client of the live engine, for the workbench: it owns a dedicated Web Worker (`worker.ts`) and turns the message
 * protocol of `runner.ts` into promises.
 *
 * - `run` posts a case and a method, reports progress (at most 30 per second) and resolves with the final result whose large
 *   arrays arrive as transferred buffers. A new `run` cancels the previous one: its promise rejects with an `AbortError`.
 * - `cancel` stops the run in flight within one iteration; `dispose` terminates the worker.
 * - A method that is not ported rejects with `NotLive` (the workbench shows "replayed from the bake"; never a silent fallback).
 * - `backend: 'auto' | 'cpu' | 'gpu'` selects the WebGPU FFT path (`gpu/`) when the worker can use it; any failure or absence
 *   falls back to the CPU path and the reason is in `RunResult.fallbackReason`.
 */
import type { ParamsRecord } from '../../lib/contract.types';
import type { ParamsLike, Progress, TrapEdit } from './engine';
import type { InMsg, OutMsg, RunOptions } from './runner';
import { AbortError, NotLive } from './types';

export { AbortError, NotLive };
export type { Progress };

/** The ported methods (a static copy of `methods/index.ts` so the page does not import the engine; a test keeps them equal). */
export const LIVE_METHODS: readonly string[] = ['M01', 'M02', 'M03', 'M04', 'M05', 'M06', 'M07', 'M08', 'M10', 'M11', 'M12', 'M14', 'M15', 'M16', 'M19'];

export interface RunRequest {
  params: ParamsRecord;
  method: string;
  options?: {
    iterations?: number;
    device?: 'ideal' | 'case';
    backend?: 'auto' | 'cpu' | 'gpu';
    /** A warm start (B3): one phase per trap, the hologram starts as the superposition with these trap phases. */
    trapPhases?: Float64Array;
    /** An edited target: overrides `params.target`. */
    traps?: { id: number; x_um: number; y_um: number; z_um: number; weight: number; charge: number }[];
    /** Method keywords (camelCase) beyond the record, for example `{ nFix: 12 }` for M07 or `{ mixing: 0.4 }` for M08. */
    extra?: Record<string, unknown>;
  };
}

export interface RunResult {
  method: string;
  backend: 'cpu' | 'gpu';
  fallbackReason: string | null;
  nPix: number;
  pad: number;
  binUm: number;
  halfFieldUm: number;
  /** `nPix * nPix`, radians in `[0, 2 pi)`. */
  phase: Float64Array;
  /** The phase after the device model (quantization, LUT, flicker), or null for the ideal device. */
  displayedPhase: Float64Array | null;
  /** `focalSize * focalSize` intensity relative to the mean trap (to the shape's interior mean for a shaped target). */
  focal: Float32Array;
  focalSize: number;
  /** `I_m / mean`, in trap id order. */
  trapIntensity: Float64Array;
  history: Progress[];
  metrics: { efficiency: number; uniformity: number; relStdPct: number; zeroOrder: number; ghost: number };
  timeMs: number;
}

export interface ParticleRequest {
  focal: Float32Array;
  focalSize: number;
  binUm: number;
  dynamics: NonNullable<ParamsRecord['dynamics']>;
  seed: number;
  /** Optional, for the exact local map of the bake: the hologram phase with the setup of the case (else the focal is interpolated). */
  phase?: Float64Array;
  params?: ParamsRecord;
  /** The trap to trap (`dynamics.trap_id` of `params` when the case is given). */
  trap?: { x_um: number; y_um: number; z_um: number };
  /** Immersion index and padding when the case is not given (defaults 1.33 and 2). */
  setup?: { pad: number; nImm: number };
}

export interface ParticleResult {
  xUm: Float64Array;
  yUm: Float64Array;
  dtS: number;
  psd: { fHz: Float64Array; p: Float64Array };
  fcHz: number;
  stiffness: { value: number; unit: string };
  /** Measured over expected corner (bead) or radial (atom) frequency: the calibration check. */
  fcRatio: number;
  boltzmannTv: number | null;
  depth: { value: number; unit: string };
}

export interface EngineClient {
  liveMethods(): string[];
  run(req: RunRequest, onProgress?: (p: Progress) => void): Promise<RunResult>;
  particle(req: ParticleRequest): Promise<ParticleResult>;
  axialCut(req: { phase: Float64Array; params: ParamsRecord; trapId: number; nz: number }): Promise<{ xz: Float32Array; nx: number; nz: number; zUm: [number, number] }>;
  /** Probe WebGPU in the worker: `{ ok: true, adapter }` or `{ ok: false, reason }`. */
  gpu(): Promise<{ ok: true; adapter: string } | { ok: false; reason: string }>;
  cancel(): void;
  dispose(): void;
}

/** The part of `Worker` the client uses (a loopback in the tests, a real `Worker` in the product). */
export interface WorkerLike {
  postMessage(msg: InMsg, transfer?: Transferable[]): void;
  terminate(): void;
  onmessage: ((e: { data: OutMsg }) => void) | null;
  onerror: ((e: { message?: string }) => void) | null;
}

interface Pending {
  resolve: (v: any) => void;
  reject: (e: Error) => void;
  onProgress?: (p: Progress) => void;
  isRun: boolean;
}

function fromError(name: string, message: string): Error {
  if (name === 'NotLive') {
    const m = /^method (\S+) is not live/.exec(message);
    const e = new NotLive(m ? m[1] : 'unknown');
    return e;
  }
  if (name === 'AbortError') return new AbortError(message);
  const e = new Error(message);
  e.name = name;
  return e;
}

/** A client over a worker made by `factory` (default: the engine worker, bundled by Vite from `worker.ts`). */
export function createEngineClient(factory: () => WorkerLike = defaultWorker): EngineClient {
  const worker = factory();
  const pending = new Map<number, Pending>();
  let next = 1;
  let currentRun = 0;
  let disposed = false;

  worker.onmessage = (e): void => {
    const m = e.data;
    const p = pending.get(m.id);
    if (!p) return;
    if (m.type === 'progress') {
      p.onProgress?.(m.p);
      return;
    }
    pending.delete(m.id);
    if (m.type === 'result') p.resolve(m.result);
    else if (m.type === 'value') p.resolve(m.value);
    else if (m.type === 'cancelled') p.reject(new AbortError());
    else p.reject(fromError(m.name, m.message));
  };
  worker.onerror = (e): void => {
    for (const [id, p] of pending) {
      pending.delete(id);
      p.reject(new Error(`the engine worker failed: ${e.message ?? 'unknown error'}`));
    }
  };

  const call = <T>(msg: (id: number) => InMsg, transfer?: Transferable[]): Promise<T> => {
    if (disposed) return Promise.reject(new AbortError('the engine client was disposed'));
    const id = next++;
    return new Promise<T>((resolve, reject) => {
      pending.set(id, { resolve, reject, isRun: false });
      worker.postMessage(msg(id), transfer);
    });
  };

  const abortRun = (): void => {
    const p = pending.get(currentRun);
    if (p && p.isRun) {
      pending.delete(currentRun);
      p.reject(new AbortError());
    }
    currentRun = 0;
  };

  return {
    liveMethods: () => [...LIVE_METHODS],
    run(req, onProgress) {
      if (disposed) return Promise.reject(new AbortError('the engine client was disposed'));
      abortRun(); // a new run cancels the previous one (the worker cancels it too on receiving the run)
      const id = next++;
      currentRun = id;
      const o = req.options ?? {};
      const options: RunOptions = { iterations: o.iterations, device: o.device, backend: o.backend, trapPhases: o.trapPhases, traps: o.traps as TrapEdit[] | undefined, extra: o.extra };
      return new Promise<RunResult>((resolve, reject) => {
        pending.set(id, { resolve, reject, onProgress, isRun: true });
        worker.postMessage({ op: 'run', id, case: req.params as ParamsLike, method: req.method, options });
      });
    },
    particle: (req) => call((id) => ({ op: 'particle', id, req: { ...req, params: req.params, trapId: req.params?.dynamics?.trap_id, setup: req.setup ? { ...req.setup } : undefined } as never })),
    axialCut: (req) => call((id) => ({ op: 'axial', id, phase: req.phase, params: req.params as ParamsLike, trapId: req.trapId, nz: req.nz })),
    gpu: () => call((id) => ({ op: 'gpu', id })),
    cancel() {
      if (!currentRun) return;
      worker.postMessage({ op: 'cancel' });
      abortRun();
    },
    dispose() {
      disposed = true;
      for (const [id, p] of pending) {
        pending.delete(id);
        p.reject(new AbortError('the engine client was disposed'));
      }
      worker.terminate();
    },
  };
}

function defaultWorker(): WorkerLike {
  return new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' }) as unknown as WorkerLike;
}
