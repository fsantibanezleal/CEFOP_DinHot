/**
 * The case-level engine: from a contract-1 params record to a scored run, a particle simulation and an axial cut.
 *
 * Python counterparts: `cases/build.py` (record to engine objects), `core/score.py` (one scoring definition for every method),
 * `stages/infer.py` (`run_method`), `stages/dynamics.py` (trapped particle) and `bake._axial` (axial cut). Conversions between the
 * record's units (um, nm, mm) and SI happen here and only here.
 */
import type { ParamsRecord } from '../../lib/contract.types';
import { EmulatedCamera } from './camera';
import { type Device, deviceFocalField, displayedPhase, makeDevice } from './device';
import { atomParams, atomTrajectory, beadParams, beadTrajectory, boltzmannCheck, fitLorentzian, psd } from './dynamics';
import type { Cx } from './fft';
import { axialCut, fftFocalField, pointTrapBackproject, pointTrapFields, slmField } from './forward';
import { ampTargets, angle, polar } from './methods/common';
import { type Setup, focalBinM, halfFieldM, makeSetup, nFft, slmAxis, wrapPhase } from './geometry';
import { getMethod } from './methods';
import { checkOnBins } from './methods/gs';
import { efficiency, powerBudget, relStd, trapIntensities, uniformity, zeroOrderFraction } from './metrics';
import { Rng } from './rng';
import { type Trap, TrapSet, checkInField } from './traps';
import * as tp from './trapphys';
import { type HistoryEntry, type MethodRun, type Result, type Target, makeBudget } from './types';
import { phaseFromCoeffs } from './zernike';

/** A params record, with or without its `case_id` (a manifest carries the record without it). */
export type ParamsLike = Omit<ParamsRecord, 'case_id'> & { case_id?: string };

export interface TrapEdit {
  id: number;
  x_um: number;
  y_um: number;
  z_um: number;
  weight: number;
  charge: number;
}

export function setupOf(p: ParamsLike): Setup {
  const s = p.setup, beam = s.beam;
  return makeSetup({
    wavelengthM: s.wavelength_nm * 1e-9, focalM: s.focal_mm * 1e-3, na: s.na, nImm: s.n_imm, nPix: s.n_pix, pitchM: s.pitch_um * 1e-6,
    pad: s.pad, beam: beam.kind, waistFrac: 'waist_frac' in beam ? beam.waist_frac : 1,
  });
}

export function deviceOf(p: ParamsLike): Device | null {
  const d = p.device;
  if (!d) return null;
  return makeDevice({
    bitDepth: d.bit_depth, crosstalk: d.crosstalk ? [d.crosstalk.sigma_per_px, d.crosstalk.q] : null, upsample: d.upsample,
    fillFactor: d.fill_factor, flickerRad: d.flicker_rad, lutGamma: d.lut_gamma,
  });
}

export const trapSetOf = (traps: readonly TrapEdit[]): TrapSet =>
  new TrapSet(traps.map((t) => ({ id: t.id, xM: t.x_um * 1e-6, yM: t.y_um * 1e-6, zM: t.z_um * 1e-6, weight: t.weight, charge: t.charge })));

/** Bin centres of the focal grid in micrometres, index `i` at `(i - nFft / 2) * bin`. */
export const binUmOf = (s: Setup): number => focalBinM(s) * 1e6;

/** The boolean shape (without margin) of a shaped target on the focal grid, row-major `[iy * m + ix]`. */
export function shapeMask(p: ParamsLike): Uint8Array {
  const t = p.target;
  if (t.kind !== 'shaped') throw new Error('the target is not a shaped potential');
  const s = setupOf(p), m = nFft(s), b = binUmOf(s), h = Math.floor(m / 2);
  const out = new Uint8Array(m * m);
  for (let iy = 0; iy < m; iy++) {
    for (let ix = 0; ix < m; ix++) {
      const x = (ix - h) * b, y = (iy - h) * b, r = Math.hypot(x, y);
      let on = false;
      if (t.shape === 'disc' || t.shape === 'top_hat') on = r <= (t.radius_um as number);
      else if (t.shape === 'ring' || t.shape === 'lg_ring') on = Math.abs(r - (t.radius_um as number)) <= (t.width_um as number) / 2;
      else if (t.shape === 'line') on = Math.abs(x) <= (t.length_um as number) / 2 && Math.abs(y) <= (t.width_um as number) / 2;
      else throw new Error(`unknown shape ${t.shape}`);
      out[iy * m + ix] = on ? 1 : 0;
    }
  }
  return out;
}

function dilate(mask: Uint8Array, m: number, bins: number): Uint8Array {
  let out = Uint8Array.from(mask);
  for (let k = 0; k < bins; k++) {
    const g = Uint8Array.from(out);
    for (let y = 0; y < m; y++) {
      for (let x = 0; x < m; x++) {
        if (!out[y * m + x]) continue;
        if (y + 1 < m) g[(y + 1) * m + x] = 1;
        if (y > 0) g[(y - 1) * m + x] = 1;
        if (x + 1 < m) g[y * m + x + 1] = 1;
        if (x > 0) g[y * m + x - 1] = 1;
      }
    }
    out = g;
  }
  return out;
}

/** The engine target of a record, with the trap list optionally replaced by an edited one. */
export function targetOf(p: ParamsLike, traps?: readonly TrapEdit[]): Target {
  const t = p.target;
  if (traps) return { kind: 'traps', traps: trapSetOf(traps) };
  if (t.kind === 'traps') return { kind: 'traps', traps: trapSetOf(t.traps) };
  const shape = shapeMask(p), m = nFft(setupOf(p));
  return { kind: 'field', amplitude: Float64Array.from(shape), mask: dilate(shape, m, t.signal_margin_bins) };
}

/** Noll coefficients in waves of the record's aberration, indexed from j = 1 up to the highest index given. */
export function aberrationCoeffs(p: ParamsLike): number[] {
  const noll = p.aberration?.noll ?? {};
  const top = Math.max(1, ...Object.keys(noll).map(Number));
  const c = new Array<number>(top).fill(0);
  for (const [k, v] of Object.entries(noll)) c[Number(k) - 1] = Number(v);
  return c;
}

export const aberrationPhase = (p: ParamsLike, s: Setup): Float64Array | null => (p.aberration ? phaseFromCoeffs(aberrationCoeffs(p), s) : null);

const isThreeD = (p: ParamsLike): boolean => p.target.kind === 'traps' && p.target.traps.some((t) => t.z_um !== 0);

/** The centred focal field of what the SLM displays, through the device when there is one. */
export function focalFieldOf(phi: Float64Array, s: Setup, device: Device | null, ab: Float64Array | null, seed: number): Cx {
  if (device) return deviceFocalField(phi, s, device, new Rng((seed ^ 0x0f11c) & 0x7fffffff));
  return fftFocalField(ab ? phi.map((v, i) => v + ab[i]) : phi, s);
}

export interface Score {
  efficiency: number;
  uniformity: number;
  relStdPct: number;
  zeroOrder: number;
  ghost: number;
  /** Trap intensities `I_m / mean`, in trap id order (empty for a shaped target). */
  trapIntensity: Float64Array;
  field: Cx;
}

const interior = (mask: Uint8Array, m: number): Uint8Array => {
  const core = Uint8Array.from(mask);
  for (let y = 0; y < m; y++) {
    for (let x = 0; x < m; x++) {
      const q = y * m + x;
      if (!mask[q]) continue;
      const edge = y === 0 || x === 0 || y === m - 1 || x === m - 1 || !mask[q - m] || !mask[q + m] || !mask[q - 1] || !mask[q + 1];
      core[q] = edge ? 0 : 1;
    }
  }
  return core.some((v) => v) ? core : mask;
};

/** The final metrics of `phi` for the record's case (`core/score.py`: one definition for every method). */
export function scoreOf(p: ParamsLike, phi: Float64Array, o: { traps?: readonly TrapEdit[]; device?: Device | null } = {}): Score {
  const s = setupOf(p), device = o.device === undefined ? deviceOf(p) : o.device;
  const ab = aberrationPhase(p, s), m = nFft(s);
  if (p.target.kind === 'traps' || o.traps) {
    const traps = o.traps ? trapSetOf(o.traps) : trapSetOf((p.target as { traps: TrapEdit[] }).traps);
    const e = focalFieldOf(phi, s, device, ab, p.seed);
    let v: Cx;
    if (device) {
      const h = Math.floor(m / 2), b = focalBinM(s);
      checkInField(s, traps);
      v = new Float64Array(2 * traps.length);
      for (let t = 0; t < traps.length; t++) {
        const o2 = 2 * ((Math.round(traps.yM[t] / b) + h) * m + Math.round(traps.xM[t] / b) + h);
        v[2 * t] = e[o2] * (s.pad / s.nPix);
        v[2 * t + 1] = e[o2 + 1] * (s.pad / s.nPix);
      }
    } else {
      v = pointTrapFields(ab ? phi.map((x, i) => x + ab[i]) : phi, s, traps);
    }
    const raw = trapIntensities(v), rel = trapIntensities(v, traps.weight);
    const eff = efficiency(raw), zero = zeroOrderFraction(e, s);
    const ghost = isThreeD(p) ? Math.max(0, 1 - eff - zero) : Math.max(0, powerBudget(e, s, traps).ghosts);
    const order = Array.from(traps.ids.keys()).sort((a, c) => traps.ids[a] - traps.ids[c]);
    let mean = 0;
    for (const x of raw) mean += x;
    mean /= raw.length;
    return {
      efficiency: eff, uniformity: uniformity(rel), relStdPct: relStd(rel), zeroOrder: zero, ghost,
      trapIntensity: Float64Array.from(order, (i) => (mean > 0 ? raw[i] / mean : 0)), field: e,
    };
  }
  const shape = shapeMask(p), region = (targetOf(p) as Extract<Target, { kind: 'field' }>).mask;
  const e = focalFieldOf(phi, s, device, null, p.seed);
  const k = s.pad ** 2 / s.nPix ** 2;
  let inShape = 0, inRegion = 0;
  for (let q = 0; q < m * m; q++) {
    const pw = (e[2 * q] ** 2 + e[2 * q + 1] ** 2) / s.nPix ** 2;
    if (shape[q]) inShape += pw;
    if (region[q]) inRegion += pw;
  }
  const core = interior(shape, m);
  let mx = -Infinity, mn = Infinity, sum = 0, cnt = 0;
  for (let q = 0; q < m * m; q++) {
    if (!core[q]) continue;
    const i = (e[2 * q] ** 2 + e[2 * q + 1] ** 2) * k;
    mx = Math.max(mx, i); mn = Math.min(mn, i); sum += i; cnt++;
  }
  const mean = sum / cnt;
  let ss = 0;
  for (let q = 0; q < m * m; q++) if (core[q]) ss += ((e[2 * q] ** 2 + e[2 * q + 1] ** 2) * k - mean) ** 2;
  return {
    efficiency: inShape, uniformity: mx + mn > 0 ? 1 - (mx - mn) / (mx + mn) : 0, relStdPct: mean > 0 ? (100 * Math.sqrt(ss / cnt)) / mean : 0,
    zeroOrder: zeroOrderFraction(e, s), ghost: Math.max(0, 1 - inRegion), trapIntensity: new Float64Array(0), field: e,
  };
}

/** The loaded sites of a rearrangement record: one portable-RNG uniform per site, in id order (`cases/library.random_loading`). */
export function randomLoading(p: ParamsLike): number[] {
  const traps = (p.target as { traps: TrapEdit[] }).traps;
  const ids = traps.map((t) => t.id).sort((a, b) => a - b);
  const u = new Rng(p.seed).uniformArray(ids.length);
  return ids.filter((_, i) => u[i] < (p.rearrangement as { loading_p: number }).loading_p);
}

export interface CaseOptions {
  iterations?: number;
  device?: 'ideal' | 'case';
  trapPhases?: Float64Array;
  traps?: readonly TrapEdit[];
  /** Method keywords (camelCase) that override what the record implies. */
  extra?: Record<string, unknown>;
}

export interface CaseRun {
  /** The method generator and the objects it was built from. */
  gen: MethodRun;
  setup: Setup;
  device: Device | null;
  target: Target;
  /** The starting hologram actually used (a warm start), or null for the method's own start. */
  init: Float64Array | null;
}

/**
 * Build the method run of a case: the setup, device and target of the record (the trap list possibly replaced by an edited
 * one), the seeded RNG, the budget, and the keywords the record implies (M12 feedback gain and camera, M14 injected aberration,
 * M16 loaded atoms). Throws `NotLive` for a method that is not ported.
 */
export function buildRun(p: ParamsLike, method: string, o: CaseOptions = {}, init: Float64Array | null = null, trapPhases: Float64Array | null = null): CaseRun {
  const mod = getMethod(method);
  const setup = setupOf(p);
  const device = (o.device ?? 'case') === 'ideal' ? null : deviceOf(p);
  let target = targetOf(p, o.traps);
  const options: Record<string, unknown> = { ...(o.extra ?? {}) };
  if (method === 'M14' && p.aberration && options.injected === undefined) options.injected = aberrationCoeffs(p);
  // M07's default form is the FFT one, which needs traps on bins; an edited or off-bin target uses the point form (identical on bins)
  if (method === 'M07' && options.form === undefined && target.kind === 'traps') {
    try { checkOnBins(setup, target.traps); } catch { options.form = 'point'; }
  }
  if (method === 'M12' && p.feedback) {
    options.gain ??= p.feedback.gain;
    if (options.camera === undefined) {
      const c = p.feedback.camera;
      options.camera = new EmulatedCamera(p.seed, { gainRms: c.gain_rms, noiseRms: c.noise_rms, blurBins: c.blur_bins, rolloff: false });
    }
  }
  if (method === 'M16' && p.rearrangement && options.atoms === undefined && target.kind === 'traps') {
    const r = p.rearrangement, sites = new Map(target.traps.traps.map((t) => [t.id, t]));
    const loaded = randomLoading(p).map((id) => sites.get(id) as Trap);
    options.atoms = new TrapSet(loaded);
    const want = new Set(r.target_ids);
    target = { kind: 'traps', traps: new TrapSet(target.traps.traps.filter((t) => want.has(t.id))) };
  }
  if (trapPhases && init === null) {
    // a warm start (B3 inference): the superposition hologram with the given trap phases, `arg sum_m a_m exp(i (Delta^m + psi_m))`
    if (target.kind !== 'traps' || trapPhases.length !== target.traps.length) throw new Error('trapPhases needs one phase per trap of a trap target');
    init = angle(pointTrapBackproject(polar(ampTargets(target.traps), trapPhases), setup, target.traps));
  }
  const budget = makeBudget(o.iterations ?? p.budget.iterations, p.budget.time_s);
  const ctx = { setup, target, device, budget, rng: new Rng(p.seed), init, options };
  return { gen: mod.run(ctx), setup, device, target, init };
}

/** Progress of one iteration in the units of the workbench. */
export interface Progress {
  iteration: number;
  efficiency: number;
  uniformity: number;
  relStdPct: number;
}

export const progressOf = (h: HistoryEntry): Progress => ({ iteration: h.iteration, efficiency: h.efficiency, uniformity: h.uniformity, relStdPct: h.relStd });

/** Everything the workbench shows of a finished run, computed from the final phase (never from the method's own history). */
export interface CaseResult {
  method: string;
  nPix: number;
  pad: number;
  binUm: number;
  halfFieldUm: number;
  phase: Float64Array;
  displayedPhase: Float64Array | null;
  focal: Float32Array;
  focalSize: number;
  trapIntensity: Float64Array;
  history: Progress[];
  metrics: { efficiency: number; uniformity: number; relStdPct: number; zeroOrder: number; ghost: number };
}

export function finishRun(p: ParamsLike, method: string, result: Result, o: CaseOptions = {}): CaseResult {
  const setup = setupOf(p);
  const device = (o.device ?? 'case') === 'ideal' ? null : deviceOf(p);
  const phase = wrapPhase(result.phi);
  const sc = scoreOf(p, phase, { traps: o.traps, device });
  const m = nFft(setup), k = setup.pad ** 2 / setup.nPix ** 2;
  let ref = 1;
  if (sc.trapIntensity.length) {
    ref = sc.efficiency / sc.trapIntensity.length || 1; // mean raw trap intensity
  } else {
    const core = interior(shapeMask(p), m);
    let s = 0, c = 0;
    for (let q = 0; q < m * m; q++) if (core[q]) { s += (sc.field[2 * q] ** 2 + sc.field[2 * q + 1] ** 2) * k; c++; }
    ref = s / c || 1;
  }
  const focal = new Float32Array(m * m);
  for (let q = 0; q < m * m; q++) focal[q] = ((sc.field[2 * q] ** 2 + sc.field[2 * q + 1] ** 2) * k) / ref;
  const displayed = device ? displayedPhase0(phase, device, p.seed) : null;
  return {
    method, nPix: setup.nPix, pad: setup.pad, binUm: binUmOf(setup), halfFieldUm: halfFieldM(setup) * 1e6, phase, displayedPhase: displayed,
    focal, focalSize: m, trapIntensity: sc.trapIntensity, history: result.history.map(progressOf),
    metrics: { efficiency: sc.efficiency, uniformity: sc.uniformity, relStdPct: sc.relStdPct, zeroOrder: sc.zeroOrder, ghost: sc.ghost },
  };
}

const displayedPhase0 = (phi: Float64Array, device: Device, seed: number): Float64Array =>
  displayedPhase(phi, device, new Rng((seed ^ 0x0f11c) & 0x7fffffff));

// ---- axial cut ----

/** Axial intensity slice through the trap `trapId` (xz plane) of a hologram: `bake._axial` with the trap chosen by the caller. */
export function axialCutOf(p: ParamsLike, phase: Float64Array, trapId: number, nz: number): { xz: Float32Array; nx: number; nz: number; zUm: [number, number] } {
  if (p.target.kind !== 'traps') throw new Error('an axial cut needs a trap target');
  const trap = p.target.traps.find((t) => t.id === trapId);
  if (!trap) throw new Error(`unknown trap id ${trapId}`);
  const s = setupOf(p);
  const halfZ = Math.max((5 * s.wavelengthM * s.nImm) / s.na ** 2, 1.5 * Math.max(...p.target.traps.map((t) => Math.abs(t.z_um * 1e-6))));
  const ab = aberrationPhase(p, s);
  const phi = ab ? phase.map((v, i) => v + ab[i]) : phase;
  const cut = axialCut(phi, s, { yM: trap.y_um * 1e-6, zRangeM: [-halfZ, halfZ], nz });
  return { xz: Float32Array.from(cut.intensity), nx: cut.nLateral, nz, zUm: [cut.zM[0] * 1e6, cut.zM[nz - 1] * 1e6] };
}

// ---- trapped particle ----

const HALF_BINS = 2.5;
const STEP_BINS = 0.1;
const RB_LAMBDA0_M = 780.241e-9;
const RB_GAMMA_HZ = 6.065e6;
const AMU_KG = 1.6605390666e-27;
const FIT_BAND = 5.0;
const SEGMENT_SAMPLES = 2048;
const MAX_TRAJECTORY = 4000;

/** `I_m` map on a local grid around a trap from the point-trap form (exact between bins), separable in x and y. */
export function localMapFromPhase(phi: Float64Array, s: Setup, cx: number, cy: number, z: number): { map: Float64Array; xs: Float64Array; ys: Float64Array } {
  const b = focalBinM(s), n = Math.round((2 * HALF_BINS) / STEP_BINS) + 1;
  const ax = Float64Array.from({ length: n }, (_, i) => (i - (n - 1) / 2) * STEP_BINS * b);
  const xs = ax.map((a) => cx + a), ys = ax.map((a) => cy + a);
  const field = slmField(phi, s), np = s.nPix, c = slmAxis(s);
  const lam = s.wavelengthM, f = s.focalM, kk = (2 * Math.PI) / (lam * f), cz = (Math.PI * z) / (lam * f * f);
  const tmp = new Float64Array(2 * np * n);
  for (let ix = 0; ix < n; ix++) {
    const gr = new Float64Array(np), gi = new Float64Array(np);
    for (let j = 0; j < np; j++) {
      const a = cz * c[j] * c[j] + kk * xs[ix] * c[j];
      gr[j] = Math.cos(a); gi[j] = -Math.sin(a);
    }
    for (let iy = 0; iy < np; iy++) {
      let tr = 0, ti = 0;
      for (let j = 0; j < np; j++) {
        const fr = field[2 * (iy * np + j)], fi = field[2 * (iy * np + j) + 1];
        tr += fr * gr[j] - fi * gi[j];
        ti += fr * gi[j] + fi * gr[j];
      }
      tmp[2 * (iy * n + ix)] = tr; tmp[2 * (iy * n + ix) + 1] = ti;
    }
  }
  const map = new Float64Array(n * n);
  for (let iy = 0; iy < n; iy++) {
    const gr = new Float64Array(np), gi = new Float64Array(np);
    for (let j = 0; j < np; j++) {
      const a = cz * c[j] * c[j] + kk * ys[iy] * c[j];
      gr[j] = Math.cos(a); gi[j] = -Math.sin(a);
    }
    for (let ix = 0; ix < n; ix++) {
      let vr = 0, vi = 0;
      for (let j = 0; j < np; j++) {
        const tr = tmp[2 * (j * n + ix)], ti = tmp[2 * (j * n + ix) + 1];
        vr += gr[j] * tr - gi[j] * ti;
        vi += gr[j] * ti + gi[j] * tr;
      }
      map[iy * n + ix] = ((vr / np ** 2) ** 2) + ((vi / np ** 2) ** 2);
    }
  }
  return { map, xs, ys };
}

/** Bicubic (Catmull-Rom) local map from a sampled focal intensity (`size x size`, centred, bin `binM`), around `(cx, cy)` metres. */
export function localMapFromFocal(focal: ArrayLike<number>, size: number, binM: number, cx: number, cy: number): { map: Float64Array; xs: Float64Array; ys: Float64Array } {
  const n = Math.round((2 * HALF_BINS) / STEP_BINS) + 1, h = Math.floor(size / 2);
  const ax = Float64Array.from({ length: n }, (_, i) => (i - (n - 1) / 2) * STEP_BINS * binM);
  const xs = ax.map((a) => cx + a), ys = ax.map((a) => cy + a);
  const at = (iy: number, ix: number): number => focal[Math.min(size - 1, Math.max(0, iy)) * size + Math.min(size - 1, Math.max(0, ix))];
  const cr = (t: number, p0: number, p1: number, p2: number, p3: number): number =>
    0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3);
  const map = new Float64Array(n * n);
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const u = xs[i] / binM + h, v = ys[j] / binM + h;
      const i0 = Math.floor(u), j0 = Math.floor(v), tx = u - i0, ty = v - j0;
      const rows = [-1, 0, 1, 2].map((dy) => cr(tx, at(j0 + dy, i0 - 1), at(j0 + dy, i0), at(j0 + dy, i0 + 1), at(j0 + dy, i0 + 2)));
      map[j * n + i] = Math.max(0, cr(ty, rows[0], rows[1], rows[2], rows[3]));
    }
  }
  return { map, xs, ys };
}

export interface ParticleResult {
  xUm: Float64Array;
  yUm: Float64Array;
  dtS: number;
  psd: { fHz: Float64Array; p: Float64Array };
  fcHz: number;
  stiffness: { value: number; unit: string };
  /** `measured / expected` corner (bead) or radial (atom) frequency: the calibration oracle of the case. */
  fcRatio: number;
  boltzmannTv: number | null;
  depth: { value: number; unit: string };
}

type Dynamics = NonNullable<ParamsRecord['dynamics']>;

/**
 * A bead or an atom in the intensity the hologram computes (`stages/dynamics.run`). The local map comes from the phase and the
 * setup (exact point-trap form, as the bake) when both are given, else from the sampled focal intensity by bicubic
 * interpolation (an approximation: the FFT grid samples the focal field at half the resolution cell for pad 2).
 */
export function simulateParticle(req: {
  dynamics: Dynamics;
  seed: number;
  focal?: ArrayLike<number>;
  focalSize?: number;
  binUm?: number;
  phase?: Float64Array;
  setup?: Setup;
  trap?: { x_um: number; y_um: number; z_um: number };
}): ParticleResult {
  const d = req.dynamics;
  const trap = req.trap ?? { x_um: 0, y_um: 0, z_um: 0 };
  let m: { map: Float64Array; xs: Float64Array; ys: Float64Array };
  let binM: number, pad: number, nImm: number;
  if (req.phase && req.setup) {
    m = localMapFromPhase(req.phase, req.setup, trap.x_um * 1e-6, trap.y_um * 1e-6, trap.z_um * 1e-6);
    binM = focalBinM(req.setup); pad = req.setup.pad; nImm = req.setup.nImm;
  } else if (req.focal && req.focalSize && req.binUm) {
    binM = req.binUm * 1e-6;
    m = localMapFromFocal(req.focal, req.focalSize, binM, trap.x_um * 1e-6, trap.y_um * 1e-6);
    pad = req.setup?.pad ?? 2; nImm = req.setup?.nImm ?? 1.33;
  } else throw new Error('a particle simulation needs the hologram phase with the setup, or the focal intensity with its bin');
  const n = Math.round(Math.sqrt(m.map.length)), h = STEP_BINS * binM;
  let best = -Infinity, iy = 0, ix = 0;
  m.map.forEach((v, q) => { if (v > best) { best = v; iy = Math.floor(q / n); ix = q % n; } });
  const cy = Math.min(Math.max(iy, 2), n - 3), cx = Math.min(Math.max(ix, 2), n - 3);
  const dxx = (m.map[cy * n + cx + 2] - 2 * m.map[cy * n + cx] + m.map[cy * n + cx - 2]) / (2 * h) ** 2 / best;
  const curv = -dxx;
  if (!(curv > 0)) throw new Error(`trap ${d.trap_id}: the computed intensity has no maximum curvature (not a trap)`);
  const pW = d.power_mw * 1e-3, iPeak = (best * pW) / (pad ** 2 * binM ** 2);
  const rng = new Rng(req.seed + 7919);
  const nSteps = d.n_steps, dt = d.dt_s;
  const start: [number, number] = [m.xs[cx], m.ys[cy]];
  let pos: Float64Array, fcExpected: number, measured: number, tv: number | null = null, spec: { f: Float64Array; p: Float64Array };
  let stiff: { value: number; unit: string }, depthOut: { value: number; unit: string };
  if (d.particle === 'bead') {
    const r = (d.bead_radius_um as number) * 1e-6;
    const alpha = tp.rayleighPolarizabilityFm2(r, d.n_particle as number, nImm);
    const depth = (alpha * iPeak) / (2 * tp.C_M_PER_S * tp.EPS0_F_PER_M);
    const gamma = 6 * Math.PI * (d.viscosity_pa_s as number) * r;
    const kappa = depth * curv;
    fcExpected = kappa / (2 * Math.PI * gamma);
    pos = beadTrajectory(m.map, m.xs, m.ys, beadParams({ depthJ: depth, gammaNsPerM: gamma, temperatureK: d.temperature_k, startM: start }), nSteps, dt, rng);
    const x = Float64Array.from({ length: nSteps + 1 }, (_, i) => pos[2 * i]);
    spec = psd(x, dt, Math.max(4, Math.floor(nSteps / SEGMENT_SAMPLES)));
    const keep = spec.f.map((f) => (f <= FIT_BAND * fcExpected ? 1 : 0));
    const fb = spec.f.filter((_, i) => keep[i]), pb = spec.p.filter((_, i) => keep[i]);
    measured = fitLorentzian(fb, pb).fc;
    const row = Array.from({ length: n }, (_, i) => m.map[cy * n + i] / best);
    const pot = (xv: number): number => {
      // np.interp over the row on the x axis
      if (xv <= m.xs[0]) return -depth * row[0];
      if (xv >= m.xs[n - 1]) return -depth * row[n - 1];
      const t = (xv - m.xs[0]) / h, i0 = Math.min(n - 2, Math.floor(t));
      return -depth * (row[i0] + (row[i0 + 1] - row[i0]) * (t - i0));
    };
    tv = boltzmannCheck(x, pot, d.temperature_k).totalVariation;
    stiff = { value: kappa * 1e6, unit: 'pN/um' };
    depthOut = { value: depth / (tp.KB_J_PER_K * d.temperature_k), unit: 'kBT' };
  } else {
    const om0 = (2 * Math.PI * tp.C_M_PER_S) / RB_LAMBDA0_M, gam = 2 * Math.PI * RB_GAMMA_HZ, delta = 2 * Math.PI * (d.detuning_thz as number) * 1e12;
    const depth = -tp.dipolePotentialJ(iPeak, om0, gam, delta);
    if (!(depth > 0)) throw new Error('a positive (blue) detuning repels the atom: there is no trap');
    const mass = (d.mass_amu as number) * AMU_KG;
    const omega = Math.sqrt((depth * curv) / mass);
    fcExpected = omega / (2 * Math.PI);
    pos = atomTrajectory(m.map, m.xs, m.ys, atomParams({ depthJ: depth, massKg: mass, temperatureK: d.temperature_k, kickMPerS: 0, startM: start }), nSteps, dt, rng).pos;
    const x = Float64Array.from({ length: nSteps + 1 }, (_, i) => pos[2 * i]);
    spec = psd(x, dt, 4);
    const sm = spec.p.map((_, i) => (i === 0 || i === spec.p.length - 1 ? NaN : (spec.p[i - 1] + spec.p[i] + spec.p[i + 1]) / 3));
    let bi = 1;
    for (let i = 1; i < sm.length - 1; i++) if (sm[i] > sm[bi]) bi = i;
    measured = spec.f[bi];
    stiff = { value: mass * omega ** 2 * 1e6, unit: 'pN/um' };
    depthOut = { value: (depth / tp.KB_J_PER_K) * 1e6, unit: 'uK' };
  }
  const dec = Math.max(1, Math.ceil((nSteps + 1) / MAX_TRAJECTORY));
  const len = Math.min(MAX_TRAJECTORY, Math.ceil((nSteps + 1) / dec));
  const xUm = Float64Array.from({ length: len }, (_, i) => (pos[2 * i * dec] - start[0]) * 1e6);
  const yUm = Float64Array.from({ length: len }, (_, i) => (pos[2 * i * dec + 1] - start[1]) * 1e6);
  return {
    xUm, yUm, dtS: dt * dec, psd: { fHz: spec.f, p: spec.p.map((v) => v * 1e12) }, fcHz: measured, stiffness: stiff, fcRatio: measured / fcExpected,
    boltzmannTv: tv, depth: depthOut,
  };
}

