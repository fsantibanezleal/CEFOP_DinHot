// DinHot's further site files (frontend/scripts/copy-data.product.mjs, called by the base copy-data.mjs): the bake's benchmark and model
// metrics, required unless the readiness row says missing or provider, and the released models, shipped only when the graph is the one
// its card describes.
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
// @ts-expect-error: a plain ES module shared with the build script
import productFiles from '../../scripts/copy-data.product.mjs';

const root = mkdtempSync(join(tmpdir(), 'dinhot-copy-data-'));
afterAll(() => rmSync(root, { recursive: true, force: true }));

function make(name: string, opts: { benchmark?: boolean; metrics?: boolean; rows?: object[] }) {
  const base = join(root, name);
  const derived = join(base, 'derived');
  const put = (rel: string, doc: unknown) => {
    mkdirSync(dirname(join(derived, rel)), { recursive: true });
    writeFileSync(join(derived, rel), JSON.stringify(doc));
  };
  if (opts.benchmark) put('benchmark/results.json', {});
  if (opts.metrics) put('models/metrics.json', {});
  const readiness = { contracts: opts.rows ?? [] };
  return { derived, out: join(base, 'public'), repo: base, readiness, modelsDir: join(base, 'models') };
}

describe('copy-data.product.mjs: DinHot declared files', () => {
  it('copies the benchmark and the metrics into the overlay', () => {
    const p = make('full', { benchmark: true, metrics: true });
    const r = productFiles(p);
    expect(r.problems).toEqual([]);
    expect(r.copied).toEqual(['benchmark/results.json', 'models/metrics.json']);
    for (const rel of r.copied) expect(existsSync(join(p.out, rel)), rel).toBe(true);
  });
  it('adversarial: an absent benchmark is a problem unless the readiness calls it missing', () => {
    const stop = productFiles(make('nobench', { metrics: true }));
    expect(stop.problems.join('\n')).toMatch(/benchmark\/results\.json/);
    const ok = productFiles(make('nobench-ok', { metrics: true, rows: [{ id: 'benchmark-results', state: 'missing', missing: [] }] }));
    expect(ok.problems).toEqual([]);
    expect(ok.absent).toEqual(['benchmark/results.json']);
  });
  it('absent metrics are declared absent when the row says provider, a problem when it says available', () => {
    const ok = productFiles(make('nometrics-provider', { benchmark: true, rows: [{ id: 'model-metrics', state: 'provider', missing: [] }] }));
    expect(ok.problems).toEqual([]);
    expect(ok.absent).toEqual(['models/metrics.json']);
    const stop = productFiles(make('nometrics-available', { benchmark: true, rows: [{ id: 'model-metrics', state: 'available', missing: [] }] }));
    expect(stop.problems.length).toBe(1);
  });
  it('ships a released model (card and graph) and refuses a card whose graph is absent or altered', () => {
    const p = make('model', { benchmark: true, metrics: true });
    const graph = Buffer.from([1, 2, 3, 4]);
    mkdirSync(p.modelsDir, { recursive: true });
    const card = { onnx: 'models/cgh-net.onnx', bytes: 4, sha256: createHash('sha256').update(graph).digest('hex') };
    writeFileSync(join(p.modelsDir, 'cgh-net.json'), JSON.stringify(card));
    expect(productFiles(p).problems.join('\n')).toMatch(/graph models\/cgh-net\.onnx, which is absent/);
    writeFileSync(join(p.modelsDir, 'cgh-net.onnx'), Buffer.from([1, 2, 3, 5]));
    expect(productFiles(p).problems.join('\n')).toMatch(/not the one its card describes/);
    writeFileSync(join(p.modelsDir, 'cgh-net.onnx'), graph);
    const ok = productFiles(p);
    expect(ok.problems).toEqual([]);
    expect(existsSync(join(p.out, 'models/cgh-net.json'))).toBe(true);
    expect(existsSync(join(p.out, 'models/cgh-net.onnx'))).toBe(true);
  });
  it('without a card no model ships (the baseline answers)', () => {
    const p = make('nomodel', { benchmark: true, metrics: true });
    const r = productFiles(p);
    expect(r.problems).toEqual([]);
    expect(existsSync(join(p.out, 'models/cgh-net.json'))).toBe(false);
  });
});
