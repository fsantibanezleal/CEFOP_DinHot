// V2, the SLM in section (ADR-0082 kind V2, the key component; SDD visualization catalog row V2): one pixel row of the phase mask cut open along
// a line the reader scrubs: the cover glass, the liquid-crystal layer with the level each pixel is commanded (the fill height), the pixel
// electrodes with the fill factor of the device, the fringing field between neighbours, the crosstalk kernel of the device, and over the
// section the phase asked for and the phase displayed. The displayed phase is the engine's own order (decode.ts stagePhase: quantize,
// response curve, crosstalk blur). The ideal device is a choice of the same switch as the rail's: one state, not a copy. A case with no
// device block shows the ideal device and says so; its case-device choice is disabled with the reason. Nothing here moves.
import { ChipGroup, PlotCard, SceneCallouts, Stage, formatNumber, useShellLang, type SceneCalloutDef } from '@fasl-work/caos-app-shell';
import { useMemo, useState } from 'react';
import type { Text } from '../lib/contract.types';
import { ReadinessNote } from '../readiness/ReadinessNote';
import { apertureEnvelopeAtEdge, crosstalkWeights, fillFactorEfficiency, levelOf, quantizationEfficiency, stagePhase, TWO_PI } from './decode';
import type { Selection } from './model';
import { calloutBand } from './OpticalTrain';
import { CASE_ROWS, cardOf, StageBox, useActions, useStateKey } from './ui';
import { MARECHAL_RMS_WAVES } from './zernike';

type Lang = 'en' | 'es';

/** One pixel row of the mask at the stages of the engine's device model. */
export interface SlmRow {
  row: number;
  n: number;
  /** True when the device of the case is on: false for the ideal choice and for a case with no device block. */
  deviceOn: boolean;
  bits: number | null;
  /** The fill factor (area fraction) of the device; null when the device is off. */
  fill: number | null;
  /** The phase the method asks for, radians in [0, 2 pi). */
  requested: number[];
  /** After quantization and the response curve, before the crosstalk blur. */
  quantized: number[];
  /** What the device shows: quantize, response, crosstalk. Equal to `requested` for the ideal device. */
  displayed: number[];
  /** The 1D crosstalk weights over -reach..reach pixels (sum 1); null without a crosstalk kernel. */
  kernel: number[] | null;
}

/** The whole displayed map of a selection, for a view that reads several rows of it. */
export function displayedMap(sel: Selection): { quantized: Float32Array; shown: Float32Array } | null {
  const maps = sel.maps;
  const dev = sel.deviceModel;
  if (!maps || !dev || sel.device !== 'case') return null;
  return { quantized: stagePhase(maps.phase, maps.nPix, { ...dev, crosstalk: null }, 'crosstalk'), shown: stagePhase(maps.phase, maps.nPix, dev, 'crosstalk') };
}

export function slmRow(sel: Selection, row: number, maps = displayedMap(sel)): SlmRow {
  const m = sel.maps;
  const n = m?.nPix ?? 0;
  const take = (a: ArrayLike<number> | undefined) => Array.from({ length: n }, (_, c) => (a ? a[row * n + c] : 0));
  const requested = take(m?.phase);
  const dev = sel.deviceModel;
  const on = !!(maps && dev && sel.device === 'case');
  const cx = on && dev?.crosstalk ? dev.crosstalk : null;
  return {
    row,
    n,
    deviceOn: on,
    bits: on ? (dev?.bit_depth ?? null) : null,
    fill: on && dev ? dev.fill_factor : null,
    requested,
    quantized: on && maps ? take(maps.quantized) : requested,
    displayed: on && maps ? take(maps.shown) : requested,
    kernel: cx && dev ? Array.from(crosstalkWeights(cx.sigma_per_px, cx.q, dev.upsample, n)) : null,
  };
}

export interface SlmPixel {
  col: number;
  requested: number;
  level: number | null;
  levels: number | null;
  /** The phase of the commanded level (the requested phase when the device has no quantizer). */
  commanded: number;
  displayed: number;
  /** displayed - requested, wrapped to (-pi, pi]. */
  error: number;
}

const wrapPi = (d: number): number => d - TWO_PI * Math.round(d / TWO_PI);

export function slmPixel(r: SlmRow, col: number): SlmPixel {
  const requested = r.requested[col];
  const levels = r.bits === null ? null : 2 ** r.bits;
  const level = r.bits === null ? null : levelOf(requested, r.bits);
  return { col, requested, level, levels, commanded: level === null || levels === null ? requested : (level * TWO_PI) / levels, displayed: r.displayed[col], error: wrapPi(r.displayed[col] - requested) };
}

const rms = (a: number[]): number => Math.sqrt(a.reduce((s, v) => s + v * v, 0) / Math.max(1, a.length));

/** What each effect costs: the closed forms of the device view (fractions of the ideal light), and the rms phase error each stage adds on this row. */
export function slmLosses(sel: Selection, r: SlmRow) {
  const dev = sel.deviceModel;
  if (!r.deviceOn || !dev) return { quantization: 0, fillFactor: 0, apertureEdge: 0, quantizationRmsRad: 0, crosstalkRmsRad: 0 };
  return {
    quantization: r.bits === null ? 0 : 1 - quantizationEfficiency(2 ** r.bits),
    fillFactor: 1 - fillFactorEfficiency(dev.fill_factor),
    apertureEdge: 1 - apertureEnvelopeAtEdge(dev.fill_factor),
    quantizationRmsRad: rms(r.quantized.map((q, c) => wrapPi(q - r.requested[c]))),
    crosstalkRmsRad: rms(r.displayed.map((d, c) => wrapPi(d - r.quantized[c]))),
  };
}

/** Whether the case's device can be chosen, and when not, why. */
export function slmDeviceSwitch(sel: Selection): { disabled: boolean; reason: Text | null } {
  if (sel.data.manifest.params.device) return { disabled: false, reason: null };
  return { disabled: true, reason: { en: 'This case has no device block: the ideal SLM is shown.', es: 'Este caso no tiene bloque de dispositivo: se muestra el SLM ideal.' } };
}

/** The first pixel of the scrubbed window of `win` pixels, centred on `col` and kept inside the row. */
export const windowStart = (col: number, n: number, win: number): number => Math.max(0, Math.min(n - win, Math.round(col - win / 2)));

interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}
export interface SlmLayout {
  win: number;
  band: number;
  graph: Box;
  cover: Box;
  lc: Box;
  elec: Box;
  kernel: Box;
  cw: number;
  caption: number;
}

/** The geometry at a stage size: pixels of the stage, top to bottom the callout row, the phase graph, the section, the kernel and the caption; it always fits. */
export function slmLayout(width: number, height: number): SlmLayout {
  const narrow = width < 520;
  const win = narrow ? 8 : 16;
  const band = calloutBand(width);
  const x0 = narrow ? 34 : 58;
  const x1 = width - 10;
  const a = Math.max(150, height - band - 4 - 20);
  const gh = a * 0.28;
  const kernelH = Math.max(28, a * 0.18);
  const coverH = 14;
  const elecH = 12;
  const lcH = Math.max(30, a - gh - kernelH - (coverH + elecH + 12 + 14));
  const secTop = band + 4 + gh + 12;
  const w = x1 - x0;
  return {
    win,
    band,
    cw: w / win,
    graph: { x: x0, y: band + 4, w, h: gh },
    cover: { x: x0, y: secTop, w, h: coverH },
    lc: { x: x0, y: secTop + coverH, w, h: lcH },
    elec: { x: x0, y: secTop + coverH + lcH, w, h: elecH },
    kernel: { x: x0, y: secTop + coverH + lcH + elecH + 14, w, h: kernelH },
    caption: height - 6,
  };
}

/** The y of a phase in the plot of the graph: the first 16 px of the graph hold its legend. */
export const phaseY = (L: SlmLayout, v: number): number => L.graph.y + 16 + (L.graph.h - 16) * (1 - v / TWO_PI);

const toneOfFill = (eff: number): 'normal' | 'warning' | 'alarm' => (eff > 0.9 ? 'normal' : eff > 0.7 ? 'warning' : 'alarm');

/** The three callouts: the level commanded to the scrubbed pixel, the phase it displays, the fill factor of the electrodes. */
export function slmCallouts(_sel: Selection, r: SlmRow, col: number, lang: Lang, width: number, height: number): SceneCalloutDef[] {
  const f = (v: number, d: number) => formatNumber(v, lang, { decimals: d });
  const L = slmLayout(width, height);
  const c0 = windowStart(col, r.n, L.win);
  const i = Math.max(0, Math.min(L.win - 1, col - c0));
  const px = L.lc.x + (i + 0.5) * L.cw;
  const p = slmPixel(r, col);
  const norm = (x: number, y: number) => ({ x: x / width, y: y / height });
  const dy = phaseY(L, p.displayed);
  const on = r.deviceOn;
  const absErr = Math.abs(p.error);
  // within half a level step of the quantizer is the quantizer's own error (normal); within a step is warning; the Marechal limit stands in
  // when the device has no quantizer (zernike.ts)
  const tol = p.levels === null ? TWO_PI * MARECHAL_RMS_WAVES : TWO_PI / p.levels / 2;
  const state = !on ? 'inactive' : absErr <= tol ? 'normal' : absErr <= 2 * tol ? 'warning' : 'alarm';
  const field = on ? { en: 'commanded: params.device.bit_depth', es: 'ordenado: params.device.bit_depth' } : { en: 'requested: reference.phase_u8', es: 'pedida: reference.phase_u8' };
  return [
    {
      id: 'level',
      eyebrow: { en: 'Level', es: 'Nivel' },
      value: p.level !== null ? `${p.level}` : f(p.requested, 3),
      unit: p.level !== null && p.levels !== null ? { en: `of ${p.levels}`, es: `de ${p.levels}` } : 'rad',
      state: on ? 'normal' : 'inactive',
      anchor: norm(px, L.lc.y + L.lc.h / 2),
      source: field,
    },
    {
      id: 'displayed',
      eyebrow: { en: 'Phase', es: 'Fase' },
      value: f(p.displayed, 3),
      unit: 'rad',
      state,
      anchor: norm(px, dy),
      source: on ? { en: 'engine stages: params.device', es: 'etapas del motor: params.device' } : { en: 'displayed = requested: reference.phase_u8', es: 'mostrada = pedida: reference.phase_u8' },
    },
    {
      id: 'fill',
      eyebrow: { en: 'Fill', es: 'Llenado' },
      value: r.fill === null ? 'ideal' : f(r.fill, 2),
      unit: r.fill === null ? { en: 'no device', es: 'sin dispositivo' } : { en: 'of area', es: 'del área' },
      state: r.fill === null ? 'inactive' : toneOfFill(fillFactorEfficiency(r.fill)),
      anchor: norm(px, L.elec.y + L.elec.h / 2),
      source: r.fill === null ? { en: 'params.device is absent in the case', es: 'params.device no existe en el caso' } : { en: 'fill factor: params.device.fill_factor', es: 'factor de llenado: params.device.fill_factor' },
    },
  ];
}

interface DrawingProps {
  sel: Selection;
  row: SlmRow;
  col: number;
  lang: Lang;
  width: number;
  height: number;
  onCol: (col: number) => void;
}

/** The section: pure, so its tests read the element tree. Positions are pixels of the stage. */
export function SlmSectionDrawing({ row, col, lang, width, height, onCol }: DrawingProps) {
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const f = (v: number, d: number) => formatNumber(v, lang, { decimals: d });
  const L = slmLayout(width, height);
  const narrow = width < 520;
  const fs = narrow ? 10 : 11;
  const c0 = windowStart(col, row.n, L.win);
  const p = slmPixel(row, col);
  const on = row.deviceOn;
  const levels = row.bits === null ? null : 2 ** row.bits;
  const half = on && row.fill !== null ? Math.sqrt(row.fill) : 1;
  const xAt = (i: number) => L.lc.x + (i + 0.5) * L.cw;
  const yPhase = (v: number) => phaseY(L, v);
  const idx = Array.from({ length: L.win }, (_, i) => i);
  const pix = idx.map((i) => slmPixel(row, c0 + i));
  const fillOf = (q: SlmPixel) => (q.level !== null && q.levels !== null ? q.level / q.levels : q.requested / TWO_PI);
  const d = (key: 'requested' | 'displayed') => pix.map((q, i) => `${i ? 'L' : 'M'}${xAt(i)},${yPhase(q[key])}`).join(' ');
  const kmid = row.kernel ? (row.kernel.length - 1) / 2 : 0;
  const kmax = row.kernel ? Math.max(...row.kernel) : 1;

  return (
    <svg className="dh-slm" viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="group" aria-label={t('The SLM in section along one pixel row, with the commanded and the displayed phase', 'El SLM en sección a lo largo de una fila de píxeles, con la fase pedida y la mostrada')} data-device={on ? 'case' : 'ideal'}>
      <title>{t('SLM in section', 'SLM en sección')}</title>
      {/* the phase over the section: requested (dashed) and displayed */}
      <g aria-hidden="true">
        <rect x={L.graph.x} y={L.graph.y + 16} width={L.graph.w} height={L.graph.h - 16} fill="var(--color-surface)" stroke="var(--color-border)" />
        <text x={L.graph.x - 4} y={L.graph.y + 25} textAnchor="end" fill="var(--color-fg-subtle)" fontSize={fs}>2π</text>
        <text x={L.graph.x - 4} y={L.graph.y + L.graph.h} textAnchor="end" fill="var(--color-fg-subtle)" fontSize={fs}>0</text>
        <text x={L.graph.x} y={L.graph.y + 11} fill="var(--color-fg)" fontSize={fs - 1} fontWeight="700" letterSpacing="0.4">{t('PHASE, RAD', 'FASE, RAD')}</text>
        <path d={d('requested')} fill="none" stroke="var(--color-accent)" strokeWidth="1.6" strokeDasharray="4 4" />
        {on && <path d={d('displayed')} fill="none" stroke="var(--color-warn)" strokeWidth="2" />}
        {pix.map((q, i) => <circle key={q.col} cx={xAt(i)} cy={yPhase(q.requested)} r="2.5" fill="var(--color-accent)" />)}
        {on && pix.map((q, i) => <circle key={`d${q.col}`} cx={xAt(i)} cy={yPhase(q.displayed)} r="2.5" fill="var(--color-warn)" />)}
        <text x={L.graph.x + L.graph.w} y={L.graph.y + 11} textAnchor="end" fontSize={fs}>
          <tspan fill="var(--color-accent)">{on ? t('requested (dashed)', 'pedida (trazos)') : t('requested = displayed (ideal SLM)', 'pedida = mostrada (SLM ideal)')}</tspan>
          {on && <tspan fill="var(--color-warn)" dx="10">{t('displayed', 'mostrada')}</tspan>}
        </text>
      </g>
      {/* the section: cover glass, liquid crystal, electrodes */}
      <rect x={L.cover.x} y={L.cover.y} width={L.cover.w} height={L.cover.h} fill="var(--color-surface-2)" stroke="var(--color-border)" />
      <text x={L.cover.x + 6} y={L.cover.y + L.cover.h - 3} fill="var(--color-fg)" fontSize={fs - 1} fontWeight="700" letterSpacing="0.4" pointerEvents="none">{t('COVER GLASS', 'VIDRIO DE CUBIERTA')}</text>
      <rect x={L.lc.x} y={L.lc.y} width={L.lc.w} height={L.lc.h} fill="var(--color-bg)" stroke="var(--color-border)" />
      {pix.map((q, i) => {
        const x = L.lc.x + i * L.cw;
        const h = L.lc.h * fillOf(q);
        const chosen = q.col === col;
        return (
          <g key={q.col} data-slm-pixel={q.col} role="button" tabIndex={0} aria-pressed={chosen} aria-label={t(`Pixel ${q.col}: level ${q.level ?? 'none'}, displayed ${f(q.displayed, 3)} rad`, `Píxel ${q.col}: nivel ${q.level ?? 'ninguno'}, mostrada ${f(q.displayed, 3)} rad`)} onClick={() => onCol(q.col)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onCol(q.col); } }} className="dh-slm-pixel">
            <rect x={x + 1} y={L.lc.y + L.lc.h - h} width={L.cw - 2} height={h} fill="var(--color-accent)" fillOpacity={chosen ? 0.5 : 0.28} />
            {on && <line x1={x + 2} x2={x + L.cw - 2} y1={L.lc.y + L.lc.h * (1 - q.displayed / TWO_PI)} y2={L.lc.y + L.lc.h * (1 - q.displayed / TWO_PI)} stroke="var(--color-warn)" strokeWidth="2" />}
            <rect x={x} y={L.lc.y} width={L.cw} height={L.lc.h + L.elec.h} fill="transparent" stroke={chosen ? 'var(--color-accent)' : 'var(--color-border)'} strokeWidth={chosen ? 2 : 0.5} />
            <text x={x + L.cw / 2} y={L.lc.y + 12} textAnchor="middle" fill="var(--color-fg)" fontSize={fs - 1} fontFamily="var(--font-mono)" pointerEvents="none">{q.level === null ? q.col : `${q.level}`}</text>
          </g>
        );
      })}
      <text x={L.lc.x + 6} y={L.lc.y + L.lc.h - 6} fill="var(--color-fg)" fontSize={fs - 1} fontWeight="700" letterSpacing="0.4" pointerEvents="none">{t('LIQUID CRYSTAL', 'CRISTAL LÍQUIDO')}{on && levels !== null ? ` (${t(`level of ${levels}`, `nivel de ${levels}`)})` : ''}</text>
      <rect x={L.elec.x} y={L.elec.y} width={L.elec.w} height={L.elec.h} fill="var(--color-surface)" stroke="var(--color-border)" />
      {pix.map((q, i) => {
        const x = L.lc.x + i * L.cw;
        const ew = L.cw * half;
        const next = pix[i + 1];
        const gap = L.cw - ew;
        // the fringing field arcs across the gap to the next pixel, as strong as the step between their commanded levels
        const step = next && on ? Math.abs(fillOf(next) - fillOf(q)) : 0;
        return (
          <g key={q.col} pointerEvents="none" aria-hidden="true">
            <rect x={x + (L.cw - ew) / 2} y={L.elec.y + 1} width={ew} height={L.elec.h - 2} fill="var(--color-fg-subtle)" />
            {on && next && gap > 1.5 && step > 0 && <path d={`M${x + (L.cw + ew) / 2},${L.elec.y} C${x + (L.cw + ew) / 2},${L.elec.y - 16} ${x + L.cw + (L.cw - ew) / 2},${L.elec.y - 16} ${x + L.cw + (L.cw - ew) / 2},${L.elec.y}`} fill="none" stroke="var(--color-warn)" strokeWidth={1 + 2 * step} strokeOpacity="0.75" />}
          </g>
        );
      })}
      <text x={L.elec.x + L.elec.w - 4} y={L.elec.y + L.elec.h + 11} textAnchor="end" fill="var(--color-fg)" fontSize={fs - 1} fontWeight="700" letterSpacing="0.4" pointerEvents="none">
        {on && row.fill !== null
          ? narrow ? t(`ELECTRODES, FILL ${f(row.fill, 2)}`, `ELECTRODOS, LLENADO ${f(row.fill, 2)}`) : t(`PIXEL ELECTRODES, FILL FACTOR ${f(row.fill, 2)}`, `ELECTRODOS, FACTOR DE LLENADO ${f(row.fill, 2)}`)
          : narrow ? t('ELECTRODES, IDEAL', 'ELECTRODOS, IDEAL') : t('PIXEL ELECTRODES, IDEAL (NO GAP)', 'ELECTRODOS, IDEAL (SIN HUECO)')}
      </text>
      {/* the crosstalk kernel at the scrubbed pixel: the share of its phase each neighbour contributes */}
      <g aria-hidden="true">
        {row.kernel ? (
          row.kernel.map((w, k) => {
            const i = col - c0 + (k - kmid);
            if (i < 0 || i >= L.win) return null;
            const bh = Math.max(2, (L.kernel.h - 14) * (w / kmax));
            const x = L.lc.x + i * L.cw;
            return (
              <g key={k}>
                <rect x={x + L.cw * 0.2} y={L.kernel.y + L.kernel.h - bh} width={L.cw * 0.6} height={bh} fill={k === kmid ? 'var(--color-warn)' : 'var(--color-fg-faint)'} fillOpacity="0.8" />
                <text x={x + L.cw / 2} y={L.kernel.y + L.kernel.h - bh - 3} textAnchor="middle" fill="var(--color-fg)" fontSize={fs - 1} fontFamily="var(--font-mono)">{f(Math.abs(w) < 5e-5 ? 0 : w * 100, 2)}</text>
              </g>
            );
          })
        ) : (
          <text x={L.kernel.x + 4} y={L.kernel.y + L.kernel.h / 2} fill="var(--color-fg-subtle)" fontSize={fs}>{on ? t('no crosstalk kernel in this device', 'este dispositivo no tiene núcleo de diafonía') : t('ideal SLM: no crosstalk', 'SLM ideal: sin diafonía')}</text>
        )}
        <text x={L.kernel.x - 4} y={L.kernel.y + L.kernel.h} textAnchor="end" fill="var(--color-fg-subtle)" fontSize={fs - 1}>%</text>
        {row.kernel && <text x={L.kernel.x + 2} y={L.kernel.y - 3} fill="var(--color-fg)" fontSize={fs - 1} fontWeight="700" letterSpacing="0.4">{narrow ? t('CROSSTALK KERNEL, %', 'NÚCLEO DE DIAFONÍA, %') : t('CROSSTALK KERNEL AT THE PIXEL, % OF ITS PHASE', 'NÚCLEO DE DIAFONÍA EN EL PÍXEL, % DE SU FASE')}</text>}
      </g>
      <text x={L.graph.x} y={L.caption} fill="var(--color-fg)" fontSize={fs + 1} fontFamily="var(--font-mono)">
        {narrow
          ? on
            ? t(`pixel ${p.col}: level ${p.level ?? '-'} of ${p.levels ?? '-'}, ${f(p.displayed, 3)} rad`, `píxel ${p.col}: nivel ${p.level ?? '-'} de ${p.levels ?? '-'}, ${f(p.displayed, 3)} rad`)
            : t(`pixel ${p.col}: ideal SLM, ${f(p.requested, 3)} rad`, `píxel ${p.col}: SLM ideal, ${f(p.requested, 3)} rad`)
          : on
          ? t(`pixel ${p.col}, row ${row.row}: requested ${f(p.requested, 3)} rad, level ${p.level ?? '-'} of ${p.levels ?? '-'}, displayed ${f(p.displayed, 3)} rad`, `píxel ${p.col}, fila ${row.row}: pedida ${f(p.requested, 3)} rad, nivel ${p.level ?? '-'} de ${p.levels ?? '-'}, mostrada ${f(p.displayed, 3)} rad`)
          : t(`pixel ${p.col}, row ${row.row}: ideal SLM, ${f(p.requested, 3)} rad requested and displayed`, `píxel ${p.col}, fila ${row.row}: SLM ideal, ${f(p.requested, 3)} rad pedidos y mostrados`)}
      </text>
    </svg>
  );
}

/** The key component of the problem: the SLM cut open along a row the reader scrubs, with its device switch and its three callouts. */
export function SlmSectionView({ sel }: { sel: Selection }) {
  const lang = useShellLang();
  const stateKey = useStateKey();
  const act = useActions();
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const f = (v: number, d: number) => formatNumber(v, lang, { decimals: d });
  const n = sel.maps?.nPix ?? 0;
  const [pos, setPos] = useState<{ col: number; row: number } | null>(null);
  const col = Math.max(0, Math.min(n - 1, pos?.col ?? Math.floor(n / 2)));
  const rowIx = Math.max(0, Math.min(n - 1, pos?.row ?? Math.floor(n / 2)));
  const maps = useMemo(() => displayedMap(sel), [sel.maps?.phase, sel.deviceModel, sel.device]); // eslint-disable-line react-hooks/exhaustive-deps
  const row = useMemo(() => slmRow(sel, rowIx, maps), [sel.maps?.phase, sel.deviceModel, sel.device, rowIx, maps]); // eslint-disable-line react-hooks/exhaustive-deps
  const sw = slmDeviceSwitch(sel);
  const loss = slmLosses(sel, row);
  const p = n ? slmPixel(row, col) : null;
  const c = cardOf(sel);
  const pct = (v: number) => formatNumber(v, lang, { percent: true, decimals: 1 });
  const note = row.deviceOn
    ? {
        en: `Cost of each effect: ${row.bits === null ? 'no quantizer' : `quantization ${pct(loss.quantization)} of the light`}, fill factor ${pct(loss.fillFactor)}, pixel aperture at the window edge ${pct(loss.apertureEdge)}. On this row the phase error added by quantization is ${f(loss.quantizationRmsRad, 3)} rad rms and by crosstalk ${f(loss.crosstalkRmsRad, 3)} rad rms.`,
        es: `Costo de cada efecto: ${row.bits === null ? 'sin cuantizador' : `cuantización ${pct(loss.quantization)} de la luz`}, factor de llenado ${pct(loss.fillFactor)}, apertura del píxel en el borde de la ventana ${pct(loss.apertureEdge)}. En esta fila el error de fase de la cuantización es ${f(loss.quantizationRmsRad, 3)} rad rms y el de la diafonía ${f(loss.crosstalkRmsRad, 3)} rad rms.`,
      }
    : {
        en: sw.disabled ? 'This case has no device block, so the SLM is ideal: every pixel shows the phase the method asks for, with no quantization, gap or crosstalk. The case device cannot be chosen.' : 'The ideal SLM is chosen: every pixel shows the phase the method asks for. Choose the case device to see what it adds.',
        es: sw.disabled ? 'Este caso no tiene bloque de dispositivo, así que el SLM es ideal: cada píxel muestra la fase que pide el método, sin cuantización, hueco ni diafonía. No se puede elegir el dispositivo del caso.' : 'Se eligió el SLM ideal: cada píxel muestra la fase que pide el método. Elija el dispositivo del caso para ver lo que añade.',
      };
  return (
    <PlotCard fill title={{ en: 'The SLM in section along one pixel row', es: 'El SLM en sección a lo largo de una fila de píxeles' }} {...c} dataKey={stateKey} note={note}>
      <ReadinessNote ids={CASE_ROWS} />
      <StageBox>
      <Stage label={{ en: 'SLM in section: cover glass, liquid crystal and electrodes of sixteen pixels, with the requested and displayed phase over them', es: 'SLM en sección: vidrio de cubierta, cristal líquido y electrodos de dieciséis píxeles, con la fase pedida y la mostrada encima' }}>
        {({ width, height }) =>
          width < 120 || height < 120 || !p ? null : (
            <div className="dh-scene">
              <SlmSectionDrawing sel={sel} row={row} col={col} lang={lang} width={width} height={height} onCol={(cc) => setPos({ col: cc, row: rowIx })} />
              <SceneCallouts items={slmCallouts(sel, row, col, lang, width, height)} placement="header" />
            </div>
          )
        }
      </Stage>
      </StageBox>
      <div className="dh-slm-controls" data-caos-plot-control="">
        <ChipGroup
          id="slm-device"
          label={{ en: 'SLM in section', es: 'SLM en sección' }}
          value={row.deviceOn ? 'case' : 'ideal'}
          onChange={(v) => act.setDevice(v === 'case' ? 'case' : 'ideal')}
          options={[
            { id: 'ideal', label: { en: 'Ideal', es: 'Ideal' }, hint: { en: 'A perfect SLM: any phase, no gap, no crosstalk.', es: 'Un SLM perfecto: cualquier fase, sin hueco, sin diafonía.' } },
            { id: 'case', label: { en: 'Case device', es: 'Dispositivo del caso' }, disabled: sw.disabled, hint: sw.reason ?? { en: 'Quantization, response, fill factor and crosstalk of this case.', es: 'Cuantización, respuesta, factor de llenado y diafonía de este caso.' } },
          ]}
        />
        <label>
          {t('Pixel column', 'Columna de píxeles')} <strong>{col}</strong>
          <input type="range" min={0} max={Math.max(0, n - 1)} step={1} value={col} aria-label={t('Scrub the pixel column along the row', 'Mover la columna de píxeles a lo largo de la fila')} onChange={(e) => setPos({ col: Number(e.target.value), row: rowIx })} />
        </label>
        <label>
          {t('Row', 'Fila')} <strong>{rowIx}</strong>
          <input type="range" min={0} max={Math.max(0, n - 1)} step={1} value={rowIx} aria-label={t('Choose the pixel row of the mask', 'Elegir la fila de píxeles de la máscara')} onChange={(e) => setPos({ col, row: Number(e.target.value) })} />
        </label>
        {sw.reason && <span className="caos-plot-note">{sw.reason[lang]}</span>}
      </div>
    </PlotCard>
  );
}
