// The selection the views share, the names of the methods, and the construction of what a view draws from the two lanes: the
// committed trace (replay) and a live run of the engine (live). A view never reads the trace or a RunResult directly; it reads a
// `Selection`, so the lane of every number is one field and cannot be forgotten (ADR-0054).
import { createContext, useContext } from 'react';
import type { CaseData } from '../api/artifacts';
import type { CaseManifest, Device, ParamsRecord, Text, Trace, Trap } from '../lib/contract.types';
import { b64ToU8, dbFromU8, decodeRle, linearToDb, phaseFromU8, type DeviceStage } from './decode';
import type { Progress, RunResult } from './engine';
import { umToPixel } from './traps';

export type Lane = 'live' | 'replay';
export type DeviceChoice = 'ideal' | 'case';

/** The ladder of methods (SDD), by id, in both languages. */
export const METHOD_NAMES: Record<string, Text> = {
  M01: { en: 'Prisms and lenses', es: 'Prismas y lentes' },
  M02: { en: 'Random superposition', es: 'Superposición aleatoria' },
  M03: { en: 'Random mask', es: 'Máscara aleatoria' },
  M04: { en: 'Gerchberg-Saxton', es: 'Gerchberg-Saxton' },
  M05: { en: 'Generalized adaptive additive', es: 'Aditivo adaptativo generalizado' },
  M06: { en: 'Weighted GS', es: 'GS ponderado' },
  M07: { en: 'Phase-fixed weighted GS', es: 'GS ponderado con fase fija' },
  M08: { en: 'MRAF', es: 'MRAF' },
  M09: { en: 'Direct search', es: 'Búsqueda directa' },
  M10: { en: 'Conjugate gradient', es: 'Gradiente conjugado' },
  M11: { en: 'Wirtinger gradient with Adam', es: 'Gradiente de Wirtinger con Adam' },
  M12: { en: 'Closed-loop WGS', es: 'WGS en lazo cerrado' },
  M13: { en: 'Device-aware CG', es: 'CG con modelo del dispositivo' },
  M14: { en: 'Zernike correction', es: 'Corrección de Zernike' },
  M15: { en: 'Laguerre-Gaussian vortices', es: 'Vórtices de Laguerre-Gauss' },
  M16: { en: 'Hungarian rearrangement', es: 'Reordenamiento húngaro' },
  M17: { en: 'Unsupervised CNN', es: 'CNN no supervisada' },
  M18: { en: 'Optimal-transport MRAF', es: 'MRAF con transporte óptimo' },
  M19: { en: 'Multi-plane GS', es: 'GS multiplano' },
  B1: { en: 'Device-aware WGS', es: 'WGS con modelo del dispositivo' },
  B2: { en: 'Flicker-bounded sequence', es: 'Secuencia acotada por parpadeo' },
  B3: { en: 'Learned warm start', es: 'Arranque aprendido' },
  B4: { en: 'Aberration-robust hologram', es: 'Holograma robusto a aberraciones' },
  B5: { en: 'Efficiency-uniformity front', es: 'Frente eficiencia-uniformidad' },
};

export const methodName = (id: string): Text => METHOD_NAMES[id] ?? { en: id, es: id };
export const methodLabel = (id: string): Text => ({ en: `${id} ${methodName(id).en}`, es: `${id} ${methodName(id).es}` });

export interface Metrics {
  efficiency: number;
  uniformity: number;
  relStdPct: number;
  zeroOrder: number;
  ghost: number;
}
export interface HistoryPoint {
  iteration: number;
  efficiency: number;
  uniformity: number;
  relStdPct: number;
}
export interface FocalMap {
  /** dB relative to the mean trap, floor..0. */
  db: Float32Array;
  size: number;
  binUm: number;
  floor: number;
}
export interface Axial {
  db: Float32Array;
  nx: number;
  nz: number;
  zUm: [number, number];
  trapId: number;
}
/** The maps of one method's hologram and its focal plane, with where they came from. */
export interface MapSet {
  lane: Lane;
  /** The method whose hologram this is. */
  method: string;
  nPix: number;
  pad: number;
  binUm: number;
  halfFieldUm: number;
  phase: Float32Array;
  displayed: Float32Array | null;
  focal: FocalMap | null;
  axial: Axial | null;
  shape: Uint8Array | null;
  backend: 'cpu' | 'gpu' | null;
  fallbackReason: string | null;
  timeMs: number | null;
}
export interface MethodResult {
  lane: Lane;
  method: string;
  metrics: Metrics | null;
  history: HistoryPoint[];
  /** I_m / mean per trap, in the order of `traps` of the trace (trap id order). */
  trapI: number[] | null;
}

export interface Region {
  /** Micrometres, x0 <= x1 and y0 <= y1. */
  x0: number;
  x1: number;
  y0: number;
  y1: number;
}

export interface Selection {
  data: CaseData;
  methodId: string;
  /** The lane of this selection's maps (the metrics carry their own). */
  device: DeviceChoice;
  deviceModel: Device | null;
  traps: Trap[];
  edited: boolean;
  trapId: number | null;
  region: Region | null;
  maps: MapSet | null;
  result: MethodResult | null;
  iteration: number;
  dbFloor: number;
  /** Aberration coefficients (waves) by Noll index - 1, as edited. */
  aberration: number[];
  aberrationEdited: boolean;
  powerMw: number;
  seed: number;
  /** Which device stage the phase mask shows, how the per-trap bars are ordered and the uniformity band in percent. */
  stage: DeviceStage;
  sortBy: 'id' | 'deviation';
  bandPct: number;
  /** The feedback step shown by the camera view and the Noll mode the aberration knob edits. */
  fbStep: number;
  zmode: number;
  /** Correction on: the aberration of the case is removed before the edits apply. */
  corrected: boolean;
  /** The aberration as a key: changes when any coefficient does, so a computed cut knows when it is stale. */
  coeffKey: string;
  /** The plane of the axial cut and the threshold of the 3D view (fraction of the peak). */
  plane: 'xz' | 'yz';
  volThreshold: number;
  /** Which model answered the learned slot this method uses, for the label. */
  slot: { slot: 'cgh-net' | 'warmstart-model'; answered: 'model' | 'baseline' } | null;
  /** A live run is under way (progress) or failed (error). */
  running: boolean;
  progress: Progress | null;
  liveError: string | null;
  /** The reader cancelled the run in flight. */
  cancelled: boolean;
  /** The params record the engine would run for the rail's values (device, traps, aberration, iterations): what a cut or a particle needs. */
  runParams: ParamsRecord;
  /** Live engine present in this build. */
  engineAvailable: boolean;
  liveMethods: string[];
}

export const ViewContext = createContext<Selection | null>(null);
export const UnavailableContext = createContext<Text | null>(null);

export function useSelection(): Selection | null {
  return useContext(ViewContext);
}

/** The traps a case starts from: the manifest's list (a shaped target has none; the trace carries its mask instead). */
export function trapsOf(manifest: CaseManifest, trace: Trace): Trap[] {
  const t = manifest.params.target;
  return t.kind === 'traps' ? t.traps.map((x) => ({ ...x })) : trace.traps.map((x) => ({ ...x }));
}

export const isShaped = (manifest: CaseManifest): boolean => manifest.params.target.kind === 'shaped';
export const is3D = (traps: readonly Trap[]): boolean => new Set(traps.map((t) => t.z_um)).size > 1;

/** The hologram and focal maps of the committed trace: the reference method's, whichever method the reader selected. */
export function replayMaps(trace: Trace, dbFloorStored = trace.reference.focal.db_floor): MapSet {
  const ref = trace.reference;
  const axial = ref.axial
    ? { db: dbFromU8(b64ToU8(ref.axial.xz_u8), dbFloorStored), nx: ref.axial.nx, nz: ref.axial.nz, zUm: [ref.axial.z_um[0], ref.axial.z_um[1]] as [number, number], trapId: ref.axial.trap_id }
    : null;
  const size = ref.focal.size;
  return {
    lane: 'replay',
    method: ref.method,
    nPix: trace.grid.n_pix,
    pad: trace.grid.pad,
    binUm: trace.grid.bin_um,
    halfFieldUm: trace.grid.half_field_um,
    phase: phaseFromU8(b64ToU8(ref.phase_u8)),
    displayed: null,
    focal: { db: dbFromU8(b64ToU8(ref.focal.intensity_db_u8), ref.focal.db_floor), size, binUm: ref.focal.bin_um, floor: ref.focal.db_floor },
    axial,
    shape: trace.shape ? decodeRle(trace.shape.mask_rle, size * size) : null,
    backend: null,
    fallbackReason: null,
    timeMs: null,
  };
}

/** What the trace holds for one method: its final metrics, its history and its per-trap intensities. */
export function replayResult(trace: Trace, methodId: string): MethodResult | null {
  const m = trace.methods[methodId];
  if (!m) return null;
  return {
    lane: 'replay',
    method: methodId,
    metrics: { efficiency: m.final.efficiency, uniformity: m.final.uniformity, relStdPct: m.final.rel_std_pct, zeroOrder: m.final.zero_order, ghost: m.final.ghost },
    history: m.history.map((h) => ({ iteration: h.iteration, efficiency: h.efficiency, uniformity: h.uniformity, relStdPct: h.rel_std_pct })),
    trapI: m.trap_intensity,
  };
}

/** The maps and result of a live run; the focal map (linear intensity) is put in dB against the mean light at the traps. */
export function liveMaps(res: RunResult, traps: readonly Trap[], dbFloor: number): { maps: MapSet; result: MethodResult } {
  const size = res.focalSize;
  let ref = 0;
  for (const t of traps) {
    const [c, r] = umToPixel(t.x_um, t.y_um, size, res.binUm);
    if (c >= 0 && c < size && r >= 0 && r < size) ref += res.focal[r * size + c];
  }
  ref = traps.length ? ref / traps.length : 1;
  const phase = new Float32Array(res.phase.length);
  for (let i = 0; i < phase.length; i++) phase[i] = ((res.phase[i] % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
  const mean = res.trapIntensity.length ? res.trapIntensity.reduce((a, v) => a + v, 0) / res.trapIntensity.length : 1;
  return {
    maps: {
      lane: 'live',
      method: res.method,
      nPix: res.nPix,
      pad: res.pad,
      binUm: res.binUm,
      halfFieldUm: res.halfFieldUm,
      phase,
      displayed: res.displayedPhase ? Float32Array.from(res.displayedPhase) : null,
      focal: { db: linearToDb(res.focal, ref, dbFloor), size, binUm: res.binUm, floor: dbFloor },
      axial: null,
      shape: null,
      backend: res.backend,
      fallbackReason: res.fallbackReason,
      timeMs: res.timeMs,
    },
    result: {
      lane: 'live',
      method: res.method,
      metrics: { ...res.metrics },
      history: res.history.map((h) => ({ ...h })),
      trapI: [...res.trapIntensity].map((v) => (mean > 0 ? v / mean : v)),
    },
  };
}

/** Per-trap relative depth I_m / mean (a trap's trapped depth scales with its intensity: U proportional to I, Grimm et al. Eq. 12). */
export function trapDeviation(trapI: readonly number[]): { min: number; max: number; rmsPct: number } {
  if (!trapI.length) return { min: NaN, max: NaN, rmsPct: NaN };
  const mean = trapI.reduce((a, v) => a + v, 0) / trapI.length;
  const rms = Math.sqrt(trapI.reduce((a, v) => a + (v - mean) ** 2, 0) / trapI.length);
  return { min: Math.min(...trapI), max: Math.max(...trapI), rmsPct: mean > 0 ? (100 * rms) / mean : NaN };
}

/** A histogram of values in `bins` equal bins over [lo, hi]: the centres and the counts. */
export function histogram(values: readonly number[], lo: number, hi: number, bins: number): { centres: number[]; counts: number[] } {
  const counts = new Array<number>(bins).fill(0);
  const w = (hi - lo) / bins || 1;
  for (const v of values) {
    const k = Math.min(bins - 1, Math.max(0, Math.floor((v - lo) / w)));
    counts[k]++;
  }
  return { centres: counts.map((_, k) => lo + (k + 0.5) * w), counts };
}

/** The history point at or before an iteration (the last one when the iteration is beyond the run). */
export function historyAt(history: readonly HistoryPoint[], iteration: number): HistoryPoint | null {
  if (!history.length) return null;
  let best = history[0];
  for (const h of history) if (h.iteration <= iteration) best = h;
  return best;
}
