// The Introduction's two views (problem-context-first.md): the shell's ExecutiveView first and open, with its landing block and
// its five sub-tabs, and the technical view second (WB-006).
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import { readFileSync } from 'node:fs';
import { renderToString } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import executive from '../../../content/executive.json';
import { CITATIONS } from '../content/citations';
import { Introduction, IntroductionPage } from './Introduction';
import { Methodology } from './Methodology';

const page = (node: React.ReactNode) =>
  renderToString(
    <CitationsProvider items={CITATIONS}>
      <MemoryRouter>{node}</MemoryRouter>
    </CitationsProvider>,
  );

const escaped = (s: string) => s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');

describe('the Introduction', () => {
  it('the Introduction opens on the executive view rendered from content/executive.json at schema 2.0.0', () => {
    const html = page(<Introduction />);
    expect(html).toContain('data-executive-view');
    expect(html).toContain('data-executive-schema="2.0.0"');
    expect(html).toContain('data-executive-valid="true"');
    // the executive tab is the first and the selected one; the technical view is the second and is not rendered while closed
    const tabs = [...html.matchAll(/<button[^>]*role="tab"[^>]*aria-selected="(true|false)"[^>]*>([^<]*)</g)].map((m) => [m[1], m[2]]);
    expect(tabs.slice(0, 2)).toEqual([
      ['true', 'Executive'],
      ['false', 'Technical'],
    ]);
    // the landing block: the problem's title, the key statement and the headline figures with their values
    expect(html).toContain(escaped(executive.title.en));
    expect(html).toContain(escaped(executive.key_statement.en.split('. ')[0]));
    for (const f of executive.headline_figures) expect(html).toContain(escaped(f.value.en));
    // the five sub-tabs, titled as the standard titles them, the first open with its key message line
    const sub = [...html.matchAll(/<button[^>]*role="tab"[^>]*>([^<]*)</g)].map((m) => m[1]);
    for (const title of ['The pain', 'The context', 'The current situation', 'The trends', 'The proposal']) expect(sub).toContain(title);
    expect(html).toContain(escaped(executive.pain.key_message.en));
    // the rubric of the old view is gone, and so is the old brief
    for (const old of ['Industry &amp; Exec Tailoring', 'AI Transformation Story', '4Cs Positioning', 'Delivery &amp; Credibility', 'What this product is']) expect(html).not.toContain(old);
  });

  it('adversarial: an invalid data file renders the error state and not a blank view', () => {
    const bad = JSON.parse(JSON.stringify(executive));
    delete bad.pain.bearers[1].cost;
    const html = page(<IntroductionPage data={bad} />);
    expect(html).toContain('data-executive-valid="false"');
    expect(html).toContain('pain.bearers[1].cost');
    expect(html).not.toContain('data-executive-valid="true"');
  });

  it('adversarial: a file in the old format (schema 1.0.0) is refused with the state of the 0.12.0 fields', () => {
    const html = page(<IntroductionPage data={{ executive: { en: 'Chief Operating Officer', es: 'Director de Operaciones' }, initiative: executive.title }} />);
    expect(html).toContain('data-executive-valid="false"');
  });

  it('adversarial: the Introduction takes the same full-width document layout as Methodology, and sets no reading column of its own', () => {
    // the shell's DocPage renders `page-body wide` (shell 0.13.1; 0.13.0 left the Introduction without `wide`) (WB-011)
    const layout = (html: string) => html.match(/<div class="(page-body[^"]*)" data-doc-page/)?.[1];
    expect(layout(page(<Introduction />))).toContain('wide');
    expect(layout(page(<Introduction />))).toBe(layout(page(<Methodology />)));
    const source = readFileSync(new URL('./Introduction.tsx', import.meta.url), 'utf8');
    expect(source).not.toMatch(/max-width|maxWidth|reading-column/);
  });
});
