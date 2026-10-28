// T11: the committed artifacts against the web's declared contract, in both directions, types included. The same assertions run on
// two roots, the committed bake (data/derived) and the provider tree (docs/contracts/fixtures/data/derived): the swap test of the
// catalog rows case-index, case-manifest, trace, benchmark-results and model-metrics, the consumer side of cgh-net, warmstart-model
// and engine-reference, and of readiness. A root that is present is checked completely; the bake root is absent until the canonical
// bake is committed, and that absence is a skipped suite that names its path (not a pass, and not a failure of the web): the day
// data/derived/manifests/index.json exists, the suite runs and an incomplete bake fails.
import { existsSync, readFileSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { b64ToU8, decodeRle } from '../workbench/decode';
import {
  BENCHMARK,
  conform,
  ENGINE_REFERENCE,
  INDEX,
  MANIFEST,
  MODEL_CARD,
  MODEL_METRICS,
  READINESS,
  SCHEMAS,
  TRACE,
  TRACE_SUMMARY,
  UNAVAILABLE,
  type BenchmarkResults,
  type CaseIndex,
  type CaseManifest,
  type ModelCard,
  type ModelMetrics,
  type Readiness,
  type Trace,
} from './contract.types';

const bake = new URL('../../../data/derived/', import.meta.url);
const provider = new URL('../../../docs/contracts/fixtures/data/derived/', import.meta.url);
const roots: [string, URL, boolean][] = [
  ['data/derived (the bake)', bake, existsSync(new URL('manifests/index.json', bake))],
  ['docs/contracts/fixtures/data/derived (the provider)', provider, true],
];
const catalogUrl = new URL('../../../docs/contracts/catalog.md', import.meta.url);
const examples = new URL('../../../docs/contracts/examples/', import.meta.url);

/** The row ids of the `## Contracts` table of the catalog, in order. */
function catalogIds(): string[] {
  const ids: string[] = [];
  let inTable = false;
  for (const line of readFileSync(catalogUrl, 'utf8').split(/\r?\n/)) {
    if (line.startsWith('## ')) {
      inTable = line.trim() === '## Contracts';
      continue;
    }
    if (inTable && line.startsWith('|')) {
      const cell = line.split('|')[1].trim();
      if (cell !== 'id' && !/^-+$/.test(cell)) ids.push(cell);
    }
  }
  return ids;
}

/** The model slots of the catalog: the rows whose `model io` cell is not `-`. */
function modelSlots(): string[] {
  const slots: string[] = [];
  let inTable = false;
  let ioColumn = -1;
  for (const line of readFileSync(catalogUrl, 'utf8').split(/\r?\n/)) {
    if (line.startsWith('## ')) {
      inTable = line.trim() === '## Contracts';
      continue;
    }
    if (!inTable || !line.startsWith('|')) continue;
    const cells = line.split('|').slice(1, -1).map((c) => c.trim());
    if (cells[0] === 'id') ioColumn = cells.findIndex((c) => c.toLowerCase() === 'model io');
    else if (!/^-+$/.test(cells[0]) && ioColumn >= 0 && cells[ioColumn] !== '-') slots.push(cells[0]);
  }
  return slots;
}

function readFrom(root: URL, rel: string): unknown {
  const url = new URL(rel, root);
  if (!existsSync(url)) throw new Error(`missing committed document: ${fileURLToPath(url)}`);
  return JSON.parse(readFileSync(url, 'utf8'));
}

const METRIC_KEYS = ['efficiency', 'uniformity', 'rel_std_pct', 'zero_order', 'ghost'] as const;

for (const [label, root, present] of roots) {
  describe.skipIf(!present)(`CONTRACT 2: ${label} is exactly what the web declares`, () => {
    const read = (rel: string): unknown => readFrom(root, rel);
    // describe bodies run even when the suite is skipped: an absent root is read as an empty index, never as a pass
    const index = (present ? read('manifests/index.json') : { schema: SCHEMAS.index, engine_version: '', default_case: '', cases: [] }) as CaseIndex;
    const baked = index.cases.filter((c) => c.status === 'baked');
    const refused = index.cases.filter((c) => c.status === 'refused');

    it('the index conforms, is sorted, and names a baked default case', () => {
      expect(conform(index, { object: INDEX })).toEqual([]);
      expect(index.schema).toBe(SCHEMAS.index);
      const ids = index.cases.map((c) => c.case_id);
      expect(ids).toEqual([...ids].sort());
      expect(baked.length).toBeGreaterThan(0);
      expect(baked.map((c) => c.case_id)).toContain(index.default_case);
    });

    it('a refused case has no manifest path and carries its reason; a baked case has a path and no reason', () => {
      for (const c of refused) {
        expect(c.path, c.case_id).toBeNull();
        expect(c.reason?.en, c.case_id).toBeTruthy();
        expect(c.reason?.es, c.case_id).toBeTruthy();
      }
      for (const c of baked) {
        expect(c.path, c.case_id).toBe(`manifests/${c.case_id}.json`);
        expect(c.reason, c.case_id).toBeNull();
      }
    });

    for (const entry of baked) {
      it(`${entry.case_id}: manifest and trace conform, and the trace's encodings decode to the sizes they state`, () => {
        const m = read(entry.path!) as CaseManifest;
        expect(conform(m, { object: MANIFEST })).toEqual([]);
        expect(m.schema).toBe(SCHEMAS.manifest);
        expect(m.case_id).toBe(entry.case_id);
        expect(m.lane).toBe(m.gate.lane);
        expect(m.params.methods).toContain(m.params.reference_method);
        // models: only catalog model slots, each real or baseline
        for (const [slot, which] of Object.entries(m.models)) {
          expect(modelSlots()).toContain(slot);
          expect(['real', 'baseline']).toContain(which);
        }
        const t = read(m.artifact.path) as Trace;
        expect(conform(t, { object: TRACE })).toEqual([]);
        expect(t.schema).toBe(SCHEMAS.trace);
        expect(t.case_id).toBe(entry.case_id);
        expect(statSync(new URL(m.artifact.path, root)).size).toBe(m.artifact.bytes);
        // the maps the workbench draws
        expect(t.methods[t.reference.method], 'reference.method is a key of methods').toBeDefined();
        expect(b64ToU8(t.reference.phase_u8).length).toBe(t.grid.n_pix ** 2);
        const f = t.reference.focal;
        expect(b64ToU8(f.intensity_db_u8).length).toBe(f.size ** 2);
        if (t.reference.axial) expect(b64ToU8(t.reference.axial.xz_u8).length).toBe(t.reference.axial.nz * t.reference.axial.nx);
        if (t.shape) expect(decodeRle(t.shape.mask_rle, f.size ** 2).length).toBe(f.size ** 2);
        // per-method vectors: one intensity per trap of the target, histories ordered by iteration
        for (const [id, mm] of Object.entries(t.methods)) {
          if (t.traps.length) expect(mm.trap_intensity.length, id).toBe(t.traps.length);
          const its = mm.history.map((h) => h.iteration);
          expect(its, id).toEqual([...its].sort((a, b) => a - b));
        }
        // the bake enforces the expected ranges; the reference method's final metrics lie inside the plain ones
        const v = m.methods[m.params.reference_method] as unknown as Record<string, number>;
        for (const key of METRIC_KEYS) {
          const range = m.expect[key];
          if (range && v) {
            expect(v[key], key).toBeGreaterThanOrEqual(range[0] - 0.005);
            expect(v[key], key).toBeLessThanOrEqual(range[1] + 0.005);
          }
        }
        expect(conform(t.summary, { object: TRACE_SUMMARY })).toEqual([]);
      });
    }

    it('the benchmark conforms, and every skipped cell is absent from the rows', () => {
      const b = read('benchmark/results.json') as BenchmarkResults;
      expect(conform(b, { object: BENCHMARK })).toEqual([]);
      expect(b.schema).toBe(SCHEMAS.benchmark);
      const geometries = new Set(b.geometries.map((g) => g.id));
      for (const r of b.rows) expect(geometries.has(r.geometry), `${r.method}/${r.geometry}`).toBe(true);
      for (const s of b.skipped ?? []) {
        expect(b.rows.some((r) => r.method === s.method && r.geometry === s.geometry), `${s.method}/${s.geometry} is skipped but has rows`).toBe(false);
      }
      for (const f of b.pareto) expect(geometries.has(f.geometry)).toBe(true);
    });

    it('the model metrics conform and name only the two slots of the catalog', () => {
      const mm = read('models/metrics.json') as ModelMetrics;
      expect(conform(mm, { object: MODEL_METRICS })).toEqual([]);
      expect(mm.schema).toBe(SCHEMAS.modelMetrics);
      for (const slot of Object.keys(mm.slots)) expect(modelSlots()).toContain(slot);
    });

    it('the readiness document conforms and lists the catalog rows in order', () => {
      const r = read('readiness.json') as Readiness;
      expect(conform(r, { object: READINESS })).toEqual([]);
      expect(r.schema).toBe(SCHEMAS.readiness);
      const expected = catalogIds().filter((id) => id !== 'readiness');
      expect(expected.length).toBeGreaterThan(0);
      expect(r.contracts.map((e) => e.id)).toEqual(expected);
    });
  });
}

describe('CONTRACT 2: the bake root', () => {
  it('is checked completely once it exists; until then the suite is skipped and the provider tree carries the same assertions', () => {
    const present = roots[0][2];
    if (present) {
      for (const rel of ['manifests/index.json', 'readiness.json', 'benchmark/results.json', 'models/metrics.json']) {
        expect(existsSync(new URL(rel, bake)), `the bake is incomplete: ${rel} is missing under ${fileURLToPath(bake)}`).toBe(true);
      }
    } else {
      expect(existsSync(new URL('manifests/index.json', provider))).toBe(true);
    }
  });
});

describe('CONTRACT 2: the model cards and the engine reference (consumer side)', () => {
  const card = (name: string) => JSON.parse(readFileSync(new URL(name, examples), 'utf8')) as ModelCard;
  it('the committed cards conform, name their slot, and agree with the tensors of the catalog', () => {
    const cgh = card('cgh-net.json');
    const warm = card('warmstart-model.json');
    for (const c of [cgh, warm]) {
      expect(conform(c, { object: MODEL_CARD })).toEqual([]);
      expect(c.schema).toBe(SCHEMAS.modelCard);
      expect(c.sha256).toMatch(/^[0-9a-f]{64}$/);
    }
    expect(cgh.slot).toBe('cgh-net');
    expect(cgh.inputs[0]).toEqual({ name: 'target', shape: [1, 1, 128, 128], dtype: 'float32' });
    expect(cgh.outputs[0]).toEqual({ name: 'phase', shape: [1, 1, 128, 128], dtype: 'float32' });
    expect(warm.slot).toBe('warmstart-model');
    expect(warm.inputs.map((i) => i.name)).toEqual(['traps', 'mask']);
    expect(warm.inputs[0].shape).toEqual([1, 1024, 4]);
    expect(warm.outputs[0]).toEqual({ name: 'trap_phase', shape: [1, 1024], dtype: 'float32' });
  });
  it('adversarial: a card with a missing or an undeclared key does not conform', () => {
    const c = card('cgh-net.json') as unknown as Record<string, unknown>;
    const { sha256: _drop, ...without } = c;
    expect(conform(without, { object: MODEL_CARD }).join('\n')).toMatch(/sha256: declared by the web, not written/);
    expect(conform({ ...c, extra: 1 }, { object: MODEL_CARD }).join('\n')).toMatch(/extra: written by the pipeline, not declared/);
  });
  it('the engine reference example conforms', () => {
    const ref = JSON.parse(readFileSync(new URL('engine-reference.json', examples), 'utf8')) as unknown;
    expect(conform(ref, { object: ENGINE_REFERENCE })).toEqual([]);
  });
});

describe('CONTRACT 2: the checker', () => {
  it('adversarial: fails on a drifted document: a boolean is not a number, and extra and missing keys are named', () => {
    const problems = conform({ best_method: true, extra: 1 }, { object: TRACE_SUMMARY }).join('\n');
    expect(problems).toMatch(/best_method: expected a string/);
    expect(problems).toMatch(/extra: written by the pipeline, not declared/);
    expect(problems).toMatch(/notes: declared by the web, not written/);
  });
  it('a nullable kind accepts null and still checks a value', () => {
    expect(conform(null, { nullable: 'number' })).toEqual([]);
    expect(conform(2, { nullable: 'number' })).toEqual([]);
    expect(conform('2', { nullable: 'number' }).join('')).toMatch(/expected a finite number/);
  });
  it('the 503 body of the API conforms, and a body without its reason does not', () => {
    const body = { detail: { state: 'missing', reason: { en: 'x', es: 'y' } } };
    expect(conform(body, { object: UNAVAILABLE })).toEqual([]);
    expect(conform({ detail: { state: 'missing' } }, { object: UNAVAILABLE }).join('')).toMatch(/reason: declared by the web/);
  });
  it('the model slots are the catalog rows with a model io cell', () => {
    expect(modelSlots()).toEqual(['cgh-net', 'warmstart-model']);
  });
  it('the catalog table is parsed: eleven rows, readiness among them', () => {
    expect(catalogIds()).toEqual(['params-record', 'case-index', 'case-manifest', 'trace', 'benchmark-results', 'cgh-net', 'warmstart-model', 'model-metrics', 'engine-reference', 'readiness', 'api']);
  });
  it('METRIC_KEYS name only keys of a method verdict', () => {
    const v: CaseManifest['methods'][string] = { lane: 'live', efficiency: 1, uniformity: 1, rel_std_pct: 0, zero_order: 0, ghost: 0, iterations: 1, converged: true };
    for (const k of METRIC_KEYS) expect(k in v).toBe(true);
  });
});
