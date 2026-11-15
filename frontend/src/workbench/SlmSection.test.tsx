// V2, the SLM in section (ADR-0082, SDD visualization catalog row V2): one pixel row of the mask in section, the commanded and the displayed
// phase in the engine's own order (quantize, response, crosstalk), the fill factor and the crosstalk kernel of the case's device, and what
// the view says on a case that has no device.
import { formatNumber, type BiText } from '@fasl-work/caos-app-shell';
import { isValidElement, type ReactElement, type ReactNode } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { apertureEnvelopeAtEdge, crosstalkWeights, fillFactorEfficiency, levelOf, quantizationEfficiency, stagePhase, TWO_PI } from './decode';
import { slmCallouts, slmDeviceSwitch, slmLayout, SlmSectionDrawing, slmLosses, slmPixel, slmRow, windowStart } from './SlmSection';
import { realSelection } from './test-real';

vi.stubGlobal('__APP_VERSION__', 'test-version');

type El = ReactElement<Record<string, unknown>>;
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
const f = (v: number, d: number, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { decimals: d });

describe('the row in section follows the engine order: quantize, response, crosstalk', () => {
  const sel = realSelection('C08_device_limited');
  const dev = sel.deviceModel!;
  const n = sel.maps!.nPix;

  it('the case has the device the test expects (4 bits, fill 0.85, a crosstalk kernel)', () => {
    expect(dev.bit_depth).toBe(4);
    expect(dev.fill_factor).toBe(0.85);
    expect(dev.crosstalk).not.toBeNull();
  });

  it('the requested phase of the row is the mask, and the displayed phase is the engine stage "crosstalk" read on that row', () => {
    const row = 64;
    const r = slmRow(sel, row);
    expect(r.deviceOn).toBe(true);
    expect(r.requested.length).toBe(n);
    const shown = stagePhase(sel.maps!.phase, n, dev, 'crosstalk');
    for (const c of [0, 17, 63, 64, 127]) {
      expect(r.requested[c]).toBe(sel.maps!.phase[row * n + c]);
      expect(r.displayed[c]).toBe(shown[row * n + c]);
    }
  });

  it('the commanded level of a pixel is the nearest of 2^bits levels of the requested phase', () => {
    const r = slmRow(sel, 40);
    for (const c of [3, 50, 99]) {
      const p = slmPixel(r, c);
      expect(p.levels).toBe(16);
      expect(p.level).toBe(levelOf(r.requested[c], 4));
      expect(p.commanded).toBeCloseTo((levelOf(r.requested[c], 4) * TWO_PI) / 16, 10);
      expect(p.requested).toBe(r.requested[c]);
      expect(p.displayed).toBe(r.displayed[c]);
    }
  });

  it('the crosstalk kernel is the engine kernel of the case, normalised, symmetric', () => {
    const r = slmRow(sel, 64);
    const w = crosstalkWeights(dev.crosstalk!.sigma_per_px, dev.crosstalk!.q, dev.upsample, n);
    expect(r.kernel).not.toBeNull();
    expect(r.kernel!.length).toBe(w.length);
    expect(r.kernel!.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 8);
    for (let i = 0; i < w.length; i++) expect(r.kernel![i]).toBeCloseTo(w[i], 12);
    expect(r.kernel![0]).toBeCloseTo(r.kernel![r.kernel!.length - 1], 12);
  });

  it('the losses are the closed forms of the device view, and the row errors are measured on the row', () => {
    const l = slmLosses(sel, slmRow(sel, 64));
    expect(l.quantization).toBeCloseTo(1 - quantizationEfficiency(16), 12);
    expect(l.fillFactor).toBeCloseTo(1 - fillFactorEfficiency(0.85), 12);
    expect(l.apertureEdge).toBeCloseTo(1 - apertureEnvelopeAtEdge(0.85), 12);
    expect(l.quantizationRmsRad).toBeGreaterThan(0);
    expect(l.crosstalkRmsRad).toBeGreaterThan(0);
  });

  it('the ideal device choice on a device case shows the requested phase unchanged', () => {
    const ideal = realSelection('C08_device_limited', { device: 'ideal', deviceModel: null });
    const r = slmRow(ideal, 64);
    expect(r.deviceOn).toBe(false);
    for (let c = 0; c < n; c += 9) expect(r.displayed[c]).toBe(r.requested[c]);
    expect(slmPixel(r, 10).level).toBeNull();
    expect(slmLosses(ideal, r).quantization).toBe(0);
    expect(slmLosses(ideal, r).fillFactor).toBe(0);
  });
});

describe('a case without a device block', () => {
  const sel = realSelection('C02_grid_feedback');
  it('has no device model, and the section is the ideal one', () => {
    expect(sel.deviceModel).toBeNull();
    const r = slmRow(sel, 100);
    expect(r.deviceOn).toBe(false);
    expect(r.kernel).toBeNull();
    expect(r.fill).toBeNull();
  });

  it('the case-device switch is disabled with its reason, in both languages', () => {
    const s = slmDeviceSwitch(sel);
    expect(s.disabled).toBe(true);
    expect(s.reason!.en).toMatch(/no device block/i);
    expect(s.reason!.es).toMatch(/bloque de dispositivo/i);
    expect(slmDeviceSwitch(realSelection('C08_device_limited')).disabled).toBe(false);
  });

  it('the drawing says ideal and prints no made-up fill factor or bit depth', () => {
    const r = slmRow(sel, 100);
    const out = renderToStaticMarkup(<SlmSectionDrawing sel={sel} row={r} col={100} lang="en" width={W} height={H} onCol={vi.fn()} />);
    expect(out).toMatch(/ideal/i);
    expect(out).not.toMatch(/fill factor 0|bits/i);
    expect(out).not.toMatch(/undefined|NaN/);
  });

  it('the callouts read the ideal SLM as numbers: the fill is the whole pixel, 1.00 of the area, and the card is inactive', () => {
    const r = slmRow(sel, 100);
    const items = slmCallouts(sel, r, 100, 'en', W, H);
    expect(items).toHaveLength(3);
    const fill = items.find((c) => c.id === 'fill')!;
    expect(fill.value).toBe('1.00');
    expect(fill.unit).toEqual({ en: 'area', es: 'área' });
    expect(fill.state).toBe('inactive');
  });
});

describe('the callouts and the drawing carry the case values', () => {
  const sel = realSelection('C08_device_limited');
  const row = slmRow(sel, 64);
  const col = 70;

  it('three callouts: commanded level, displayed phase, fill factor, with units, states and sources', () => {
    const items = slmCallouts(sel, row, col, 'en', W, H);
    expect(items.map((c) => c.id)).toEqual(['level', 'displayed', 'fill']);
    const p = slmPixel(row, col);
    expect(items[0].value).toBe(`${p.level}`);
    expect(txt(items[0].unit, 'en')).toBe('of 16');
    expect(items[1].value).toBe(f(p.displayed, 3));
    expect(txt(items[1].unit, 'en')).toBe('rad');
    expect(items[2].value).toBe(f(0.85, 2));
    for (const c of items) {
      expect(['alarm', 'warning', 'normal', 'selected', 'inactive']).toContain(c.state);
      for (const l of ['en', 'es'] as const) expect(txt(c.source, l)).not.toMatch(/[a-z]+\.[a-z_]+|\[\]|[a-z]+_[a-z_]+/);
      expect(c.anchor.x).toBeGreaterThan(0);
      expect(c.anchor.x).toBeLessThan(1);
      expect(c.anchor.y).toBeGreaterThan(0);
      expect(c.anchor.y).toBeLessThan(1);
    }
    expect(items[2].state).toBe('warning');
  });

  it('prints the pixel readout, the fill factor and the kernel weights of the case', () => {
    const out = renderToStaticMarkup(<SlmSectionDrawing sel={sel} row={row} col={col} lang="en" width={W} height={H} onCol={vi.fn()} />);
    const p = slmPixel(row, col);
    expect(out).toContain(`${p.level}`);
    expect(out).toContain(f(0.85, 2));
    expect(out).toContain(f(row.kernel![Math.floor(row.kernel!.length / 2)] * 100, 2));
    expect(out).not.toMatch(/undefined|NaN/);
  });

  it('the Spanish drawing prints the decimal comma and Spanish labels', () => {
    const out = renderToStaticMarkup(<SlmSectionDrawing sel={sel} row={row} col={col} lang="es" width={W} height={H} onCol={vi.fn()} />);
    expect(out).toContain(f(0.85, 2, 'es'));
    expect(out).toMatch(/VIDRIO DE CUBIERTA/);
  });

  it('clicking a pixel of the section moves the scrubbed column to it', () => {
    const onCol = vi.fn();
    const pixels = nodes(<SlmSectionDrawing sel={sel} row={row} col={col} lang="en" width={W} height={H} onCol={onCol} />).filter((n) => n.props['data-slm-pixel'] !== undefined);
    expect(pixels.length).toBeGreaterThanOrEqual(8);
    const target = pixels[2];
    (target.props.onClick as () => void)();
    expect(onCol).toHaveBeenCalledWith(Number(target.props['data-slm-pixel']));
  });

  it('draws nothing that moves', () => {
    const out = renderToStaticMarkup(<SlmSectionDrawing sel={sel} row={row} col={col} lang="en" width={W} height={H} onCol={vi.fn()} />);
    expect(out).not.toMatch(/<animate|dh-flow|animation/);
  });
});

describe('the scrubbed window', () => {
  it('stays inside the row and centres on the pixel when it can', () => {
    expect(windowStart(64, 128, 16)).toBe(56);
    expect(windowStart(0, 128, 16)).toBe(0);
    expect(windowStart(127, 128, 16)).toBe(112);
    expect(windowStart(5, 128, 8)).toBe(1);
  });

  it('a 340 px stage draws 8 pixels, a 1000 px stage 16', () => {
    const sel = realSelection('C08_device_limited');
    const r = slmRow(sel, 64);
    const wide = nodes(<SlmSectionDrawing sel={sel} row={r} col={64} lang="en" width={1000} height={460} onCol={vi.fn()} />).filter((n) => n.props['data-slm-pixel'] !== undefined);
    const narrow = nodes(<SlmSectionDrawing sel={sel} row={r} col={64} lang="en" width={340} height={400} onCol={vi.fn()} />).filter((n) => n.props['data-slm-pixel'] !== undefined);
    expect(wide).toHaveLength(16);
    expect(narrow).toHaveLength(8);
  });
});

describe('the electrodes label and the kernel label never share a line (gate G10)', () => {
  it('the kernel starts at least 24 px under the electrodes, at every stage size, so the two labels sit one under the other', () => {
    for (const [w, h] of [[340, 400], [390, 560], [768, 640], [1000, 460], [1280, 700]] as const) {
      const L = slmLayout(w, h);
      expect(L.kernel.y - (L.elec.y + L.elec.h), `${w} x ${h}`).toBeGreaterThanOrEqual(24);
      expect(L.kernel.y + L.kernel.h).toBeLessThanOrEqual(L.caption);
    }
  });
});
