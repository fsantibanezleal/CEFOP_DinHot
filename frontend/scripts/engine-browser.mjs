// Browser run of the live engine (local and in the gate run, never in Node CI: ADR-0074, ADR-0069 A69.7).
//
//   PLAYWRIGHT_BROWSERS_PATH=<temp root>/ms-playwright node scripts/engine-browser.mjs [--mode shell|chromium] [--out file.json] [--assert]
//
// It serves the engine through Vite's dev server, opens it in Chromium and measures, in a real Web Worker:
//   - the live budget: a 30-iteration M07 run on the 256 x 256 padded-2 grid (cases C02 and C03 of data/examples/cases.json), CPU path;
//   - that the main thread is not blocked (the longest gap of a 10 ms ticker while the worker computes);
//   - cancellation (no progress message after the cancel is acted on, a new run rejects the previous one with AbortError);
//   - the WebGPU path: detection, the agreement with the CPU path (one iteration and thirty), timings, and the fallback with its
//     reason when WebGPU is absent (`--mode shell`: Playwright's headless shell has `navigator.gpu` but no adapter).
// `--mode chromium` uses the new headless mode (`channel: 'chromium'`), the only one that exposes an adapter (R2 D5).
// With `--assert` the process exits 1 when a gate fails: CPU lane budget 1500 ms, agreement tolerances below, fallback reason present.
import { readFileSync, writeFileSync } from 'node:fs';
import { createServer } from 'vite';
import { chromium } from 'playwright';

const args = process.argv.slice(2);
const opt = (name, dflt) => (args.includes(name) ? args[args.indexOf(name) + 1] : dflt);
const mode = opt('--mode', 'chromium');
const out = opt('--out', null);
const ASSERT = args.includes('--assert');
const sections = opt('--sections', 'cpu,cancel,gpu').split(',');
const LANE_BUDGET_MS = 1500;
// observed on the Intel gen-12lp adapter (T1 report): 3e-5 rad, 5e-7, 5e-5, 9e-5; the tolerances keep a factor of about 10
const AGREE = { oneIterationPhaseRms: 5e-4, efficiency: 5e-6, uniformity: 5e-4, trapIntensityRel: 1e-3 };

const frontend = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const cases = JSON.parse(readFileSync(new URL('../../data/examples/cases.json', import.meta.url), 'utf8'));
const rec = (id) => cases.find((c) => c.case_id === id);

const server = await createServer({
  configFile: false, root: frontend, logLevel: 'error', server: { host: '127.0.0.1', port: 5197, strictPort: true, fs: { strict: false } },
  // the entries are scanned at start so fft.js is pre-bundled before the page loads (a late discovery reloads the page)
  optimizeDeps: { include: ['fft.js'], entries: ['scripts/engine-browser.html', 'src/engine/holo/worker.ts'] },
});
await server.listen();
const browser = await chromium.launch(
  mode === 'shell'
    ? { headless: true }
    : { channel: 'chromium', headless: true, args: ['--enable-unsafe-webgpu', '--enable-features=Vulkan', '--ignore-gpu-blocklist'] },
);
const failures = [];
const report = { mode, browser: browser.version(), results: {} };
const gate = (ok, what) => { if (!ok) failures.push(what); return ok; };

try {
  const page = await browser.newPage();
  page.on('pageerror', (e) => console.error('pageerror', e.message));
  for (let attempt = 0; attempt < 3; attempt++) { // a dev-server dependency reload destroys the first page context; settle first
    await page.goto('http://127.0.0.1:5197/scripts/engine-browser.html');
    await page.waitForFunction('window.__ready === true', null, { timeout: 60000 });
    await page.waitForTimeout(1500);
    try {
      await page.evaluate(async () => { const c = window.__engine.createEngineClient(); await c.gpu(); c.dispose(); });
      break;
    } catch (e) {
      console.error('settling:', String(e.message).split(String.fromCharCode(10))[0]);
    }
  }

  // ---- CPU live budget and main-thread liveness ----
  report.results.cpu = {};
  for (const id of sections.includes('cpu') ? ['C02_grid_feedback', 'C03_large_array'] : []) {
    const r = await page.evaluate(async ({ params }) => {
      const { createEngineClient } = window.__engine;
      const client = createEngineClient();
      let maxGap = 0, last = performance.now();
      const tick = setInterval(() => { const t = performance.now(); maxGap = Math.max(maxGap, t - last); last = t; }, 10);
      const runs = [];
      let progressCount = 0;
      for (let i = 0; i < 4; i++) { // the first run carries module and JIT warm-up; the lane gate judges a warm run
        const t0 = performance.now();
        const res = await client.run({ params, method: 'M07', options: { iterations: 30, backend: 'cpu' } }, () => { progressCount++; });
        runs.push({ wallMs: performance.now() - t0, workerMs: res.timeMs, timing: res.timing, efficiency: res.metrics.efficiency, uniformity: res.metrics.uniformity, relStdPct: res.metrics.relStdPct });
      }
      clearInterval(tick);
      client.dispose();
      return { runs, maxMainThreadGapMs: maxGap, progressMessages: progressCount };
    }, { params: rec(id) });
    const warm = r.runs.slice(1).map((x) => x.wallMs);
    r.warmMedianMs = warm.sort((a, b) => a - b)[Math.floor(warm.length / 2)];
    report.results.cpu[id] = r;
    // the lane gate judges the case's reference method (C02, the default case); C03 (1024 off-bin traps) is recorded, not gated
    if (id === 'C02_grid_feedback') gate(r.warmMedianMs <= LANE_BUDGET_MS, `${id}: CPU M07 30 iterations ${r.warmMedianMs.toFixed(0)} ms exceeds the lane budget ${LANE_BUDGET_MS} ms`);
    else r.informational = `${r.warmMedianMs.toFixed(0)} ms against the ${LANE_BUDGET_MS} ms lane budget: not gated (a 1024-trap array is a baked case)`;
    gate(r.maxMainThreadGapMs < 200, `${id}: the main thread was blocked for ${r.maxMainThreadGapMs.toFixed(0)} ms`);
  }

  // ---- cancellation ----
  if (sections.includes('cancel')) report.results.cancel = await page.evaluate(async ({ params }) => {
    const { createEngineClient, AbortError } = window.__engine;
    const client = createEngineClient();
    const seen = [];
    let cancelAt = 0, rejected = null;
    const t0 = performance.now();
    const first = client.run({ params, method: 'M07', options: { iterations: 400, backend: 'cpu' } }, (p) => {
      seen.push({ t: performance.now() - t0, it: p.iteration });
      if (!cancelAt && p.iteration >= 3) { cancelAt = performance.now() - t0; client.cancel(); }
    }).catch((e) => { rejected = e instanceof AbortError; });
    await first;
    const afterCancel = seen.filter((s) => s.t > cancelAt + 1).length;
    await new Promise((r) => setTimeout(r, 300)); // any progress after the cancel would still be arriving
    const late = seen.filter((s) => s.t > cancelAt + 1).length;
    // a new run cancels the previous one
    const a = client.run({ params, method: 'M07', options: { iterations: 400, backend: 'cpu' } });
    const aOutcome = a.then(() => 'result', (e) => e.name);
    const b = await client.run({ params, method: 'M06', options: { iterations: 3, backend: 'cpu' } });
    client.dispose();
    return { rejectedWithAbortError: rejected, progressBeforeCancel: seen.length, progressAfterCancelCall: afterCancel, progressLate: late, superseded: await aOutcome, secondRun: b.method };
  }, { params: rec('C02_grid_feedback') });
  if (report.results.cancel) {
  gate(report.results.cancel.rejectedWithAbortError === true, 'cancel: the promise did not reject with AbortError');
  gate(report.results.cancel.progressLate <= 2, `cancel: ${report.results.cancel.progressLate} progress messages after the cancel`);
  gate(report.results.cancel.superseded === 'AbortError', 'a new run did not cancel the previous one');
  }

  // ---- WebGPU: detection, agreement, timings, fallback ----
  // The GPU path takes traps on FFT bins; C02 and C03 are the cases of data/examples/cases.json with every trap moved to its nearest bin
  // (the cases themselves are off-bin: the first run of each is the fallback test with the reason).
  const snap = (r) => {
    const s = r.setup, bin = (s.wavelength_nm * 1e-9 * s.focal_mm * 1e-3) / (s.pad * s.n_pix * s.pitch_um * 1e-6) * 1e6;
    return { ...r, case_id: `${r.case_id}_onbins`, target: { ...r.target, traps: r.target.traps.map((t) => ({ ...t, x_um: Math.round(t.x_um / bin) * bin, y_um: Math.round(t.y_um / bin) * bin })) } };
  };
  const gpuCases = sections.includes('gpu') ? [snap(rec('C02_grid_feedback')), snap(rec('C03_large_array'))] : [];
  const gpuOut = gpuCases.length ? await page.evaluate(async ({ cases, offBin }) => {
    const { createEngineClient } = window.__engine;
    const client = createEngineClient();
    const probe = await client.gpu();
    const out = { probe, mainThreadHasGpu: 'gpu' in navigator, cases: {} };
    const circ = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) { let d = Math.abs(a[i] - b[i]) % (2 * Math.PI); d = Math.min(d, 2 * Math.PI - d); s += d * d; } return Math.sqrt(s / a.length); };
    const time = async (params, backend, n) => {
      const ms = [];
      for (let i = 0; i < n; i++) ms.push((await client.run({ params, method: 'M07', options: { iterations: 30, backend } })).timeMs);
      ms.sort((x, y) => x - y);
      return { median: ms[Math.floor(ms.length / 2)], min: ms[0] };
    };
    // an off-bin case with 'auto' and with 'gpu': the CPU path, with the reason
    const off = await client.run({ params: offBin, method: 'M07', options: { iterations: 5, backend: 'auto' } });
    out.offBin = { backend: off.backend, reason: off.fallbackReason };
    if (!probe.ok) {
      const auto = await client.run({ params: cases[0], method: 'M07', options: { iterations: 5, backend: 'auto' } });
      out.absent = { backend: auto.backend, reason: auto.fallbackReason };
      return out;
    }
    for (const params of cases) {
      const cpu1 = await client.run({ params, method: 'M07', options: { iterations: 1, backend: 'cpu' } });
      const gpu1 = await client.run({ params, method: 'M07', options: { iterations: 1, backend: 'gpu' } });
      const cpu30 = await client.run({ params, method: 'M07', options: { iterations: 30, backend: 'cpu' } });
      const gpu30 = await client.run({ params, method: 'M07', options: { iterations: 30, backend: 'gpu' } });
      const auto = await client.run({ params, method: 'M07', options: { iterations: 30, backend: 'auto' } });
      let tiRel = 0;
      for (let i = 0; i < cpu30.trapIntensity.length; i++) tiRel = Math.max(tiRel, Math.abs(gpu30.trapIntensity[i] - cpu30.trapIntensity[i]) / cpu30.trapIntensity[i]);
      out.cases[params.case_id] = {
        traps: params.target.traps.length,
        backends: [gpu1.backend, gpu30.backend, auto.backend],
        fallbackReasons: [gpu1.fallbackReason, gpu30.fallbackReason, auto.fallbackReason],
        oneIterationPhaseRms: circ(cpu1.phase, gpu1.phase),
        oneIterationEfficiencyDiff: Math.abs(cpu1.metrics.efficiency - gpu1.metrics.efficiency),
        thirtyEfficiencyDiff: Math.abs(cpu30.metrics.efficiency - gpu30.metrics.efficiency),
        thirtyUniformityDiff: Math.abs(cpu30.metrics.uniformity - gpu30.metrics.uniformity),
        thirtyTrapIntensityMaxRel: tiRel,
        cpu30: cpu30.metrics, gpu30: gpu30.metrics,
        timing30Ms: { cpu: await time(params, 'cpu', 5), gpu: await time(params, 'gpu', 5) },
        gpuTiming: gpu30.timing,
      };
    }
    client.dispose();
    return out;
  }, { cases: gpuCases, offBin: rec('C02_grid_feedback') }) : null;
  report.results.gpu = gpuOut;
  if (gpuOut) {
    gate(gpuOut.offBin.backend === 'cpu' && /not eligible for the WebGPU path|WebGPU/.test(gpuOut.offBin.reason ?? ''), 'fallback: an off-bin case did not fall back with a reason');
    if (gpuOut.probe.ok) {
      for (const [id, a] of Object.entries(gpuOut.cases)) {
        gate(a.backends.every((b) => b === 'gpu'), `${id}: a gpu or auto run did not run on the GPU (${a.fallbackReasons.join('; ')})`);
        gate(a.oneIterationPhaseRms <= AGREE.oneIterationPhaseRms, `${id}: one-iteration phase rms ${a.oneIterationPhaseRms}`);
        gate(a.thirtyEfficiencyDiff <= AGREE.efficiency, `${id}: efficiency differs by ${a.thirtyEfficiencyDiff}`);
        gate(a.thirtyUniformityDiff <= AGREE.uniformity, `${id}: uniformity differs by ${a.thirtyUniformityDiff}`);
        gate(a.thirtyTrapIntensityMaxRel <= AGREE.trapIntensityRel, `${id}: trap intensity differs by ${a.thirtyTrapIntensityMaxRel}`);
      }
    } else {
      gate(gpuOut.absent.backend === 'cpu' && typeof gpuOut.absent.reason === 'string' && gpuOut.absent.reason.length > 0, 'fallback: no reason recorded when WebGPU is absent');
    }
  }
} finally {
  await browser.close();
  await server.close();
}
report.failures = failures;
const text = JSON.stringify(report, null, 2);
if (out) writeFileSync(out, text);
console.log(text);
if (ASSERT && failures.length) {
  console.error(`FAILED:\n- ${failures.join('\n- ')}`);
  process.exit(1);
}
