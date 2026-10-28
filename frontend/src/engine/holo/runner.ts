/**
 * The message protocol of the live engine and the runner behind the Web Worker (`worker.ts`).
 *
 * The runner is plain TypeScript with an injected `post` function and an injected scheduler, so the same code runs inside a
 * dedicated worker (the product), in Node (the tests) and behind a loopback (the client tests). A run is a method generator:
 * the runner steps it one iteration at a time and yields to the event loop after every iteration, which is what lets a
 * `cancel` message stop it within one iteration and keeps the page's main thread free (the compute is in the worker).
 *
 * Messages (main to worker): `{op:'run', id, case, method, options}`, `{op:'cancel'}`, `{op:'particle', id, ...}`,
 * `{op:'axial', id, ...}`, `{op:'methods', id}`, `{op:'gpu', id}` (capability probe).
 * Worker to main: `{type:'progress', id, p}` (at most 30 per second), `{type:'result', id, result}` with transferable buffers,
 * `{type:'cancelled', id}`, `{type:'error', id, name, message}`, `{type:'value', id, value}`.
 */
import { type CaseOptions, type CaseResult, type ParamsLike, type Progress, axialCutOf, buildRun, finishRun, progressOf, setupOf, simulateParticle } from './engine';
import { liveMethodIds } from './methods';
import { AbortError, type HistoryEntry, type MethodRun, type Result } from './types';

export type Backend = 'auto' | 'cpu' | 'gpu';

/** What the client sends for a run (the `options` of the public `RunRequest`, minus the transferables handled by structured clone). */
export interface RunOptions extends CaseOptions {
  backend?: Backend;
}

export interface RunResultMsg extends CaseResult {
  backend: 'cpu' | 'gpu';
  fallbackReason: string | null;
  timeMs: number;
  /** Where the time went, in ms: the method iterations (including the yields between them) and the scoring from the final phase. */
  timing: { methodMs: number; scoreMs: number; yieldMs: number };
}

export type InMsg =
  | { op: 'run'; id: number; case: ParamsLike; method: string; options?: RunOptions }
  | { op: 'cancel'; id?: number }
  | { op: 'particle'; id: number; req: Parameters<typeof simulateParticle>[0] & { params?: ParamsLike; trapId?: number } }
  | { op: 'axial'; id: number; phase: Float64Array; params: ParamsLike; trapId: number; nz: number }
  | { op: 'methods'; id: number }
  | { op: 'gpu'; id: number };

export type OutMsg =
  | { type: 'progress'; id: number; p: Progress }
  | { type: 'result'; id: number; result: RunResultMsg }
  | { type: 'cancelled'; id: number }
  | { type: 'error'; id: number; name: string; message: string }
  | { type: 'value'; id: number; value: unknown };

/** A GPU implementation of the FFT-form iterations: `null` when it cannot take the run, with the reason. */
export interface GpuBackend {
  /** Run-time detection: `{ok:false, reason}` when WebGPU is absent or fails. */
  probe(): Promise<{ ok: true; adapter: string } | { ok: false; reason: string }>;
  /** A GPU run of the method on the case, or a reason why this run is not eligible. */
  start(p: ParamsLike, method: string, o: RunOptions, init: Float64Array | null): { gen: AsyncGenerator<HistoryEntry, Result> } | { reason: string };
}

export interface Scheduler {
  /** Let the event loop run (and so deliver a pending `cancel`). */
  yield(): Promise<void>;
  now(): number;
}

/** A scheduler on `MessageChannel` (no 4 ms timer clamp), falling back to `setTimeout`. */
export function defaultScheduler(): Scheduler {
  const now = (): number => performance.now();
  if (typeof MessageChannel === 'undefined') return { yield: () => new Promise<void>((r) => setTimeout(r, 0)), now };
  const ch = new MessageChannel();
  const waiting: (() => void)[] = [];
  ch.port1.onmessage = (): void => waiting.shift()?.();
  return {
    yield: () => new Promise<void>((r) => { waiting.push(r); ch.port2.postMessage(0); }),
    now,
  };
}

/** Minimum gap between two progress messages: at most 30 per second. */
export const PROGRESS_MIN_GAP_MS = 1000 / 30;

interface Token {
  id: number;
  cancelled: boolean;
}

export class EngineRunner {
  private current: Token | null = null;
  private yieldMs = 0;

  constructor(
    private readonly post: (msg: OutMsg, transfer?: Transferable[]) => void,
    private readonly sched: Scheduler = defaultScheduler(),
    private readonly gpu: GpuBackend | null = null,
  ) {}

  /** Entry point for one message from the main thread; never throws (an error becomes an `error` message). */
  handle(msg: InMsg): void {
    switch (msg.op) {
      case 'cancel':
        this.cancelCurrent();
        break;
      case 'run':
        this.cancelCurrent(); // a new run cancels the previous one
        void this.run(msg);
        break;
      case 'methods':
        this.post({ type: 'value', id: msg.id, value: liveMethodIds() });
        break;
      case 'gpu':
        void (this.gpu ? this.gpu.probe() : Promise.resolve({ ok: false as const, reason: 'no WebGPU backend in this build' })).then(
          (value) => this.post({ type: 'value', id: msg.id, value }),
          (e: unknown) => this.post({ type: 'value', id: msg.id, value: { ok: false, reason: String(e) } }),
        );
        break;
      case 'particle':
        this.value(msg.id, () => {
          const r = msg.req;
          const trap = r.params && r.trapId !== undefined ? (r.params.target as { traps: { id: number; x_um: number; y_um: number; z_um: number }[] }).traps.find((t) => t.id === r.trapId) : r.trap;
          const setup = r.params ? setupOf(r.params) : r.setup;
          return simulateParticle({ ...r, trap, setup });
        });
        break;
      case 'axial':
        this.value(msg.id, () => axialCutOf(msg.params, msg.phase, msg.trapId, msg.nz));
        break;
    }
  }

  /** Cancel the run in flight (its promise rejects with an `AbortError` on the client). */
  cancelCurrent(): void {
    if (this.current) this.current.cancelled = true;
  }

  private value(id: number, f: () => unknown): void {
    try {
      const v = f();
      const transfer: Transferable[] = [];
      collectBuffers(v, transfer);
      this.post({ type: 'value', id, value: v }, transfer);
    } catch (e) {
      this.fail(id, e);
    }
  }

  private fail(id: number, e: unknown): void {
    const err = e instanceof Error ? e : new Error(String(e));
    this.post({ type: 'error', id, name: err.name, message: err.message });
  }

  private async run(msg: Extract<InMsg, { op: 'run' }>): Promise<void> {
    const token: Token = { id: msg.id, cancelled: false };
    this.current = token;
    this.yieldMs = 0;
    const o = msg.options ?? {};
    const t0 = this.sched.now();
    try {
      const warm = o.trapPhases ?? null;
      let backend: 'cpu' | 'gpu' = 'cpu';
      let reason: string | null = null;
      const want = o.backend ?? 'auto';
      let result: Result | null = null;
      if (want !== 'cpu') {
        const g = await this.tryGpu(msg, warm, token, t0);
        if ('result' in g) {
          result = g.result;
          backend = 'gpu';
        } else reason = g.reason;
        if (token.cancelled) throw new AbortError();
      }
      if (!result) result = await this.runCpu(msg, warm, token, t0);
      if (token.cancelled) throw new AbortError();
      const t1 = this.sched.now();
      const done = finishRun(msg.case, msg.method, result, o);
      const t2 = this.sched.now();
      const out: RunResultMsg = { ...done, backend, fallbackReason: want === 'cpu' ? null : reason, timeMs: t2 - t0, timing: { methodMs: t1 - t0, scoreMs: t2 - t1, yieldMs: this.yieldMs } };
      const transfer: Transferable[] = [];
      collectBuffers(out, transfer);
      if (this.current === token) this.current = null;
      this.post({ type: 'result', id: msg.id, result: out }, transfer);
    } catch (e) {
      if (this.current === token) this.current = null;
      if (e instanceof AbortError || token.cancelled) this.post({ type: 'cancelled', id: msg.id });
      else this.fail(msg.id, e);
    }
  }

  private progress(token: Token, entry: HistoryEntry, state: { last: number }, force = false): void {
    if (entry.phase !== undefined) return; // a warm-up step of a method (not an iteration of the budget)
    const t = this.sched.now();
    if (!force && t - state.last < PROGRESS_MIN_GAP_MS) return;
    state.last = t;
    this.post({ type: 'progress', id: token.id, p: progressOf(entry) });
  }

  private async runCpu(msg: Extract<InMsg, { op: 'run' }>, warm: Float64Array | null, token: Token, t0: number): Promise<Result> {
    const o = msg.options ?? {};
    const run = buildRun(msg.case, msg.method, o, null, warm);
    const state = { last: -Infinity };
    void t0;
    return this.drive(run.gen, token, state);
  }

  private async drive(gen: MethodRun, token: Token, state: { last: number }): Promise<Result> {
    for (;;) {
      if (token.cancelled) throw new AbortError();
      const r = gen.next();
      if (r.done) return r.value;
      this.progress(token, r.value, state);
      const y0 = this.sched.now();
      await this.sched.yield(); // after every iteration, so a cancel message is seen within one iteration
      this.yieldMs += this.sched.now() - y0;
    }
  }

  private async tryGpu(msg: Extract<InMsg, { op: 'run' }>, warm: Float64Array | null, token: Token, t0: number): Promise<{ result: Result } | { reason: string }> {
    void t0;
    if (!this.gpu) return { reason: 'WebGPU is not available in this build' };
    const probe = await this.gpu.probe();
    if (!probe.ok) return { reason: probe.reason };
    const o = msg.options ?? {};
    let init: Float64Array | null = null;
    if (warm) init = buildRun(msg.case, msg.method, o, null, warm).init;
    const started = this.gpu.start(msg.case, msg.method, o, init);
    if ('reason' in started) return { reason: started.reason };
    const state = { last: -Infinity };
    try {
      for (;;) {
        if (token.cancelled) throw new AbortError();
        const r = await started.gen.next();
        if (r.done) return { result: r.value };
        this.progress(token, r.value, state);
        await this.sched.yield();
      }
    } catch (e) {
      if (e instanceof AbortError) throw e;
      return { reason: `WebGPU run failed: ${e instanceof Error ? e.message : String(e)}` };
    } finally {
      await started.gen.return(undefined as never); // releases the GPU buffers when the run ends early
    }
  }
}

/** Collect the ArrayBuffers of typed arrays inside a result so they are transferred, not copied. */
export function collectBuffers(v: unknown, out: Transferable[], seen = new Set<ArrayBufferLike>()): void {
  if (!v || typeof v !== 'object') return;
  if (ArrayBuffer.isView(v)) {
    const b = v.buffer;
    if (b instanceof ArrayBuffer && !seen.has(b)) {
      seen.add(b);
      out.push(b);
    }
    return;
  }
  for (const k of Object.keys(v as object)) collectBuffers((v as Record<string, unknown>)[k], out, seen);
}
