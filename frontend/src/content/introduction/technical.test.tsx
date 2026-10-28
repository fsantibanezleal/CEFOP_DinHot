// The technical view of the Introduction (English render; the Spanish strings are read from the source below): the five areas of ADR-0017 section 2.1 with what the gate measures in each
// (dense paragraphs, captioned equations, the glossary, the ordered steps, the one honest callout), every citation resolved, no measured
// DinHot number, no em-dash and no arrow, and Spanish with its accents. The shell's own gate measures the built page; this test fails
// earlier and names the area.
import { CitationsProvider, useLangStore } from '@fasl-work/caos-app-shell';
import { readFileSync } from 'node:fs';
import { renderToString } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';
import { CITATIONS } from '../citations';
import { INTRODUCTION_CITATIONS } from '../citations/introduction';
import { METHODOLOGY_CITATIONS } from '../citations/methodology';
import { TechnicalView } from './technical';

const ITEMS = [...CITATIONS, ...METHODOLOGY_CITATIONS, ...INTRODUCTION_CITATIONS];

function render(lang: 'en' | 'es'): string {
  useLangStore.setState({ lang });
  return renderToString(
    <CitationsProvider items={ITEMS}>
      <MemoryRouter>
        <TechnicalView />
      </MemoryRouter>
    </CitationsProvider>,
  );
}

const text = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&quot;|&#x27;|&amp;/g, ' ').replace(/\s+/g, ' ');
const section = (html: string, area: string) => {
  const re = new RegExp(`<section[^>]*data-area="${area}"[\\s\\S]*?(?=<section|$)`);
  return html.match(re)?.[0] ?? '';
};
const dense = (html: string) => [...html.matchAll(/<p[^>]*>([\s\S]*?)<\/p>/g)].filter((m) => text(m[1]).trim().split(' ').length >= 40).length;

afterEach(() => useLangStore.setState({ lang: 'en' }));

describe('the technical view (English render)', () => {
  const html = render('en');

  it('declares the five areas of ADR-0017 section 2.1, each with the content it requires', () => {
    for (const area of ['problem', 'principles', 'math', 'pipeline', 'honesty']) expect(section(html, area), area).not.toBe('');
    expect(dense(section(html, 'problem'))).toBeGreaterThanOrEqual(2);
    expect(dense(section(html, 'principles'))).toBeGreaterThanOrEqual(2);
    expect(dense(section(html, 'honesty'))).toBeGreaterThanOrEqual(1);
    expect((section(html, 'pipeline').match(/<li/g) ?? []).length).toBeGreaterThanOrEqual(4);
    expect(html).toContain('data-glossary');
    expect((section(html, 'math').match(/data-glossary-item/g) ?? []).length).toBeGreaterThanOrEqual(10);
  });

  it('holds at least 3 captioned equations, at least 1 figure and exactly 1 honest callout', () => {
    const equations = (html.match(/class="equation"/g) ?? []).length;
    expect(equations).toBeGreaterThanOrEqual(3);
    expect((html.match(/class="equation-caption"/g) ?? []).length).toBe(equations);
    expect((html.match(/<svg[^>]*role="img"/g) ?? []).length).toBeGreaterThanOrEqual(2);
    expect((html.match(/data-callout="honest"/g) ?? []).length).toBe(1);
  });

  it('resolves every citation and uses no literal colour in its figures', () => {
    expect(html).not.toMatch(/unknown reference|missing citation|\[\?\]/i);
    expect(html).not.toMatch(/(fill|stroke)="#[0-9a-f]{3,8}"/i);
  });

  it('carries no em-dash, no arrow, and no DinHot measured number', () => {
    const t = text(html);
    expect(t).not.toMatch(new RegExp('[\u2014\u2015\u2190-\u21FF\u27F5-\u27FF]'));
    // the page quotes published figures only through citations; none of the benchmark's own units appears as a result
    expect(t).not.toMatch(/\b\d+(\.\d+)? ?(ms per iteration|x faster|times faster)\b/i);
  });
});

describe('the Spanish text', () => {
  // The server render cannot switch the language (the shell's store answers 'en' on the server), so the Spanish strings are read from
  // the source: they must carry their accents and never an unaccented form of a word that takes one.
  const source = readFileSync(new URL('./technical.tsx', import.meta.url), 'utf8') + readFileSync(new URL('./figure.tsx', import.meta.url), 'utf8');
  it('is written as Spanish, with its accents', () => {
    for (const w of ['Holograma', 'Convergencia', 'Dinámica', 'física', 'matemática', 'Aberraciones', 'óptica', 'Introducción']) expect(source).toContain(w);
    expect(source).not.toMatch(/(Dinamica|fisica|matematica|optica|Introduccion|Metodologia|informacion|ubicacion)/);
  });
});
