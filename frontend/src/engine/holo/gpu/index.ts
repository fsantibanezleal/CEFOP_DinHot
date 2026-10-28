/**
 * The optional WebGPU backend: run-time detection in the worker, eligibility of a run, and the GPU weighted-GS loop
 * (`wgs.ts`). Anything that is not eligible, absent or failing returns a reason; the runner then takes the CPU path and records the
 * reason in `RunResult.fallbackReason` (ADR-0069 A69.7: parity, latency, memory and fallback gates).
 */
import { setupOf, targetOf, type ParamsLike } from '../engine';
import { srStart } from '../methods/common';
import type { GpuBackend, RunOptions } from '../runner';
import { Rng } from '../rng';
import { makeBudget } from '../types';
import { type GpuMode, gpuIneligible, openGpu, runWgsGpu } from './wgs';

const MODES: Record<string, GpuMode> = { M04: 'gs', M06: 'gsw', M07: 'wgsFixed' };

export function createGpuBackend(): GpuBackend {
  return {
    async probe() {
      const o = await openGpu();
      return 'reason' in o ? { ok: false, reason: o.reason } : { ok: true, adapter: o.adapter };
    },
    start(p: ParamsLike, method: string, o: RunOptions, init: Float64Array | null) {
      const mode = MODES[method];
      if (!mode) return { reason: `method ${method} has no WebGPU path (the FFT-form iterations M04, M06 and M07 do)` };
      if (p.target.kind !== 'traps' && !o.traps) return { reason: 'a shaped-field target has no WebGPU path' };
      if ((o.device ?? 'case') === 'case' && p.device) return { reason: 'the case device model (quantization, crosstalk) is evaluated on the CPU path only' };
      const setup = setupOf(p);
      const target = targetOf(p, o.traps);
      if (target.kind !== 'traps') return { reason: 'a shaped-field target has no WebGPU path' };
      const traps = target.traps;
      const why = gpuIneligible(setup, traps);
      if (why) return { reason: `not eligible for the WebGPU path: ${why}` };
      const nFix = typeof o.extra?.nFix === 'number' ? o.extra.nFix : 12;
      const budget = makeBudget(o.iterations ?? p.budget.iterations, p.budget.time_s);
      const start = init ?? srStart(setup, traps, new Rng(p.seed));
      async function* gen() {
        const g = await openGpu();
        if ('reason' in g) throw new Error(g.reason);
        return yield* runWgsGpu(g, method, setup, traps, mode, budget, start, nFix);
      }
      return { gen: gen() };
    },
  };
}
