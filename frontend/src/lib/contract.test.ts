// T11: the committed artifacts against the web's declared contract, in both directions, types included. The same
// assertions run on two roots, the committed bake (data/derived) and the provider tree
// (docs/contracts/fixtures/data/derived): the swap test of the catalog rows case-index, case-manifest and trace, and
// the consumer side of readiness. An absent root or document is a failure naming its path, never a pass.
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
  conform,
  INDEX,
  MANIFEST,
  READINESS,
  SCHEMAS,
  TRACE,
  TRACE_SUMMARY,
  UNAVAILABLE,
  type CaseIndex,
  type CaseManifest,
  type Readiness,
  type Trace,
} from './contract.types';

const roots = {
  'data/derived (the bake)': new URL('../../../data/derived/', import.meta.url),
  'docs/contracts/fixtures/data/derived (the provider)': new URL('../../../docs/contracts/fixtures/data/derived/', import.meta.url),
};
const catalogUrl = new URL('../../../docs/contracts/catalog.md', import.meta.url);

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

for (const [label, root] of Object.entries(roots)) {
  describe(`CONTRACT 2: ${label} is exactly what the web declares`, () => {
    const read = (rel: string): unknown => readFrom(root, rel);
    const index = read('manifests/index.json') as CaseIndex;

    it('the index conforms and names a baked default case', () => {
      expect(conform(index, { object: INDEX })).toEqual([]);
      expect(index.schema).toBe(SCHEMAS.index);
      expect(index.n_cases).toBe(index.cases.length);
      expect(index.cases.length).toBeGreaterThan(0);
      expect(index.cases.map((c) => c.case_id)).toContain(index.default_case);
      const ids = index.cases.map((c) => c.case_id);
      expect(ids).toEqual([...ids].sort());
    });

    for (const entry of index.cases) {
      it(`${entry.case_id}: manifest and trace conform`, () => {
        const m = read(entry.manifest_path) as CaseManifest;
        expect(conform(m, { object: MANIFEST })).toEqual([]);
        expect(m.schema).toBe(SCHEMAS.manifest);
        expect(m.case_id).toBe(entry.case_id);
        expect(m.lane).toBe(m.gate.lane);
        // models: only catalog model slots (a row with a model io cell), each real or baseline
        expect(Object.keys(m.models).length).toBeGreaterThan(0);
        for (const [slot, which] of Object.entries(m.models)) {
          expect(modelSlots()).toContain(slot);
          expect(['real', 'baseline']).toContain(which);
        }
        const t = read(m.artifact.path) as Trace;
        expect(conform(t, { object: TRACE })).toEqual([]);
        expect(t.schema).toBe(SCHEMAS.trace);
        expect(t.case_id).toBe(entry.case_id);
        // equal lengths of t, S, I and R; the artifact bytes are the size of the file
        expect(new Set([t.t.length, t.S.length, t.I.length, t.R.length]).size).toBe(1);
        expect(readFileSync(new URL(m.artifact.path, root)).length).toBe(m.artifact.bytes);
        // the bake enforces the expected ranges; the committed summary must lie inside them
        const s = t.summary as unknown as Record<string, number>;
        for (const [metric, [lo, hi]] of Object.entries(m.expect)) {
          expect(s[metric]).toBeGreaterThanOrEqual(lo - 0.005);
          expect(s[metric]).toBeLessThanOrEqual(hi + 0.005);
        }
      });
    }

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

describe('CONTRACT 2: the checker', () => {
  it('adversarial: fails on a drifted document: a boolean is not a number, and extra and missing keys are named', () => {
    const problems = conform({ peak_I: true, t_peak: 3, extra: 1 }, { object: TRACE_SUMMARY }).join('\n');
    expect(problems).toMatch(/peak_I: expected a finite number/);
    expect(problems).toMatch(/extra: written by the pipeline, not declared/);
    expect(problems).toMatch(/attack_rate: declared by the web, not written/);
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
    expect(modelSlots()).toEqual(['surrogate-model']);
  });
  it('the catalog table is parsed: seven rows, readiness among them', () => {
    expect(catalogIds()).toEqual(['params-record', 'case-index', 'case-manifest', 'trace', 'surrogate-model', 'readiness', 'api']);
  });
});
