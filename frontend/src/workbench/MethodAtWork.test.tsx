// V5, the method at work (ADR-0082, SDD catalog row V5): the spread and the efficiency per iteration with the phase-freeze iteration
// marked, coupled to the focal plane and the per-trap intensities at the scrubbed iteration. The focal plane at iteration k is the engine's
// run with the method's budget set to k; here the engine runs in Node behind the same client and loopback the worker tests use.
import { formatNumber, LinkedViewProvider } from '@fasl-work/caos-app-shell';
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createEngineClient, type EngineClient, type RunResult, type WorkerLike } from '../engine/holo/client';
import { EngineRunner, type InMsg, type OutMsg } from '../engine/holo/runner';
import { PHASE_FREEZE, focalAtIteration, freezeIteration, methodCallouts, MethodAtWorkView, pointAt, runRequestAt, spreadText } from './MethodAtWork';
import { realCase } from './test-real';
import { selectionFor } from './test-data';

vi.stubGlobal('__APP_VERSION__', 'test-version');

const sel = (id = 'C02_grid_feedback', over = {}) => selectionFor(realCase(id), over);

/** The engine behind its message protocol, in-process: the client of the product over a runner that answers on the next tick. */
function realClient(): EngineClient {
  const w: WorkerLike = {
    onmessage: null,
    onerror: null,
    terminate: () => undefined,
    postMessage: (msg: InMsg) => queueMicrotask(() => runner.handle(msg)),
  };
  const runner = new EngineRunner((m: OutMsg) => queueMicrotask(() => w.onmessage?.({ data: m })));
  return createEngineClient(() => w);
}

describe('the iteration the cursor stands on', () => {
  const h = realCase('C02_grid_feedback').trace.methods.M07.history.map((p) => ({ iteration: p.iteration, efficiency: p.efficiency, uniformity: p.uniformity, relStdPct: p.rel_std_pct }));
  it('is the last iteration when the cursor is unset or past the run, and the last one at or before it otherwise', () => {
    expect(pointAt(h, null)?.iteration).toBe(h.length);
    expect(pointAt(h, 999)?.iteration).toBe(h.length);
    expect(pointAt(h, 7)?.iteration).toBe(7);
    expect(pointAt(h, 7.6)?.iteration).toBe(7);
    expect(pointAt(h, -3)?.iteration).toBe(1);
    expect(pointAt([], 3)).toBeNull();
  });
});

describe('the phase-freeze iteration', () => {
  it('is the n_fix of M07 in the engine, 12 by default; the other methods never freeze', () => {
    const baseline = readFileSync(new URL('../engine/holo/methods/baseline.ts', import.meta.url), 'utf8');
    expect(baseline).toContain(`const nFix = o.nFix ?? ${PHASE_FREEZE.M07};`);
    expect(freezeIteration('M07')).toBe(12);
    expect(freezeIteration('M06')).toBeNull();
    expect(freezeIteration('B1')).toBeNull();
  });
});

describe('the focal plane at a scrubbed iteration', () => {
  it('asks the engine for the method with its budget set to k, at the rail device', () => {
    const s = sel('C08_device_limited', { methodId: 'M07' });
    const r = runRequestAt(s, 9);
    expect(r.method).toBe('M07');
    expect(r.options.iterations).toBe(9);
    expect(r.options.device).toBe('case');
    expect(r.params.case_id).toBe('C08_device_limited');
  });

  it('is redrawn: a different iteration returns a different focal plane and different per-trap intensities, with the time it took', async () => {
    const calls: number[] = [];
    const fake = {
      run: async (req: { options?: { iterations?: number } }) => {
        const k = req.options?.iterations ?? 0;
        calls.push(k);
        const size = realCase('C02_grid_feedback').trace.reference.focal.size;
        const focal = new Float32Array(size * size).map((_, i) => 1 + ((i * k) % 7));
        return { method: 'M07', backend: 'cpu', fallbackReason: null, nPix: 4, pad: 2, binUm: realCase('C02_grid_feedback').trace.grid.bin_um, halfFieldUm: 4, phase: new Float64Array(16), displayedPhase: null, focal, focalSize: size, trapIntensity: Float64Array.from({ length: 100 }, (_, i) => 1 + (i % 3) * k * 0.01), history: [], metrics: { efficiency: 0.5, uniformity: 0.9, relStdPct: 10 / k, zeroOrder: 0, ghost: 0 }, timeMs: 1, timing: { methodMs: 1, scoreMs: 0, yieldMs: 0 } } as RunResult;
      },
    };
    let t = 0;
    const clock = () => (t += 5);
    const a = await focalAtIteration(fake, sel(), 3, clock);
    const b = await focalAtIteration(fake, sel(), 12, clock);
    expect(calls).toEqual([3, 12]);
    expect(a.k).toBe(3);
    expect(b.k).toBe(12);
    expect(a.ms).toBe(5);
    expect(a.maps.focal?.db).not.toEqual(b.maps.focal?.db);
    expect(a.result.trapI).not.toEqual(b.result.trapI);
    expect(a.maps.lane).toBe('live');
    expect(a.result.method).toBe('M07');
  });

  it('with the real engine on C02: the map and the spread change with the iteration and the spread falls as the trace records it', async () => {
    const client = realClient();
    const s = sel();
    const t0 = performance.now();
    const early = await focalAtIteration(client, s, 1);
    const mid = await focalAtIteration(client, s, 12);
    const end = await focalAtIteration(client, s, 30);
    const seconds = (performance.now() - t0) / 1000;
    expect(early.maps.focal?.db).not.toEqual(end.maps.focal?.db);
    expect(early.result.metrics!.relStdPct).toBeGreaterThan(mid.result.metrics!.relStdPct);
    expect(mid.result.metrics!.relStdPct).toBeGreaterThan(end.result.metrics!.relStdPct);
    // the engine's spread at the end of the budget is the trace's final spread to its tolerance (parity with the Python engine)
    const finalSpread = realCase('C02_grid_feedback').trace.methods.M07.final.rel_std_pct;
    expect(end.result.metrics!.relStdPct).toBeLessThan(finalSpread + 0.05);
    expect(end.result.trapI).toHaveLength(100);
    // per-trap intensities are I_m over the mean: the spread of the list is the spread the metric reports
    const trapI = end.result.trapI!;
    const mean = trapI.reduce((x, y) => x + y, 0) / trapI.length;
    const rms = Math.sqrt(trapI.reduce((x, y) => x + (y - mean) ** 2, 0) / trapI.length);
    expect((100 * rms) / mean).toBeCloseTo(end.result.metrics!.relStdPct, 3);
    const fmt = (v: number, decimals: number) => formatNumber(v, 'en', { decimals });
    console.log(`V5 timing (Node, CPU): k=1 ${fmt(early.ms, 0)} ms, k=12 ${fmt(mid.ms, 0)} ms, k=30 ${fmt(end.ms, 0)} ms; three runs ${fmt(seconds, 2)} s`);
    client.dispose();
  }, 120000);

  it('C08: the ideal-device spread of the trace history is what the engine reports for the same method on the ideal device', async () => {
    const client = realClient();
    const c = realCase('C08_device_limited');
    const s = selectionFor(c, { methodId: 'M07', device: 'ideal', deviceModel: null, runParams: { ...selectionFor(c).runParams, device: null } });
    const r = await focalAtIteration(client, s, 30);
    const h = c.trace.methods.M07.history;
    const last = h[h.length - 1];
    expect(r.result.metrics!.efficiency).toBeCloseTo(last.efficiency, 2);
    expect(r.result.metrics!.relStdPct).toBeLessThan(0.1);
    expect(last.rel_std_pct).toBeLessThan(0.1);
    client.dispose();
  }, 120000);
});

describe('the callouts and the number format', () => {
  it('print a spread of any size with two significant figures', () => {
    expect(spreadText(26.7653, 'en')).toBe('26.8');
    expect(spreadText(0.0138, 'en')).toBe('0.014');
    expect(spreadText(0.0045, 'en')).toBe('0.0045');
    expect(spreadText(1.4786, 'es')).toBe('1,48');
    expect(spreadText(0, 'en')).toBe('0.00');
  });

  it('are three, with a unit, a state and a source naming the trace field, and name the method', () => {
    const items = methodCallouts(sel(), 5, 'es');
    expect(items.map((i) => i.id)).toEqual(['spread', 'efficiency', 'freeze']);
    for (const i of items) {
      expect(i.unit).toBeTruthy();
      expect(JSON.stringify(i.source)).toMatch(/Phase-fixed weighted GS|n_fix/);
    }
    expect(JSON.stringify(items[0].source)).toContain('GS ponderado con fase fija');
  });
});

describe('the view', () => {
  const render = (reduced: boolean) => {
    vi.stubGlobal('matchMedia', (q: string) => ({ matches: reduced && q.includes('reduce'), media: q, addEventListener: () => undefined, removeEventListener: () => undefined }));
    return renderToStaticMarkup(
      <LinkedViewProvider>
        <MethodAtWorkView sel={sel()} />
      </LinkedViewProvider>,
    );
  };
  afterEach(() => vi.unstubAllGlobals());

  it('offers the play control that can pause, with a slider for the iteration, when motion is allowed', () => {
    const html = render(false);
    expect(html).toContain('Play the iterations');
    expect(html).toContain('data-linked-cursor');
    expect(html).toContain('type="range"');
    expect(html).toContain('Phase-fixed weighted GS');
  });

  it('plays nothing under reduced motion: the slider remains and the reason is stated', () => {
    const html = render(true);
    expect(html).not.toContain('Play the iterations');
    expect(html).toContain('Reduced motion: the iterations do not play');
    expect(html).toContain('type="range"');
  });

  it('says so when the bake holds no history for the method', () => {
    const s = sel('C02_grid_feedback', { result: { lane: 'replay', method: 'M07', metrics: null, history: [], trapI: null } });
    const html = renderToStaticMarkup(
      <LinkedViewProvider>
        <MethodAtWorkView sel={s} />
      </LinkedViewProvider>,
    );
    expect(html).toContain('no iteration history');
  });
});
