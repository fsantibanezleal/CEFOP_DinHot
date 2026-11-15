// V4: the bead in its trap. The pure parts of the dynamics view: the time of a frame, the window of the zoomed map, the three callouts, the
// offer of the dynamics case, and the link that opens it in the App.
import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { appHref, DYNAMICS_CASE, framePoint, beadWindow, frameTimeMs, particleCallouts, unitText } from './particle';

const tr = { fcHz: 34.5168, stiffness: { value: 1.97802, unit: 'pN/um' }, dtS: 5e-5 * 33, xUm: [0, 0.1, -0.2], yUm: [0, 0.05, 0.1] };

describe('the time cursor', () => {
  it('is the frame times the decimated step, in milliseconds', () => {
    expect(frameTimeMs(0, 5e-5 * 33)).toBe(0);
    expect(frameTimeMs(1000, 5e-5 * 33)).toBeCloseTo(1000 * 5e-5 * 33 * 1e3, 6);
  });
  it('reads the bead position at a frame and holds at the last one', () => {
    expect(framePoint(tr, 1)).toEqual({ xUm: 0.1, yUm: 0.05 });
    expect(framePoint(tr, 99)).toEqual({ xUm: -0.2, yUm: 0.1 });
  });
});

describe('the window of the zoomed map', () => {
  it('shows a few cells either side of the trap the bead sits in, never fewer than three', () => {
    expect(beadWindow(0.5, 0.498)).toBe(4);
    expect(beadWindow(0.05, 0.498)).toBeGreaterThanOrEqual(3);
  });
});

describe('the micro sign', () => {
  it('writes micrometres with the micro sign, in a unit and in a rate', () => {
    expect(unitText('pN/um')).toBe('pN/µm');
    expect(unitText('um^2/Hz')).toBe('µm^2/Hz');
    expect(unitText('kBT')).toBe('kBT');
  });
});

describe('the three callouts of the dynamics view', () => {
  const dyn = { depth: { value: 98.1448, unit: 'kBT' }, powerMw: 10 };
  it('are the stiffness, the corner frequency and the depth, from the trajectory and the case', () => {
    const items = particleCallouts({ tr, depth: dyn.depth, depthScale: 1, particle: 'bead', lang: 'en', narrow: false });
    expect(items.map((i) => i.id)).toEqual(['kappa', 'fc', 'depth']);
    expect(items[0].value).toBe('1.98');
    expect(items[0].unit).toBe('pN/µm');
    expect(items[1].value).toBe('34.5');
    expect(items[2].value).toBe('98');
    for (const i of items) {
      expect(i.anchor.x).toBeGreaterThan(0);
      expect(i.anchor.x).toBeLessThan(1);
      expect(JSON.stringify(i.source)).not.toMatch(/trace\.|\.json|_pn_per/);
    }
  });
  it('writes the number in the page language', () => {
    expect(particleCallouts({ tr, depth: dyn.depth, depthScale: 1, particle: 'bead', lang: 'es', narrow: false })[0].value).toBe('1,98');
  });
  it('names an atom by its radial frequency, not a stiffness', () => {
    const atom = particleCallouts({ tr: { ...tr, stiffness: { value: 120.5, unit: 'Hz' } }, depth: null, depthScale: 1, particle: 'atom', lang: 'en', narrow: false });
    expect(atom.map((i) => i.id)).toEqual(['kappa', 'fc']);
    expect((atom[0].eyebrow as { en: string }).en).toBe('RADIAL FREQUENCY');
  });
});

describe('a case without dynamics', () => {
  it('opens the dynamics case in one action: a link to the App on its dynamics view', () => {
    expect(appHref('/', { case: DYNAMICS_CASE, view: 'dynamics' })).toBe(`/app/?case=${DYNAMICS_CASE}&view=dynamics`);
    expect(appHref('/DinHot/', { case: 'C01_square_grid', method: 'M07', view: 'convergence' })).toBe('/DinHot/app/?case=C01_square_grid&method=M07&view=convergence');
  });
  it('names a case of the bake that holds a particle simulation', () => {
    const f = `../../../data/derived/manifests/${DYNAMICS_CASE}.json`;
    const url = new URL(f, import.meta.url);
    expect(existsSync(url)).toBe(true);
    expect(JSON.parse(readFileSync(url, 'utf-8')).params.dynamics).toBeTruthy();
  });
});
