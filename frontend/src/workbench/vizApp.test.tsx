// The visual-review fixes on the App's Focal plane, Traps, Dynamics and Pareto views (ADR-0082): the trap selected anywhere is marked in the
// per-trap views, the focal image carries axes and three anchored callouts, the dynamics view draws the bead, and the Pareto view recommends
// a method from the benchmark document with its reason.
import { LinkedViewProvider, formatNumber } from '@fasl-work/caos-app-shell';
import { createElement, type ReactElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { axisTicks, niceStep } from './HeatmapStage';
import { mapAnchor } from './CalloutScene';
import { focalCallouts } from './focalCallouts';
import { selectedIndex, selectedSeries, selectedValue } from './trapSelection';
import { selectionFor, richCase } from './test-data';
import { IntensityView } from './TrapsGroup';
import { ActionsContext, type Actions } from './ui';
import { UnavailableContext, ViewContext, type Selection } from './model';

vi.stubGlobal('__APP_VERSION__', 'test-version');

const actions = { mode: 'inspect', selectTrap: () => undefined, setIteration: () => undefined, zmode: 4 } as unknown as Actions;
const render = (node: ReactElement, sel: Selection): string =>
  renderToStaticMarkup(createElement(LinkedViewProvider, null, createElement(UnavailableContext.Provider, { value: null }, createElement(ViewContext.Provider, { value: sel }, createElement(ActionsContext.Provider, { value: actions }, node)))));

describe('the trap selected anywhere is marked in the per-trap views (ADR-0082 rule 6)', () => {
  const items = [
    { id: 4, v: 1.2 },
    { id: 9, v: 0.9 },
    { id: 72, v: 1.05 },
  ];
  it('finds the selected trap among the items as drawn, in any order', () => {
    expect(selectedIndex(items, 72)).toBe(2);
    expect(selectedIndex([...items].reverse(), 72)).toBe(0);
    expect(selectedIndex(items, null)).toBe(-1);
    expect(selectedIndex(items, 5)).toBe(-1);
  });
  it('draws one point of the selected series, at the selected trap, and a gap everywhere else', () => {
    expect(selectedSeries(items, 72)).toEqual([null, null, 1.05]);
    expect(selectedSeries(items, null)).toBeNull();
  });
  it('gives the histogram the selected trap value for its mark', () => {
    expect(selectedValue(items, 9)).toBe(0.9);
    expect(selectedValue(items, 11)).toBeNull();
  });
  it('the sorted-points chart of a large array carries the selected trap as a series of its own', () => {
    const data = richCase({ id: 'R04', nTraps: 100 });
    const sel = { ...selectionFor(data), trapId: 37 } as Selection;
    const html = render(createElement(IntensityView, { sel }), sel);
    expect(html).toContain('Selected trap 37');
    const none = { ...selectionFor(data), trapId: null } as Selection;
    expect(render(createElement(IntensityView, { sel: none }), none)).not.toContain('Selected trap');
  });
});

describe('the axes of the focal image', () => {
  it('steps by 1, 2 or 5 times a power of ten, at least minPx apart', () => {
    expect(niceStep(0.05, 64)).toBe(5);
    expect(niceStep(0.5 / 20, 64)).toBe(2);
    expect(niceStep(1, 64)).toBe(100);
  });
  it('ticks at the multiples of the step inside the range, with a true zero', () => {
    expect(axisTicks(-7, 7, 5)).toEqual([-5, 0, 5]);
    expect(axisTicks(-0.3, 0.3, 0.1)).toEqual([-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3]);
  });
});

describe('the callouts of the focal image', () => {
  it('places an anchor on the cell it names, inside the map box under the band', () => {
    const c = mapAnchor(15, 15, 30, 30, 600, 500, 86);
    expect(c.x).toBeCloseTo(0.5, 1);
    expect(c.y).toBeGreaterThan(86 / 500);
    const corner = mapAnchor(0, 0, 30, 30, 600, 500, 86);
    expect(corner.x).toBeLessThan(c.x);
    expect(corner.y).toBeLessThan(c.y);
  });
  it('are three: the selected trap against its target, the zero order and the spread pinned to the worst trap', () => {
    const data = richCase({ id: 'R04', nTraps: 100 });
    const sel = { ...selectionFor(data), trapId: 3 } as Selection;
    const items = focalCallouts(sel, 'en');
    expect(items.map((i) => i.id)).toEqual(['trap', 'zero', 'spread']);
    expect((items[0].eyebrow as { en: string }).en).toBe('TRAP 3');
    const tI = sel.result!.trapI!;
    expect(items[0].value).toBe(formatNumber(tI[sel.traps.findIndex((t) => t.id === 3)], 'en', { decimals: 3 }));
    for (const i of items) {
      expect(i.anchor.x).toBeGreaterThan(0);
      expect(i.anchor.x).toBeLessThan(1);
      expect(i.anchor.y).toBeGreaterThan(0);
      expect(i.anchor.y).toBeLessThan(1);
      expect(JSON.stringify(i.source)).not.toMatch(/\.[a-z]+_[a-z_]+|\.ts/);
    }
  });
  it('leave out a quantity the result does not hold', () => {
    const data = richCase({ id: 'R03', nTraps: 9 });
    const sel = { ...selectionFor(data), trapId: null, result: null } as Selection;
    expect(focalCallouts(sel, 'en')).toEqual([]);
  });
});
