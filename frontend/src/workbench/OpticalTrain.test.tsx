// V1, the optical train (ADR-0082, SDD visualization catalog row V1): every value it prints is the selected case's, the light moves only
// while motion is allowed and playing, an element is a button that opens the view it stands for, and a trap dot selects a trap.
import { formatNumber, layoutSceneCallouts, type BiText } from '@fasl-work/caos-app-shell';
import { isValidElement, type ReactElement, type ReactNode } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { openTrainElement, OpticalTrainDrawing, TRAIN_TARGET, trainCallouts, trainItems, trainLayout, type TrainId } from './OpticalTrain';
import { richCase, selectionFor } from './test-data';
import { realCase, realSelection } from './test-real';

vi.stubGlobal('__APP_VERSION__', 'test-version');

type El = ReactElement<Record<string, unknown>>;

/** Every element of a tree, with function components expanded (the drawing is pure: no hooks inside). */
function nodes(node: ReactNode, out: El[] = []): El[] {
  if (Array.isArray(node)) {
    node.forEach((n) => nodes(n, out));
    return out;
  }
  if (!isValidElement(node)) return out;
  const el = node as El;
  if (typeof el.type === 'function') return nodes((el.type as (p: unknown) => ReactNode)(el.props), out);
  out.push(el);
  return nodes(el.props.children as ReactNode, out);
}

const txt = (b: BiText, lang: 'en' | 'es'): string => (typeof b === 'string' ? b : b[lang]);
const W = 1000;
const H = 460;
const draw = (over: Record<string, unknown> = {}, caseId = 'C02_grid_feedback', lang: 'en' | 'es' = 'en') => {
  const sel = realSelection(caseId);
  return {
    sel,
    props: { sel, lang, width: W, height: H, motion: true, playing: true, selectedId: null as string | null, onOpen: vi.fn(), onSelectTrap: vi.fn(), ...over },
  };
};
const html = (props: Record<string, unknown>) => renderToStaticMarkup(<OpticalTrainDrawing {...(props as unknown as Parameters<typeof OpticalTrainDrawing>[0])} />);
const el = (props: Record<string, unknown>) => nodes(<OpticalTrainDrawing {...(props as unknown as Parameters<typeof OpticalTrainDrawing>[0])} />);

describe('the optical train prints the values of the selected case', () => {
  it('C02: wavelength, beam at the SLM, pixels and pitch, aperture N p, focal length, NA, trap count and the method efficiency', () => {
    const c = realCase('C02_grid_feedback');
    const s = c.manifest.params.setup;
    const items = Object.fromEntries(trainItems(realSelection('C02_grid_feedback'), 'en').map((i) => [i.id, i]));
    const f = (v: number, d: number) => formatNumber(v, 'en', { decimals: d });
    expect(items.laser.value).toBe(`${f(s.wavelength_nm, 0)} nm`);
    expect(items.expander.value).toBe(`${f((1.0 * s.n_pix * s.pitch_um) / 1000, 2)} mm`);
    expect(items.slm.value).toBe(`${s.n_pix} x ${s.n_pix} px`);
    expect(items.slm.detail).toContain(`${f(s.pitch_um, 1)} um`);
    expect(items.slm.detail).toContain(`${f((s.n_pix * s.pitch_um) / 1000, 2)} mm`);
    expect(items.objective.value).toBe(`f ${f(s.focal_mm, 1)} mm`);
    expect(items.objective.detail).toContain(`NA ${f(s.na, 2)}`);
    expect(items.focal.value).toBe(`${c.trace.traps.length} traps`);
    const eff = c.trace.methods[c.manifest.params.reference_method].final.efficiency;
    expect(items.focal.detail).toContain(formatNumber(eff, 'en', { percent: true, decimals: 1 }));
  });

  it('C08: the device case prints its own focal length, pixel count and the efficiency of its reference method', () => {
    const c = realCase('C08_device_limited');
    const items = Object.fromEntries(trainItems(realSelection('C08_device_limited'), 'en').map((i) => [i.id, i]));
    expect(items.slm.value).toBe('128 x 128 px');
    expect(items.objective.value).toBe('f 3.0 mm');
    expect(items.expander.value).toBe('2.56 mm');
    expect(items.focal.value).toBe(`${c.trace.traps.length} traps`);
    expect(items.focal.detail).toContain(formatNumber(c.trace.methods.B1.final.efficiency, 'en', { percent: true, decimals: 1 }));
  });

  it('Spanish prints the decimal comma and the Spanish words', () => {
    const items = Object.fromEntries(trainItems(realSelection('C08_device_limited'), 'es').map((i) => [i.id, i]));
    expect(items.expander.value).toBe('2,56 mm');
    expect(items.focal.value).toMatch(/trampas$/);
    expect(items.slm.detail).toContain('20,0 um');
  });

  it('the drawing contains every item value and no number of another case', () => {
    const { sel, props } = draw();
    const out = html(props);
    for (const i of trainItems(sel, 'en')) {
      if (i.value) expect(out).toContain(i.value);
      if (i.detail) expect(out).toContain(i.detail);
    }
    // C02 is 850 nm, 256 pixels of 20 um; the numbers of C07 (2.4 mm) and of the richCase fixture (1064 nm) must not appear
    expect(out).not.toContain('1064');
    expect(out).not.toContain('2.4 mm');
    expect(out).not.toMatch(/undefined|NaN/);
  });

  it('a flat beam prints its aperture, not a waist; a waist fraction scales the beam diameter', () => {
    const c = richCase({ id: 'R10' });
    const sel = selectionFor(c);
    const setup = c.manifest.params.setup;
    expect(setup.beam.kind).toBe('gaussian');
    const waist = (setup.beam as { waist_frac: number }).waist_frac;
    expect(waist).not.toBe(1);
    expect(trainItems(sel, 'en').find((i) => i.id === 'expander')!.value).toBe(`${formatNumber((waist * setup.n_pix * setup.pitch_um) / 1000, 'en', { decimals: 2 })} mm`);
    const flat = selectionFor({ ...c, manifest: { ...c.manifest, params: { ...c.manifest.params, setup: { ...c.manifest.params.setup, beam: { kind: 'flat' } } } } });
    expect(trainItems(flat, 'en').find((i) => i.id === 'expander')!.value).toBe(`${formatNumber((c.manifest.params.setup.n_pix * c.manifest.params.setup.pitch_um) / 1000, 'en', { decimals: 2 })} mm`);
  });

  it('a shaped target says so instead of printing a trap count, and a missing efficiency says so', () => {
    const shaped = realSelection('C04_disc_crosstalk');
    const focal = trainItems(shaped, 'en').find((i) => i.id === 'focal')!;
    expect(focal.value).toBe('shaped potential');
    const none = trainItems(realSelection('C02_grid_feedback', { result: null }), 'en').find((i) => i.id === 'focal')!;
    expect(none.detail).toMatch(/efficiency not available/);
  });
});

describe('the three callouts', () => {
  it('are three, each with a value, a unit, a recognised state and a source naming the artifact field', () => {
    const sel = realSelection('C02_grid_feedback');
    const items = trainCallouts(sel, 'en', W, H);
    expect(items).toHaveLength(3);
    for (const c of items) {
      expect(c.value.length).toBeGreaterThan(0);
      expect(txt(c.unit, 'en').length).toBeGreaterThan(0);
      expect(txt(c.unit, 'es').length).toBeGreaterThan(0);
      expect(['alarm', 'warning', 'normal', 'selected', 'inactive']).toContain(c.state);
      expect(txt(c.source, 'en')).toMatch(/params\.|trace|methods\./);
      expect(c.anchor.x).toBeGreaterThan(0);
      expect(c.anchor.x).toBeLessThan(1);
      expect(c.anchor.y).toBeGreaterThan(0);
      expect(c.anchor.y).toBeLessThan(1);
    }
  });

  it('carry the case values and are anchored on the element they describe', () => {
    const sel = realSelection('C02_grid_feedback');
    const items = trainCallouts(sel, 'en', W, H);
    const layout = trainLayout(W, H);
    const byId = Object.fromEntries(items.map((c) => [c.id, c]));
    const eff = formatNumber(sel.result!.metrics!.efficiency, 'en', { percent: true, decimals: 1 });
    expect(byId.laser.value).toBe(formatNumber(850, 'en', { decimals: 0 }));
    expect(byId.slm.value).toBe('5.12');
    expect(byId.focal.value).toBe(eff.replace(/\s*%$/, ''));
    for (const id of ['laser', 'slm', 'focal'] as TrainId[]) {
      const box = layout.items[id];
      expect(byId[id].anchor.x).toBeCloseTo((box.x + box.w / 2) / W, 5);
      expect(byId[id].anchor.y).toBeCloseTo((box.y + box.h / 2) / H, 5);
    }
  });

  it('the shell can place them without one covering another anchor', () => {
    const sel = realSelection('C08_device_limited');
    const items = trainCallouts(sel, 'en', W, H);
    const boxes = layoutSceneCallouts(items, W, H);
    expect(boxes).toHaveLength(3);
  });

  it('the focal callout takes the rail readout thresholds for efficiency: normal from 0.8, warning to 0.4, alarm below', () => {
    const state = (id: string) => trainCallouts(realSelection(id), 'en', W, H).find((c) => c.id === 'focal')!.state;
    expect(state('C01_square_grid')).toBe('normal'); // 0.8168
    expect(state('C02_grid_feedback')).toBe('warning'); // 0.7977
    expect(state('C08_device_limited')).toBe('warning'); // 0.652
    expect(state('C04_disc_crosstalk')).toBe('alarm'); // 0.3733
  });
});

describe('motion', () => {
  it('moves the light along the beam while motion is allowed and playing', () => {
    const { props } = draw();
    const out = html(props);
    expect(out).toContain('dh-flow');
    expect(out).toContain('data-animated="true"');
  });

  it('draws no animation under reduced motion, and shows the direction statically instead', () => {
    const { props } = draw({ motion: false });
    const out = html(props);
    expect(out).not.toContain('dh-flow');
    expect(out).not.toContain('data-animated="true"');
    expect(out).not.toMatch(/<animate/);
    expect(out).toContain('data-direction="static"');
  });

  it('stops when the reader pauses it', () => {
    const { props } = draw({ playing: false });
    expect(html(props)).not.toContain('dh-flow');
  });
});

describe('the elements are buttons', () => {
  it('selecting the SLM calls the view switch with the SLM element, and the switch opens Device effects', () => {
    const { props } = draw();
    const slm = el(props).find((n) => n.props['data-train-element'] === 'slm')!;
    expect(slm.props.role).toBe('button');
    expect(slm.props.tabIndex).toBe(0);
    (slm.props.onClick as () => void)();
    expect(props.onOpen).toHaveBeenCalledWith('slm');
    const open = vi.fn();
    openTrainElement('slm', open);
    expect(open).toHaveBeenCalledWith({ group: 'hologram', tab: 'device' });
    expect(TRAIN_TARGET.slm).toEqual({ group: 'hologram', tab: 'device' });
  });

  it('selecting the focal plane opens the Focal plane group', () => {
    const { props } = draw();
    const focal = el(props).find((n) => n.props['data-train-element'] === 'focal')!;
    (focal.props.onClick as () => void)();
    expect(props.onOpen).toHaveBeenCalledWith('focal');
    const open = vi.fn();
    openTrainElement('focal', open);
    expect(open).toHaveBeenCalledWith({ group: 'focal', tab: 'plane' });
  });

  it('an element that opens nothing (the laser) is not a button', () => {
    const { props } = draw();
    const laser = el(props).find((n) => n.props['data-train-element'] === 'laser')!;
    expect(laser.props.role).toBeUndefined();
    const open = vi.fn();
    openTrainElement('laser', open);
    expect(open).not.toHaveBeenCalled();
  });

  it('the Enter and Space keys act as a click on a button element', () => {
    const { props } = draw();
    const slm = el(props).find((n) => n.props['data-train-element'] === 'slm')!;
    const preventDefault = vi.fn();
    (slm.props.onKeyDown as (e: unknown) => void)({ key: 'Enter', preventDefault });
    (slm.props.onKeyDown as (e: unknown) => void)({ key: ' ', preventDefault });
    (slm.props.onKeyDown as (e: unknown) => void)({ key: 'a', preventDefault });
    expect(props.onOpen).toHaveBeenCalledTimes(2);
  });
});

describe('the trap sites in the focal plane', () => {
  it('draws one site per trap, each a linked item carrying its trap id, and a click selects that trap', () => {
    const { sel, props } = draw();
    const dots = el(props).filter((n) => n.props['data-linked-id'] !== undefined);
    expect(dots).toHaveLength(sel.traps.length);
    const third = dots.find((d) => d.props['data-linked-id'] === String(sel.traps[3].id))!;
    expect(third.props['data-linked-view']).toBe('scene');
    expect(third.props.role).toBe('button');
    (third.props.onClick as (e: { stopPropagation: () => void }) => void)({ stopPropagation: () => undefined });
    expect(props.onSelectTrap).toHaveBeenCalledWith(sel.traps[3].id);
    expect(props.onOpen).not.toHaveBeenCalled();
  });

  it('marks the site that the linked selection names', () => {
    const { sel, props } = draw({ selectedId: String(5) });
    const dots = el(props).filter((n) => n.props['data-linked-id'] !== undefined);
    const picked = dots.filter((d) => d.props['data-linked-selected'] === 'true');
    expect(picked).toHaveLength(1);
    expect(picked[0].props['data-linked-id']).toBe('5');
    expect(sel.traps.some((t) => t.id === 5)).toBe(true);
  });

  it('a very large array keeps the sites as decorations and picks the nearest trap from the pointer instead', () => {
    const { props } = draw({}, 'C03_large_array');
    const dots = el(props).filter((n) => n.props['data-linked-id'] !== undefined);
    expect(dots.length).toBe(0);
    const field = el(props).find((n) => n.props['data-train-field'] !== undefined);
    expect(field).toBeDefined();
    expect(typeof field!.props.onPointerDown).toBe('function');
  });
});

describe('what the pointer can reach (gate G5)', () => {
  it('traps of one lateral position on different planes are drawn apart (C05 has three planes)', () => {
    const { props } = draw({}, 'C05_multiplane_vortices');
    const dots = el(props).filter((n) => n.props['data-linked-id'] !== undefined);
    const at = dots.map((d) => `${Number(d.props.cx).toFixed(2)},${Number(d.props.cy).toFixed(2)}`);
    expect(new Set(at).size).toBe(dots.length);
  });

  it('the focal plane button is the strip under the box, so no site or pick area covers its centre', () => {
    const { props } = draw();
    const focal = el(props).find((n) => n.props['data-train-element'] === 'focal')!;
    const hit = nodes(focal.props.children as ReactNode)[0];
    const cx = Number(hit.props.x) + Number(hit.props.width) / 2;
    const cy = Number(hit.props.y) + Number(hit.props.height) / 2;
    const field = trainLayout(W, H).field;
    expect(cy).toBeGreaterThan(field.y + field.h);
    expect(cx).toBeGreaterThanOrEqual(field.x - 1);
  });
});

describe('the narrow layout', () => {
  it('draws the train as rows at 340 px with no horizontal overflow of its viewBox', () => {
    const { props } = draw({ width: 340, height: 400 });
    const out = html(props);
    expect(out).toContain('data-layout="rows"');
    expect(out).toContain('viewBox="0 0 340 400"');
    const layout = trainLayout(340, 400);
    for (const b of Object.values(layout.items)) {
      expect(b.x).toBeGreaterThanOrEqual(0);
      expect(b.x + b.w).toBeLessThanOrEqual(340);
      expect(b.y + b.h).toBeLessThanOrEqual(400);
    }
  });
});
