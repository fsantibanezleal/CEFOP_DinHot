// The guided story (ADR-0082 rules 3 to 5): five steps over the App's own state, one measured finding per step. Every headline number is
// computed here from the loaded artifact (case-manifest, trace, benchmark-results), never typed; a number the artifact does not hold is
// stated as missing on the step. The views are the App's (V1, V2, V4, V5) composed in the shell's story frame; the exit lands on /app with
// the step's case, the group and the method. Routes: /story/setup, /story/device, /story/method, /story/compare, /story/hold.
import { ChipGroup, PlotCard, Stage, StoryFrame, formatNumber, pick, useLinkedCursor, useLinkedItem, useLinkedView, useShellLang, type BiText, type SceneCalloutDef, type StoryStep } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { loadBenchmark, loadCase, loadIndex, useArtifact, type CaseData, type Loaded } from '../api/artifacts';
import type { BenchmarkResults } from '../lib/contract.types';
import { caseAbsent } from '../readiness/readiness';
import { ReadinessNote } from '../readiness/ReadinessNote';
import { useReadiness } from '../readiness/useReadiness';
import { INTENSITY_LUT } from '../workbench/colormaps';
import { ParticleView } from '../workbench/DynamicsGroup';
import { Heatmap, type HeatMark } from '../workbench/HeatmapStage';
import { MethodAtWorkView, freezeIteration, pointAt, spreadText, useFocalAtIteration } from '../workbench/MethodAtWork';
import { methodName, replayMaps, replayResult, trapsOf, type DeviceChoice, type Selection } from '../workbench/model';
import { BAND_GAP, CalloutHeader, anchorInDrawing, useCalloutBand } from '../workbench/CalloutHeader';
import { OpticalTrainView } from '../workbench/OpticalTrain';
import { paramsFor } from '../workbench/run';
import { SlmSectionView } from '../workbench/SlmSection';
import { umToPixel } from '../workbench/traps';
import { trapToLinked } from '../workbench/trapLink';
import { ActionsContext, CASE_ROWS, type Actions } from '../workbench/ui';
import { coeffArray } from '../workbench/zernike';
import '../workbench/workbench.css';
import './story.css';
import { ID } from '../lib/methodIds';

type Lang = 'en' | 'es';
const bi = (en: string, es: string) => ({ en, es });
const num = (v: number, lang: Lang, d: number) => formatNumber(v, lang, { decimals: d });
/** The words of a headline, counted the way a reader counts them (the brief caps a headline at twelve). */
export const wordCount = (text: string): number => text.trim().split(/\s+/).filter(Boolean).length;
/** A name of a method in the page language: the catalog name, never the engine id alone. */
const nameOf = (id: string, lang: Lang): string => methodName(id)[lang];
/** A method's name where room is short (a point label, a headline): the device-aware WGS drops its "model of the device" tail. */
const short = (id: string, l: Lang): string => (id === ID.B1 ? (l === 'en' ? 'Device-aware WGS' : 'WGS con dispositivo') : nameOf(id, l));
/** What a fact reads, in words: the quantity of the trace and the method it belongs to, never the artifact path. */
const traceSource = (id: string, what: Tx): Tx => both((l) => `${what[l]}, ${nameOf(id, l)}`);
type Tx = { en: string; es: string };
const both = (make: (lang: Lang) => string): Tx => ({ en: make('en'), es: make('es') });

export type StepId = 'setup' | 'device' | 'method' | 'compare' | 'hold';
export interface StepDef {
  id: StepId;
  /** The case whose artifact the step reads; the compare step reads the benchmark and exits on the default case. */
  caseId: string;
  group: 'hologram' | 'convergence' | 'dynamics';
  /** The sub-view of the group the exit opens (the id the App's group gives it): the step's own view, never the group's first. */
  tab: string;
  /** The method the exit loads when the step names one (the device step is about the phase-fixed weighted GS); null leaves the case's reference method. */
  method: string | null;
  accent: 1 | 2 | 3 | 4 | 5;
  verb: BiText;
}

/** The five steps, in order, with the case each one reads (SDD, Visualization catalog). The case ids are the case-manifest ids. */
export const STEP_DEFS: readonly StepDef[] = [
  { id: 'setup', caseId: 'C02_grid_feedback', group: 'hologram', tab: 'train', method: null, accent: 1, verb: bi('Split the beam', 'Dividir el haz') },
  { id: 'device', caseId: 'C08_device_limited', group: 'hologram', tab: 'device', method: ID.M07, accent: 2, verb: bi('Meet the device', 'Conocer el dispositivo') },
  { id: 'method', caseId: 'C02_grid_feedback', group: 'convergence', tab: 'method', method: null, accent: 3, verb: bi('Watch it converge', 'Ver la convergencia') },
  { id: 'compare', caseId: 'C02_grid_feedback', group: 'convergence', tab: 'pareto', method: ID.M06, accent: 4, verb: bi('Compare the methods', 'Comparar los métodos') },
  { id: 'hold', caseId: 'C01_square_grid', group: 'dynamics', tab: 'particle', method: null, accent: 5, verb: bi('Hold a bead', 'Sujetar una microesfera') },
];
export const stepDef = (id: string): StepDef => STEP_DEFS.find((s) => s.id === id) ?? STEP_DEFS[0];

/** The device step's method: the weighted GS with fixed phase (M07) optimizes against the ideal model, so its own history is the ideal-device value and its final is the case device's. */
export const DEVICE_STEP_METHOD = ID.M07;
/** The cell of the benchmark the compare step names: 100 random traps on the modelled device (where the device-aware method is meant to work), 100 iterations, default parameters. */
export const COMPARE_CELL = { geometry: 'G3', device: 'device', budget: 100 } as const;
export const WEIGHTED_GS = ID.M06;
/** The second comparator on the cell: the weighted GS with fixed phase, the device step's method. */
export const PHASE_FIXED_GS = DEVICE_STEP_METHOD;

/** The device of a benchmark cell, named from the cell: `ideal` is the ideal SLM; any other is the modelled device of the benchmark protocol (short form for a subline). */
export function cellDevice(device: string, lang: Lang, short = false): string {
  if (device === 'ideal') return lang === 'es' ? 'SLM ideal' : 'ideal SLM';
  if (short) return lang === 'es' ? 'SLM modelado' : 'modelled SLM';
  return lang === 'es' ? 'el SLM modelado (fase de 4 bits, diafonía, factor de llenado)' : 'the modelled SLM (4-bit phase, crosstalk, fill factor)';
}
/** A method name inside a sentence: its first letter in lower case unless the name opens with an acronym ("WGS ...", "GS ..."). */
export const inSentence = (name: string): string => (/^[A-Z]{2,}/.test(name) ? name : name.charAt(0).toLowerCase() + name.slice(1));

export interface Finding {
  headline: Tx;
  summary: Tx;
  /** Lines of the panel: label, value, source field. */
  facts: { label: Tx; value: Tx; source: Tx }[];
}
/** A number the artifact does not hold, or one whose case has not loaded yet (`loading`: the headline says so instead of claiming it is missing). */
export type Missing = { missing: Tx; loading?: true };
const absent = (what: string, es: string): Missing => ({ missing: bi(`${what} is not in the artifact, so this number is not shown.`, `${es} no está en el artefacto, así que esta cifra no se muestra.`) });

export function setupFinding(data: CaseData): (Finding & { n: number; eff: number; method: string }) | Missing {
  const ref = data.manifest.params.reference_method;
  const final = data.trace.methods[ref]?.final;
  const n = data.trace.traps.length;
  if (!final || !n) return absent(`The efficiency of ${methodName(ref).en} or the trap count of ${data.manifest.case_id}`, `La eficiencia de ${methodName(ref).es} o el número de trampas de ${data.manifest.case_id}`);
  const eff = final.efficiency;
  return {
    n,
    eff,
    method: ref,
    headline: both((l) => (l === 'en' ? `One beam becomes ${n} traps at ${num(eff * 100, l, 1)}% efficiency` : `Un haz se convierte en ${n} trampas con ${num(eff * 100, l, 1)}% de eficiencia`)),
    summary: both((l) => (l === 'en' ? `${nameOf(ref, l)} shapes the beam on the SLM; the rest of the light is the zero order and ghosts.` : `${nameOf(ref, l)} da forma al haz en el SLM; el resto de la luz es el orden cero y los fantasmas.`)),
    facts: [
      { label: bi('Traps', 'Trampas'), value: bi(String(n), String(n)), source: bi('trace: the traps of the case', 'traza: las trampas del caso') },
      { label: bi('Efficiency', 'Eficiencia'), value: both((l) => `${num(eff * 100, l, 1)} %`), source: traceSource(ref, bi('trace: final efficiency', 'traza: eficiencia final')) },
      { label: bi('Uniformity', 'Uniformidad'), value: both((l) => num(final.uniformity, l, 3)), source: traceSource(ref, bi('trace: final uniformity', 'traza: uniformidad final')) },
    ],
  };
}

export function deviceFinding(data: CaseData): (Finding & { ideal: { spread: number; eff: number }; device: { spread: number; eff: number } }) | Missing {
  const m = data.trace.methods[DEVICE_STEP_METHOD];
  const dev = data.manifest.params.device;
  const last = m?.history[m.history.length - 1];
  if (!m || !last || !dev) return absent(`The device block or the ${methodName(DEVICE_STEP_METHOD).en} history of ${data.manifest.case_id}`, `El bloque del dispositivo o el historial de ${methodName(DEVICE_STEP_METHOD).es} de ${data.manifest.case_id}`);
  const ideal = { spread: last.rel_std_pct, eff: last.efficiency };
  const device = { spread: m.final.rel_std_pct, eff: m.final.efficiency };
  const ref = data.manifest.params.reference_method;
  const refFinal = data.trace.methods[ref]?.final;
  const id = DEVICE_STEP_METHOD;
  const bits = dev.bit_depth;
  return {
    ideal,
    device,
    headline: both((l) => (l === 'en' ? `On the device, ${inSentence(nameOf(id, l))} spread rises from ${spreadText(ideal.spread, l)}% to ${spreadText(device.spread, l)}%` : `Dispersión del ${nameOf(id, l)}: de ${spreadText(ideal.spread, l)}% a ${spreadText(device.spread, l)}%`)),
    summary: both((l) =>
      l === 'en'
        ? `${bits === null ? 'Unquantized' : `${bits}-bit`} phase, crosstalk and a fill factor of ${num(dev.fill_factor, l, 2)} cost ${num((ideal.eff - device.eff) * 100, l, 1)} points of efficiency${refFinal ? `; ${nameOf(ref, l)}, which models the device, holds ${spreadText(refFinal.rel_std_pct, l)}%` : ''}.`
        : `${bits === null ? 'La fase sin cuantizar' : `La fase de ${bits} bits`}, la diafonía y un factor de llenado de ${num(dev.fill_factor, l, 2)} cuestan ${num((ideal.eff - device.eff) * 100, l, 1)} puntos de eficiencia${refFinal ? `; ${nameOf(ref, l)}, que modela el dispositivo, mantiene ${spreadText(refFinal.rel_std_pct, l)}%` : ''}.`,
    ),
    facts: [
      { label: both((l) => (l === 'en' ? `${nameOf(id, l)}: spread, ideal model` : `${nameOf(id, l)}: dispersión, modelo ideal`)), value: both((l) => `${spreadText(ideal.spread, l)} %`), source: traceSource(id, bi('trace: spread at the last iteration, ideal model', 'traza: dispersión en la última iteración, modelo ideal')) },
      { label: both((l) => (l === 'en' ? `${nameOf(id, l)}: spread, case device` : `${nameOf(id, l)}: dispersión, dispositivo del caso`)), value: both((l) => `${spreadText(device.spread, l)} %`), source: traceSource(id, bi('trace: final spread on the case device', 'traza: dispersión final con el dispositivo del caso')) },
      { label: bi('Efficiency cost', 'Costo en eficiencia'), value: both((l) => `${num((ideal.eff - device.eff) * 100, l, 1)} ${l === 'en' ? 'points' : 'puntos'}`), source: traceSource(id, bi('trace: efficiency, ideal model against case device', 'traza: eficiencia, modelo ideal frente al dispositivo del caso')) },
      { label: bi('Phase levels', 'Niveles de fase'), value: bits === null ? bi('not quantized', 'sin cuantizar') : bi(`${2 ** bits}`, `${2 ** bits}`), source: bi('case device: bit depth', 'dispositivo del caso: profundidad de bits') },
    ],
  };
}

export function methodFinding(data: CaseData): (Finding & { first: number; last: number; iterations: number; freeze: number | null; method: string }) | Missing {
  const ref = data.manifest.params.reference_method;
  const h = data.trace.methods[ref]?.history ?? [];
  if (h.length < 2) return absent(`The iteration history of ${methodName(ref).en} on ${data.manifest.case_id}`, `El historial de iteraciones de ${methodName(ref).es} en ${data.manifest.case_id}`);
  const first = h[0].rel_std_pct;
  const last = h[h.length - 1].rel_std_pct;
  const iterations = h[h.length - 1].iteration;
  const freeze = freezeIteration(ref);
  return {
    first,
    last,
    iterations,
    freeze,
    method: ref,
    headline: both((l) => (l === 'en' ? `The spread falls from ${spreadText(first, l)}% to ${spreadText(last, l)}% in ${iterations} iterations` : `La dispersión cae de ${spreadText(first, l)}% a ${spreadText(last, l)}% en ${iterations} iteraciones`)),
    summary: both((l) =>
      l === 'en'
        ? `${nameOf(ref, l)} on ${data.trace.traps.length} traps${freeze === null ? '' : `, with the phase frozen at iteration ${freeze}`}; scrub the iteration to redraw the focal plane.`
        : `${nameOf(ref, l)} en ${data.trace.traps.length} trampas${freeze === null ? '' : `, con la fase fijada en la iteración ${freeze}`}; recorra la iteración para redibujar el plano focal.`,
    ),
    facts: [
      { label: bi('Spread, first iteration', 'Dispersión, primera iteración'), value: both((l) => `${spreadText(first, l)} %`), source: traceSource(ref, bi('trace: spread at the first iteration', 'traza: dispersión en la primera iteración')) },
      { label: bi('Spread, last iteration', 'Dispersión, última iteración'), value: both((l) => `${spreadText(last, l)} %`), source: traceSource(ref, bi('trace: spread at the last iteration', 'traza: dispersión en la última iteración')) },
      { label: bi('Iterations', 'Iteraciones'), value: bi(String(iterations), String(iterations)), source: traceSource(ref, bi('trace: iterations run', 'traza: iteraciones ejecutadas')) },
    ],
  };
}

type Row = BenchmarkResults['rows'][number];
export interface ComparePoint {
  method: string;
  seeds: number;
  eff: Row['efficiency'];
  spread: Row['rel_std_pct'];
  onFront: boolean;
}
export interface CompareCell {
  geometry: string;
  device: string;
  budget: number;
}

/** One point per method on a cell: the default-parameter row of the benchmark. The tuned rows answer another question and are left out. */
export function comparePoints(bench: BenchmarkResults, cell: CompareCell): ComparePoint[] {
  const rows = bench.rows.filter((r) => r.geometry === cell.geometry && r.device === cell.device && r.budget_kind === 'iterations' && r.budget === cell.budget && r.params === 'default');
  const pts = rows.map((r) => ({ method: r.method, seeds: r.n_seeds, eff: r.efficiency, spread: r.rel_std_pct, onFront: false }));
  for (const p of pts) p.onFront = !pts.some((q) => q !== p && q.spread.median <= p.spread.median && q.eff.median >= p.eff.median && (q.spread.median < p.spread.median || q.eff.median > p.eff.median));
  return pts.sort((a, b) => a.spread.median - b.spread.median || b.eff.median - a.eff.median);
}

export function compareFinding(bench: BenchmarkResults, at: CompareCell = COMPARE_CELL): (Finding & { best: ComparePoint; gs: ComparePoint; fixed: ComparePoint; cell: CompareCell }) | Missing {
  const cell: CompareCell = { ...at };
  const pts = comparePoints(bench, cell);
  const gs = pts.find((p) => p.method === WEIGHTED_GS);
  const fixed = pts.find((p) => p.method === PHASE_FIXED_GS);
  const best = pts[0];
  const geo = bench.geometries.find((g) => g.id === cell.geometry);
  if (!best || !gs || !fixed || !geo) return absent(`The cell ${cell.geometry} on ${cellDevice(cell.device, 'en')} at ${cell.budget} iterations, or the weighted GS or phase-fixed weighted GS row on it,`, `La celda ${cell.geometry} en ${cellDevice(cell.device, 'es')} a ${cell.budget} iteraciones, o la fila del GS ponderado o del GS ponderado de fase fija en ella,`);
  const src = (p: ComparePoint): Tx => both((l) => (l === 'en' ? `benchmark: median over the seeds of ${nameOf(p.method, l)} on ${cell.geometry}, ${cellDevice(cell.device, l, true)}, ${cell.budget} iterations` : `benchmark: mediana sobre las semillas de ${nameOf(p.method, l)} en ${cell.geometry}, ${cellDevice(cell.device, l, true)}, ${cell.budget} iteraciones`));
  return {
    best,
    gs,
    fixed,
    cell,
    headline: both((l) => (l === 'en' ? `${short(best.method, l)}: ${spreadText(best.spread.median, l)}% spread against ${spreadText(gs.spread.median, l)}% for ${nameOf(gs.method, l)}` : `${short(best.method, l)}: dispersión ${spreadText(best.spread.median, l)}% frente a ${spreadText(gs.spread.median, l)}% del ${nameOf(gs.method, l)}`)),
    summary: both((l) =>
      l === 'en'
        ? `${geo.name.en}, ${cell.budget} iterations, ${cellDevice(cell.device, l, true)}: ${best.seeds}, ${gs.seeds} and ${fixed.seeds} seeds; ${nameOf(fixed.method, l)} ${spreadText(fixed.spread.median, l)}%.`
        : `${geo.name.es}, ${cell.budget} iteraciones, ${cellDevice(cell.device, l, true)}: ${best.seeds}, ${gs.seeds} y ${fixed.seeds} semillas; ${nameOf(fixed.method, l)} ${spreadText(fixed.spread.median, l)}%.`,
    ),
    facts: [
      { label: both((l) => (l === 'en' ? `${nameOf(best.method, l)}, median spread` : `${nameOf(best.method, l)}, dispersión mediana`)), value: both((l) => `${spreadText(best.spread.median, l)} %`), source: src(best) },
      { label: both((l) => (l === 'en' ? `${nameOf(gs.method, l)}, median spread` : `${nameOf(gs.method, l)}, dispersión mediana`)), value: both((l) => `${spreadText(gs.spread.median, l)} %`), source: src(gs) },
      { label: both((l) => (l === 'en' ? `${nameOf(fixed.method, l)}, median spread` : `${nameOf(fixed.method, l)}, dispersión mediana`)), value: both((l) => `${spreadText(fixed.spread.median, l)} %`), source: src(fixed) },
      { label: bi('Seeds', 'Semillas'), value: bi(`${best.seeds}, ${gs.seeds} and ${fixed.seeds}`, `${best.seeds}, ${gs.seeds} y ${fixed.seeds}`), source: both((l) => (l === 'en' ? `benchmark: seeds of each of the three cells (${cell.geometry}, ${cellDevice(cell.device, l, true)}, ${cell.budget} iterations)` : `benchmark: semillas de cada una de las tres celdas (${cell.geometry}, ${cellDevice(cell.device, l, true)}, ${cell.budget} iteraciones)`)) },
    ],
  };
}

export function holdFinding(data: CaseData): (Finding & { kappa: number; fc: number; method: string }) | Missing {
  const dyn = data.trace.dynamics;
  const ref = data.manifest.params.reference_method;
  const kappa = dyn?.kappa_pn_per_um;
  const fc = dyn?.fc_hz;
  if (!dyn || kappa === undefined || fc === undefined) return absent(`The stiffness and the corner frequency of ${data.manifest.case_id}`, `La rigidez y la frecuencia de corte de ${data.manifest.case_id}`);
  return {
    kappa,
    fc,
    method: ref,
    headline: both((l) => (l === 'en' ? `The bead feels ${num(kappa, l, 2)} pN/µm at a ${num(fc, l, 1)} Hz corner frequency` : `La microesfera siente ${num(kappa, l, 2)} pN/µm con frecuencia de corte de ${num(fc, l, 1)} Hz`)),
    summary: both((l) =>
      l === 'en'
        ? `A simulated bead in a trap of the ${nameOf(ref, l)} hologram; the stiffness is read from the power spectrum of its position.`
        : `Una microesfera simulada en una trampa del holograma de ${nameOf(ref, l)}; la rigidez se lee del espectro de potencia de su posición.`,
    ),
    facts: [
      { label: bi('Trap stiffness', 'Rigidez de la trampa'), value: both((l) => `${num(kappa, l, 2)} pN/µm`), source: bi('trace: stiffness of the simulated trap', 'traza: rigidez de la trampa simulada') },
      { label: bi('Corner frequency', 'Frecuencia de corte'), value: both((l) => `${num(fc, l, 1)} Hz`), source: bi('trace: corner frequency of the position spectrum', 'traza: frecuencia de corte del espectro de la posición') },
      { label: bi('Trap depth', 'Profundidad de la trampa'), value: both((l) => `${num(dyn.depth.value, l, 0)} ${dyn.depth.unit}`), source: bi('trace: depth of the simulated trap', 'traza: profundidad de la trampa simulada') },
    ],
  };
}

/** The stage height a phone gives a step: the step's own floor, or the band the callout cards measured plus the 490 px of drawing that fit before, whichever is taller, never above the shell's 900. */
export function storyStageFloor(base: number, band: number): number {
  return Math.min(900, Math.max(base, Math.round(band + 490)));
}

/** The band the callout cards of the story stage measured (the shell sets `--caos-callout-band` on its layer), followed as the cards re-lay out. 0 until measured. */
function useStoryBand(stepId: string): number {
  const [band, setBand] = useState(0);
  useEffect(() => {
    const root = document.querySelector('.dh-story');
    if (!root) return;
    const read = () => {
      const layer = root.querySelector<HTMLElement>('[data-caos-callout-layer]');
      const v = layer ? Number.parseFloat(layer.style.getPropertyValue('--caos-callout-band')) : 0;
      setBand(Number.isFinite(v) && v > 0 ? Math.round(v) : 0);
    };
    read();
    const watch = new MutationObserver(read);
    watch.observe(root, { subtree: true, childList: true, attributes: true, attributeFilter: ['style'] });
    return () => watch.disconnect();
  }, [stepId]);
  return band;
}

/** The App link of a step: its case, its group and sub-view of the views, and the method (the App reads `case`, `view`, `tab` and `method` on load). */
export function exitHref(step: StepDef, method: string | null): string {
  const q = new URLSearchParams({ case: step.caseId, view: step.group, tab: step.tab });
  if (method) q.set('method', method);
  return `/app?${q.toString()}`;
}

/** A Selection on the replay lane, as the App builds it before the engine answers; the story's views read it as the App's do. */
export function storySelection(data: CaseData, device: DeviceChoice | null = null, trapId: number | null = null): Selection {
  const p = data.manifest.params;
  const traps = trapsOf(data.manifest, data.trace);
  const dev: DeviceChoice = device ?? (p.device ? 'case' : 'ideal');
  return {
    data,
    methodId: p.reference_method,
    device: dev,
    deviceModel: dev === 'case' ? p.device : null,
    traps,
    edited: false,
    trapId: trapId ?? p.dynamics?.trap_id ?? traps[0]?.id ?? null,
    region: null,
    maps: replayMaps(data.trace),
    result: replayResult(data.trace, p.reference_method),
    iteration: p.budget.iterations,
    dbFloor: -40,
    aberration: coeffArray(p.aberration?.noll),
    aberrationEdited: false,
    powerMw: p.dynamics?.power_mw ?? 0,
    seed: data.manifest.seed,
    stage: 'ideal',
    sortBy: 'id',
    bandPct: 5,
    fbStep: data.trace.feedback?.steps[0]?.step ?? 0,
    zmode: 4,
    corrected: false,
    coeffKey: '',
    plane: 'xz',
    volThreshold: 0.2,
    slot: null,
    running: false,
    progress: null,
    liveError: null,
    cancelled: false,
    runParams: paramsFor(data, { device: dev, iterations: p.budget.iterations, traps, edited: false, aberration: null, aberrationEdited: false }),
    engineAvailable: false,
    liveMethods: [],
  };
}

// ---- the comparison view (V6) -----------------------------------------------------------------------------------------------------

/** The half length, in px, of the end caps of a point's quartile range: a range narrower than the caps is still drawn, as caps. */
const CAP = 4;
const SPREAD_FLOOR = 0.001;
const SPREAD_CEIL = 300;
export interface CompareLayout {
  plot: { x: number; y: number; w: number; h: number };
  x: (eff: number) => number;
  y: (spread: number) => number;
  yTicks: number[];
  xTicks: number[];
}
/** The geometry of the scatter: efficiency across (0 to 1), the relative spread up on a log scale from SPREAD_FLOOR (a median of zero sits on the floor). */
export function compareLayout(width: number, height: number, band?: number): CompareLayout {
  const left = 58;
  const right = 14;
  const bottom = 46;
  // the plot starts under the band the callout cards measured; until they are measured, under a nominal one
  const top = band !== undefined ? band : Math.min(width < 640 ? 190 : 96, height * 0.45);
  const plot = { x: left, y: top, w: Math.max(60, width - left - right), h: Math.max(60, height - top - bottom) };
  const lo = Math.log10(SPREAD_FLOOR);
  const hi = Math.log10(SPREAD_CEIL);
  return {
    plot,
    x: (eff) => plot.x + Math.max(0, Math.min(1, eff)) * plot.w,
    y: (spread) => plot.y + plot.h * (1 - (Math.log10(Math.max(spread, SPREAD_FLOOR)) - lo) / (hi - lo)),
    yTicks: [0.001, 0.01, 0.1, 1, 10, 100],
    xTicks: [0.25, 0.5, 0.75, 1],
  };
}

/** The x of each dot, moved aside in steps of one dot (right, left, two right, ...) until it touches no earlier dot and stays inside the plot (two methods may share a median; each stays reachable). */
export function nudgeDots(pts: readonly ComparePoint[], L: CompareLayout, r = 12): number[] {
  const placed: { x: number; y: number }[] = [];
  const lo = L.plot.x;
  const hi = L.plot.x + L.plot.w;
  return pts.map((p) => {
    const x0 = L.x(p.eff.median);
    const y = L.y(p.spread.median);
    let x = x0;
    for (let k = 0; k <= 2 * Math.ceil((hi - lo) / r); k++) {
      const c = x0 + (k % 2 === 1 ? 1 : -1) * Math.ceil(k / 2) * r;
      if (c < lo || c > hi) continue;
      if (!placed.some((q) => Math.hypot(q.x - c, q.y - y) < r)) {
        x = c;
        break;
      }
    }
    placed.push({ x, y });
    return x;
  });
}

/** Where a method's dot is drawn, in px of the stage (the dots are moved aside when they touch, so the callouts point at the dot, not at its median). */
export type DotAt = Readonly<Record<string, { x: number; y: number }>>;

export function compareCallouts(f: { best: ComparePoint; gs: ComparePoint; cell: CompareCell }, lang: Lang, L: CompareLayout, width: number, height: number, dots?: DotAt): SceneCalloutDef[] {
  const px = (p: ComparePoint) => dots?.[p.method] ?? { x: L.x(p.eff.median), y: L.y(p.spread.median) };
  const norm = (x: number, y: number) => ({ x: Math.min(0.98, Math.max(0.02, x / width)), y: Math.min(0.98, Math.max(0.02, y / height)) });
  const at = (p: ComparePoint) => norm(px(p).x, px(p).y);
  const a = px(f.best);
  const b = px(f.gs);
  return [
    { id: 'best', eyebrow: { en: 'LOWEST SPREAD', es: 'MENOR DISPERSIÓN' }, value: spreadText(f.best.spread.median, lang), unit: '%', state: 'normal', anchor: at(f.best), source: { en: `${nameOf(f.best.method, 'en')}: benchmark median over its seeds`, es: `${nameOf(f.best.method, 'es')}: mediana del benchmark sobre sus semillas` } },
    { id: 'gs', eyebrow: { en: 'WEIGHTED GS', es: 'GS PONDERADO' }, value: spreadText(f.gs.spread.median, lang), unit: '%', state: 'warning', anchor: at(f.gs), source: { en: `${nameOf(f.gs.method, 'en')}: benchmark median over its seeds`, es: `${nameOf(f.gs.method, 'es')}: mediana del benchmark sobre sus semillas` } },
    // the seeds card points at the middle of the line the plot draws between the two compared points
    { id: 'seeds', eyebrow: { en: 'SEEDS', es: 'SEMILLAS' }, value: `${f.best.seeds}/${f.gs.seeds}`, unit: { en: 'seeds', es: 'semillas' }, state: 'selected', anchor: norm((a.x + b.x) / 2, (a.y + b.y) / 2), source: { en: 'benchmark: seeds of the two cells compared', es: 'benchmark: semillas de las dos celdas comparadas' } },
  ];
}

function CompareView({ bench, cell, finding }: { bench: BenchmarkResults; cell: CompareCell; finding: ReturnType<typeof compareFinding> }) {
  const lang = useShellLang() as Lang;
  const selected = useLinkedView((s) => s.selectedId);
  const select = useLinkedView((s) => s.select);
  const pts = useMemo(() => comparePoints(bench, cell), [bench, cell]);
  const cb = useCalloutBand(0);
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const geo = bench.geometries.find((g) => g.id === cell.geometry);
  const front = pts.filter((p) => p.onFront).sort((a, b) => a.eff.median - b.eff.median);
  return (
    <PlotCard fill title={{ en: 'Spread against efficiency, by method', es: 'Dispersión contra eficiencia, por método' }} lane="replay" provenance="synthetic" note={{ en: `${geo?.name.en ?? cell.geometry}, ${cell.budget} iterations, ${cellDevice(cell.device, 'en')}, default parameters. Each point is a method's median over its seeds with the quartile range drawn (a range narrower than a few pixels is drawn with its end caps and its numbers are printed beside the two compared points); the line joins the methods no other beats on both axes. A median of zero sits on the floor of the axis.`, es: `${geo?.name.es ?? cell.geometry}, ${cell.budget} iteraciones, ${cellDevice(cell.device, 'es')}, parámetros por defecto. Cada punto es la mediana de un método sobre sus semillas con el rango intercuartil dibujado (un rango más estrecho que unos pocos píxeles se dibuja con sus remates y sus cifras se imprimen junto a los dos puntos comparados); la línea une los métodos que ningún otro supera en ambos ejes. Una mediana de cero queda en el piso del eje.` }}>
      <ReadinessNote ids={['benchmark-results']} />
      <div className="dh-cmp" data-caos-flow="" data-compare-cell={`${cell.geometry}|${cell.device}|${cell.budget}`}>
        <div className="dh-cmp-stage">
        <Stage label={{ en: 'Median spread against median efficiency of each method, with the quartile ranges and the Pareto front', es: 'Dispersión mediana contra eficiencia mediana de cada método, con los rangos intercuartiles y el frente de Pareto' }}>
          {({ width, height }) => {
            if (width < 120 || height < 120) return null;
            const L = compareLayout(width, height, cb.band > 0 ? cb.band + BAND_GAP : undefined);
            const nudged = nudgeDots(pts, L);
            const dots: Record<string, { x: number; y: number }> = {};
            pts.forEach((p, i) => (dots[p.method] = { x: nudged[i], y: L.y(p.spread.median) }));
            const compared = !('missing' in finding) ? [finding.best.method, finding.gs.method] : [];
            const cmpA = compared.length ? dots[compared[0]] : null;
            const cmpB = compared.length ? dots[compared[1]] : null;
            return (
              <div className="dh-scene">
                <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="group" aria-label={t('Methods on the spread and efficiency axes', 'Métodos en los ejes de dispersión y eficiencia')} className="dh-cmp-svg">
                  {L.yTicks.map((v) => (
                    <g key={`y${v}`}>
                      <line x1={L.plot.x} x2={L.plot.x + L.plot.w} y1={L.y(v)} y2={L.y(v)} stroke="var(--color-border)" strokeWidth={1} />
                      <text x={L.plot.x - 6} y={L.y(v) + 4} textAnchor="end" fontSize={11} fill="var(--color-fg-subtle)">{formatNumber(v, lang, { decimals: v < 1 ? 3 : 0 })}</text>
                    </g>
                  ))}
                  {L.xTicks.map((v) => (
                    <g key={`x${v}`}>
                      <line y1={L.plot.y} y2={L.plot.y + L.plot.h} x1={L.x(v)} x2={L.x(v)} stroke="var(--color-border)" strokeWidth={1} />
                      <text x={L.x(v)} y={L.plot.y + L.plot.h + 16} textAnchor="middle" fontSize={11} fill="var(--color-fg-subtle)">{formatNumber(v, lang, { decimals: 2 })}</text>
                    </g>
                  ))}
                  <text x={L.plot.x + L.plot.w / 2} y={height - 6} textAnchor="middle" fontSize={12} fill="var(--color-fg)">{t('Efficiency (fraction of the light in the traps)', 'Eficiencia (fracción de la luz en las trampas)')}</text>
                  <text transform={`translate(14 ${L.plot.y + L.plot.h / 2}) rotate(-90)`} textAnchor="middle" fontSize={12} fill="var(--color-fg)">{t('Relative spread (%, log)', 'Dispersión relativa (%, log)')}</text>
                  {cmpA && cmpB && <line pointerEvents="none" x1={cmpA.x} y1={cmpA.y} x2={cmpB.x} y2={cmpB.y} stroke="var(--color-accent)" strokeWidth={1.5} strokeDasharray="2 3" data-compared="" />}
                  {front.length > 1 && <polyline pointerEvents="none" points={front.map((p) => `${L.x(p.eff.median)},${L.y(p.spread.median)}`).join(' ')} fill="none" stroke="var(--color-good)" strokeWidth={2} strokeDasharray="5 4" />}
                  {pts.map((p, i) => {
                    const on = selected === p.method;
                    const cx = nudged[i];
                    const cy = L.y(p.spread.median);
                    const tone = p.method === WEIGHTED_GS ? 'var(--color-warn)' : p.onFront ? 'var(--color-good)' : 'var(--color-accent)';
                    const label = on || p.method === WEIGHTED_GS || p === pts[0];
                    return (
                      <g key={p.method}>
                        {/* the whiskers and the label are outside the button, so its box (and the pointer's hit) is the dot */}
                        <g aria-hidden="true" pointerEvents="none" data-interval={p.method}>
                          <line x1={Math.min(cx + (L.x(p.eff.q1) - L.x(p.eff.median)), cx - CAP)} x2={Math.max(cx + (L.x(p.eff.q3) - L.x(p.eff.median)), cx + CAP)} y1={cy} y2={cy} stroke={tone} strokeWidth={1.5} />
                          <line x1={Math.min(cx + (L.x(p.eff.q1) - L.x(p.eff.median)), cx - CAP)} x2={Math.min(cx + (L.x(p.eff.q1) - L.x(p.eff.median)), cx - CAP)} y1={cy - CAP} y2={cy + CAP} stroke={tone} strokeWidth={1.5} />
                          <line x1={Math.max(cx + (L.x(p.eff.q3) - L.x(p.eff.median)), cx + CAP)} x2={Math.max(cx + (L.x(p.eff.q3) - L.x(p.eff.median)), cx + CAP)} y1={cy - CAP} y2={cy + CAP} stroke={tone} strokeWidth={1.5} />
                          <line x1={cx} x2={cx} y1={Math.max(L.y(p.spread.q1), cy + CAP)} y2={Math.min(L.y(p.spread.q3), cy - CAP)} stroke={tone} strokeWidth={1.5} />
                          <line x1={cx - CAP} x2={cx + CAP} y1={Math.max(L.y(p.spread.q1), cy + CAP)} y2={Math.max(L.y(p.spread.q1), cy + CAP)} stroke={tone} strokeWidth={1.5} />
                          <line x1={cx - CAP} x2={cx + CAP} y1={Math.min(L.y(p.spread.q3), cy - CAP)} y2={Math.min(L.y(p.spread.q3), cy - CAP)} stroke={tone} strokeWidth={1.5} />
                          {label && <text x={cx + (cx > L.plot.x + L.plot.w * 0.6 ? -9 : 9)} y={cy - 7} textAnchor={cx > L.plot.x + L.plot.w * 0.6 ? 'end' : 'start'} fontSize={11} fill="var(--color-fg)">{short(p.method, lang)}</text>}
                          {compared.includes(p.method) && <text x={cx + (cx > L.plot.x + L.plot.w * 0.6 ? -9 : 9)} y={cy + 14} textAnchor={cx > L.plot.x + L.plot.w * 0.6 ? 'end' : 'start'} fontSize={10} fill="var(--color-fg-subtle)">{t('quartiles', 'cuartiles')} {spreadText(p.spread.q1, lang)} {t('to', 'a')} {spreadText(p.spread.q3, lang)} %</text>}
                        </g>
                        <g data-method={p.method} data-linked-id={p.method} data-linked-view="scene" data-linked-selected={on ? 'true' : 'false'} role="button" tabIndex={0} aria-pressed={on} aria-label={t(`${nameOf(p.method, 'en')}: median spread ${spreadText(p.spread.median, 'en')} %, efficiency ${num(p.eff.median, 'en', 3)}, ${p.seeds} seeds`, `${nameOf(p.method, 'es')}: dispersión mediana ${spreadText(p.spread.median, 'es')} %, eficiencia ${num(p.eff.median, 'es', 3)}, ${p.seeds} semillas`)} onClick={() => select(on ? null : p.method, 'scene')} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), select(on ? null : p.method, 'scene'))} style={{ cursor: 'pointer' }}>
                          <circle cx={cx} cy={cy} r={on ? 8 : 5.5} fill={tone} stroke={on ? 'var(--color-fg)' : 'var(--color-surface)'} strokeWidth={on ? 2 : 1} />
                        </g>
                      </g>
                    );
                  })}
                </svg>
                {'missing' in finding ? null : <CalloutHeader items={compareCallouts(finding, lang, L, width, height, dots)} onLayout={cb.onLayout} />}
              </div>
            );
          }}
        </Stage>
        </div>
        <ul className="dh-cmp-list" aria-label={t('The methods of the cell, by median spread', 'Los métodos de la celda, por dispersión mediana')}>
          {pts.slice(0, 8).map((p) => (
            <li key={p.method}>
              {nameOf(p.method, lang)}: {spreadText(p.spread.median, lang)} %, {num(p.eff.median * 100, lang, 1)} %, {p.seeds} {t('seeds', 'semillas')}
            </li>
          ))}
        </ul>
      </div>
    </PlotCard>
  );
}

// ---- the story ------------------------------------------------------------------------------------------------------------------------

export interface StoryLoaded {
  c02: Loaded<CaseData>;
  c08: Loaded<CaseData>;
  c01: Loaded<CaseData>;
  bench: Loaded<BenchmarkResults>;
}

function useStoryCase(caseId: string): Loaded<CaseData> {
  return useArtifact((s) => loadCase(caseId, s), [caseId]);
}

const reasonOf = (l: Loaded<unknown>): Tx | null => (l.state === 'unavailable' ? l.reason : l.state === 'error' ? { en: l.error, es: l.error } : null);

/** One trap of the panel's list: the same linked selection as the sites of the optical train (scene) and the dots of the map. */
function PanelTrap({ id }: { id: number }) {
  const item = useLinkedItem(String(id), 'panel');
  return (
    <button type="button" {...item}>
      {id}
    </button>
  );
}

/** The panel of the setup step (V3): the focal plane at the iteration the shared scrub names, the scrub itself and the trap list. */
function StoryFocal({ sel }: { sel: Selection }) {
  const lang = useShellLang() as Lang;
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const selectedId = useLinkedView((s) => s.selectedId);
  const select = useLinkedView((s) => s.select);
  const cursor = useLinkedView((s) => s.cursor);
  const scrub = useLinkedView((s) => s.scrub);
  const marker = useLinkedCursor().markerProps;
  const history = sel.result?.history ?? [];
  const point = history.length ? pointAt(history, cursor) : null;
  const focal = useFocalAtIteration(sel, cursor === null || !point ? null : point.iteration);
  const at = cursor !== null && (focal.state === 'ready' || (focal.state === 'loading' && focal.at)) ? focal.at : null;
  const map = at?.maps.focal ?? sel.maps?.focal ?? null;
  if (!map) return <p className="dh-story-missing">{t('The focal map is not in the artifact.', 'El mapa focal no está en el artefacto.')}</p>;
  const marks: HeatMark[] = sel.traps
    .filter((tr) => sel.traps.length <= 36 || trapToLinked(tr.id) === selectedId)
    .map((tr) => {
      const [col, row] = umToPixel(tr.x_um, tr.y_um, map.size, map.binUm);
      const on = trapToLinked(tr.id) === selectedId;
      return { id: tr.id, col, row, kind: 'ring', tone: on ? 'accent' : 'good', selected: on, label: on ? String(tr.id) : undefined };
    });
  const first = history[0]?.iteration ?? 1;
  const last = history[history.length - 1]?.iteration ?? 1;
  const trapI = at?.result.trapI ?? sel.result?.trapI ?? null;
  const chosen = selectedId === null ? -1 : sel.traps.findIndex((tr) => trapToLinked(tr.id) === selectedId);
  return (
    <>
      <div className="dh-story-focal" data-story-focal="" data-iteration={at ? at.k : ''} {...marker}>
        <Heatmap
          label={{ en: `Focal-plane intensity in dB after ${at ? at.k : 'the final'} iterations, with the trap sites`, es: `Intensidad del plano focal en dB tras ${at ? at.k : 'las'} iteraciones, con los sitios de trampas` }}
          data={map.db}
          cols={map.size}
          rows={map.size}
          lut={INTENSITY_LUT}
          range={[sel.dbFloor, 0]}
          marks={marks}
          onPick={(col, row) => {
            let best: number | null = null;
            let bd = 4;
            for (const tr of sel.traps) {
              const [tc, tr2] = umToPixel(tr.x_um, tr.y_um, map.size, map.binUm);
              const d = Math.hypot(tc - col, tr2 - row);
              if (d <= bd) {
                bd = d;
                best = tr.id;
              }
            }
            select(trapToLinked(best), 'panel');
          }}
          describe={(col, row, v) => `bin (${col}, ${row}): ${num(v, lang, 1)} dB`}
          summary={t(`Focal plane ${map.size} by ${map.size} with ${sel.traps.length} traps marked.`, `Plano focal de ${map.size} por ${map.size} con ${sel.traps.length} trampas marcadas.`)}
        />
      </div>
      {history.length > 0 && (
        <label className="dh-mw-scrub">
          {t('Iteration', 'Iteración')} <strong>{point?.iteration ?? last}</strong>
          <input type="range" min={first} max={last} step={1} value={point?.iteration ?? last} data-linked-cursor="" aria-label={t('Scrub the iteration of the method: the focal plane is redrawn', 'Recorrer la iteración del método: se redibuja el plano focal')} onChange={(e) => scrub(Number(e.target.value))} />
        </label>
      )}
      {point && (
        <p>
          {t('After', 'Tras')} <strong>{point.iteration}</strong> {t('iterations', 'iteraciones')}: {t('spread', 'dispersión')} <strong>{spreadText(point.relStdPct, lang)} %</strong>, {t('efficiency', 'eficiencia')} <strong>{num(point.efficiency * 100, lang, 1)} %</strong>
          {cursor !== null && focal.state === 'loading' ? ` (${t('computing the map', 'calculando el mapa')})` : ''}.
        </p>
      )}
      <div className="dh-story-picks" role="group" aria-label={t('Traps', 'Trampas')}>
        {sel.traps.slice(0, 8).map((tr) => (
          <PanelTrap key={tr.id} id={tr.id} />
        ))}
        {sel.traps.length > 8 && <span>{t(`of ${sel.traps.length}; pick the others on the drawing or the map`, `de ${sel.traps.length}; elija las otras en el dibujo o en el mapa`)}</span>}
      </div>
      {chosen >= 0 && trapI && (
        <p>
          {t('Trap', 'Trampa')} <strong>{sel.traps[chosen].id}</strong>: {num(trapI[chosen], lang, 3)} {t('of the mean intensity', 'de la intensidad media')}.
        </p>
      )}
    </>
  );
}

export function holdCallouts(f: { kappa: number; fc: number }, data: CaseData, lang: Lang, drawing?: { band: number; height: number }): SceneCalloutDef[] {
  const dyn = data.trace.dynamics!;
  const place = (a: { x: number; y: number }) => (drawing ? anchorInDrawing(a, drawing.band, drawing.height) : a);
  return [
    { id: 'kappa', eyebrow: { en: 'STIFFNESS', es: 'RIGIDEZ' }, value: num(f.kappa, lang, 2), unit: 'pN/µm', state: 'selected', anchor: place({ x: 0.5, y: 0.5 }), source: { en: 'trace: stiffness of the simulated trap', es: 'traza: rigidez de la trampa simulada' } },
    { id: 'fc', eyebrow: { en: 'CORNER FREQUENCY', es: 'FRECUENCIA DE CORTE' }, value: num(f.fc, lang, 1), unit: 'Hz', state: 'normal', anchor: place({ x: 0.5, y: 0.56 }), source: { en: 'trace: corner frequency of the position spectrum', es: 'traza: frecuencia de corte del espectro de la posición' } },
    { id: 'depth', eyebrow: { en: 'TRAP DEPTH', es: 'PROFUNDIDAD' }, value: num(dyn.depth.value, lang, 0), unit: dyn.depth.unit, state: 'normal', anchor: place({ x: 0.45, y: 0.5 }), source: { en: 'trace: depth of the simulated trap', es: 'traza: profundidad de la trampa simulada' } },
  ];
}

/** The hold step's stage: the callout cards over the drawing, the drawing under the band the cards measure, the anchors written on the drawing (anchorInDrawing). */
function HoldStage({ sel, finding, lang }: { sel: Selection; finding: { kappa: number; fc: number } | Missing; lang: Lang }) {
  const cb = useCalloutBand(0);
  const box = useRef<HTMLDivElement | null>(null);
  const [height, setHeight] = useState(0);
  useEffect(() => {
    const node = box.current;
    if (!node) return;
    const watch = new ResizeObserver((entries) => setHeight(entries[0]?.contentRect.height ?? 0));
    watch.observe(node);
    return () => watch.disconnect();
  }, []);
  const band = cb.band > 0 ? cb.band + BAND_GAP : null;
  const items = 'missing' in finding ? [] : holdCallouts(finding, sel.data, lang, band !== null && height > 0 ? { band, height } : undefined);
  return (
    <div className="dh-story-stage" ref={box}>
      {items.length > 0 && <CalloutHeader items={items} className="dh-story-callouts" onLayout={cb.onLayout} />}
      <div className="dh-story-drawing" style={band !== null ? ({ paddingTop: band } as CSSProperties) : undefined}>
        <div className="dh-story-card">
          <ParticleView sel={sel} />
        </div>
      </div>
    </div>
  );
}

function Facts({ finding, lang }: { finding: Finding; lang: Lang }) {
  return (
    <dl className="dh-story-facts">
      {finding.facts.map((x) => (
        <div key={pick(x.source, 'en')}>
          <dt>{pick(x.label, lang)}</dt>
          <dd>
            <strong>{pick(x.value, lang)}</strong> <small>{pick(x.source, lang)}</small>
          </dd>
        </div>
      ))}
    </dl>
  );
}

const MissingLine = ({ m, lang }: { m: Missing; lang: Lang }) => (
  <p className="dh-story-missing" role="status" data-missing="">
    {pick(m.missing, lang)}
  </p>
);

export interface StoryViewProps {
  stepId: StepId;
  loaded: StoryLoaded;
  lang: Lang;
  onStepChange: (id: string) => void;
  onExit: () => void;
  /** The method picked on the comparison, loaded into the App on exit. */
  method?: string | null;
  cell?: CompareCell;
  onCell?: (cell: CompareCell) => void;
  device?: DeviceChoice | null;
  onDevice?: (d: DeviceChoice) => void;
}

/** The story frame over the loaded artifacts. Pure of routing, so a test renders it; the page below wires the router and the loaders. */
export function StoryView({ stepId, loaded, lang, onStepChange, onExit, cell = COMPARE_CELL, onCell, device = null, onDevice }: StoryViewProps) {
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const selectedId = useLinkedView((s) => s.selectedId);
  const select = useLinkedView((s) => s.select);
  const active = stepDef(stepId);
  const caseData = (l: Loaded<CaseData>): CaseData | null => (l.state === 'ready' ? l.data : null);
  const c02 = caseData(loaded.c02);
  const c08 = caseData(loaded.c08);
  const c01 = caseData(loaded.c01);
  const bench = loaded.bench.state === 'ready' ? loaded.bench.data : null;
  const notLoaded = (what: string, es: string, l: Loaded<unknown>): Missing => {
    const reason = reasonOf(l);
    return reason ? { missing: reason } : { missing: bi(`${what} is loading.`, `${es} se está cargando.`), loading: true };
  };
  const setup = c02 ? setupFinding(c02) : notLoaded('The case C02', 'El caso C02', loaded.c02);
  const dev = c08 ? deviceFinding(c08) : notLoaded('The case C08', 'El caso C08', loaded.c08);
  const method = c02 ? methodFinding(c02) : notLoaded('The case C02', 'El caso C02', loaded.c02);
  const compare = bench ? compareFinding(bench, cell) : notLoaded('The benchmark', 'El benchmark', loaded.bench);
  const hold = c01 ? holdFinding(c01) : notLoaded('The case C01', 'El caso C01', loaded.c01);
  const findings: Record<StepId, Finding | Missing> = { setup, device: dev, method, compare, hold };
  const cursor = useLinkedView((s) => s.cursor);
  const band = useStoryBand(active.id);

  // The views read the App's contexts: the actions a story step needs are the device switch and the trap selection of the shared store.
  const sel: Selection | null = useMemo(() => {
    const data = active.id === 'device' ? c08 : active.id === 'hold' ? c01 : c02;
    if (!data) return null;
    const linkedTrap = selectedId !== null && data.trace.traps.some((tr) => String(tr.id) === selectedId) ? Number(selectedId) : null;
    const base = storySelection(data, active.id === 'device' ? device : null, linkedTrap);
    return active.id === 'device' ? { ...base, methodId: data.manifest.params.reference_method } : base;
  }, [active.id, c02, c08, c01, device, selectedId]);
  const actions: Actions = useMemo(
    () => ({
      mode: 'inspect',
      selectTrap: (id) => select(trapToLinked(id), 'panel'),
      setDevice: (d) => onDevice?.(d),
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
    }),
    [select, onDevice],
  );

  const unavailableFor = (id: StepId): Tx | null => {
    const l = id === 'device' ? loaded.c08 : id === 'hold' ? loaded.c01 : id === 'compare' ? loaded.bench : loaded.c02;
    return reasonOf(l);
  };
  const failed = unavailableFor(active.id);
  if (failed) {
    return (
      <section className="dh-story-state" data-state="unavailable">
        <h1>{t('Guided story', 'Recorrido guiado')}</h1>
        <p className="caos-pending" data-state="unavailable">{pick(failed, lang)}</p>
        <a href={exitHref(active, null)}>{t('Return to the App', 'Volver a la App')}</a>
      </section>
    );
  }

  const headlineOf = (f: Finding | Missing): Tx => ('missing' in f ? (f.loading ? bi('Loading this number', 'Cargando esta cifra') : bi('This number is not available in the release', 'Esta cifra no está disponible en la versión')) : f.headline);
  const summaryOf = (f: Finding | Missing): Tx => ('missing' in f ? f.missing : f.summary);
  const steps: StoryStep[] = STEP_DEFS.map((d) => ({
    id: d.id,
    number: STEP_DEFS.indexOf(d) + 1,
    verb: d.verb,
    headline: headlineOf(findings[d.id]),
    summary: summaryOf(findings[d.id]),
    href: `/story/${d.id}`,
    accent: d.accent,
    stage: null,
    panel: null,
  }));
  const current = steps.find((s) => s.id === active.id)!;
  const f = findings[active.id];
  const provenance = (active.id === 'compare' ? 'synthetic' : (sel?.data.manifest.real_or_synthetic ?? 'synthetic')) as 'synthetic' | 'real';
  // the step's artifacts are still loading: the stage says so, so that the page is not taken for settled while it has no scene and no callouts
  const activeLoad = active.id === 'device' ? loaded.c08 : active.id === 'hold' ? loaded.c01 : active.id === 'compare' ? loaded.bench : loaded.c02;
  const stageOf = (): ReactNode => {
    if (activeLoad.state === 'loading') return <p className="caos-pending" data-state="loading" role="status">{t('Loading the story…', 'Cargando el recorrido…')}</p>;
    if (active.id === 'compare') return bench ? <div className="dh-story-view"><CompareView bench={bench} cell={cell} finding={compare as ReturnType<typeof compareFinding>} /></div> : null;
    if (!sel) return null;
    if (active.id === 'setup') return <div className="dh-story-view"><OpticalTrainView sel={sel} /></div>;
    if (active.id === 'device') return <div className="dh-story-view"><SlmSectionView sel={sel} /></div>;
    if (active.id === 'method') return <div className="dh-story-view"><MethodAtWorkView sel={sel} /></div>;
    return <HoldStage sel={sel} finding={f as unknown as { kappa: number; fc: number } | Missing} lang={lang} />;
  };
  const point = sel && active.id === 'method' ? pointAt(sel.result?.history ?? [], cursor) : null;
  const extra: ReactNode = (() => {
    if (active.id === 'setup' && sel) return <StoryFocal sel={sel} />;
    if (active.id === 'method' && point && sel) return <p>{t('At the scrubbed iteration', 'En la iteración elegida')} <strong>{point.iteration}</strong>: {t('spread', 'dispersión')} <strong>{spreadText(point.relStdPct, lang)} %</strong>, {t('efficiency', 'eficiencia')} <strong>{num(point.efficiency * 100, lang, 1)} %</strong>.</p>;
    if (active.id === 'compare' && bench) {
      const geos = bench.geometries.filter((g) => bench.rows.some((r) => r.geometry === g.id && r.device === cell.device));
      return (
        <div className="dh-story-picks">
          <ChipGroup id="story-geometry" label={{ en: 'Geometry', es: 'Geometría' }} value={cell.geometry} onChange={(v) => onCell?.({ ...cell, geometry: v })} options={geos.map((g) => ({ id: g.id, label: { en: g.id, es: g.id }, hint: g.name }))} />
          <ChipGroup id="story-budget" label={{ en: 'Iterations', es: 'Iteraciones' }} value={String(cell.budget)} onChange={(v) => onCell?.({ ...cell, budget: Number(v) })} options={[10, 30, 100].map((b) => ({ id: String(b), label: { en: String(b), es: String(b) } }))} />
          {selectedId && <p>{t('Selected', 'Elegido')}: <strong>{nameOf(selectedId, lang)}</strong> ({selectedId}). {t('Leave the story to load it in the App.', 'Salga del recorrido para cargarlo en la App.')}</p>}
        </div>
      );
    }
    return null;
  })();
  const stage = stageOf();
  const panel = (
    <section className="dh-story-evidence" data-story-panel={active.id}>
      <h2>{pick(active.verb, lang)}</h2>
      {'missing' in f ? <MissingLine m={f} lang={lang} /> : <><p>{pick(f.summary, lang)}</p><Facts finding={f} lang={lang} /></>}
      {extra}
      {sel && <p><strong>{pick(sel.data.manifest.title, lang)}</strong> · {sel.data.manifest.case_id}</p>}
      <span className="badge" data-provenance={provenance}>{provenance === 'synthetic' ? t('Synthetic case replay', 'Reproducción de caso sintético') : t('Real data', 'Datos reales')}</span>
      <ReadinessNote ids={active.id === 'compare' ? ['benchmark-results'] : CASE_ROWS} />
    </section>
  );
  const withStage = steps.map((s) => (s.id === current.id ? { ...s, stage, panel } : s));
  return (
    <ActionsContext.Provider value={actions}>
      <StoryFrame className="dh-story" steps={withStage} activeId={active.id} mobileStageMinHeight={storyStageFloor(active.id === 'method' ? 900 : active.id === 'hold' ? 860 : 640, band)} onStepChange={onStepChange} onExit={onExit} />
    </ActionsContext.Provider>
  );
}

export function Story() {
  const lang = useShellLang() as Lang;
  const { step = 'setup' } = useParams();
  const [query] = useSearchParams();
  const navigate = useNavigate();
  const readiness = useReadiness();
  const index = useArtifact((s) => loadIndex(s), []);
  const c02 = useStoryCase('C02_grid_feedback');
  const c08 = useStoryCase('C08_device_limited');
  const c01 = useStoryCase('C01_square_grid');
  const bench = useArtifact((s) => loadBenchmark(s), []);
  const selectedId = useLinkedView((s) => s.selectedId);
  const select = useLinkedView((s) => s.select);
  const [cell, setCell] = useState<CompareCell>({ ...COMPARE_CELL });
  const [device, setDevice] = useState<DeviceChoice | null>(null);
  const id = stepDef(step).id;
  // a selection belongs to the step that made it (a trap id on one, a method id on another)
  useEffect(() => {
    select(null, 'external');
  }, [id, select]);
  const from = query.get('from');
  const safeFrom = from && from.startsWith('/app') && !from.startsWith('//') && !from.includes('\\') ? from : null;
  const def = stepDef(step);
  const pickedMethod = def.id === 'compare' && selectedId && /^[MB]\d+$/.test(selectedId) ? selectedId : null;
  const loaded: StoryLoaded = useMemo(() => {
    const gone = (l: Loaded<CaseData>, caseId: string): Loaded<CaseData> => (l.state === 'ready' && caseAbsent(readiness ?? null, caseId, index.state === 'ready' ? (index.data.cases.find((c) => c.case_id === caseId)?.path ?? '') : '') ? { state: 'unavailable', reason: bi(`${caseId} is listed as not available in the release evidence.`, `${caseId} figura como no disponible en la evidencia de la versión.`) } : l);
    return { c02: gone(c02, 'C02_grid_feedback'), c08: gone(c08, 'C08_device_limited'), c01: gone(c01, 'C01_square_grid'), bench };
  }, [c02, c08, c01, bench, readiness, index]);
  return (
    <StoryView
      stepId={id}
      loaded={loaded}
      lang={lang}
      cell={cell}
      onCell={setCell}
      device={device}
      onDevice={setDevice}
      onStepChange={(next) => navigate(`/story/${next}${safeFrom ? `?from=${encodeURIComponent(safeFrom)}` : ''}`)}
      onExit={() => navigate(safeFrom ?? exitHref(def, methodOfStep(def, { C02_grid_feedback: c02, C08_device_limited: c08, C01_square_grid: c01 }, pickedMethod)))}
    />
  );
}

/** The method the exit loads into the App: the one the reader picked on the comparison, else the step's own (the device step's phase-fixed weighted GS, the comparison's weighted GS), else the reference method of the step's case. */
export function methodOfStep(def: StepDef, cases: { C02_grid_feedback: Loaded<CaseData>; C08_device_limited: Loaded<CaseData>; C01_square_grid: Loaded<CaseData> }, picked: string | null = null): string | null {
  if (picked) return picked;
  if (def.method) return def.method;
  const l = cases[def.caseId as keyof typeof cases];
  return l?.state === 'ready' ? l.data.manifest.params.reference_method : null;
}
