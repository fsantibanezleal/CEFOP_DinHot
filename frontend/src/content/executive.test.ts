// The example's executive view (CAOS_MANAGE conventions/problem-context-first.md, decided 2026-10-13): an executive frame of a
// problem space, general, never a client and never a pitch, valid against the shell's schema 2.0.0, with three illustrations
// that meet the standard the shell's gate measures in the page (WB-007).
import { readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { EXECUTIVE_SCHEMA_VERSION, FOUR_CS, validateExecutive } from '@fasl-work/caos-app-shell';
import { describe, expect, it } from 'vitest';
import executive from '../../../content/executive.json';
import pkg from '../../package.json';

const PUBLIC = new URL('../../public/', import.meta.url);
const NAMES = ['pain', 'situation', 'proposal'] as const;
const read = (name: (typeof NAMES)[number]) => readFileSync(new URL(executive.illustrations[name].file as string, PUBLIC), 'utf8');

const TOKEN = /^(none|currentColor|var\(--color-[a-z0-9-]+\))$/;

/** What is wrong with one illustration, in the terms of the gate: literal colours, charts, labels without a twin, no viewBox. */
export function svgProblems(svg: string): string[] {
  const out: string[] = [];
  if (!/viewBox="[^"]+"/.test(svg)) out.push('no viewBox');
  if (/<(img|image|script|foreignObject)\b/i.test(svg)) out.push('holds an img, image, script or foreignObject');
  if (/data-chart/i.test(svg)) out.push('declares a chart (data-chart)');
  if (/#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(/i.test(svg)) out.push('a literal colour');
  for (const m of svg.matchAll(/\b(fill|stroke|stop-color|flood-color)="([^"]*)"/g)) {
    if (!TOKEN.test(m[2])) out.push(`${m[1]}="${m[2]}" is not a theme token`);
  }
  for (const m of svg.matchAll(/style="([^"]*)"/g)) {
    if (/(fill|stroke|color)\s*:/.test(m[1])) out.push('a colour set in a style attribute');
  }
  const count = (lang: string) => [...svg.matchAll(new RegExp(`<text[^>]*data-lang="${lang}"`, 'g'))].length;
  if (count('en') < 5) out.push(`only ${count('en')} English label(s)`);
  if (count('en') !== count('es')) out.push(`${count('en')} English and ${count('es')} Spanish labels`);
  if (/<text(?![^>]*data-lang=)/.test(svg)) out.push('a label with no data-lang');
  if (/font-family/.test(svg)) out.push('a label sets its own font family');
  return [...new Set(out)];
}

/** The geometry of every rectangle, so two scenes can be compared for the setting they share. */
const rects = (svg: string) => new Set([...svg.matchAll(/<rect x="([\d.-]+)" y="([\d.-]+)" width="([\d.-]+)" height="([\d.-]+)"/g)].map((m) => m.slice(1, 5).join(',')));

// The shell's own analysis of an animated SVG (gate/areas.mjs, the module the gate and the template's guard script share); the
// path is a variable so the type checker does not read the untyped module.
const AREAS = fileURLToPath(new URL('../../node_modules/@fasl-work/caos-app-shell/gate/areas.mjs', import.meta.url));
const { analyseSvgAnimation, animationFailures, FLIP_LIMITS } = (await import(/* @vite-ignore */ pathToFileURL(AREAS).href)) as {
  analyseSvgAnimation: (svg: string) => { animated: boolean; reducedBlock: boolean; neutralises: boolean; seconds: number };
  animationFailures: (a: unknown, name: string) => string[];
  FLIP_LIMITS: { title: Record<'en' | 'es', number>; back: Record<'en' | 'es', number> };
};

const words = (t: string) => t.split(/\s+/).filter((w) => /[\p{L}\p{N}]/u.test(w)).length;
type Bi = { en: string; es: string };
/** The labels the shell prints on the back of a card (ExecutiveView.tsx UI table), so a back is counted as the gate counts it. */
const LABELS = {
  cost: { en: 'Cost', es: 'Costo' },
  measure: { en: 'Measured by', es: 'Se mide por' },
  decides: { en: 'Decides', es: 'Decide' },
  needs: { en: 'Needs', es: 'Necesita' },
  achieves: { en: 'Achieves', es: 'Logra' },
  fallsShort: { en: 'Falls short', es: 'Se queda corto' },
} satisfies Record<string, Bi>;
/** The four flip groups: the title field and the fields (with their label) that make the back. A source mark adds one more token. */
const FLIP_GROUPS: Record<string, { rows: any[]; title: (r: any) => Bi; back: (r: any) => Array<[Bi | null, Bi]>; extra: number }> = {
  'pain.bearers': { rows: executive.pain.bearers, title: (r) => r.who, back: (r) => [[LABELS.cost, r.cost], [LABELS.measure, r.measure]], extra: 0 },
  'situation.roles': { rows: executive.situation.roles, title: (r) => r.role, back: (r) => [[LABELS.decides, r.decides], [LABELS.needs, r.needs]], extra: 0 },
  'situation.state_of_the_art': {
    rows: executive.situation.state_of_the_art,
    title: (r) => r.approach,
    back: (r) => [[LABELS.achieves, r.achieves], [LABELS.fallsShort, r.falls_short]],
    extra: 1,
  },
  'proposal.four_cs': { rows: executive.proposal.four_cs, title: (r) => r.c, back: (r) => [[null, r.applies]], extra: 0 },
};

/** The cards of the flip groups that break the shell's limits, one line each (the gate's G16 reads the rendered cards; this reads the data). */
function flipProblems(groups: typeof FLIP_GROUPS): string[] {
  const out: string[] = [];
  for (const lang of ['en', 'es'] as const) {
    for (const [path, g] of Object.entries(groups)) {
      for (const [i, row] of g.rows.entries()) {
        const title = words(g.title(row)[lang]);
        if (title > FLIP_LIMITS.title[lang]) out.push(`${path}[${i}] title ${lang}: ${title} words, the limit is ${FLIP_LIMITS.title[lang]}`);
        const back = g.back(row).reduce((n, [label, text]) => n + (label ? words(label[lang]) : 0) + words(text[lang]), 0) + g.extra;
        if (back > FLIP_LIMITS.back[lang]) out.push(`${path}[${i}] back ${lang}: ${back} words, the limit is ${FLIP_LIMITS.back[lang]}`);
      }
    }
  }
  return out;
}

const clone = () => JSON.parse(JSON.stringify(executive));

/** The floors of the standard (problem-context-first.md) as [min, max] counts of rows; the shell's schema holds the same numbers. */
const FLOORS: Record<string, [number, number]> = {
  headline_figures: [2, 3],
  'pain.paragraphs': [2, 3],
  'pain.bearers': [3, 5],
  'pain.figures': [2, 4],
  'pain.causes': [3, 5],
  'context.paragraphs': [1, 2],
  'context.forces': [3, 4],
  'context.evidence': [1, 4],
  'situation.roles': [3, 5],
  'situation.state_of_the_art': [3, 5],
  'trends.items': [3, 5],
  'proposal.paragraphs': [1, 2],
  'proposal.four_cs': [4, 4],
  'proposal.actions': [3, 6],
  'proposal.risks': [1, 4],
  'proposal.unknowns': [1, 4],
};

/** The source ids cited in each part of the file: 0 is the landing, 1 to 4 the sub-tabs that cite (the proposal cites none). */
function citations(): Array<{ source: string; tab: number }> {
  const out: Array<{ source: string; tab: number }> = [];
  const walk = (node: unknown, tab: number) => {
    if (Array.isArray(node)) node.forEach((n) => walk(n, tab));
    else if (node && typeof node === 'object') {
      for (const [k, v] of Object.entries(node)) {
        if (k === 'source' && typeof v === 'string') out.push({ source: v, tab });
        else walk(v, tab);
      }
    }
  };
  walk(executive.headline_figures, 0);
  walk(executive.pain, 1);
  walk(executive.context, 2);
  walk(executive.situation, 3);
  walk(executive.trends, 4);
  return out;
}

describe('the example executive view', () => {
  it('the shell is pinned exactly at 0.19.1 (0.14.0 brought flip cards, carousels, animated illustrations and Focus mode; 0.15.0 added the G19 value check; 0.16.0 gave SurfacePage Focus; 0.19.0 added Tier A chart interaction and accessible data tables; 0.19.1 improves narrow table flow and Spanish time-axis labels)', () => {
    expect(pkg.dependencies['@fasl-work/caos-app-shell']).toBe('0.19.1');
    expect(EXECUTIVE_SCHEMA_VERSION).toBe('2.0.0');
  });

  it('the example executive data is valid against schema 2.0.0', () => {
    expect(validateExecutive(executive)).toEqual([]);
    expect(FOUR_CS).toHaveLength(4);
    expect(executive.proposal.four_cs.map((r) => r.c.en)).toEqual(['Choice', 'Context', 'Cost', 'Control']);
  });

  it('the example meets every floor of the standard, in the sub-tabs and the landing', () => {
    const at = (path: string): unknown[] => path.split('.').reduce((node: any, key) => node[key], executive);
    for (const [path, [min, max]] of Object.entries(FLOORS)) {
      const n = at(path).length;
      expect(n, path).toBeGreaterThanOrEqual(min);
      expect(n, path).toBeLessThanOrEqual(max);
    }
    expect(executive.pain.figures.length + executive.context.evidence.length + executive.situation.state_of_the_art.length).toBeGreaterThanOrEqual(7);
  });

  it('every source is a titled https link that some figure or claim cites, and no sub-tab names more than six', () => {
    const cited = new Set(citations().map((c) => c.source));
    expect(executive.sources.length).toBeGreaterThanOrEqual(8);
    for (const s of executive.sources) {
      expect(s.url, s.id).toMatch(/^https:\/\/[^\s]+$/);
      expect(s.title.en.length, s.id).toBeGreaterThan(10);
      expect(s.title.es.length, s.id).toBeGreaterThan(10);
      expect(cited.has(s.id), s.id).toBe(true);
    }
    for (const tab of [1, 2, 3, 4]) {
      const ids = new Set(citations().filter((c) => c.tab === tab).map((c) => c.source));
      expect(ids.size, `sub-tab ${tab}`).toBeLessThanOrEqual(6);
    }
  });

  it('the example frames a problem space: no organisation, no client, no product and no call to act on a product', () => {
    const text = JSON.stringify({ ...executive, sources: undefined });
    expect(text).not.toMatch(/\b(NHS|Kaiser|Mayo|Clinic|Inc\.|Ltd|GmbH)\b/);
    expect(text).not.toMatch(/\b(our client|nuestro cliente|workbench|banco de trabajo|this product|este producto|the app|la app)\b/i);
    expect(text).not.toMatch(/\bSIR\b/);
  });

  it('every flip card of the four flip groups is small: a title and a back within the limits of the shell, in both languages (WB-012)', () => {
    expect(flipProblems(FLIP_GROUPS)).toEqual([]);
  });

  it('adversarial: a flip card with a title or a back over the limits is named, and a group of four cards is not a carousel (WB-012)', () => {
    const bearers = clone().pain.bearers;
    bearers[1].who.en = 'Patients on planned care lists who wait for a bed that is never free';
    bearers[2].cost.es = Array.from({ length: 48 }, () => 'palabra').join(' ');
    const planted = { ...FLIP_GROUPS, 'pain.bearers': { ...FLIP_GROUPS['pain.bearers'], rows: bearers } };
    const found = flipProblems(planted).join(' | ');
    expect(found).toContain('pain.bearers[1] title en');
    expect(found).toContain('pain.bearers[2] back es');
    const four = Object.entries(FLIP_GROUPS).filter(([, g]) => g.rows.length >= 5).length;
    const without = Object.values({ ...FLIP_GROUPS, 'pain.bearers': { ...FLIP_GROUPS['pain.bearers'], rows: bearers.slice(0, 4) } }).filter((g) => g.rows.length >= 5).length;
    expect(without).toBe(four - 1);
  });

  it('the example holds a carousel: a flip group of five or more cards, each with real content (WB-012)', () => {
    const long = Object.entries(FLIP_GROUPS).filter(([, g]) => g.rows.length >= 5);
    expect(long.length).toBeGreaterThanOrEqual(1);
    for (const [path, g] of long) {
      const titles = g.rows.map((r) => g.title(r).en);
      expect(new Set(titles).size, `${path} distinct titles`).toBe(titles.length);
      for (const r of g.rows) for (const [, text] of g.back(r)) expect(words(text.en), path).toBeGreaterThanOrEqual(4);
    }
  });

  it('the example has an animated illustration that explains a change, with its reduced-motion final frame, ten seconds at most (WB-013)', () => {
    const animated = NAMES.filter((n) => analyseSvgAnimation(read(n)).animated);
    expect(animated.length).toBeGreaterThanOrEqual(1);
    for (const name of animated) {
      const a = analyseSvgAnimation(read(name));
      expect(a.reducedBlock, `${name} reduced-motion block`).toBe(true);
      expect(a.neutralises, `${name} stops its animation`).toBe(true);
      expect(a.seconds, `${name} seconds`).toBeGreaterThan(0);
      expect(a.seconds, `${name} seconds`).toBeLessThanOrEqual(10);
      expect(animationFailures(a, name), name).toEqual([]);
      expect(svgProblems(read(name)), name).toEqual([]);
    }
  });

  it('adversarial: an animated illustration without its reduced-motion block, or over ten seconds, is refused by the shell analysis (WB-013)', () => {
    const svg = read('pain');
    const noBlock = svg.replace(/@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*?\}\s*\}/, '');
    expect(noBlock).not.toBe(svg);
    expect(animationFailures(analyseSvgAnimation(noBlock), 'pain').join()).toMatch(/reduced-motion/);
    const slow = svg.replace(/(\d+(?:\.\d+)?)s ease/, '14s ease');
    expect(animationFailures(analyseSvgAnimation(slow), 'pain').join()).toMatch(/limit is 10 s/);
  });

  it('the example illustrations use only theme tokens and carry both languages', () => {
    for (const name of NAMES) expect(svgProblems(read(name)), name).toEqual([]);
  });

  it('the illustrations are named pain, situation and proposal and are scenes of people and places, not charts', () => {
    for (const name of NAMES) {
      const svg = read(name);
      expect(executive.illustrations[name].file, name).toBe(`executive/${name}.svg`);
      expect(svg, name).not.toMatch(/<(polyline|image)\b|axis|tick/i);
      expect((svg.match(/<circle\b/g) ?? []).length, `${name} people`).toBeGreaterThanOrEqual(6);
      expect((svg.match(/<(rect|path|circle)\b/g) ?? []).length, `${name} detail`).toBeGreaterThanOrEqual(80);
    }
  });

  it('the pain and the proposal share the setting, so the change is visible between them', () => {
    const [pain, , proposal] = NAMES.map((n) => rects(read(n)));
    const shared = [...pain].filter((r) => proposal.has(r)).length / Math.min(pain.size, proposal.size);
    expect(shared).toBeGreaterThan(0.6);
  });

  it('adversarial: planted literal colours, charts, missing labels, long sentences and broken rules are refused', () => {
    const svg = read('pain');
    expect(svgProblems(svg.replace('var(--color-bad)', '#ff0000'))).toContain('a literal colour');
    expect(svgProblems(svg.replace('var(--color-bad)', 'red')).join()).toMatch(/not a theme token/);
    expect(svgProblems(svg.replace('<svg ', '<svg data-chart="line" '))).toContain('declares a chart (data-chart)');
    expect(svgProblems(svg.replace(/<text data-lang="es"[^>]*>[^<]*<\/text>/, ''))[0]).toMatch(/English and \d+ Spanish/);
    expect(svgProblems(svg.replace(/ viewBox="[^"]*"/, ''))).toContain('no viewBox');

    const long = clone();
    long.pain.key_message.en = Array.from({ length: 31 }, () => 'word').join(' ') + '.';
    expect(validateExecutive(long).map((p) => p.path)).toContain('pain.key_message.en');

    const uncited = clone();
    uncited.sources.push({ id: 'extra', title: { en: 'An extra source', es: 'Una fuente extra' }, url: 'https://example.org/x' });
    expect(validateExecutive(uncited).map((p) => p.message).join()).toMatch(/cited by no figure/);

    const nolink = clone();
    nolink.sources[0].url = 'http://example.org/insecure';
    expect(validateExecutive(nolink).length).toBeGreaterThan(0);

    const owner = clone();
    owner.proposal.actions[0].owner.en = 'A role nobody has';
    expect(validateExecutive(owner).map((p) => p.path)).toContain('proposal.actions[0].owner');

    const weights = clone();
    weights.pain.causes.forEach((c: { weight: number }) => (c.weight = 60));
    expect(validateExecutive(weights).map((p) => p.path)).toContain('pain.causes');

    const pitch = clone();
    pitch.proposal.actions[0].action.en = 'Buy the product now.';
    expect(validateExecutive(pitch).map((p) => p.message).join()).toMatch(/promotional/);

    const fourcs = clone();
    fourcs.proposal.four_cs.reverse();
    expect(validateExecutive(fourcs).map((p) => p.path).join()).toMatch(/four_cs/);
  });
});
