// The Experiments page against the committed bake (data/derived): every template of the page is filled in both languages from the real
// artifacts, no template holds a number of its own, no value the text asks for is missing, every range the bake checked is read as inside,
// the oracle ratios are the ones the bake accepted, and each case section renders the two dense paragraphs the gate counts. The suite is
// skipped, with the path named, while the bake is absent.
import { CitationsProvider, formatNumber, useLangStore } from '@fasl-work/caos-app-shell';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { renderToString } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseIndex, CaseManifest, Trace } from '../../lib/contract.types';
import { CITATIONS } from '../citations';
import { EXPERIMENTS_CITATIONS } from '../citations/experiments';
import { METHODOLOGY_CITATIONS } from '../citations/methodology';
import { bakeRows, CASES, common, type Fmt, type Lang } from './cases';
import { fill, particleOracle, planesUm, pupilDepthOfField, rangeScore, tokensOf, unregisteredMethods, type CaseView } from './data';
import { AbsentSection, CaseSection, GENERIC, REFUSED } from './views';

const root = new URL('../../../../data/derived/', import.meta.url);
const present = existsSync(new URL('manifests/index.json', root));
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, root), 'utf8')) as T;

function load(): { index: CaseIndex; views: CaseView[] } {
  const index = read<CaseIndex>('manifests/index.json');
  const views: CaseView[] = [];
  for (const entry of index.cases) {
    if (entry.path === null) continue;
    const manifest = read<CaseManifest>(entry.path);
    views.push({ entry, manifest, trace: read<Trace>(manifest.artifact.path) });
  }
  return { index, views };
}

const fmt = (lang: Lang, ids: string[]): Fmt => {
  const n: Fmt['n'] = (v, o) => (v === null || v === undefined || !Number.isFinite(v) ? '-' : formatNumber(v, lang, { grouping: false, ...(o ?? { digits: 3 }) }));
  return { lang, caseIds: ids, n, pct: (v, o) => `${n(v, o)} %` };
};

// ids (C02, M07, B4), years of a citation and the word 3D are not numbers of the page
const strip = (s: string) => s.replace(/\{\w+\}/g, '').replace(/\b[CMBP]\d{1,2}\b/g, '').replace(/\b(19|20)\d{2}\b/g, '').replace(/\b3D\b/g, '');

const dense = (html: string, area: string): number => {
  const re = new RegExp(`<section[^>]*data-area="${area}"[\\s\\S]*?</section>`, 'g');
  let count = 0;
  for (const sec of html.match(re) ?? []) {
    for (const p of sec.match(/<p[^>]*>[\s\S]*?<\/p>/g) ?? []) {
      const words = p.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().split(' ').filter(Boolean).length;
      if (words >= 40) count += 1;
    }
  }
  return count;
};

afterEach(() => useLangStore.setState({ lang: 'en' }));

describe.skipIf(!present)('the Experiments page reads the committed bake', () => {
  const { index, views } = present ? load() : { index: { cases: [] } as unknown as CaseIndex, views: [] as CaseView[] };
  const ids = index.cases.map((c) => c.case_id);

  it('reads the cases of the index at run time (a thirteenth appears when it lands)', () => {
    expect(index.cases.length).toBeGreaterThanOrEqual(12);
    expect(views.length).toBe(index.cases.filter((c) => c.status !== 'refused').length);
    expect(index.cases.filter((c) => c.status === 'refused').map((c) => c.case_id)).toContain('C11_outside_field');
  });

  it('holds no number of its own in any template, in either language', () => {
    const all: [string, string][] = [
      ...Object.entries(CASES).flatMap(([id, c]): [string, string][] => [
        [`${id}.setup.en`, c.setup.en],
        [`${id}.setup.es`, c.setup.es],
        [`${id}.result.en`, c.result.en],
        [`${id}.result.es`, c.result.es],
        [`${id}.question.en`, c.question.en],
        [`${id}.question.es`, c.question.es],
      ]),
      ['generic.setup.en', GENERIC.setup.en],
      ['generic.setup.es', GENERIC.setup.es],
      ['generic.result.en', GENERIC.result.en],
      ['generic.result.es', GENERIC.result.es],
      ...(['refused', 'other'] as const).flatMap((k) => (['p1', 'p2'] as const).flatMap((p): [string, string][] => [[`${k}.${p}.en`, REFUSED[k][p].en], [`${k}.${p}.es`, REFUSED[k][p].es]])),
    ];
    const bad = all.filter(([, t]) => /\d/.test(strip(t))).map(([k, t]) => `${k}: ${strip(t).match(/.{0,25}\d.{0,15}/)?.[0]}`);
    expect(bad).toEqual([]);
  });

  it('gives every template the same tokens in English and in Spanish', () => {
    for (const [id, c] of Object.entries(CASES)) {
      for (const k of ['setup', 'result'] as const) {
        expect(tokensOf(c[k].es).sort(), `${id}.${k}`).toEqual(tokensOf(c[k].en).sort());
      }
    }
  });

  for (const lang of ['en', 'es'] as const) {
    it(`fills every template of every baked case from the artifacts (${lang})`, () => {
      const f = fmt(lang, ids);
      for (const v of views) {
        const text = CASES[v.manifest.case_id];
        expect(text, `${v.manifest.case_id} has written text`).toBeDefined();
        const vals = text.vals(v, f);
        for (const k of ['setup', 'result'] as const) {
          const out = fill(text[k][lang], vals);
          expect(out, `${v.manifest.case_id}.${k}`).not.toMatch(/\{|NaN|undefined/);
          const missing = tokensOf(text[k][lang]).filter((t) => vals[t] === '-');
          expect(missing, `${v.manifest.case_id}.${k} has a token with no value`).toEqual([]);
        }
        if (lang === 'es') expect(Object.values(vals).join(' ')).not.toMatch(/\d\.\d/);
      }
    });
  }

  it('reads every checked range of every method as inside (the bake passed them)', () => {
    for (const v of views)
      for (const id of Object.keys(v.manifest.methods)) {
        const s = rangeScore(v.manifest, id);
        expect(s.ok, `${v.manifest.case_id} ${id}`).toBe(s.of);
      }
  });

  it('computes the oracle ratio inside the range the bake checked', () => {
    for (const v of views.filter((x) => x.trace.dynamics)) {
      const o = particleOracle(v);
      expect(o, v.manifest.case_id).not.toBeNull();
      const r = v.manifest.expect['fc_ratio'];
      expect(o!.ratio).toBeGreaterThanOrEqual(r[0]);
      expect(o!.ratio).toBeLessThanOrEqual(r[1]);
    }
  });

  it('writes the table rows of the bake from the manifest, with a verdict for every range', () => {
    const f = fmt('en', ids);
    for (const v of views) {
      const rows = bakeRows(v, f);
      expect(rows.length, v.manifest.case_id).toBeGreaterThan(0);
      for (const r of rows) expect(r.reading, `${v.manifest.case_id}: ${r.label}`).toBe('inside');
      const extra = CASES[v.manifest.case_id]?.extra?.(v, f) ?? [];
      for (const r of extra) expect(r.published, r.label).toMatch(/\d/);
    }
  });

  it('derives the geometry of the multi-plane case from the record', () => {
    const c05 = views.find((v) => v.manifest.case_id === 'C05_multiplane_vortices');
    expect(c05).toBeDefined();
    expect(planesUm(c05!.manifest).length).toBeGreaterThan(1);
    expect(pupilDepthOfField(c05!.manifest).naPupil).toBeGreaterThan(0);
    const t = c05!.manifest.params.target;
    expect(common(c05!, fmt('en', ids)).n).toBe(String('traps' in t ? t.traps.length : 0));
  });

  it('names the methods the bake could not register from the flags', () => {
    const planted = { ...views[0], manifest: { ...views[0].manifest, flags: [...views[0].manifest.flags, { case_id: views[0].manifest.case_id, flag: 'methods not registered in this build: B3, M17' }] } };
    expect(unregisteredMethods([planted, ...views.slice(1)])).toEqual(expect.arrayContaining(['B3', 'M17']));
    // the committed bake names only ladder ids, if any
    for (const id of unregisteredMethods(views)) expect(id).toMatch(/^(M(0[1-9]|1[0-9])|B[1-5])$/);
  });

  for (const lang of ['en', 'es'] as const) {
    it(`renders the section of every case with two dense paragraphs (${lang})`, () => {
      useLangStore.setState({ lang });
      const items = [...CITATIONS, ...METHODOLOGY_CITATIONS, ...EXPERIMENTS_CITATIONS];
      for (const v of views) {
        const html = renderToString(
          <CitationsProvider items={items}>
            <MemoryRouter>
              <CaseSection view={v} caseIds={ids} />
            </MemoryRouter>
          </CitationsProvider>,
        );
        expect(dense(html, 'question'), v.manifest.case_id).toBeGreaterThanOrEqual(2);
        expect(html).not.toMatch(/[\u2014\u2192]/);
      }
      for (const e of index.cases.filter((c) => c.status === 'refused')) {
        const html = renderToString(
          <CitationsProvider items={items}>
            <MemoryRouter>
              <AbsentSection item={{ caseId: e.case_id, title: e.title, reason: e.reason! }} status={e.status} />
            </MemoryRouter>
          </CitationsProvider>,
        );
        expect(dense(html, 'question'), e.case_id).toBeGreaterThanOrEqual(2);
      }
    });
  }

  it('keeps the source of the page free of em-dashes and arrows', () => {
    const dir = new URL('./', import.meta.url);
    for (const f of readdirSync(dir).filter((x) => /\.(ts|tsx)$/.test(x) && !x.endsWith('.test.tsx'))) {
      expect(readFileSync(new URL(f, dir), 'utf8'), f).not.toMatch(/[\u2014\u2192\u2190\u21d2]/);
    }
  });
});
