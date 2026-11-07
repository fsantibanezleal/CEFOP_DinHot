// The guided story (ADR-0082 rules 3 to 5): every headline is computed from the loaded artifact and states one finding with its number, in
// at most twelve words and in both languages; a number the artifact does not hold is stated as missing; each step has its three callouts,
// each with a unit, a state and a source that names an artifact field; the deep link of each step opens it and the exit carries the state.
// The artifacts are the real ones of data/derived (test-real.ts), not numbers invented for a fixture.
import { LinkedViewProvider, formatNumber, type SceneCalloutDef } from '@fasl-work/caos-app-shell';
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import type { BenchmarkResults } from '../lib/contract.types';
import { trainCallouts } from '../workbench/OpticalTrain';
import { slmCallouts, slmRow } from '../workbench/SlmSection';
import { methodCallouts } from '../workbench/MethodAtWork';
import { methodName } from '../workbench/model';
import { realCase, realSelection } from '../workbench/test-real';
import {
  COMPARE_CELL,
  DEVICE_STEP_METHOD,
  STEP_DEFS,
  StoryView,
  WEIGHTED_GS,
  compareCallouts,
  compareFinding,
  compareLayout,
  comparePoints,
  deviceFinding,
  exitHref,
  holdCallouts,
  holdFinding,
  methodFinding,
  methodOfStep,
  setupFinding,
  stepDef,
  storySelection,
  wordCount,
  type Finding,
  type Missing,
  type StoryLoaded,
} from './Story';

vi.stubGlobal('__APP_VERSION__', 'test-version');

const bench = (): BenchmarkResults => JSON.parse(readFileSync(new URL('../../../data/derived/benchmark/results.json', import.meta.url), 'utf8')) as BenchmarkResults;
const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
const isFinding = (f: Finding | Missing): f is Finding => 'headline' in f;
const must = <T extends Finding | Missing>(f: T): Exclude<T, Missing> => {
  if (!isFinding(f as Finding | Missing)) throw new Error('the finding is missing');
  return f as Exclude<T, Missing>;
};
const txt = (b: string | { en: string; es: string }, lang: 'en' | 'es'): string => (typeof b === 'string' ? b : b[lang]);

describe('the five steps and their deep links', () => {
  it('are setup, device, method, compare and hold, in the order of the SDD, each on the route /story/<id>', () => {
    expect(STEP_DEFS.map((s) => s.id)).toEqual(['setup', 'device', 'method', 'compare', 'hold']);
    expect(STEP_DEFS.map((s) => s.accent)).toEqual([1, 2, 3, 4, 5]);
    expect(STEP_DEFS.map((s) => s.caseId)).toEqual(['C02_grid_feedback', 'C08_device_limited', 'C02_grid_feedback', 'C02_grid_feedback', 'C01_square_grid']);
  });

  it('the app registers /story/:step and marks /story immersive; an unknown step opens the first', () => {
    const source = readFileSync(new URL('../App.tsx', import.meta.url), 'utf8');
    expect(source).toContain('<Route path="/story/:step" element={<Story />} />');
    expect(source).toContain("immersiveRoutes: ['/story']");
    expect(stepDef('nonsense').id).toBe('setup');
    for (const s of STEP_DEFS) expect(stepDef(s.id)).toBe(s);
  });

  it('the exit lands on /app with the step case, its group of views and the method', () => {
    const device = new URL(exitHref(stepDef('device'), 'B1'), 'https://x.test');
    expect(device.pathname).toBe('/app');
    expect(device.searchParams.get('case')).toBe('C08_device_limited');
    expect(device.searchParams.get('view')).toBe('hologram');
    expect(device.searchParams.get('method')).toBe('B1');
    const method = new URL(exitHref(stepDef('method'), 'M07'), 'https://x.test');
    expect(method.searchParams.get('view')).toBe('convergence');
    expect(new URL(exitHref(stepDef('hold'), null), 'https://x.test').searchParams.has('method')).toBe(false);
    expect(new URL(exitHref(stepDef('hold'), null), 'https://x.test').searchParams.get('view')).toBe('dynamics');
  });
});

describe('the exit method', () => {
  it('is the reference method of the case the step reads: B1 on C08, M07 on C02, M06 on C01', () => {
    const cases = { C02_grid_feedback: { state: 'ready', data: realCase('C02_grid_feedback') }, C08_device_limited: { state: 'ready', data: realCase('C08_device_limited') }, C01_square_grid: { state: 'ready', data: realCase('C01_square_grid') } } as const;
    expect(methodOfStep(stepDef('device'), cases)).toBe('B1');
    expect(methodOfStep(stepDef('setup'), cases)).toBe('M07');
    expect(methodOfStep(stepDef('hold'), cases)).toBe('M06');
    expect(methodOfStep(stepDef('hold'), { ...cases, C01_square_grid: { state: 'loading' } })).toBeNull();
  });
});

describe('the headlines are computed from the artifacts', () => {
  const c02 = realCase('C02_grid_feedback');
  const c08 = realCase('C08_device_limited');
  const c01 = realCase('C01_square_grid');

  it('setup: N is the trap count of the trace and E the reference method efficiency, in both languages', () => {
    const f = must(setupFinding(c02));
    const ref = c02.manifest.params.reference_method;
    const n = c02.trace.traps.length;
    const e = c02.trace.methods[ref].final.efficiency;
    expect(f.n).toBe(n);
    expect(f.eff).toBe(e);
    expect(f.headline.en).toBe(`One beam becomes ${n} traps at ${formatNumber(e * 100, 'en', { decimals: 1 })}% efficiency`);
    expect(f.headline.es).toBe(`Un haz se convierte en ${n} trampas con ${formatNumber(e * 100, 'es', { decimals: 1 })}% de eficiencia`);
    expect(f.headline.es).toMatch(/\d,\d%/);
  });

  it('a different artifact gives a different headline: no number is typed', () => {
    const other = clone(c02);
    const ref = other.manifest.params.reference_method;
    other.trace.methods[ref].final.efficiency = 0.5;
    other.trace.traps = other.trace.traps.slice(0, 7);
    const f = must(setupFinding(other));
    expect(f.headline.en).toBe('One beam becomes 7 traps at 50.0% efficiency');
    expect(must(setupFinding(c02)).headline.en).not.toBe(f.headline.en);
  });

  it('device: the spread of the ideal-model optimizer against the spread on the case device, from the same method', () => {
    const f = must(deviceFinding(c08));
    const m = c08.trace.methods[DEVICE_STEP_METHOD];
    expect(f.ideal.spread).toBe(m.history[m.history.length - 1].rel_std_pct);
    expect(f.device.spread).toBe(m.final.rel_std_pct);
    expect(f.device.spread).toBeGreaterThan(f.ideal.spread);
    expect(f.headline.en).toContain(methodName(DEVICE_STEP_METHOD).en);
    expect(f.headline.es).toContain(methodName(DEVICE_STEP_METHOD).es);
    expect(f.headline.en).toMatch(/from 0\.0045% to 13\.4%/);
    expect(f.headline.es).toMatch(/de 0,0045% a 13,4%/);
  });

  it('method: the first and the last spread of the history and its iteration count', () => {
    const f = must(methodFinding(c02));
    const h = c02.trace.methods[c02.manifest.params.reference_method].history;
    expect(f.first).toBe(h[0].rel_std_pct);
    expect(f.last).toBe(h[h.length - 1].rel_std_pct);
    expect(f.iterations).toBe(h.length);
    expect(f.headline.en).toBe(`The spread falls from 26.8% to 0.014% in ${h.length} iterations`);
    expect(f.headline.es).toBe(`La dispersión cae de 26,8% a 0,014% en ${h.length} iteraciones`);
    expect(f.freeze).toBe(12);
  });

  it('compare: the method with the lowest median spread on the named cell against weighted GS, with the seed counts', () => {
    const b = bench();
    const f = must(compareFinding(b));
    const rows = b.rows.filter((r) => r.geometry === COMPARE_CELL.geometry && r.device === COMPARE_CELL.device && r.budget_kind === 'iterations' && r.budget === COMPARE_CELL.budget && r.params === 'default');
    const lowest = Math.min(...rows.map((r) => r.rel_std_pct.median));
    expect(f.best.spread.median).toBe(lowest);
    const gs = rows.find((r) => r.method === WEIGHTED_GS)!;
    expect(f.gs.spread.median).toBe(gs.rel_std_pct.median);
    expect(f.gs.seeds).toBe(gs.n_seeds);
    expect(f.headline.en).toContain(methodName(WEIGHTED_GS).en);
    expect(f.summary.en).toContain(`${f.best.seeds} seeds`);
    expect(f.summary.en).toContain(`${f.gs.seeds} for`);
    expect(f.summary.en).toContain('Square 10 x 10');
    expect(f.summary.en).toContain('100 iterations');
  });

  it('hold: the stiffness and the corner frequency of the bead', () => {
    const f = must(holdFinding(c01));
    const d = c01.trace.dynamics!;
    expect(f.kappa).toBe(d.kappa_pn_per_um);
    expect(f.fc).toBe(d.fc_hz);
    expect(f.headline.en).toBe(`The bead feels ${formatNumber(d.kappa_pn_per_um!, 'en', { decimals: 2 })} pN/um at a ${formatNumber(d.fc_hz, 'en', { decimals: 1 })} Hz corner frequency`);
    expect(f.headline.es).toContain(formatNumber(d.kappa_pn_per_um!, 'es', { decimals: 2 }));
  });

  it('every headline is at most twelve words in both languages and carries a number', () => {
    const all = [setupFinding(c02), deviceFinding(c08), methodFinding(c02), compareFinding(bench()), holdFinding(c01)].map(must);
    expect(all).toHaveLength(5);
    for (const f of all) {
      for (const lang of ['en', 'es'] as const) {
        const h = f.headline[lang];
        expect(wordCount(h), h).toBeLessThanOrEqual(12);
        expect(h, h).toMatch(/\d/);
      }
    }
  });

  it('a method is named by its catalog name wherever the text mentions its id', () => {
    const all = [setupFinding(c02), deviceFinding(c08), methodFinding(c02), compareFinding(bench()), holdFinding(c01)].map(must);
    const ids = /\b([MB]\d{1,2})\b/g;
    for (const f of all) {
      const texts = [f.headline, f.summary, ...f.facts.map((x) => x.label), ...f.facts.map((x) => x.value)];
      for (const lang of ['en', 'es'] as const) {
        for (const t of texts) {
          const s = t[lang];
          for (const m of s.matchAll(ids)) {
            // the id sits in parentheses right after its name: "Weighted GS (M06)"
            const before = s.slice(0, m.index);
            expect(before.endsWith(`${methodName(m[1])[lang]} (`), `${lang}: ${s}`).toBe(true);
          }
        }
      }
    }
  });
});

describe('a number the artifact does not hold is stated as missing', () => {
  it('no reference method final, no history, no device block, no stiffness, no benchmark cell', () => {
    const c02 = clone(realCase('C02_grid_feedback'));
    delete (c02.trace.methods as Record<string, unknown>)[c02.manifest.params.reference_method];
    expect(setupFinding(c02)).toHaveProperty('missing');
    expect(methodFinding(c02)).toHaveProperty('missing');
    const c08 = clone(realCase('C08_device_limited'));
    c08.manifest.params.device = null;
    expect(deviceFinding(c08)).toHaveProperty('missing');
    const c01 = clone(realCase('C01_square_grid'));
    delete c01.trace.dynamics!.kappa_pn_per_um;
    expect(holdFinding(c01)).toHaveProperty('missing');
    const b = clone(bench());
    b.rows = b.rows.filter((r) => r.method !== WEIGHTED_GS);
    const m = compareFinding(b) as Missing;
    expect(m.missing.en).toContain('is not in the artifact');
    expect(m.missing.es).toContain('no está en el artefacto');
  });

  it('the step then shows the missing line and no invented number', () => {
    const c08 = clone(realCase('C08_device_limited'));
    c08.manifest.params.device = null;
    const html = render('device', { c08: { state: 'ready', data: c08 } });
    expect(html).toContain('data-missing');
    expect(html).toContain('is not in the artifact');
    expect(html).toContain('This number is not available in the release');
  });
});

function loaded(over: Partial<Record<keyof StoryLoaded, StoryLoaded[keyof StoryLoaded]>> = {}): StoryLoaded {
  return {
    c02: { state: 'ready', data: realCase('C02_grid_feedback') },
    c08: { state: 'ready', data: realCase('C08_device_limited') },
    c01: { state: 'ready', data: realCase('C01_square_grid') },
    bench: { state: 'ready', data: bench() },
    ...over,
  } as StoryLoaded;
}
function render(step: string, over: Partial<Record<keyof StoryLoaded, unknown>> = {}, lang: 'en' | 'es' = 'en'): string {
  return renderToStaticMarkup(
    <MemoryRouter>
      <LinkedViewProvider>
        <StoryView stepId={stepDef(step).id} loaded={loaded(over as never)} lang={lang} onStepChange={() => undefined} onExit={() => undefined} />
      </LinkedViewProvider>
    </MemoryRouter>,
  );
}

describe('the story renders each step over the loaded artifacts', () => {
  it('every step renders its number, its headline computed from the artifacts and its panel, in English and in Spanish', () => {
    for (const s of STEP_DEFS) {
      for (const lang of ['en', 'es'] as const) {
        const html = render(s.id, {}, lang);
        expect(html, `${s.id} ${lang}`).toContain('dh-story');
        expect(html).toContain(`data-story-panel="${s.id}"`);
      }
    }
    expect(render('setup')).toContain('One beam becomes 100 traps at 79.8% efficiency');
    // the frame's own language is the shell's store (English here); the panel follows the `lang` the page passes from the same store
    expect(render('setup', {}, 'es')).toContain('Dividir el haz');
    expect(render('setup', {}, 'es')).toContain('79,8 %');
    expect(render('hold')).toContain('The bead feels 4.01 pN/um');
    expect(render('compare')).toContain('Square 10 x 10');
  });

  it('a case that fails to load shows the unavailable state with its reason and the link back to the App', () => {
    const html = render('device', { c08: { state: 'unavailable', reason: { en: 'C08 is not available yet: the pipeline did not write it', es: 'C08 aún no está disponible' } } });
    expect(html).toContain('data-state="unavailable"');
    expect(html).toContain('the pipeline did not write it');
    expect(html).toContain('href="/app?case=C08_device_limited&amp;view=hologram"');
    const es = render('device', { c08: { state: 'error', error: 'HTTP 500' } }, 'es');
    expect(es).toContain('Volver a la App');
  });

  it('the other steps still name their findings while one case is loading', () => {
    const html = render('hold', { c08: { state: 'loading' } });
    expect(html).toContain('The bead feels 4.01 pN/um');
  });
});

const hasFields = (items: SceneCalloutDef[]) => {
  expect(items).toHaveLength(3);
  for (const c of items) {
    expect(c.value, c.id).not.toBe('');
    expect(c.unit, c.id).toBeTruthy();
    expect(['alarm', 'warning', 'normal', 'selected', 'inactive']).toContain(c.state);
    // the source names the artifact field the value is read from
    expect(txt(c.source, 'en'), c.id).toMatch(/(trace|params|benchmark|methods|history|rows|n_seeds|n_fix|n_pix|dynamics)/);
    expect(c.anchor.x).toBeGreaterThanOrEqual(0);
    expect(c.anchor.x).toBeLessThanOrEqual(1);
    expect(c.anchor.y).toBeGreaterThanOrEqual(0);
    expect(c.anchor.y).toBeLessThanOrEqual(1);
  }
};

describe('each step has its three callouts', () => {
  it('setup (the optical train), device (the SLM section), method (V5), compare (V6) and hold (V4)', () => {
    const c02 = storySelection(realCase('C02_grid_feedback'));
    hasFields(trainCallouts(c02, 'en', 1000, 460));
    const c08 = storySelection(realCase('C08_device_limited'));
    hasFields(slmCallouts(c08, slmRow(c08, 32), 32, 'en', 1000, 460));
    hasFields(methodCallouts(c02, 12, 'en'));
    hasFields(methodCallouts(c02, 12, 'es'));
    const f = must(compareFinding(bench()));
    const L = compareLayout(900, 420);
    hasFields(compareCallouts(f, 'en', L, 900, 420));
    const c01 = realCase('C01_square_grid');
    hasFields(holdCallouts(must(holdFinding(c01)), c01, 'en'));
  });

  it('the V5 callouts follow the scrubbed iteration and name the method', () => {
    const sel = storySelection(realCase('C02_grid_feedback'));
    const at1 = methodCallouts(sel, 1, 'en');
    const at30 = methodCallouts(sel, 30, 'en');
    expect(at1[0].value).not.toBe(at30[0].value);
    expect(at30[0].value).toBe('0.014');
    expect(txt(at1[0].source, 'en')).toContain('Phase-fixed weighted GS');
    expect(at1[2].state).toBe('normal');
    expect(at30[2].state).toBe('selected');
    expect(at30[2].value).toBe('12');
  });
});

describe('the comparison (V6)', () => {
  it('has one default-parameter point per method and the front is not dominated', () => {
    const pts = comparePoints(bench(), { ...COMPARE_CELL });
    expect(new Set(pts.map((p) => p.method)).size).toBe(pts.length);
    expect(pts[0].spread.median).toBeLessThanOrEqual(pts[pts.length - 1].spread.median);
    const front = pts.filter((p) => p.onFront);
    expect(front.length).toBeGreaterThan(0);
    for (const p of front) expect(pts.some((q) => q !== p && q.spread.median <= p.spread.median && q.eff.median >= p.eff.median && (q.spread.median < p.spread.median || q.eff.median > p.eff.median))).toBe(false);
  });

  it('the layout puts a larger spread higher and a median of zero on the floor of the axis', () => {
    const L = compareLayout(900, 420);
    expect(L.y(10)).toBeLessThan(L.y(1));
    expect(L.y(0)).toBe(L.y(0.001));
    expect(L.x(0.9)).toBeGreaterThan(L.x(0.1));
    expect(L.plot.x + L.plot.w).toBeLessThanOrEqual(900);
  });
});

describe('the selection the story gives the views', () => {
  it('is the replay lane of the case, at its own device and the trap of its dynamics', () => {
    const s = storySelection(realCase('C01_square_grid'));
    expect(s.maps?.lane).toBe('replay');
    expect(s.trapId).toBe(realCase('C01_square_grid').manifest.params.dynamics!.trap_id);
    expect(s.engineAvailable).toBe(false);
    expect(storySelection(realCase('C08_device_limited'), 'ideal').deviceModel).toBeNull();
    expect(storySelection(realCase('C08_device_limited')).deviceModel).not.toBeNull();
    expect(realSelection('C02_grid_feedback').result?.history.length).toBe(30);
  });
});
