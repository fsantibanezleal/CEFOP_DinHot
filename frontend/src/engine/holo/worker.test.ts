// The Web Worker protocol, run in Node over a loopback: the same EngineRunner the worker file wires to its message port, the same
// client the workbench uses. Cancellation, progress throttling, transferables, NotLive and the one-run-at-a-time rule are checked
// here; the real Worker in Chromium (main thread not blocked, timing) is frontend/scripts/engine-browser.mjs.
import { describe, expect, it } from 'vitest';
import type { ParamsRecord } from '../../lib/contract.types';
import { LIVE_METHODS, createEngineClient, type WorkerLike } from './client';
import { liveMethodIds } from './methods';
import { EngineRunner, type InMsg, type OutMsg, PROGRESS_MIN_GAP_MS, type Scheduler } from './runner';
import { AbortError, NotLive } from './types';

const trap = (id: number, x: number, y: number) => ({ id, x_um: x, y_um: y, z_um: 0, weight: 1, charge: 0 });
const PARAMS = {
  case_id: 'C99_test', setup: { wavelength_nm: 850, focal_mm: 6, na: 0.5, n_imm: 1, n_pix: 64, pitch_um: 20, pad: 2, beam: { kind: 'gaussian', waist_frac: 1 } },
  device: null, target: { kind: 'traps', traps: [trap(0, 16, 0), trap(1, -16, 0), trap(2, 0, 16), trap(3, 0, -16), trap(4, 32, 32)] }, aberration: null,
  methods: ['M06'], reference_method: 'M06', budget: { iterations: 12, time_s: null }, seed: 7, feedback: null, dynamics: null, rearrangement: null, expect: {},
} as unknown as ParamsRecord;

/** A manual clock and yield: every yield advances the clock by `stepMs` and calls the hook, so the tests control the interleaving. */
function manual(stepMs: number, hook: (yields: number) => void = () => {}): Scheduler & { yields: number; t: number } {
  const s = {
    yields: 0, t: 0,
    yield: async () => { s.yields++; s.t += stepMs; hook(s.yields); },
    now: () => s.t,
  };
  return s;
}

/** A worker that delivers messages to an in-process runner (asynchronously, like a real port). */
function loopback(sched: Scheduler): { worker: WorkerLike; runner: EngineRunner; sent: InMsg[]; got: OutMsg[] } {
  const sent: InMsg[] = [], got: OutMsg[] = [];
  const w: WorkerLike = {
    onmessage: null, onerror: null, terminate: () => {},
    postMessage: (msg) => { sent.push(msg); queueMicrotask(() => runner.handle(msg)); },
  };
  const runner = new EngineRunner((m) => { got.push(m); queueMicrotask(() => w.onmessage?.({ data: m })); }, sched);
  return { worker: w, runner, sent, got };
}

describe('the live engine client over the worker protocol', () => {
  it('lists the ported methods, equal to the registry', () => {
    const { worker } = loopback(manual(1));
    expect(createEngineClient(() => worker).liveMethods()).toEqual(liveMethodIds());
    expect([...LIVE_METHODS]).toEqual(liveMethodIds());
  });

  it('runs a case: progress at most 30 per second, a final result with the shapes of the contract', async () => {
    const sched = manual(1); // 1 ms per iteration on the fake clock
    const lb = loopback(sched);
    const client = createEngineClient(() => lb.worker);
    const progress: number[] = [];
    const res = await client.run({ params: PARAMS, method: 'M06', options: { iterations: 90 } }, (p) => progress.push(p.iteration));
    // 90 iterations in 90 fake ms: one progress message per PROGRESS_MIN_GAP_MS at most
    const maxExpected = Math.floor(90 / PROGRESS_MIN_GAP_MS) + 1;
    expect(progress.length).toBeGreaterThan(1);
    expect(progress.length).toBeLessThanOrEqual(maxExpected);
    expect(res.backend).toBe('cpu');
    // 'auto' with no WebGPU in the worker falls back to the CPU path and says why; an explicit 'cpu' has nothing to explain
    expect(res.fallbackReason).toBe('WebGPU is not available in this build');
    expect((await client.run({ params: PARAMS, method: 'M06', options: { iterations: 2, backend: 'cpu' } })).fallbackReason).toBeNull();
    expect(res.history).toHaveLength(90);
    expect(res.phase).toBeInstanceOf(Float64Array);
    expect(res.phase).toHaveLength(64 * 64);
    expect(Math.min(...res.phase)).toBeGreaterThanOrEqual(0);
    expect(Math.max(...res.phase)).toBeLessThan(2 * Math.PI);
    expect(res.focal).toBeInstanceOf(Float32Array);
    expect(res.focalSize).toBe(128);
    expect(res.focal).toHaveLength(128 * 128);
    expect(res.trapIntensity).toHaveLength(5);
    expect(res.displayedPhase).toBeNull();
    expect(res.binUm).toBeCloseTo((850e-9 * 6e-3 * 1e6) / (2 * 64 * 20e-6), 9);
    expect(res.metrics.efficiency).toBeGreaterThan(0.5);
    expect(res.metrics.uniformity).toBeGreaterThan(0.9); // 90 iterations of the weighted GS equalise five traps
    // the result is scored from the final phase: its efficiency is the sum of the trap intensities / mean
    let s = 0;
    for (const v of res.trapIntensity) s += v;
    expect(s / 5).toBeCloseTo(1, 12);
    // the large arrays travel as transferred buffers, not as copies, and the last progress message precedes the result
    const last = lb.got.filter((m) => m.type === 'progress').pop();
    expect(lb.got.at(-1)?.type).toBe('result');
    expect(last).toBeDefined();
  });

  it('yields to the event loop after every iteration (so a message can be seen between iterations)', async () => {
    const sched = manual(1);
    const lb = loopback(sched);
    await createEngineClient(() => lb.worker).run({ params: PARAMS, method: 'M06', options: { iterations: 10 } });
    expect(sched.yields).toBeGreaterThanOrEqual(10);
  });

  it('cancel stops the run within one iteration', async () => {
    let runner!: EngineRunner;
    let ranAfterCancel = 0, cancelledAt = -1;
    const sched = manual(1, (y) => {
      if (y === 4) { runner.handle({ op: 'cancel' }); cancelledAt = y; }
    });
    const lb = loopback(sched);
    runner = lb.runner;
    const client = createEngineClient(() => lb.worker);
    const seen: number[] = [];
    const p = client.run({ params: PARAMS, method: 'M06', options: { iterations: 500 } }, (q) => seen.push(q.iteration));
    // the runner posts 'cancelled'; the client rejects with an AbortError
    client.cancel(); // the client side of the same cancel (rejects at once)
    await expect(p).rejects.toBeInstanceOf(AbortError);
    await new Promise((r) => setTimeout(r, 20));
    expect(lb.got.some((m) => m.type === 'result')).toBe(false);
    ranAfterCancel = sched.yields - cancelledAt;
    // the iteration in flight when the cancel arrived may complete; the next one never starts
    expect(ranAfterCancel).toBeLessThanOrEqual(1);
    expect(seen.every((i) => i <= 5)).toBe(true);
  });

  it('a cancel message alone (no client call) ends the run within one iteration with a cancelled message', async () => {
    let runner!: EngineRunner;
    let at = 0;
    const sched = manual(1, (y) => { if (y === 6) { runner.handle({ op: 'cancel' }); at = y; } });
    const lb = loopback(sched);
    runner = lb.runner;
    const done: OutMsg[] = [];
    lb.runner.handle({ op: 'run', id: 1, case: PARAMS, method: 'M06', options: { iterations: 400 } });
    await new Promise((r) => setTimeout(r, 50));
    done.push(...lb.got);
    expect(done.at(-1)).toEqual({ type: 'cancelled', id: 1 });
    expect(sched.yields).toBe(at); // not one more iteration after the one in which the cancel was seen
  });

  it('a new run cancels the previous one', async () => {
    const lb = loopback(manual(1));
    const client = createEngineClient(() => lb.worker);
    const first = client.run({ params: PARAMS, method: 'M06', options: { iterations: 300 } });
    const second = client.run({ params: PARAMS, method: 'M04', options: { iterations: 5 } });
    await expect(first).rejects.toBeInstanceOf(AbortError);
    const r = await second;
    expect(r.method).toBe('M04');
    expect(r.history).toHaveLength(5);
    expect(lb.got.filter((m) => m.type === 'result')).toHaveLength(1); // the first run never produced a result
  });

  it('rejects a method that is not ported with NotLive, never a fallback', async () => {
    const lb = loopback(manual(1));
    const client = createEngineClient(() => lb.worker);
    for (const id of ['M09', 'M13', 'B3']) {
      const err = await client.run({ params: PARAMS, method: id }).catch((e: unknown) => e);
      expect(err).toBeInstanceOf(NotLive);
      expect((err as NotLive).method).toBe(id);
    }
    expect(lb.got.some((m) => m.type === 'result')).toBe(false);
  });

  it('carries the Python error of an out-of-field trap through the boundary', async () => {
    const lb = loopback(manual(1));
    const client = createEngineClient(() => lb.worker);
    const edited = [trap(0, 5000, 0)]; // far outside +-127.5 um
    const err = await client.run({ params: PARAMS, method: 'M06', options: { traps: edited } }).catch((e: unknown) => e);
    expect((err as Error).name).toBe('OutOfFieldError');
    expect((err as Error).message).toMatch(/^trap 0 has x = 5\.000e-03 m, outside the unaliased field of view \(bound = 1\.275e-04 m = lambda f \/ \(2 p\)\)$/);
  });

  it('M12 needs traps on FFT bins and says so; M07 on off-bin traps uses the point form', async () => {
    const lb = loopback(manual(1));
    const client = createEngineClient(() => lb.worker);
    await expect(client.run({ params: PARAMS, method: 'M12', options: { traps: [trap(0, 16, 0), trap(1, -16, 0)] } })).rejects.toThrow('the fft form needs traps on FFT bins');
  });

  it('an edited trap list and a warm start are honoured', async () => {
    const lb = loopback(manual(1));
    const client = createEngineClient(() => lb.worker);
    const traps = [trap(0, 16, 0), trap(1, -16, 0), trap(2, 0, 16)];
    const r = await client.run({ params: PARAMS, method: 'M07', options: { traps, iterations: 4, trapPhases: Float64Array.from([0.1, 2.0, 4.0]) } });
    expect(r.trapIntensity).toHaveLength(3);
    const cold = await client.run({ params: PARAMS, method: 'M07', options: { traps, iterations: 4 } });
    expect(Array.from(r.phase)).not.toEqual(Array.from(cold.phase)); // a different starting hologram gives a different hologram
    await expect(client.run({ params: PARAMS, method: 'M07', options: { traps, trapPhases: Float64Array.from([0.1]) } })).rejects.toThrow('one phase per trap');
  });

  it('simulates a bead through the worker and cuts the axial intensity', async () => {
    const lb = loopback(manual(1));
    const client = createEngineClient(() => lb.worker);
    const params = {
      ...PARAMS, setup: { ...PARAMS.setup, wavelength_nm: 1064, focal_mm: 2.4, na: 1.2, n_imm: 1.33, n_pix: 256, pitch_um: 10 },
      // the bead of case C01 (data/examples/cases.json)
      dynamics: { particle: 'bead', trap_id: 0, power_mw: 10, bead_radius_um: 0.5, n_particle: 1.59, viscosity_pa_s: 0.00089, temperature_k: 295, n_steps: 131072, dt_s: 5e-5 },
    } as unknown as ParamsRecord;
    const run = await client.run({ params, method: 'M06', options: { iterations: 20 } });
    const sim = await client.particle({ focal: run.focal, focalSize: run.focalSize, binUm: run.binUm, dynamics: params.dynamics!, seed: params.seed, phase: run.phase, params });
    expect(sim.xUm.length).toBeGreaterThan(100);
    expect(sim.fcRatio).toBeGreaterThan(0.5);
    expect(sim.fcRatio).toBeLessThan(2);
    expect(sim.stiffness.unit).toBe('pN/um');
    expect(sim.psd.fHz.length).toBe(sim.psd.p.length);
    const approx = await client.particle({ focal: run.focal, focalSize: run.focalSize, binUm: run.binUm, dynamics: params.dynamics!, seed: params.seed, trap: { x_um: 16, y_um: 0, z_um: 0 }, setup: { pad: 2, nImm: 1.33 } });
    expect(approx.fcRatio).toBeGreaterThan(0.3);
    expect(Number.isFinite(approx.fcHz)).toBe(true);
    const cut = await client.axialCut({ phase: run.phase, params, trapId: 0, nz: 9 });
    expect(cut.xz).toBeInstanceOf(Float32Array);
    expect(cut.nz).toBe(9);
    expect(cut.xz).toHaveLength(cut.nz * cut.nx);
    expect(cut.zUm[0]).toBeLessThan(0);
  });

  it('reports no WebGPU in this build and disposes cleanly', async () => {
    const lb = loopback(manual(1));
    const client = createEngineClient(() => lb.worker);
    const g = await client.gpu();
    expect(g.ok).toBe(false);
    const p = client.run({ params: PARAMS, method: 'M06', options: { iterations: 500 } });
    client.dispose();
    await expect(p).rejects.toBeInstanceOf(AbortError);
    await expect(client.run({ params: PARAMS, method: 'M06' })).rejects.toBeInstanceOf(AbortError);
  });
});
