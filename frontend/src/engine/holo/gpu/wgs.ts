/**
 * The WebGPU weighted-GS iteration (FFT form) for point traps on FFT bins: `gs` (M04), `gsw` (M06) and the phase-fixed `wgsFixed`
 * (M07), float32, the whole iteration on the GPU.
 *
 * Python and CPU counterparts: `methods/baseline/_gs.py` `run_traps(form='fft')` and `methods/gs.ts`. One iteration is a single
 * command buffer: `fill` (padded field `A exp(i phi)`), a Stockham radix-2 2D FFT (`wgsl.ts`), `gather` (the trap fields
 * `V_m = F[bin] ramp pad / (nPix N)`), `rule` (the WGS amplitude pass), `zero` and `scatter` (the focal deltas `c_m` at the trap
 * bins), the inverse FFT and `phase` (`phi = arg`). Only the `M` trap fields cross the bus per iteration (for the history and
 * the progress); the phase stays on the GPU until the run ends.
 *
 * Agreement: at the end the final phase is read back and the trap fields are recomputed on the CPU in float64
 * (`fftFields`); the run is rejected (and the runner falls back to the CPU path with the reason) when the intensities differ by
 * more than `AGREEMENT_TOL`. The workbench metrics are always scored from the final phase on the CPU (`engine.finishRun`), never
 * from the GPU's own numbers.
 */
import { ramp } from '../forward';
import { type Setup, focalBinM, inputAmplitude, nFft } from '../geometry';
import { efficiency, relStd, trapIntensities, uniformity } from '../metrics';
import { checkOnBins } from '../methods/gs';
import { fftFields } from '../methods/common';
import { type TrapSet, rint } from '../traps';
import type { Budget, HistoryEntry, Result } from '../types';
import { FILL, GATHER, PHASE, RULE, SCATTER, STAGE, ZERO } from './wgsl';

/** The GPU result must reproduce the float64 trap intensities within this fraction of the mean trap intensity. */
export const AGREEMENT_TOL = 2e-3;

export type GpuMode = 'gs' | 'gsw' | 'wgsFixed';
export const MODE_CODE: Record<GpuMode, number> = { gs: 0, gsw: 1, wgsFixed: 2 };

/* eslint-disable @typescript-eslint/no-explicit-any */
type Dev = any;

const USAGE = (): any => (globalThis as any).GPUBufferUsage;
const MAP_READ = (): number => (globalThis as any).GPUMapMode.READ;

interface Pipelines {
  stage: any; fill: any; zero: any; gather: any; scatter: any; rule: any; phase: any;
}
const cache = new WeakMap<object, Pipelines>();

function pipelines(dev: Dev): Pipelines {
  let p = cache.get(dev);
  if (p) return p;
  const mk = (code: string, entry: string): any => dev.createComputePipeline({ layout: 'auto', compute: { module: dev.createShaderModule({ code }), entryPoint: entry } });
  p = { stage: mk(STAGE, 'stage'), fill: mk(FILL, 'fill'), zero: mk(ZERO, 'zero'), gather: mk(GATHER, 'gather'), scatter: mk(SCATTER, 'scatter'), rule: mk(RULE, 'rule'), phase: mk(PHASE, 'phase') };
  cache.set(dev, p);
  return p;
}

export interface GpuOpen {
  device: Dev;
  adapter: string;
}

let opened: Promise<GpuOpen | { reason: string }> | null = null;

/** Run-time detection and device acquisition (cached): the reason when WebGPU is absent or fails. */
export function openGpu(): Promise<GpuOpen | { reason: string }> {
  if (opened) return opened;
  opened = (async () => {
    const nav = (globalThis as any).navigator;
    if (!nav || !nav.gpu) return { reason: 'WebGPU is not available: navigator.gpu is undefined in this context' };
    let adapter: any;
    try {
      adapter = await nav.gpu.requestAdapter();
    } catch (e) {
      return { reason: `WebGPU requestAdapter failed: ${e instanceof Error ? e.message : String(e)}` };
    }
    if (!adapter) return { reason: 'WebGPU has no adapter (requestAdapter returned null: headless shell, blocklisted GPU or no driver)' };
    try {
      const device = await adapter.requestDevice();
      const info = adapter.info ?? (adapter.requestAdapterInfo ? await adapter.requestAdapterInfo() : {});
      device.lost.then((l: any) => { opened = null; void l; });
      return { device, adapter: `${info.vendor ?? 'unknown'} ${info.architecture ?? ''} ${info.device ?? ''}`.trim() };
    } catch (e) {
      return { reason: `WebGPU requestDevice failed: ${e instanceof Error ? e.message : String(e)}` };
    }
  })();
  return opened;
}

/** Why this run cannot use the GPU path, or null. */
export function gpuIneligible(setup: Setup, traps: TrapSet): string | null {
  const m = nFft(setup);
  if (m < 2 || (m & (m - 1)) !== 0) return `the FFT size ${m} is not a power of two`;
  if (traps.length > 65535) return 'more than 65535 traps';
  try { checkOnBins(setup, traps); } catch (e) { return (e as Error).message; }
  const seen = new Set<string>();
  const b = focalBinM(setup);
  for (let i = 0; i < traps.length; i++) {
    const key = `${rint(traps.xM[i] / b)},${rint(traps.yM[i] / b)}`;
    if (seen.has(key)) return 'two traps share one FFT bin';
    seen.add(key);
  }
  return null;
}

const f32 = (a: ArrayLike<number>): Float32Array => Float32Array.from(a);

/**
 * Run the FFT-form iteration on the GPU. `init` is the starting hologram (float64, the SR start drawn through the portable RNG on
 * the CPU like the CPU path does). Yields one history entry per iteration (the entry of iteration `k` is available one pass later).
 */
export async function* runWgsGpu(
  gpu: GpuOpen, mid: string, setup: Setup, traps: TrapSet, mode: GpuMode, budget: Budget, init: Float64Array, nFix: number,
): AsyncGenerator<HistoryEntry, Result> {
  const dev = gpu.device, U = USAGE(), pl = pipelines(dev);
  const n = setup.nPix, M = nFft(setup), L = Math.round(Math.log2(M)), count = traps.length, h = Math.floor(M / 2);
  const t0 = performance.now();
  const bufs: any[] = [];
  const buf = (size: number, usage: number): any => {
    const b = dev.createBuffer({ size: Math.max(16, size), usage });
    bufs.push(b);
    return b;
  };
  const S = U.STORAGE | U.COPY_DST | U.COPY_SRC;
  const uni = (data: Uint32Array | Float32Array): any => {
    const b = buf(data.byteLength, U.UNIFORM | U.COPY_DST);
    dev.queue.writeBuffer(b, 0, data);
    return b;
  };
  try {
    // constants per trap
    const { iy, ix } = ((): { iy: number[]; ix: number[] } => {
      const b = focalBinM(setup);
      return { iy: Array.from(traps.yM, (v) => rint(v / b) + h), ix: Array.from(traps.xM, (v) => rint(v / b) + h) };
    })();
    const r = ramp(setup);
    const idx = new Uint32Array(count), gm = new Float32Array(2 * count), rc = new Float32Array(2 * count);
    for (let t = 0; t < count; t++) {
      const ky = (iy[t] - h + M) % M, kx = (ix[t] - h + M) % M;
      idx[t] = ky * M + kx;
      const pr = r.re[iy[t]] * r.re[ix[t]] - r.im[iy[t]] * r.im[ix[t]], pi = r.re[iy[t]] * r.im[ix[t]] + r.im[iy[t]] * r.re[ix[t]];
      const g = setup.pad / (n * M);
      gm[2 * t] = pr * g; gm[2 * t + 1] = pi * g;
      const c = n / setup.pad;
      rc[2 * t] = pr * c; rc[2 * t + 1] = -pi * c; // (n / pad) conj(ramp)
    }
    const a = Float64Array.from(traps.weight, Math.sqrt);
    const w0 = mode === 'gsw' ? a : new Float64Array(count).fill(1);

    const phi = buf(4 * n * n, S), ampB = buf(4 * n * n, S);
    const A = buf(8 * M * M, S), B = buf(8 * M * M, S);
    const idxB = buf(4 * count, S), gmB = buf(8 * count, S), rcB = buf(8 * count, S);
    const aB = buf(4 * count, S), wB = buf(4 * count, S), psiB = buf(4 * count, S);
    const vB = buf(8 * count, S), coefB = buf(8 * count, S);
    const vStage = buf(8 * count, U.MAP_READ | U.COPY_DST), phiStage = buf(4 * n * n, U.MAP_READ | U.COPY_DST);
    dev.queue.writeBuffer(phi, 0, f32(init));
    dev.queue.writeBuffer(ampB, 0, f32(inputAmplitude(setup)));
    dev.queue.writeBuffer(idxB, 0, idx);
    dev.queue.writeBuffer(gmB, 0, gm);
    dev.queue.writeBuffer(rcB, 0, rc);
    dev.queue.writeBuffer(aB, 0, f32(a));
    dev.queue.writeBuffer(wB, 0, f32(w0));
    dev.queue.writeBuffer(psiB, 0, new Float32Array(count));

    const q = uni(new Uint32Array([M, n, count, 0]));
    const ruleU = uni(new Uint32Array([count, MODE_CODE[mode], 0, nFix]));
    const bg = (p: any, entries: any[]): any => dev.createBindGroup({ layout: p.getBindGroupLayout(0), entries: entries.map((resource, binding) => ({ binding, resource: resource.size !== undefined && resource.usage !== undefined ? { buffer: resource } : resource })) });
    const fillBG = bg(pl.fill, [q, phi, ampB, A]);
    const zeroBG = bg(pl.zero, [q, A]);
    const gatherBG = bg(pl.gather, [q, A, idxB, gmB, vB]);
    const scatterBG = bg(pl.scatter, [q, idxB, coefB, A]);
    const ruleBG = bg(pl.rule, [ruleU, vB, aB, wB, psiB, rcB, coefB]);
    const phaseBG = bg(pl.phase, [q, A, phi]);
    // FFT stages: [axis][stage] for the forward (sign -1) and inverse (sign +1) transforms; global stage g alternates A -> B -> A
    const stageBGs = (sign: number): any[] => {
      const out: any[] = [];
      for (let g = 0; g < 2 * L; g++) {
        const axis = g < L ? 0 : 1, s = g % L;
        const p = new ArrayBuffer(32);
        new Uint32Array(p).set([M, 2 ** s, axis, 0]);
        new Float32Array(p)[4] = sign;
        const u = uni(new Uint32Array(p));
        out.push(bg(pl.stage, g % 2 === 0 ? [u, A, B] : [u, B, A]));
      }
      return out;
    };
    const fwd = stageBGs(-1), inv = stageBGs(1);
    const wgM = Math.ceil((M * M) / 256), wgS = Math.ceil((M * (M / 2)) / 256), wgC = Math.ceil(count / 256), wgN = Math.ceil((n * n) / 256);

    const encodePass = (update: boolean): any => {
      const enc = dev.createCommandEncoder();
      const pass = enc.beginComputePass();
      const run = (p: any, group: any, groups: number): void => { pass.setPipeline(p); pass.setBindGroup(0, group); pass.dispatchWorkgroups(groups); };
      run(pl.fill, fillBG, wgM);
      for (const g of fwd) run(pl.stage, g, wgS);
      run(pl.gather, gatherBG, wgC);
      if (update) {
        run(pl.rule, ruleBG, 1);
        run(pl.zero, zeroBG, wgM);
        run(pl.scatter, scatterBG, wgC);
        for (const g of inv) run(pl.stage, g, wgS);
        run(pl.phase, phaseBG, wgN);
      }
      pass.end();
      enc.copyBufferToBuffer(vB, 0, vStage, 0, 8 * count);
      return enc;
    };
    const readV = async (): Promise<Float64Array> => {
      await vStage.mapAsync(MAP_READ());
      const v = Float64Array.from(new Float32Array(vStage.getMappedRange().slice(0)));
      vStage.unmap();
      return v;
    };
    const entryOf = (k: number, v: Float64Array): HistoryEntry => {
      const iw = trapIntensities(v, traps.weight);
      return { iteration: k, efficiency: efficiency(trapIntensities(v)), uniformity: uniformity(iw), relStd: relStd(iw), timeS: (performance.now() - t0) / 1000 };
    };

    const history: HistoryEntry[] = [];
    let k = 0;
    for (;;) {
      k++;
      dev.queue.writeBuffer(ruleU, 0, new Uint32Array([count, MODE_CODE[mode], k, nFix]));
      dev.queue.submit([encodePass(true).finish()]);
      const v = await readV(); // the fields of the hologram before this update: iteration k - 1
      if (k > 1) {
        const e = entryOf(k - 1, v);
        history.push(e);
        yield e;
      }
      if (k >= budget.iterations || (budget.timeS !== null && (performance.now() - t0) / 1000 >= budget.timeS)) break;
    }
    // the fields of the final hologram, and the hologram itself
    const enc = encodePass(false);
    enc.copyBufferToBuffer(phi, 0, phiStage, 0, 4 * n * n);
    dev.queue.submit([enc.finish()]);
    const vFinal = await readV();
    await phiStage.mapAsync(MAP_READ());
    const phiOut = Float64Array.from(new Float32Array(phiStage.getMappedRange().slice(0)));
    phiStage.unmap();
    const last = entryOf(k, vFinal);
    history.push(last);
    yield last;

    // agreement with the float64 CPU evaluation of the same phase
    const cpu = fftFields(phiOut, setup, traps).v;
    const iG = trapIntensities(vFinal), iC = trapIntensities(cpu);
    let mean = 0;
    for (const x of iC) mean += x;
    mean /= iC.length;
    let maxDiff = 0;
    for (let t = 0; t < iC.length; t++) maxDiff = Math.max(maxDiff, Math.abs(iG[t] - iC[t]) / mean);
    if (!(maxDiff <= AGREEMENT_TOL)) {
      throw new Error(`the WebGPU result disagrees with the CPU evaluation of its own phase: max |dI| / mean I = ${maxDiff.toExponential(2)} > ${AGREEMENT_TOL}`);
    }
    return {
      phi: phiOut, history, fields: cpu,
      meta: { method: mid, form: 'fft', iterations: k, backend: 'gpu', gpuAdapter: gpu.adapter, gpuAgreement: maxDiff },
    };
  } finally {
    for (const b of bufs) b.destroy?.();
  }
}
