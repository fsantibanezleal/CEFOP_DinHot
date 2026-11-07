// V1, the optical train (ADR-0082 kind V1, the system; SDD visualization catalog row V1): a side view of the beam path as optics papers draw it,
// laser, beam expander, SLM, 4f relay, objective, focal plane with the trap array, unfolded into one line. The light is the beam envelope,
// moving along it as a dash pattern while motion is allowed and playing (off under prefers-reduced-motion, where the chevrons give the
// direction instead). Each element carries the value of the selected case; the SLM opens Device effects, the focal plane opens the Focal
// plane group, a trap site selects that trap everywhere (the shell's linked store). Three SceneCallouts name what the reader should read.
// Nothing here is a default: a value the case lacks is said to be absent. The geometry is a pure function of the stage size (trainLayout).
import { PlotCard, SceneCallouts, Stage, formatNumber, prefersReducedMotion, useLinkedView, useShellLang, type SceneCalloutDef } from '@fasl-work/caos-app-shell';
import { useCallback, useEffect, useMemo, useState, type KeyboardEvent, type PointerEvent as ReactPointerEvent } from 'react';
import type { Text } from '../lib/contract.types';
import { ReadinessNote } from '../readiness/ReadinessNote';
import { isShaped, type Selection } from './model';
import { useNav, type ViewTarget } from './nav';
import { CASE_ROWS, cardOf, StageBox, useStateKey } from './ui';

export type TrainId = 'laser' | 'expander' | 'slm' | 'relay' | 'objective' | 'focal';
export const TRAIN_IDS: readonly TrainId[] = ['laser', 'expander', 'slm', 'relay', 'objective', 'focal'];
type Lang = 'en' | 'es';

/** The view each element opens; an element absent here is not a button. */
export const TRAIN_TARGET: Partial<Record<TrainId, ViewTarget>> = {
  slm: { group: 'hologram', tab: 'device' },
  focal: { group: 'focal', tab: 'plane' },
};

/** What selecting an element does: open its view through the workbench switch. Elements with no view do nothing. */
export function openTrainElement(id: TrainId, open: (target: ViewTarget) => void): void {
  const target = TRAIN_TARGET[id];
  if (target) open(target);
}

export interface TrainItem {
  id: TrainId;
  name: string;
  /** The case's value on this element; empty when the case holds none (the 4f relay is not in the engine). */
  value: string;
  detail: string;
}

const NAMES: Record<TrainId, Text> = {
  laser: { en: 'Laser', es: 'Láser' },
  expander: { en: 'Beam expander', es: 'Expansor de haz' },
  slm: { en: 'SLM', es: 'SLM' },
  relay: { en: '4f relay', es: 'Relevo 4f' },
  objective: { en: 'Objective', es: 'Objetivo' },
  focal: { en: 'Focal plane', es: 'Plano focal' },
};

/** The 1/e^2 diameter of the beam at the SLM in millimetres: the waist fraction of the aperture N p (geometry.py), or the aperture for a flat beam. */
export function beamDiameterMm(sel: Selection): { mm: number; flat: boolean } {
  const s = sel.data.manifest.params.setup;
  const aperture = (s.n_pix * s.pitch_um) / 1000;
  const beam = s.beam as { kind: string; waist_frac?: number };
  return beam.kind === 'gaussian' && typeof beam.waist_frac === 'number' ? { mm: beam.waist_frac * aperture, flat: false } : { mm: aperture, flat: true };
}

/** The efficiency the selected method reaches at the focal plane (the live run's when there is one, else the baked), or null. */
export const efficiencyOf = (sel: Selection): number | null => sel.result?.metrics?.efficiency ?? null;

/** The six elements with the values of the selected case, in the language of the page. */
export function trainItems(sel: Selection, lang: Lang): TrainItem[] {
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const f = (v: number, d: number) => formatNumber(v, lang, { decimals: d });
  const s = sel.data.manifest.params.setup;
  const aperture = (s.n_pix * s.pitch_um) / 1000;
  const beam = beamDiameterMm(sel);
  const eff = efficiencyOf(sel);
  const shaped = isShaped(sel.data.manifest);
  const n = sel.traps.length;
  return [
    { id: 'laser', name: NAMES.laser[lang], value: `${f(s.wavelength_nm, 0)} nm`, detail: t('wavelength', 'longitud de onda') },
    { id: 'expander', name: NAMES.expander[lang], value: `${f(beam.mm, 2)} mm`, detail: beam.flat ? t('flat beam over the aperture', 'haz plano sobre la apertura') : t('1/e2 diameter at the SLM', 'diámetro 1/e2 en el SLM') },
    { id: 'slm', name: NAMES.slm[lang], value: `${s.n_pix} x ${s.n_pix} px`, detail: t(`pitch ${f(s.pitch_um, 1)} um, aperture ${f(aperture, 2)} mm`, `paso ${f(s.pitch_um, 1)} um, apertura ${f(aperture, 2)} mm`) },
    { id: 'relay', name: NAMES.relay[lang], value: '', detail: t('not modelled: one Fourier lens', 'no modelado: una lente de Fourier') },
    { id: 'objective', name: NAMES.objective[lang], value: `f ${f(s.focal_mm, 1)} mm`, detail: `NA ${f(s.na, 2)}, n ${f(s.n_imm, 2)}` },
    {
      id: 'focal',
      name: NAMES.focal[lang],
      value: shaped ? t('shaped potential', 'potencial con forma') : t(`${n} ${n === 1 ? 'trap' : 'traps'}`, `${n} ${n === 1 ? 'trampa' : 'trampas'}`),
      detail: eff === null ? t('efficiency not available', 'eficiencia no disponible') : t(`efficiency ${formatNumber(eff, lang, { percent: true, decimals: 1 })}`, `eficiencia ${formatNumber(eff, lang, { percent: true, decimals: 1 })}`),
    },
  ];
}

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}
export interface TrainLayout {
  mode: 'line' | 'rows';
  /** The height the callout row takes at the top of the stage. */
  band: number;
  /** The glyph box of each element: where its drawing sits and where its callout points. */
  items: Record<TrainId, Box>;
  /** The face-on square of the focal plane, inside the focal element's box. */
  field: Box;
  axisY: number;
}

/** The height of the shell's header row of three callouts at a stage width (SceneCallouts placement="header"), plus a gap. */
export function calloutBand(width: number): number {
  const compact = width < 640;
  const w = compact ? 164 : 184;
  const h = compact ? 54 : 68;
  const gap = compact ? 6 : 8;
  const columns = width < 520 ? 2 : Math.max(1, Math.min(3, Math.floor((width - 16 + gap) / (w + gap))));
  const rows = Math.ceil(3 / columns);
  return 8 + rows * h + (rows - 1) * gap + 22;
}

/** The geometry of the train at a stage size: six columns on a line, or at phone width six rows down a vertical beam. */
export function trainLayout(width: number, height: number): TrainLayout {
  const band = calloutBand(width);
  const rest = Math.max(0, height - band);
  if (width >= 520) {
    const m = 12;
    const col = (width - 2 * m) / 6;
    const gh = Math.max(56, Math.min(240, rest * 0.5));
    // the glyphs and the three label lines under them form one block, centred in what the callout row leaves
    const y = band + Math.max(6, (rest - gh - 56) / 2);
    const items = {} as Record<TrainId, Box>;
    TRAIN_IDS.forEach((id, i) => {
      items[id] = { x: m + i * col + 3, y, w: col - 6, h: gh };
    });
    const side = Math.min(items.focal.w - 8, gh);
    const field = { x: items.focal.x + (items.focal.w - side) / 2, y: y + (gh - side) / 2, w: side, h: side };
    return { mode: 'line', band, items, field, axisY: y + gh / 2 };
  }
  const m = 12;
  const focalH = Math.max(64, Math.min(120, rest * 0.3));
  const rowH = Math.max(30, Math.min(44, (rest - focalH - 12) / 5));
  const items = {} as Record<TrainId, Box>;
  TRAIN_IDS.forEach((id, i) => {
    items[id] = i < 5 ? { x: m, y: band + 4 + i * rowH, w: width - 2 * m, h: rowH - 4 } : { x: m, y: band + 4 + 5 * rowH, w: width - 2 * m, h: focalH };
  });
  const side = Math.min(focalH - 10, 96);
  const f = items.focal;
  return { mode: 'rows', band, items, field: { x: f.x + f.w - side - 6, y: f.y + (f.h - side) / 2, w: side, h: side }, axisY: items.laser.y };
}

const center = (b: Box) => ({ x: b.x + b.w / 2, y: b.y + b.h / 2 });

/** The three callouts of the train: the laser's wavelength, the SLM aperture and the share of the light that reaches the traps. */
export function trainCallouts(sel: Selection, lang: Lang, width: number, height: number): SceneCalloutDef[] {
  const s = sel.data.manifest.params.setup;
  const f = (v: number, d: number) => formatNumber(v, lang, { decimals: d });
  const layout = trainLayout(width, height);
  const at = (id: TrainId) => {
    const c = center(layout.items[id]);
    return { x: c.x / width, y: c.y / height };
  };
  const eff = efficiencyOf(sel);
  const m = sel.result?.method ?? sel.methodId;
  return [
    {
      id: 'laser',
      eyebrow: { en: 'Laser', es: 'Láser' },
      value: f(s.wavelength_nm, 0),
      unit: 'nm',
      state: 'normal',
      anchor: at('laser'),
      source: { en: 'wavelength: params.setup.wavelength_nm', es: 'longitud de onda: params.setup.wavelength_nm' },
    },
    {
      id: 'slm',
      eyebrow: { en: 'SLM', es: 'SLM' },
      value: f((s.n_pix * s.pitch_um) / 1000, 2),
      unit: 'mm',
      state: 'normal',
      anchor: at('slm'),
      source: { en: 'aperture: params.setup.n_pix x pitch_um', es: 'apertura: params.setup.n_pix x pitch_um' },
    },
    {
      id: 'focal',
      eyebrow: { en: 'Traps', es: 'Trampas' },
      value: eff === null ? '-' : formatNumber(eff, lang, { percent: true, decimals: 1 }).replace(/\s*%$/, ''),
      unit: '%',
      // the thresholds of the rail readout of the same quantity (Workbench: good 0.8, bad 0.4)
      state: eff === null ? 'inactive' : eff >= 0.8 ? 'normal' : eff >= 0.4 ? 'warning' : 'alarm',
      anchor: at('focal'),
      source: { en: `light in the traps: trace methods.${m}.final.efficiency`, es: `luz en las trampas: trace methods.${m}.final.efficiency` },
    },
  ];
}

/** The traps drawn as individually selectable sites up to this count; a larger array is picked by the pointer's nearest trap. */
export const SITES_MAX = 200;

interface DrawingProps {
  sel: Selection;
  lang: Lang;
  width: number;
  height: number;
  /** Motion is allowed (the page does not ask for reduced motion). */
  motion: boolean;
  /** The reader has not paused the light. */
  playing: boolean;
  /** The linked selection (a trap id as a string). */
  selectedId: string | null;
  onOpen: (id: TrainId) => void;
  onSelectTrap: (id: number) => void;
}

/** The point of a trap in the focal square: the array's own extent fills the square, y up. */
function siteAt(field: Box, ext: number, x: number, y: number) {
  const half = field.w / 2;
  const k = (half - 5) / ext;
  return { x: field.x + half + x * k, y: field.y + field.h / 2 - y * k };
}

const extentOf = (traps: readonly { x_um: number; y_um: number }[]): number => Math.max(1e-6, ...traps.map((t) => Math.max(Math.abs(t.x_um), Math.abs(t.y_um)))) * 1.1;

/** The drawing: pure, so its tests read the element tree. Positions are pixels of the stage. */
export function OpticalTrainDrawing(p: DrawingProps) {
  const { sel, lang, width, height, motion, playing, selectedId } = p;
  const L = trainLayout(width, height);
  const items = trainItems(sel, lang);
  const byId = Object.fromEntries(items.map((i) => [i.id, i])) as Record<TrainId, TrainItem>;
  const animated = motion && playing;
  const flow = animated ? 'dh-flow' : undefined;
  const eff = efficiencyOf(sel);
  const rows = L.mode === 'rows';
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const traps = sel.traps;
  const ext = extentOf(traps);
  const sites = traps.length <= SITES_MAX;
  const f = (v: number, d: number) => formatNumber(v, lang, { decimals: d });

  const open = (id: TrainId) => (TRAIN_TARGET[id] ? { role: 'button' as const, tabIndex: 0, onClick: () => p.onOpen(id), onKeyDown: (e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); p.onOpen(id); } } } : {});
  const label = (i: TrainItem) => [i.name, i.value, i.detail].filter(Boolean).join(', ') + (TRAIN_TARGET[i.id] ? t(' (opens its view)', ' (abre su vista)') : '');

  // The beam envelope: half-heights along the unfolded path (the aperture is the SLM glyph's full height).
  const slm = L.items.slm;
  const beam = beamDiameterMm(sel);
  const rb = (slm.h / 2) * 0.9 * Math.min(1, beam.flat ? 1 : beam.mm / ((sel.data.manifest.params.setup.n_pix * sel.data.manifest.params.setup.pitch_um) / 1000));
  const cx = (id: TrainId) => center(L.items[id]).x;
  const col = (L.items.slm.w + 6);
  const ay = L.axisY;
  const pts: [number, number][] = rows
    ? []
    : [
        [cx('laser') + col * 0.28, 3],
        [cx('expander') - col * 0.28, 3],
        [cx('expander') + col * 0.28, rb],
        [cx('slm'), rb],
        [cx('relay') - col * 0.3, rb],
        [cx('relay'), rb * 0.28],
        [cx('relay') + col * 0.3, rb],
        [cx('objective'), rb],
        [L.field.x, 2],
      ];
  const upper = pts.map(([x, r]) => `${x},${ay - r}`);
  const lower = pts.map(([x, r]) => `${x},${ay + r}`).reverse();
  const afterSlm = pts.filter(([x]) => x >= cx('slm'));
  const coreScale = eff === null ? 0 : Math.max(0, Math.min(1, eff));
  const core = [...afterSlm.map(([x, r]) => `${x},${ay - r * coreScale}`), ...afterSlm.map(([x, r]) => `${x},${ay + r * coreScale}`).reverse()];

  // The vertical beam of the narrow layout.
  const vx = rows ? L.items.laser.x + 9 : 0;
  const vy0 = rows ? L.items.laser.y + 6 : 0;
  const vy1 = rows ? L.items.focal.y + 8 : 0;

  const elementBox = (id: TrainId) => {
    const b = L.items[id];
    const i = byId[id];
    const isBtn = !!TRAIN_TARGET[id];
    return (
      <g key={id} data-train-element={id} aria-label={label(i)} {...open(id)} className={isBtn ? 'dh-train-button' : undefined}>
        <rect x={b.x} y={b.y} width={b.w} height={b.h} rx="8" fill="var(--color-surface)" fillOpacity={isBtn ? 1 : 0.6} stroke={isBtn ? 'var(--color-accent)' : 'var(--color-border)'} strokeWidth={isBtn ? 1.5 : 1} />
      </g>
    );
  };

  const glyph = (id: TrainId) => {
    const b = L.items[id];
    const c = center(b);
    const stroke = { stroke: 'var(--color-fg)', strokeWidth: 1.6 };
    if (rows) return null;
    switch (id) {
      case 'laser':
        return <g aria-hidden="true"><rect x={b.x + 6} y={c.y - 12} width={b.w * 0.55} height="24" rx="4" fill="var(--color-surface-2)" {...stroke} /><circle cx={b.x + 6 + b.w * 0.55} cy={c.y} r="3" fill="var(--color-accent)" /></g>;
      case 'expander':
        return <g aria-hidden="true"><ellipse cx={c.x - b.w * 0.2} cy={c.y} rx="4" ry="9" fill="none" {...stroke} /><ellipse cx={c.x + b.w * 0.22} cy={c.y} rx="6" ry={Math.min(rb + 4, b.h / 2 - 4)} fill="none" {...stroke} /></g>;
      case 'slm':
        return (
          <g aria-hidden="true">
            <rect x={c.x - 5} y={c.y - b.h * 0.45} width="10" height={b.h * 0.9} rx="2" fill="var(--color-surface-2)" {...stroke} />
            {Array.from({ length: 9 }, (_, k) => <line key={k} x1={c.x - 5} x2={c.x + 5} y1={c.y - b.h * 0.45 + ((k + 1) * b.h * 0.9) / 10} y2={c.y - b.h * 0.45 + ((k + 1) * b.h * 0.9) / 10} stroke="var(--color-border)" strokeWidth="1" />)}
          </g>
        );
      case 'relay':
        return <g aria-hidden="true"><ellipse cx={c.x - b.w * 0.3} cy={c.y} rx="4" ry={Math.min(rb + 2, b.h / 2 - 4)} fill="none" {...stroke} /><ellipse cx={c.x + b.w * 0.3} cy={c.y} rx="4" ry={Math.min(rb + 2, b.h / 2 - 4)} fill="none" {...stroke} /></g>;
      case 'objective':
        return <g aria-hidden="true"><ellipse cx={c.x} cy={c.y} rx="7" ry={Math.min(rb + 4, b.h / 2 - 3)} fill="var(--color-surface-2)" {...stroke} /></g>;
      default:
        return null;
    }
  };

  const textBlock = (id: TrainId) => {
    const b = L.items[id];
    const i = byId[id];
    if (rows && id === 'focal') {
      // the focal row holds the face-on array at its right: the texts stack at its left
      return (
        <g key={`t-${id}`} pointerEvents="none">
          <text x={b.x + 22} y={b.y + b.h / 2 - 8} fill="var(--color-fg)" fontSize="12" fontWeight="700" letterSpacing="0.4">{i.name.toUpperCase()}</text>
          <text x={b.x + 22} y={b.y + b.h / 2 + 8} fill="var(--color-fg)" fontSize="12" fontFamily="var(--font-mono)">{i.value}</text>
          <text x={b.x + 22} y={b.y + b.h / 2 + 23} fill="var(--color-fg-subtle)" fontSize="11">{i.detail}</text>
        </g>
      );
    }
    if (rows) {
      return (
        <g key={`t-${id}`} pointerEvents="none">
          <text x={b.x + 22} y={b.y + b.h / 2 + 4} fill="var(--color-fg)" fontSize="12" fontWeight="700" letterSpacing="0.4">{i.name.toUpperCase()}</text>
          {i.value ? <text x={b.x + b.w - 8} y={b.y + b.h / 2 + 4} textAnchor="end" fill="var(--color-fg)" fontSize="12" fontFamily="var(--font-mono)">{i.value}</text> : null}
        </g>
      );
    }
    const top = b.y + b.h + 16;
    return (
      <g key={`t-${id}`} pointerEvents="none">
        <text x={b.x + b.w / 2} y={top} textAnchor="middle" fill="var(--color-fg)" fontSize="11" fontWeight="700" letterSpacing="0.5">{i.name.toUpperCase()}</text>
        {i.value ? <text x={b.x + b.w / 2} y={top + 17} textAnchor="middle" fill="var(--color-fg)" fontSize="13" fontFamily="var(--font-mono)">{i.value}</text> : null}
        <text x={b.x + b.w / 2} y={top + (i.value ? 33 : 17)} textAnchor="middle" fill="var(--color-fg-subtle)" fontSize="11">{i.detail}</text>
      </g>
    );
  };

  const nearest = (e: ReactPointerEvent<SVGRectElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = L.field.x + ((e.clientX - r.left) / Math.max(1, r.width)) * L.field.w;
    const py = L.field.y + ((e.clientY - r.top) / Math.max(1, r.height)) * L.field.h;
    let best = traps[0];
    let bd = Infinity;
    for (const tr of traps) {
      const s = siteAt(L.field, ext, tr.x_um, tr.y_um);
      const d = (s.x - px) ** 2 + (s.y - py) ** 2;
      if (d < bd) { bd = d; best = tr; }
    }
    if (best) p.onSelectTrap(best.id);
  };

  const dot = Math.max(2.2, Math.min(5, (L.field.w - 10) / (2 * Math.sqrt(Math.max(1, traps.length)))));
  const selectedTrap = selectedId === null ? null : traps.find((tr) => String(tr.id) === selectedId) ?? null;

  return (
    <svg className="dh-train" viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="group" aria-label={t('Optical train: laser, beam expander, SLM, 4f relay, objective and focal plane with the values of the case', 'Tren óptico: láser, expansor de haz, SLM, relevo 4f, objetivo y plano focal con los valores del caso')} data-layout={rows ? 'rows' : 'line'} data-animated={animated ? 'true' : 'false'}>
      <title>{t('Optical train of the case', 'Tren óptico del caso')}</title>
      {TRAIN_IDS.map((id) => (id === 'focal' ? null : elementBox(id)))}
      {/* the light: the envelope of the beam, its edge rays moving along it, and the share that reaches the traps */}
      {rows ? (
        <g aria-hidden="true" pointerEvents="none">
          <line x1={vx} x2={vx} y1={vy0} y2={vy1} stroke="var(--color-accent)" strokeWidth="2" strokeOpacity="0.35" />
          <line className={flow} x1={vx} x2={vx} y1={vy0} y2={vy1} stroke="var(--color-accent)" strokeWidth="3" strokeDasharray="6 10" />
          {!animated && <g data-direction="static">{[0.2, 0.5, 0.8].map((k) => <path key={k} d={`M${vx - 4},${vy0 + (vy1 - vy0) * k - 3} L${vx},${vy0 + (vy1 - vy0) * k + 3} L${vx + 4},${vy0 + (vy1 - vy0) * k - 3}`} fill="none" stroke="var(--color-accent)" strokeWidth="2" />)}</g>}
        </g>
      ) : (
        <g aria-hidden="true" pointerEvents="none">
          <polygon points={[...upper, ...lower].join(' ')} fill="var(--color-accent)" fillOpacity="0.1" stroke="none" />
          {core.length > 2 && <polygon points={core.join(' ')} fill="var(--color-accent)" fillOpacity="0.28" stroke="none" data-share-in-traps={eff === null ? undefined : String(eff)} />}
          <polyline className={flow} points={upper.join(' ')} fill="none" stroke="var(--color-accent)" strokeWidth="1.6" strokeDasharray="6 10" />
          <polyline className={flow} points={lower.slice().reverse().join(' ')} fill="none" stroke="var(--color-accent)" strokeWidth="1.6" strokeDasharray="6 10" />
          <line className={flow} x1={pts[0][0]} x2={L.field.x} y1={ay} y2={ay} stroke="var(--color-accent)" strokeWidth="2" strokeDasharray="3 9" />
          {!animated && (
            <g data-direction="static">
              {[cx('expander'), cx('relay') + col * 0.45, (cx('objective') + L.field.x) / 2].map((x) => <path key={x} d={`M${x - 4},${ay - 5} L${x + 3},${ay} L${x - 4},${ay + 5}`} fill="none" stroke="var(--color-accent)" strokeWidth="2" />)}
            </g>
          )}
        </g>
      )}
      {TRAIN_IDS.map((id) => (id === 'focal' ? null : <g key={`g-${id}`} pointerEvents="none">{glyph(id)}</g>))}
      {/* the focal plane: a button for the view, the array face-on inside it */}
      {elementBox('focal')}
      <rect x={L.field.x} y={L.field.y} width={L.field.w} height={L.field.h} rx="4" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1" pointerEvents="none" />
      <text x={L.field.x + 4} y={L.field.y + 11} fill="var(--color-fg-subtle)" fontSize="10" fontFamily="var(--font-mono)" pointerEvents="none">{traps.length ? `±${f(ext / 1.1, 1)} um` : ''}</text>
      {TRAIN_IDS.map((id) => textBlock(id))}
      <g data-train-sites="">
        {sites
          ? traps.map((tr) => {
              const s = siteAt(L.field, ext, tr.x_um, tr.y_um);
              const chosen = selectedId === String(tr.id);
              return (
                <circle
                  key={tr.id}
                  cx={s.x}
                  cy={s.y}
                  r={chosen ? dot + 2 : dot}
                  role="button"
                  tabIndex={-1}
                  aria-label={t(`Trap ${tr.id}`, `Trampa ${tr.id}`)}
                  aria-pressed={chosen}
                  data-linked-id={String(tr.id)}
                  data-linked-view="scene"
                  data-linked-selected={chosen ? 'true' : 'false'}
                  fill={chosen ? 'var(--color-bad)' : 'var(--color-accent)'}
                  stroke={chosen ? 'var(--color-bg)' : 'none'}
                  strokeWidth="1.5"
                  onClick={(e) => { e.stopPropagation(); p.onSelectTrap(tr.id); }}
                />
              );
            })
          : traps.map((tr) => {
              const s = siteAt(L.field, ext, tr.x_um, tr.y_um);
              return <circle key={tr.id} cx={s.x} cy={s.y} r={dot} fill="var(--color-accent)" aria-hidden="true" pointerEvents="none" />;
            })}
        {!sites && (
          <rect data-train-field="" x={L.field.x} y={L.field.y} width={L.field.w} height={L.field.h} fill="transparent" role="application" aria-label={t('Focal plane sites: click to select the nearest trap', 'Sitios del plano focal: pulse para elegir la trampa más cercana')} onPointerDown={nearest} />
        )}
        {!sites && selectedTrap && (() => { const s = siteAt(L.field, ext, selectedTrap.x_um, selectedTrap.y_um); return <circle cx={s.x} cy={s.y} r={dot + 3} fill="none" stroke="var(--color-bad)" strokeWidth="2" pointerEvents="none" data-linked-selected-trap={String(selectedTrap.id)} />; })()}
      </g>
    </svg>
  );
}

/** The user's choice to see the light still, remembered nowhere: a view starts playing unless the page asks for reduced motion. */
function useMotionAllowed(): boolean {
  const [reduced, setReduced] = useState(() => prefersReducedMotion());
  useEffect(() => {
    if (typeof matchMedia === 'undefined') return;
    const q = matchMedia('(prefers-reduced-motion: reduce)');
    const on = () => setReduced(q.matches);
    on();
    q.addEventListener('change', on);
    return () => q.removeEventListener('change', on);
  }, []);
  return !reduced;
}

/** The first view of the Hologram group: the optical train of the selected case, with its callouts, play control and takeaway. */
export function OpticalTrainView({ sel }: { sel: Selection }) {
  const lang = useShellLang();
  const stateKey = useStateKey();
  const nav = useNav();
  const motion = useMotionAllowed();
  const [playing, setPlaying] = useState(true);
  const selectedId = useLinkedView((s) => s.selectedId);
  const select = useLinkedView((s) => s.select);
  const onOpen = useCallback((id: TrainId) => nav && openTrainElement(id, nav.open), [nav]);
  const onSelectTrap = useCallback((id: number) => select(String(id), 'scene'), [select]);
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const eff = efficiencyOf(sel);
  const n = sel.traps.length;
  const note = useMemo(
    () => ({
      en: `The beam fills the SLM aperture, the hologram splits it, and ${eff === null ? 'the share that reaches' : formatNumber(eff, 'en', { percent: true, decimals: 1 })} of the light reaches ${isShaped(sel.data.manifest) ? 'the shaped potential' : `the ${n} ${n === 1 ? 'trap' : 'traps'}`} (method ${sel.result?.method ?? sel.methodId}). The bright core after the SLM is that share; the light moves from the laser to the focal plane.`,
      es: `El haz llena la apertura del SLM, el holograma lo reparte y ${eff === null ? 'la fracción que llega' : formatNumber(eff, 'es', { percent: true, decimals: 1 })} de la luz llega ${isShaped(sel.data.manifest) ? 'al potencial con forma' : `a ${n === 1 ? 'la trampa' : `las ${n} trampas`}`} (método ${sel.result?.method ?? sel.methodId}). El núcleo brillante tras el SLM es esa fracción; la luz va del láser al plano focal.`,
    }),
    [eff, n, sel],
  );
  const c = cardOf(sel);
  return (
    <PlotCard fill title={{ en: 'Optical train, laser to traps', es: 'Tren óptico, del láser a las trampas' }} {...c} dataKey={stateKey} note={note}>
      <ReadinessNote ids={CASE_ROWS} />
      <StageBox>
      <Stage label={{ en: 'Optical train of the case with the value of each element', es: 'Tren óptico del caso con el valor de cada elemento' }}>
        {({ width, height }) =>
          width < 120 || height < 120 ? null : (
            <div className="dh-scene">
              <OpticalTrainDrawing sel={sel} lang={lang} width={width} height={height} motion={motion} playing={playing} selectedId={selectedId} onOpen={onOpen} onSelectTrap={onSelectTrap} />
              <SceneCallouts items={trainCallouts(sel, lang, width, height)} placement="header" />
            </div>
          )
        }
      </Stage>
      </StageBox>
      <div className="dh-row" data-caos-plot-control="">
        {motion ? (
          <button type="button" className="btn" aria-pressed={!playing} onClick={() => setPlaying((v) => !v)}>
            {playing ? t('Pause the light', 'Pausar la luz') : t('Play the light', 'Reanudar la luz')}
          </button>
        ) : (
          <span className="caos-plot-note">{t('Reduced motion: the light is drawn still, with its direction marked.', 'Movimiento reducido: la luz se dibuja quieta, con su dirección marcada.')}</span>
        )}
        <span className="caos-plot-note">{t('Select the SLM for the device effects, the focal plane for the traps, a site to select a trap.', 'Elija el SLM para los efectos del dispositivo, el plano focal para las trampas, un sitio para elegir una trampa.')}</span>
      </div>
    </PlotCard>
  );
}
