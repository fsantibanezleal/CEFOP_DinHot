// The build copies what the index declares: one artifact or several per manifest, and the index's further files.
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
// @ts-expect-error: a plain ES module shared with the build script
import { artifactPaths, declaredFiles, READINESS_REL } from '../../scripts/declared.mjs';

const root = mkdtempSync(join(tmpdir(), 'declared-'));
afterAll(() => rmSync(root, { recursive: true, force: true }));
const put = (rel: string, doc: unknown) => {
  mkdirSync(dirname(join(root, rel)), { recursive: true });
  writeFileSync(join(root, rel), JSON.stringify(doc));
};

describe('the declared files of the site', () => {
  it('reads one artifact or a list of artifacts', () => {
    expect(artifactPaths({ artifact: { path: 'A/trace.json' } })).toEqual(['A/trace.json']);
    expect(artifactPaths({ artifacts: [{ path: 'B/v1.json' }, { path: 'B/v2.json' }] })).toEqual(['B/v1.json', 'B/v2.json']);
    expect(artifactPaths({})).toEqual([]);
  });
  it('names every missing declared file, and a manifest that names no artifact', () => {
    put('manifests/index.json', {
      files: ['contract/index.json'],
      cases: [
        { case_id: 'A', path: 'manifests/A.json' },
        { case_id: 'B', path: 'manifests/B.json' },
        { case_id: 'C', path: 'manifests/C.json' },
      ],
    });
    put('manifests/A.json', { artifact: { path: 'A/trace.json' } });
    put('A/trace.json', {});
    put('manifests/B.json', { artifacts: [{ path: 'B/v1.json' }, { path: 'B/v2.json' }] });
    put('B/v1.json', {});
    put('manifests/C.json', { title: 'no artifact' });
    put('readiness.json', {});
    const { declared, missing, problems } = declaredFiles(root);
    expect(declared).toEqual([
      'manifests/index.json', 'readiness.json', 'contract/index.json', 'manifests/A.json', 'A/trace.json', 'manifests/B.json',
      'B/v1.json', 'B/v2.json', 'manifests/C.json',
    ]);
    expect(missing).toEqual(['contract/index.json', 'B/v2.json']);
    expect(problems).toEqual(['manifests/C.json: names no artifact (artifact or artifacts)']);
  });
  it('declares the readiness document right after the index, and reports it missing when absent', () => {
    expect(READINESS_REL).toBe('readiness.json');
    const bare = join(root, 'bare');
    mkdirSync(join(bare, 'manifests'), { recursive: true });
    writeFileSync(join(bare, 'manifests/index.json'), JSON.stringify({ cases: [] }));
    const { declared, missing } = declaredFiles(bare);
    expect(declared).toEqual(['manifests/index.json', 'readiness.json']);
    expect(missing).toEqual(['readiness.json']);
  });
});

describe('a declared-partial bake builds', () => {
  const partial = join(root, 'partial');
  const putPartial = (rel: string, doc: unknown) => {
    mkdirSync(dirname(join(partial, rel)), { recursive: true });
    writeFileSync(join(partial, rel), JSON.stringify(doc));
  };
  const readiness = (missing: string[], state = 'partial') => ({
    contracts: [{ id: 'trace', state, missing }, { id: 'params-record', state: 'partial', missing: ['some_case_id'] }],
  });
  const setup = (doc: unknown) => {
    putPartial('manifests/index.json', { cases: [{ case_id: 'A', path: 'manifests/A.json' }, { case_id: 'B', path: 'manifests/B.json' }] });
    putPartial('manifests/A.json', { artifact: { path: 'A/trace.json' } });
    putPartial('manifests/B.json', { artifact: { path: 'B/trace.json' } });
    putPartial('A/trace.json', {});
    if (doc !== null) putPartial('readiness.json', doc);
  };
  it('tolerates an absent file that the readiness lists in a partial row, and only that one', () => {
    setup(readiness(['B/trace.json']));
    const { missing, tolerated } = declaredFiles(partial);
    expect(missing).toEqual(['B/trace.json']);
    expect(tolerated).toEqual(['B/trace.json']);
  });
  it('does not tolerate an absent file that the readiness does not list', () => {
    setup(readiness(['A/other.json']));
    const { missing, tolerated } = declaredFiles(partial);
    expect(missing).toEqual(['B/trace.json']);
    expect(tolerated).toEqual([]);
  });
  it('lists nothing as declared-absent for a row whose state is not partial', () => {
    setup(readiness(['B/trace.json'], 'available'));
    expect(declaredFiles(partial).tolerated).toEqual([]);
  });
  it('tolerates nothing when the readiness is absent or unreadable', () => {
    setup(null);
    expect(declaredFiles(partial).tolerated).toEqual([]);
    putPartial('readiness.json', 'not an object');
    expect(declaredFiles(partial).tolerated).toEqual([]);
  });
});

describe('a refused case', () => {
  it('declares no manifest and no artifact: the index carries its reason', () => {
    const r = join(root, 'refused');
    mkdirSync(join(r, 'manifests'), { recursive: true });
    writeFileSync(join(r, 'manifests/index.json'), JSON.stringify({ cases: [{ case_id: 'C11', path: null, status: 'refused', reason: { en: 'x', es: 'y' } }, { case_id: 'A', path: 'manifests/A.json', status: 'baked' }] }));
    writeFileSync(join(r, 'manifests/A.json'), JSON.stringify({ artifact: { path: 'A/trace.json' } }));
    mkdirSync(join(r, 'A'), { recursive: true });
    writeFileSync(join(r, 'A/trace.json'), '{}');
    writeFileSync(join(r, 'readiness.json'), '{}');
    const d = declaredFiles(r);
    expect(d.declared).toEqual(['manifests/index.json', 'readiness.json', 'manifests/A.json', 'A/trace.json']);
    expect(d.missing).toEqual([]);
  });
});

// each case starts a node process; a loaded machine needs more than the default 5 s
describe('copy-data.mjs: DinHot declared files (benchmark, model metrics, released models)', { timeout: 60000 }, () => {
  const script = new URL('../../scripts/copy-data.mjs', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
  const make = (name: string, opts: { benchmark?: boolean; metrics?: boolean; readinessRows?: object[] }) => {
    const base = join(root, name);
    const derived = join(base, 'derived');
    const put2 = (rel: string, doc: unknown) => {
      mkdirSync(dirname(join(derived, rel)), { recursive: true });
      writeFileSync(join(derived, rel), typeof doc === 'string' ? doc : JSON.stringify(doc));
    };
    put2('manifests/index.json', { cases: [{ case_id: 'A', path: 'manifests/A.json', status: 'baked' }] });
    put2('manifests/A.json', { artifact: { path: 'A/trace.json' } });
    put2('A/trace.json', {});
    put2('readiness.json', { contracts: opts.readinessRows ?? [] });
    if (opts.benchmark) put2('benchmark/results.json', {});
    if (opts.metrics) put2('models/metrics.json', {});
    return { base, derived, out: join(base, 'public'), models: join(base, 'models') };
  };
  const run = (p: { derived: string; out: string; models: string }) =>
    spawnSync(process.execPath, [script], { env: { ...process.env, CAOS_DATA_ROOT: p.derived, CAOS_PUBLIC_DIR: p.out, CAOS_MODELS_DIR: p.models }, encoding: 'utf8' });

  it('copies the benchmark and the metrics beside the case files', () => {
    const p = make('full', { benchmark: true, metrics: true });
    const r = run(p);
    expect(r.status, r.stderr).toBe(0);
    for (const rel of ['benchmark/results.json', 'models/metrics.json', 'A/trace.json', 'readiness.json']) expect(existsSync(join(p.out, rel)), rel).toBe(true);
  });
  it('adversarial: stops on an absent benchmark the readiness does not call missing, and builds when it does', () => {
    const p = make('nobench', { metrics: true });
    const stop = run(p);
    expect(stop.status).toBe(1);
    expect(stop.stderr).toMatch(/benchmark\/results\.json/);
    const q = make('nobench-ok', { metrics: true, readinessRows: [{ id: 'benchmark-results', state: 'missing', missing: [] }] });
    const ok = run(q);
    expect(ok.status, ok.stderr).toBe(0);
    expect(ok.stdout).toMatch(/1 declared absent/);
    expect(existsSync(join(q.out, 'benchmark/results.json'))).toBe(false);
  });
  it('builds when the metrics are absent and the readiness row says provider (the producer does not exist yet)', () => {
    const p = make('nometrics-provider', { benchmark: true, readinessRows: [{ id: 'model-metrics', state: 'provider', missing: [] }] });
    const ok = run(p);
    expect(ok.status, ok.stderr).toBe(0);
    expect(existsSync(join(p.out, 'models/metrics.json'))).toBe(false);
    const q = make('nometrics-available', { benchmark: true, readinessRows: [{ id: 'model-metrics', state: 'available', missing: [] }] });
    expect(run(q).status).toBe(1);
  });
  it('ships a released model (card and graph) and refuses a card whose graph is absent or altered', () => {
    const p = make('model', { benchmark: true, metrics: true });
    const graph = Buffer.from([1, 2, 3, 4]);
    mkdirSync(p.models, { recursive: true });
    const card = { onnx: 'models/cgh-net.onnx', bytes: 4, sha256: createHash('sha256').update(graph).digest('hex') };
    writeFileSync(join(p.models, 'cgh-net.json'), JSON.stringify(card));
    const absent = run(p);
    expect(absent.status).toBe(1);
    expect(absent.stderr).toMatch(/graph models\/cgh-net\.onnx, which is absent/);
    writeFileSync(join(p.models, 'cgh-net.onnx'), Buffer.from([1, 2, 3, 5]));
    expect(run(p).stderr).toMatch(/not the one its card describes/);
    writeFileSync(join(p.models, 'cgh-net.onnx'), graph);
    const ok = run(p);
    expect(ok.status, ok.stderr).toBe(0);
    expect(existsSync(join(p.out, 'models/cgh-net.json'))).toBe(true);
    expect(existsSync(join(p.out, 'models/cgh-net.onnx'))).toBe(true);
  });
  it('without a card no model ships (the baseline answers)', () => {
    const p = make('nomodel', { benchmark: true, metrics: true });
    expect(run(p).status).toBe(0);
    expect(existsSync(join(p.out, 'models/cgh-net.json'))).toBe(false);
  });
});

