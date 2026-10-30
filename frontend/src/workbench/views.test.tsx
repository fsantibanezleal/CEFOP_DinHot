// The views on data of the shape the bake writes: the rich test cases conform to the contract descriptors, every view renders on them
// without throwing and says what it must (the lane, the reason a view is unavailable, the held edit), and the pure maths the views
// lean on (the Lorentzian fit, the thermal width, the lobes and their overlaps, the metrics of a trap list) is held to known values.

import { createElement, type ReactElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { conform, MANIFEST, TRACE } from '../lib/contract.types';
import { ConvergenceGroup, CameraView, MetricsView } from './ConvergenceGroup';
import { atTheBake, DynamicsGroup, lorentzianFit, ParticleView, RearrangementView, SpectrumView, thermalSigmaUm } from './DynamicsGroup';
import { AxialView, FocalGroup, FocalPlaneView } from './FocalGroup';
import { AberrationView, DeviceEffectsView, HologramGroup, PhaseMaskView } from './HologramGroup';
import { lobesOf, overlaps } from './Lobes3D';
import { histogram, historyAt, is3D, liveMaps, replayMaps, replayResult, trapDeviation, ViewContext, UnavailableContext, type Selection } from './model';
import { BudgetView, DepthView, IntensityView, TrapsGroup } from './TrapsGroup';
import { richCase, selectionFor, SIZE } from './test-data';
import { ActionsContext, Fill, Provenance, type Actions } from './ui';

vi.stubGlobal('__APP_VERSION__', 'test-version');

const actions: Actions = {
  mode: 'inspect',
  selectTrap: () => undefined,
  setRegion: () => undefined,
  addTrap: () => undefined,
  moveTrap: () => undefined,
  deleteTrap: () => undefined,
  editError: null,
  setIteration: () => undefined,
  selectMode: () => undefined,
  zmode: 4,
  setCorrected: () => undefined,
  setCoeff: () => undefined,
  setPlane: () => undefined,
  setVolThreshold: () => undefined,
};

function render(node: ReactElement, sel: Selection | null, unavailable: { en: string; es: string } | null = null): string {
  return renderToStaticMarkup(
    createElement(UnavailableContext.Provider, { value: unavailable }, createElement(ViewContext.Provider, { value: sel }, createElement(ActionsContext.Provider, { value: actions }, node))),
  );
}

const cases = {
  device: richCase({ id: 'R01', device: true, dynamics: 'bead', feedback: true, rearrangement: true }),
  threeD: richCase({ id: 'R02', threeD: true, aberration: true, dynamics: 'atom' }),
  plain: richCase({ id: 'R03', nTraps: 9 }),
  many: richCase({ id: 'R04', nTraps: 100 }),
};

describe('the rich test cases', () => {
  it.each(Object.entries(cases))('%s conforms to the manifest and trace descriptors', (_n, c) => {
    expect(conform(c.manifest, { object: MANIFEST })).toEqual([]);
    expect(conform(c.trace, { object: TRACE })).toEqual([]);
  });
});

describe('every view renders on the data of its case', () => {
  const views: [string, (s: Selection) => ReactElement][] = [
    ['PhaseMaskView', (s) => createElement(PhaseMaskView, { sel: s })],
    ['DeviceEffectsView', (s) => createElement(DeviceEffectsView, { sel: s })],
    ['AberrationView', (s) => createElement(AberrationView, { sel: s })],
    ['FocalPlaneView', (s) => createElement(FocalPlaneView, { sel: s })],
    ['AxialView', (s) => createElement(AxialView, { sel: s })],
    ['IntensityView', (s) => createElement(IntensityView, { sel: s })],
    ['DepthView', (s) => createElement(DepthView, { sel: s })],
    ['BudgetView', (s) => createElement(BudgetView, { sel: s })],
    ['MetricsView', (s) => createElement(MetricsView, { sel: s })],
    ['CameraView', (s) => createElement(CameraView, { sel: s })],
    ['ParticleView', (s) => createElement(ParticleView, { sel: s })],
    ['SpectrumView', (s) => createElement(SpectrumView, { sel: s })],
    ['RearrangementView', (s) => createElement(RearrangementView, { sel: s })],
  ];
  for (const [caseName, data] of Object.entries(cases)) {
    for (const [name, make] of views) {
      it(`${caseName}: ${name}`, () => {
        const html = render(make(selectionFor(data)), selectionFor(data));
        expect(html.length).toBeGreaterThan(50);
        expect(html).not.toMatch(/undefined|NaN/);
      });
    }
  }
  it('the groups render their first sub-view with the case in context, and with no case say it is loading, never blank', () => {
    for (const G of [HologramGroup, FocalGroup, TrapsGroup, ConvergenceGroup, DynamicsGroup]) {
      expect(render(createElement(G), selectionFor(cases.device))).toContain('<button');
      expect(render(createElement(G), null)).toContain('data-state="loading"');
    }
  });
  it('a refused case shows its reason in every view, never an empty chart', () => {
    const reason = { en: 'A trap lies outside the unaliased field of view', es: 'Una trampa queda fuera del campo' };
    const g = render(createElement(HologramGroup), null, reason);
    expect(g).toContain('data-state="unavailable"');
    expect(g).toContain(reason.en);
  });
});

describe('what a view says when it cannot draw', () => {
  it('a case with no dynamics, feedback or rearrangement says so in those views, with the way to see them', () => {
    const s = selectionFor(cases.plain);
    for (const v of [ParticleView, SpectrumView, RearrangementView, CameraView]) {
      const html = render(createElement(v, { sel: s }), s);
      expect(html).toContain('data-state="unavailable"');
    }
    expect(render(createElement(RearrangementView, { sel: s }), s)).toMatch(/rearrangement sequence/);
  });
  it('a case without an axial cut and without the engine says why', () => {
    const s = selectionFor(cases.plain);
    expect(render(createElement(AxialView, { sel: s }), s)).toMatch(/no axial cut in the bake/);
  });
  it('a method with no history in the bake says so instead of drawing an empty chart (M17 has none)', () => {
    const s = selectionFor(cases.device, { methodId: 'M17', result: replayResult(cases.device.trace, 'M17') });
    expect(render(createElement(MetricsView, { sel: s }), s)).toMatch(/no iteration history for M17/);
  });
  it('a focal map that the browser model cannot give says the engine is needed', () => {
    const base = selectionFor(cases.device);
    const s = selectionFor(cases.device, { maps: { ...base.maps!, focal: null, lane: 'live', method: 'M17' } });
    expect(render(createElement(FocalPlaneView, { sel: s }), s)).toMatch(/returns the SLM phase only/);
  });
});

describe('the lane of everything shown (ADR-0054)', () => {
  it('replayed maps are labelled replayed from the bake and name the reference method; they are never labelled live', () => {
    const s = selectionFor(cases.device);
    const html = render(createElement(Fill, null, 'x'), s);
    expect(html).toMatch(/Replayed from the bake: the maps are those of the reference method M04/);
    expect(html).not.toMatch(/Live:/);
    expect(html).toContain('data-lane="replay"');
  });
  it('a live result is labelled live with its backend and time', () => {
    const base = selectionFor(cases.device);
    const s = selectionFor(cases.device, { maps: { ...base.maps!, lane: 'live', method: 'M06', backend: 'cpu', timeMs: 120, fallbackReason: 'no adapter' } });
    const html = renderToStaticMarkup(createElement(Provenance, { sel: s, mapsOnly: false }));
    expect(html).toMatch(/Live: M06 computed in your browser \(CPU, 120 ms\)/);
    expect(html).not.toMatch(/fell back/); // the reason is in the rail, not repeated on every card
    expect(html).toContain('data-lane="live"');
  });
  it('trap edits without the live engine are held back and the result is said to be the baked case', () => {
    const s = selectionFor(cases.device, { edited: true });
    expect(renderToStaticMarkup(createElement(Provenance, { sel: s, mapsOnly: false }))).toMatch(/edits are held: the live engine is not on this build/);
    const t = selectionFor(cases.device, { edited: true, engineAvailable: true, liveMethods: ['M04'], methodId: 'M06' });
    expect(renderToStaticMarkup(createElement(Provenance, { sel: t, mapsOnly: false }))).toMatch(/M06 is replayed from the bake, not run live/);
  });
  it('a cancelled run says the replay is shown', () => {
    const s = selectionFor(cases.device, { cancelled: true });
    expect(renderToStaticMarkup(createElement(Provenance, { sel: s, mapsOnly: false }))).toMatch(/The live run was cancelled; the replay is shown/);
  });
  it('a running method shows its progress and a failed run shows its message', () => {
    const s = selectionFor(cases.device, { running: true, progress: { iteration: 7, efficiency: 0.5, uniformity: 0.812, relStdPct: 9 }, liveError: 'boom' });
    const html = renderToStaticMarkup(createElement(Provenance, { sel: s, mapsOnly: false }));
    expect(html).toMatch(/Running: iteration 7, uniformity 0\.812. Change any control to cancel/);
    expect(html).toMatch(/The live run failed: boom/);
  });
  it('a baked method shows its own metrics and says the maps are those of the reference method', () => {
    const s = selectionFor(cases.device, { methodId: 'M06', result: replayResult(cases.device.trace, 'M06') });
    expect(renderToStaticMarkup(createElement(Provenance, { sel: s, mapsOnly: false }))).toMatch(/M06 is not run live, so its metrics and per-trap intensities are its own but the maps drawn are those of the reference method M04/);
  });
});

describe('the model of the workbench', () => {
  it('decodes the reference maps of a trace and reads the per-method results', () => {
    const c = cases.device;
    const m = replayMaps(c.trace);
    expect(m.lane).toBe('replay');
    expect(m.phase.length).toBe(64 * 64);
    expect(m.focal!.db.length).toBe(SIZE * SIZE);
    expect(Math.min(...m.focal!.db)).toBeGreaterThanOrEqual(-40);
    expect(replayResult(c.trace, 'M06')!.metrics!.uniformity).toBe(0.97);
    expect(replayResult(c.trace, 'M99')).toBeNull();
  });
  it('puts a live focal map in dB against the mean light at the traps', () => {
    const c = cases.plain;
    const size = 9;
    const focal = new Float32Array(size * size).fill(0.001);
    const trapsList = c.trace.traps.slice(0, 1);
    focal[4 * size + 4] = 2;
    const { maps, result } = liveMaps(
      { method: 'M04', backend: 'gpu', fallbackReason: null, nPix: 64, pad: 2, binUm: 10, halfFieldUm: 665, phase: new Float64Array(64 * 64).fill(-1), displayedPhase: null, focal, focalSize: size, trapIntensity: Float64Array.of(2, 4), history: [], metrics: { efficiency: 0.5, uniformity: 0.9, relStdPct: 3, zeroOrder: 0, ghost: 0 }, timeMs: 5, timing: { methodMs: 4, scoreMs: 1, yieldMs: 0 } },
      [{ ...trapsList[0], x_um: 0, y_um: 0 }],
      -60,
    );
    expect(maps.lane).toBe('live');
    expect(maps.focal!.db[4 * size + 4]).toBeCloseTo(0, 6);
    expect(maps.focal!.db[0]).toBeCloseTo(10 * Math.log10(0.001 / 2), 4);
    expect(maps.phase[0]).toBeCloseTo(2 * Math.PI - 1, 5);
    expect(result.trapI).toEqual([2 / 3, 4 / 3]);
  });
  it('the spread, the histogram and the history cursor', () => {
    const d = trapDeviation([0.9, 1, 1.1]);
    expect(d.min).toBe(0.9);
    expect(d.max).toBe(1.1);
    expect(d.rmsPct).toBeCloseTo(8.165, 2);
    const h = histogram([0.5, 1, 1, 1.5], 0.5, 1.5, 2);
    expect(h.counts).toEqual([1, 3]);
    const hist = [{ iteration: 0, efficiency: 0, uniformity: 0, relStdPct: 0 }, { iteration: 10, efficiency: 1, uniformity: 1, relStdPct: 1 }];
    expect(historyAt(hist, 5)!.iteration).toBe(0);
    expect(historyAt(hist, 99)!.iteration).toBe(10);
    expect(historyAt([], 3)).toBeNull();
    expect(is3D(cases.threeD.trace.traps)).toBe(true);
    expect(is3D(cases.plain.trace.traps)).toBe(false);
  });
});

describe('the spectrum and the Boltzmann width', () => {
  it('recovers the amplitude of an exact Lorentzian and a zero residual', () => {
    const f = Array.from({ length: 30 }, (_, i) => 5 * 1.3 ** i);
    const fc = 90;
    const p = f.map((x) => 2e-3 / (x * x + fc * fc));
    const fit = lorentzianFit(f, p, fc);
    expect(fit.A / 2e-3).toBeCloseTo(1, 9);
    expect(fit.resid).toBeLessThan(1e-9);
    // a wrong corner frequency leaves a residual
    expect(lorentzianFit(f, p, 400).resid).toBeGreaterThan(0.05);
  });
  it('the thermal width of a bead is sqrt(kT / kappa): 20 nm at 295 K and 10 pN/um; an atom uses its mass and radial frequency', () => {
    const bead = cases.device.manifest.params.dynamics!;
    expect(thermalSigmaUm(bead, { value: 10, unit: 'pN/um' }) * 1e3).toBeCloseTo(20.18, 1);
    const atom = cases.threeD.manifest.params.dynamics!;
    const sigma = thermalSigmaUm(atom, { value: 80000, unit: 'Hz' });
    expect(sigma).toBeGreaterThan(0);
    expect(sigma).toBeLessThan(1);
  });
});

describe('the 3D lobes', () => {
  it('a brighter trap has a bigger lobe, a trap dimmer than the threshold has none, and overlaps are counted at true size', () => {
    const s = selectionFor(cases.threeD);
    const lobes = lobesOf(s, 0.5);
    expect(lobes.length).toBe(16);
    const bright = lobes.find((l) => l.rel > 1.05);
    const dim = lobes.find((l) => l.rel < 0.95);
    expect(bright && dim && bright.axy > dim.axy).toBe(true);
    expect(lobesOf(s, 0.99).some((l) => l.axy === 0)).toBe(true);
    // two lobes on top of each other overlap, two far apart do not
    const near = [{ id: 0, x: 0, y: 0, z: 0, axy: 1, az: 2, rel: 1 }, { id: 1, x: 0.5, y: 0, z: 0, axy: 1, az: 2, rel: 1 }];
    const far = [{ id: 0, x: 0, y: 0, z: 0, axy: 1, az: 2, rel: 1 }, { id: 1, x: 90, y: 0, z: 0, axy: 1, az: 2, rel: 1 }];
    expect(overlaps(near)).toEqual({ pairs: 1, checked: 1 });
    expect(overlaps(far)).toEqual({ pairs: 0, checked: 1 });
    expect(overlaps(Array.from({ length: 401 }, (_, i) => ({ ...near[0], id: i })))).toBeNull();
  });
});

describe('the particle is replayed only while the rail asks for what the bake simulated', () => {
  const c = cases.device;
  const base = () => selectionFor(c, { seed: c.manifest.seed });
  it('at the bake seed and power on the baked hologram, nothing is asked of the engine', () => {
    expect(atTheBake(base())).toBe(true);
  });
  it.each([
    ['another seed', { seed: c.manifest.seed + 1 }],
    ['another power', { powerMw: (c.manifest.params.dynamics?.power_mw ?? 1) * 2 }],
    ['edited traps', { edited: true }],
    ['an edited aberration', { aberrationEdited: true }],
    ['the ideal device', { device: 'ideal' as const }],
    ['a live hologram', { maps: { ...replayMaps(c.trace), lane: 'live' as const } }],
  ])('%s asks the engine', (_n, over) => {
    expect(atTheBake({ ...base(), ...over })).toBe(false);
  });
});
