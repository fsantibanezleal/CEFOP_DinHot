// The consumer and swap test of readiness 1.0.0 (docs/contracts/catalog.md, Missing-data states): the committed
// document and the provider tree's document conform to the schema this side reads, every view's note comes from the
// document (never from a state typed in a view), each of the six states maps to the behavior the catalog names, and
// a case the document lists as absent is refused as unavailable, with its reason, instead of drawn empty.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ArtifactUnavailable, loadCase, loadIndex } from '../api/artifacts';
import { conform, READINESS, type ContractState, type Readiness, type ReadinessEntry } from '../lib/contract.types';
import { NoteLine } from './ReadinessNote';
import { behavior, entryFor, isUnavailable, loadReadiness, resetReadiness, viewState, SEVERITY } from './readiness';

vi.stubGlobal('__APP_VERSION__', 'test-version');

const here = dirname(fileURLToPath(import.meta.url));
const repo = join(here, '..', '..', '..');
const read = (rel: string): Readiness => JSON.parse(readFileSync(join(repo, rel), 'utf8'));
const committed = read('data/derived/readiness.json');
const fixture = read('docs/contracts/fixtures/data/derived/readiness.json');

const VIEWS: Record<string, string[]> = {
  workbench: ['case-index', 'case-manifest', 'trace'],
  experiments: ['case-index', 'case-manifest', 'trace'],
  benchmark: ['case-index', 'case-manifest', 'trace', 'surrogate-model'],
  implementation: committed.contracts.map((c) => c.id),
};

const entry = (id: string, state: ContractState, over: Partial<ReadinessEntry> = {}): ReadinessEntry => ({
  id,
  version: '1.0.0',
  status: 'real',
  provenance: state === 'missing' ? null : 'real',
  state,
  reason: state === 'available' ? null : { en: `${id} is ${state}`, es: `${id} está ${state}` },
  missing: state === 'partial' ? ['x/y.json'] : [],
  ...over,
});
const doc = (...entries: ReadinessEntry[]): Readiness => ({ schema: 'example.readiness/v1', product_version: '9.9.9', catalog_sha256: '0', contracts: entries });

describe('the committed documents', () => {
  it.each([['committed bake', committed], ['provider tree', fixture]])('%s conforms to READINESS', (_n, d) => {
    expect(conform(d, { object: READINESS })).toEqual([]);
  });
  it.each([['committed bake', committed], ['provider tree', fixture]])('%s gives each view the state its rows say', (_n, d) => {
    for (const [view, ids] of Object.entries(VIEWS)) {
      const rows = ids.map((id) => entryFor(d, id)).filter((e): e is ReadinessEntry => !!e);
      const worst = SEVERITY.find((s) => rows.some((r) => r.state === s)) ?? 'available';
      const got = viewState(d, ids);
      expect(got.state, view).toBe(worst);
      if (got.state !== 'unknown' && got.state !== 'available') {
        expect(got.rows.every((r) => r.state !== 'available' && r.reason !== null), view).toBe(true);
      }
    }
  });
  it('the provider tree says provider on every artifact row (its api row is missing, by the catalog); the note names the provider from the document', () => {
    for (const view of ['workbench', 'experiments', 'benchmark']) expect(viewState(fixture, VIEWS[view]).state, view).toBe('provider');
    expect(viewState(fixture, VIEWS.implementation).state).toBe('missing');
    const html = renderToStaticMarkup(createElement(NoteLine, { view: viewState(fixture, VIEWS.workbench), lang: 'en' }));
    expect(html).toContain('data-readiness="provider"');
    expect(html).toContain(fixture.contracts.find((c) => c.id === 'case-index')!.reason!.en);
  });
});

describe('the six states', () => {
  it('adversarial: order: missing, partial, training, provider, stale, available; the most severe wins', () => {
    expect(SEVERITY).toEqual(['missing', 'partial', 'training', 'provider', 'stale', 'available']);
    const d = doc(entry('a', 'stale'), entry('b', 'partial'), entry('c', 'available'));
    expect(viewState(d, ['a', 'b', 'c']).state).toBe('partial');
    expect(viewState(doc(entry('a', 'available')), ['a'])).toEqual({ state: 'available', rows: [] });
  });
  it.each<[ContractState, boolean, boolean]>([
    ['available', true, false],
    ['partial', true, true],
    ['stale', true, true],
    ['provider', true, true],
    ['training', true, true],
    ['missing', false, true],
  ])('%s: shows the result %s, with a note %s', (state, showsResult, note) => {
    expect(behavior(state)).toEqual({ showsResult, note });
    const view = viewState(doc(entry('a', state)), ['a']);
    const html = renderToStaticMarkup(createElement(NoteLine, { view, lang: 'es' }));
    if (note) {
      expect(html).toContain(`data-readiness="${state}"`);
      expect(html).toContain(`a está ${state}`);
    } else {
      expect(html).toBe('');
    }
  });
  it('a row of the view that is not in the document is ignored; a view with none of its rows is unknown', () => {
    expect(viewState(doc(entry('a', 'stale')), ['a', 'zzz']).state).toBe('stale');
    expect(viewState(doc(entry('a', 'stale')), ['zzz']).state).toBe('unknown');
  });
});

describe('a missing readiness document', () => {
  it('adversarial: a null document is readiness unknown, in both languages', () => {
    const view = viewState(null, VIEWS.workbench);
    expect(view.state).toBe('unknown');
    expect(renderToStaticMarkup(createElement(NoteLine, { view, lang: 'en' }))).toMatch(/data-readiness="unknown".*Readiness unknown/);
    expect(renderToStaticMarkup(createElement(NoteLine, { view, lang: 'es' }))).toMatch(/data-readiness="unknown".*Disponibilidad desconocida/);
  });
  it('a fetch that fails resolves to null, names the cause on the console, and is asked for once', async () => {
    resetReadiness();
    const fetch = vi.fn(async () => ({ ok: false, status: 404, headers: new Headers({ 'content-type': 'text/html' }), json: async () => ({}) }));
    vi.stubGlobal('fetch', fetch);
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    await expect(loadReadiness()).resolves.toBeNull();
    await expect(loadReadiness()).resolves.toBeNull();
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(err.mock.calls.flat().join(' ')).toMatch(/readiness\.json: HTTP 404/);
    err.mockRestore();
  });
  it('a document without contracts is treated as unreadable', async () => {
    resetReadiness();
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, headers: new Headers({ 'content-type': 'application/json' }), json: async () => ({ nope: 1 }) })));
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    await expect(loadReadiness()).resolves.toBeNull();
    err.mockRestore();
  });
});

describe('a case the document lists as absent', () => {
  const MANIFEST = { case_id: 'C1', artifact: { path: 'C1/trace.json' } };
  function serve(readiness: unknown) {
    const answers: Record<string, unknown> = { 'readiness.json': readiness, 'manifests/C1.json': MANIFEST, 'C1/trace.json': { case_id: 'C1' } };
    const fetch = vi.fn(async (url: string) => {
      const rel = Object.keys(answers).find((k) => url.includes(`/data/${k}`));
      return { ok: !!rel, status: rel ? 200 : 404, headers: new Headers({ 'content-type': 'application/json' }), json: async () => answers[rel ?? ''] };
    });
    vi.stubGlobal('fetch', fetch);
    return fetch;
  }
  beforeEach(() => resetReadiness());
  afterEach(() => vi.unstubAllGlobals());

  it('isUnavailable is true for a path a row lists in missing, and for every path when the case-index row is missing', () => {
    const d = doc(entry('trace', 'partial', { missing: ['C1/trace.json'] }), entry('case-index', 'available'));
    expect(isUnavailable(d, 'C1/trace.json')).toBe(true);
    expect(isUnavailable(d, 'C2/trace.json')).toBe(false);
    expect(isUnavailable(doc(entry('case-index', 'missing')), 'anything.json')).toBe(true);
    expect(isUnavailable(null, 'C1/trace.json')).toBe(false);
  });
  it('adversarial: loadCase rejects with ArtifactUnavailable naming the path and the reason, and never fetches the trace', async () => {
    const fetch = serve(doc(entry('trace', 'partial', { missing: ['C1/trace.json'] })));
    vi.stubGlobal('__APP_VERSION__', 'test-version');
    const e = await loadCase('C1').catch((x: unknown) => x);
    expect(e).toBeInstanceOf(ArtifactUnavailable);
    expect((e as ArtifactUnavailable).reason.en).toContain('C1/trace.json');
    expect((e as ArtifactUnavailable).reason.es).toContain('C1/trace.json');
    expect(fetch.mock.calls.some((c) => String(c[0]).includes('C1/trace.json'))).toBe(false);
  });
  it('loadIndex rejects with ArtifactUnavailable when the case-index row is missing', async () => {
    serve(doc(entry('case-index', 'missing')));
    vi.stubGlobal('__APP_VERSION__', 'test-version');
    await expect(loadIndex()).rejects.toBeInstanceOf(ArtifactUnavailable);
  });
  it('loadCase reads the case when the document lists nothing absent, and when the document is unreadable', async () => {
    serve(doc(entry('trace', 'stale')));
    vi.stubGlobal('__APP_VERSION__', 'test-version');
    await expect(loadCase('C1')).resolves.toMatchObject({ trace: { case_id: 'C1' } });
    resetReadiness();
    serve({ nope: 1 });
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    await expect(loadCase('C1')).resolves.toMatchObject({ trace: { case_id: 'C1' } });
    err.mockRestore();
  });
});
