// The name of method B5 (unit U2b of 0.02.004): the method is a weighted-cost continuation of the efficiency-uniformity trade-off, and its own
// paper shows its points are not the Pareto front (4 to 7 of its 20 points are dominated by weighted GS iterates). No reader text of the app,
// in English or Spanish, names B5 or its points a "Pareto front" or a "front"; the name where a true non-dominated set of measured points is
// described stays (the allow-list below, each entry the one place where the set is computed). The identifiers (the id `B5`, the contract key
// `pareto`, the `front` series kind, the tab id `pareto`) are not reader text and are not checked.
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { LADDER } from './ladder';

const SRC = fileURLToPath(new URL('../..', import.meta.url));
const DIST = fileURLToPath(new URL('../../../dist', import.meta.url));
const SDD = readFileSync(new URL('../../../../docs/design/SDD.md', import.meta.url), 'utf8');

/** The reader texts that keep the name because they describe a non-dominated set computed from measured points (rule of the unit's brief). */
const NON_DOMINATED_USES = [
  // Story page, stage of the spread-against-efficiency chart: the front drawn is `onFront`, the non-dominated points of the methods' medians.
  { file: 'pages/Story.tsx', contains: 'the quartile ranges and the Pareto front' },
  { file: 'pages/Story.tsx', contains: 'los rangos intercuartiles y el frente de Pareto' },
];

/** Phrases that name B5 or its points as a front, in both languages. */
const PHRASES = [
  /pareto fronts?\b/i,
  /frentes? de pareto/i,
  /efficiency-uniformity fronts?\b/i,
  /frentes? (de )?(la )?eficiencia-uniformidad/i,
  /fronts? of efficiency-uniformity/i,
  /\bfront points\b/i,
  /\bpuntos del frente\b/i,
  /\b(the|a|its|whole|schematic|efficient) front\b/i,
  /\bel frente (completo|de eficiencia|esquem|eficiencia)/i,
];

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, out);
    else out.push(p);
  }
  return out;
}

const rel = (p: string, base: string) => p.slice(base.length).replaceAll('\\', '/').replace(/^\//, '');
const allowed = (file: string, text: string) => NON_DOMINATED_USES.some((u) => u.file === file && text.includes(u.contains));

function offences(files: string[], base: string): string[] {
  const out: string[] = [];
  for (const f of files) {
    const file = rel(f, base);
    readFileSync(f, 'utf8')
      .split('\n')
      .forEach((line, i) => {
        for (const re of PHRASES) {
          const m = re.exec(line);
          if (m && !allowed(file, line)) out.push(`${file}:${i + 1}: ${m[0]}`);
        }
      });
  }
  return out;
}

describe('the name of method B5 in the app', () => {
  it('is Efficiency-uniformity continuation in both languages', () => {
    const b5 = LADDER.find((r) => r.id === 'B5');
    expect(b5?.name).toEqual({ en: 'Efficiency-uniformity continuation', es: 'Continuación eficiencia-uniformidad' });
    expect(b5?.short.en).not.toMatch(/front/i);
    expect(b5?.short.es).not.toMatch(/frente/i);
  });

  it('is the name of the SDD ladder row', () => {
    const row = SDD.split('\n').find((l) => l.startsWith('| BS-5 |')) ?? '';
    const method = row.split('|')[3]?.trim() ?? '';
    expect(method).toBe('Efficiency-uniformity continuation (engine id B5)');
    expect(method).not.toMatch(/pareto|front/i);
  });

  it('is never a Pareto front or a front in the source strings', () => {
    const files = walk(SRC).filter((f) => /\.(tsx?|svg)$/.test(f) && !/\.test\.tsx?$/.test(f));
    expect(files.length).toBeGreaterThan(50);
    expect(offences(files, SRC)).toEqual([]);
  });

  it('keeps the name only where a non-dominated set of measured points is described', () => {
    const story = readFileSync(join(SRC, 'pages/Story.tsx'), 'utf8');
    for (const u of NON_DOMINATED_USES) expect(story, u.contains).toContain(u.contains);
    expect(story).toContain('onFront');
  });

  const built = existsSync(DIST) ? it : it.skip;
  built('is never a Pareto front or a front in the built text (run after npm run build)', () => {
    const files = walk(DIST).filter((f) => /\.(html|js|json|svg)$/.test(f) && !f.includes('/data/'.replaceAll('/', '\\')) && !/[\\/]data[\\/]/.test(f));
    const out: string[] = [];
    for (const f of files) {
      const text = readFileSync(f, 'utf8');
      for (const re of PHRASES) {
        const g = new RegExp(re.source, 'gi');
        for (const m of text.matchAll(g)) {
          const ctx = text.slice(Math.max(0, m.index - 40), m.index + m[0].length + 40);
          if (!NON_DOMINATED_USES.some((u) => ctx.includes(u.contains.slice(-30)))) out.push(`${rel(f, DIST)}: ${ctx.replace(/\s+/g, ' ')}`);
        }
      }
    }
    expect(out).toEqual([]);
  });
});
