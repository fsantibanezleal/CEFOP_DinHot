/**
 * Control methods M12, M14, M15 and M16 (the live lane).
 *
 * Python counterparts: `methods/control/m12_closed_loop.py`, `m14_zernike.py`, `m15_vortex.py`, `m16_rearrangement.py`
 * (each docstring there carries the model, the dossier section and the UNVERIFIED items). Keywords (camelCase) in
 * `ctx.options`: M12 `variant`, `gain`, `camera`, `nInner`, `nStart`, `start`; M14 `mode`, `injected`, `known`, `camera`,
 * `modes`, `trialWaves`, `baseIterations`; M15 `charge`; M16 `atoms` (a TrapSet), `alpha`, `maxStepBins`, `nFix`.
 */
import { EmulatedCamera } from '../camera';
import type { Cx } from '../fft';
import { fftFocalField, pointTrapBackproject, pointTrapFields, pointTrapProjection, slmField, trapFieldsFromFft } from '../forward';
import { J_MAX, wavefrontWaves } from '../zernike';
import { TWO_PI, focalBinM, wrapPhase } from '../geometry';
import { efficiency, relStd, trapIntensities, uniformity } from '../metrics';
import { Trap, TrapSet } from '../traps';
import type { HistoryEntry, MethodModule, MethodRun, RunContext } from '../types';
import { Recorder, ampTargets, angle, fftBackproject, fftFields, mean, now, polar, requireKinds, startPhase, trapsOf } from './common';
import * as gs from './gs';

// ---- M12 ----

const VARIANTS = ['nogrette', 'kim'];

function* m12(ctx: RunContext): MethodRun {
  requireKinds(ctx.target, ['traps'], 'M12');
  const { setup, budget, rng, init, options: o } = ctx;
  const variant: string = o.variant ?? 'nogrette';
  const gain: number = o.gain ?? 0.7;
  const start: string = o.start ?? 'gsw';
  if (!VARIANTS.includes(variant)) throw new Error(`variant must be one of [${VARIANTS.map((v) => `'${v}'`).join(', ')}], got '${variant}'`);
  if (!(gain > 0 && gain <= 1)) throw new Error(`gain must be in (0, 1], got ${gain}`);
  if (start !== 'gsw' && start !== 'gs') throw new Error(`start must be 'gsw' or 'gs', got '${start}'`);
  const nInner: number = o.nInner ?? (variant === 'nogrette' ? 1 : 3);
  const nStart: number = o.nStart ?? 30;
  if (nInner < 1 || nStart < 1) throw new Error('n_inner and n_start must be >= 1');
  const traps = trapsOf(ctx.target);
  gs.checkOnBins(setup, traps);
  const camera: EmulatedCamera = o.camera ?? new EmulatedCamera(rng.nextU32(), { gainRms: 0.19, rolloff: false });
  const w = traps.weight, M = traps.length;
  const aBase = ampTargets(traps);
  const t0 = now();
  const wOf = (m: Float64Array): Float64Array => m.map((x, i) => x / w[i]);

  let phi = startPhase(setup, traps, rng, init);
  if (init === null) {
    const rule = start === 'gsw' ? gs.ruleGsw : gs.ruleGs;
    const state: gs.RuleState = { a: Float64Array.from(aBase), w: start === 'gsw' ? Float64Array.from(aBase) : new Float64Array(M).fill(1) };
    for (let k = 1; k <= nStart; k++) {
      const { v } = fftFields(phi, setup, traps);
      phi = angle(fftBackproject(rule(state, v, k), setup, traps));
      yield { iteration: k, efficiency: 0, uniformity: 0, relStd: 0, timeS: now() - t0, phase: 0 };
    }
  }
  let { e, v } = fftFields(phi, setup, traps);
  let meas = camera.measure(e, setup, traps);
  const openLoop = relStd(wOf(meas));
  let a = Float64Array.from(aBase);
  const history: HistoryEntry[] = [];
  for (let k = 1; k <= budget.iterations; k++) {
    const mw = wOf(meas);
    const mm = mean(mw);
    const rho = mw.map((x) => Math.max(x / mm, 1e-3));
    if (variant === 'nogrette') {
      a = a.map((ai, i) => ai * Math.sqrt(1 / (1 - gain * (1 - rho[i]))));
      const state: gs.RuleState = { a: Float64Array.from(a), w: new Float64Array(M).fill(1) };
      for (let j = 1; j <= nInner; j++) {
        ({ v } = fftFields(phi, setup, traps));
        phi = angle(fftBackproject(gs.ruleGs(state, v, j), setup, traps));
      }
    } else {
      a = a.map((ai, i) => ai / Math.sqrt(rho[i]));
      let g = new Float64Array(M).fill(1);
      let psi: Float64Array | null = null;
      for (let j = 1; j <= nInner; j++) {
        ({ v } = fftFields(phi, setup, traps));
        if (psi === null) psi = angle(v);
        else {
          const b = Float64Array.from(a, (ai, i) => Math.max(Math.hypot(v[2 * i], v[2 * i + 1]) / ai, 1e-300));
          const bm = mean(b);
          g = g.map((gi, i) => gi * (bm / b[i]));
        }
        phi = angle(fftBackproject(polar(g.map((gi, i) => gi * a[i]), psi), setup, traps));
      }
    }
    ({ e, v } = fftFields(phi, setup, traps));
    meas = camera.measure(e, setup, traps);
    const mw2 = wOf(meas);
    const entry: HistoryEntry = {
      iteration: k, efficiency: efficiency(trapIntensities(v)), uniformity: uniformity(mw2), relStd: relStd(mw2),
      timeS: now() - t0, relStdTrue: relStd(trapIntensities(v, w)),
    };
    history.push(entry);
    yield entry;
    if (budget.timeS !== null && entry.timeS >= budget.timeS) break;
  }
  return { phi, history, fields: v, meta: { method: 'M12', variant, gain, openLoopRelStd: openLoop, cameraSeed: camera.seed, nInner } };
}

// ---- M14 ----

const MODES = [4, 5, 6, 7, 8, 9, 10, 11];

function vector(c: ArrayLike<number> | null | undefined, name: string): Float64Array {
  const v = new Float64Array(J_MAX);
  if (c) {
    if (c.length > J_MAX) throw new Error(`${name}: at most ${J_MAX} coefficients (Noll j = 1..${J_MAX}), got ${c.length}`);
    for (let i = 0; i < c.length; i++) {
      if (!Number.isFinite(c[i])) throw new Error(`${name}: coefficients must be finite`);
      v[i] = c[i];
    }
  }
  return v;
}

function* m14(ctx: RunContext): MethodRun {
  requireKinds(ctx.target, ['traps'], 'M14');
  const { setup, budget, rng, init, options: o } = ctx;
  const mode: string = o.mode ?? 'recover';
  if (mode !== 'recover' && mode !== 'correct') throw new Error(`mode must be 'recover' or 'correct', got '${mode}'`);
  const modes: number[] = (o.modes ?? MODES).map(Number);
  if (!modes.length || modes.some((j) => j < 1 || j > J_MAX) || new Set(modes).size !== modes.length) {
    throw new Error(`modes must be distinct Noll indices in 1..${J_MAX}, got [${modes}]`);
  }
  const trial: number = o.trialWaves ?? 0.06;
  if (!(Number.isFinite(trial) && trial > 0)) throw new Error('trial_waves must be finite and positive');
  const inj = vector(o.injected, 'injected');
  if (mode === 'correct' && (o.known === undefined || o.known === null)) throw new Error("mode='correct' needs the known coefficients (known=...)");
  const traps = trapsOf(ctx.target);
  const n = setup.nPix;
  const t0 = now();
  const basisCache = new Map<number, Float64Array>();
  const basis = (j: number): Float64Array => {
    let b = basisCache.get(j);
    if (!b) {
      b = wavefrontWaves(Float64Array.from({ length: J_MAX }, (_, i) => (i === j - 1 ? 1 : 0)), setup);
      basisCache.set(j, b);
    }
    return b;
  };
  const combine = (c: Float64Array, js: number[]): Float64Array => {
    const w = new Float64Array(n * n);
    for (const j of js) {
      if (c[j - 1] === 0) continue;
      const b = basis(j);
      for (let q = 0; q < w.length; q++) w[q] += c[j - 1] * b[q];
    }
    return w;
  };
  const allJ = Array.from({ length: J_MAX }, (_, i) => i + 1);
  const wInj = combine(inj, allJ);

  let phiBase: Float64Array;
  if (init === null) {
    const base = yield* gs.runTraps('M06', setup, traps, { iterations: o.baseIterations ?? 30, timeS: null }, rng, null, 'point', gs.ruleGsw, {});
    phiBase = base.phi;
  } else phiBase = Float64Array.from(init);

  const focal = (cHat: Float64Array): Cx => {
    const wCorr = combine(cHat, modes);
    const ph = new Float64Array(n * n);
    for (let q = 0; q < ph.length; q++) ph[q] = phiBase[q] - TWO_PI * wCorr[q] + TWO_PI * wInj[q];
    return fftFocalField(ph, setup);
  };
  const trueV = (c: Float64Array): Cx => trapFieldsFromFft(focal(c), setup, traps);
  const zero = new Float64Array(J_MAX);
  const baseEff = efficiency(trapIntensities(trapFieldsFromFft(fftFocalField(phiBase, setup), setup, traps)));
  const uncorrectedEff = efficiency(trapIntensities(trueV(zero)));
  const rec = new Recorder(budget, traps.weight);

  if (mode === 'correct') {
    const kVec = vector(o.known, 'known');
    const wCorr = combine(kVec, allJ);
    const phi = new Float64Array(n * n);
    for (let q = 0; q < phi.length; q++) phi[q] = phiBase[q] - TWO_PI * wCorr[q];
    const wrapped = wrapPhase(phi);
    const ph2 = Float64Array.from(wrapped, (p, q) => p + TWO_PI * wInj[q]);
    const v = trapFieldsFromFft(fftFocalField(ph2, setup), setup, traps);
    yield rec.add(1, v);
    return { phi: wrapped, history: rec.history, fields: v, meta: { method: 'M14', mode, coefficients: kVec, baseEfficiency: baseEff, uncorrectedEfficiency: uncorrectedEff } };
  }

  const camera: EmulatedCamera = o.camera ?? new EmulatedCamera(rng.nextU32(), { gainRms: 0, rolloff: false });
  const merit = (c: Float64Array): number => {
    const m = camera.measure(focal(c), setup, traps);
    let s = 0;
    for (const x of m) s += x;
    return s;
  };
  const cHat = new Float64Array(J_MAX);
  let k = 0;
  let v: Cx;
  for (;;) {
    k++;
    let biggest = 0;
    for (const j of modes) {
      const y: number[] = [];
      for (const off of [-trial, 0, trial]) {
        const t = Float64Array.from(cHat);
        t[j - 1] += off;
        y.push(Math.log(Math.max(merit(t), 1e-300)));
      }
      const curv = y[0] - 2 * y[1] + y[2];
      let step: number;
      if (curv < 0) step = Math.min(Math.max((trial * (y[0] - y[2])) / (2 * curv), -2 * trial), 2 * trial);
      else step = [-trial, 0, trial][y.indexOf(Math.max(...y))];
      cHat[j - 1] += step;
      biggest = Math.max(biggest, Math.abs(step));
    }
    v = trueV(cHat);
    let err = 0;
    for (const j of modes) err += (cHat[j - 1] - inj[j - 1]) ** 2;
    yield rec.add(k, v, { coefRmsError: Math.sqrt(err) });
    if (rec.done(k) || biggest < 1e-4) break;
  }
  const wCorr = combine(cHat, modes);
  const phi = wrapPhase(Float64Array.from(phiBase, (p, q) => p - TWO_PI * wCorr[q]));
  return {
    phi, history: rec.history, fields: v,
    meta: { method: 'M14', mode, coefficients: cHat, baseEfficiency: baseEff, uncorrectedEfficiency: uncorrectedEff, sweeps: k, elapsedS: now() - t0 },
  };
}

// ---- M15 ----

const N_RING = 48;

function ringTraps(setup: RunContext['setup'], trap: Trap, radiusBins: number): TrapSet {
  const r = radiusBins * focalBinM(setup);
  return new TrapSet(Array.from({ length: N_RING }, (_, i) => {
    const t = (TWO_PI * i) / N_RING;
    return { id: i, xM: trap.xM + r * Math.cos(t), yM: trap.yM + r * Math.sin(t), zM: trap.zM };
  }));
}

const wrapPi = (x: number): number => Math.atan2(Math.sin(x), Math.cos(x));

export interface RingProfile {
  winding: number;
  sign: number;
  radiusBins: number;
  maxError: number;
  rmsError: number;
  ringIntensity: number;
}

/** Winding and line-fit error of the focal phase on a ring around `trap` (see the Python module docstring). */
export function ringPhaseProfile(phi: ArrayLike<number>, setup: RunContext['setup'], trap: Trap, radiusBins?: number): RingProfile {
  const field = slmField(phi, setup);
  const sample = (rad: number): Cx => pointTrapProjection(field, setup, ringTraps(setup, trap, rad));
  const meanInt = (v: Cx): number => {
    let s = 0;
    for (let i = 0; i < v.length / 2; i++) s += v[2 * i] ** 2 + v[2 * i + 1] ** 2;
    return s / (v.length / 2);
  };
  let rb = radiusBins;
  if (rb === undefined) {
    let best = -Infinity;
    for (let r = 0.5; r <= 5.0 + 1e-9; r += 0.25) {
      const m = meanInt(sample(r));
      if (m > best) {
        best = m;
        rb = r;
      }
    }
  }
  const radius = rb as number;
  const v = sample(radius);
  const ph = angle(v);
  let winding = 0;
  for (let i = 0; i < N_RING; i++) winding += wrapPi(ph[(i + 1) % N_RING] - ph[i]);
  const sign = winding >= 0 ? 1 : -1;
  const l = Math.abs(Math.round(winding / TWO_PI));
  const resid = Float64Array.from(ph, (p, i) => wrapPi(p - sign * l * ((TWO_PI * i) / N_RING)));
  let cr = 0, ci = 0;
  for (const r of resid) {
    cr += Math.cos(r);
    ci += Math.sin(r);
  }
  const c = Math.atan2(ci / N_RING, cr / N_RING);
  const err = resid.map((r) => Math.abs(wrapPi(r - c)));
  return {
    winding, sign, radiusBins: radius, maxError: Math.max(...err), rmsError: Math.sqrt(err.reduce((a, x) => a + x * x, 0) / N_RING),
    ringIntensity: meanInt(v),
  };
}

function* m15(ctx: RunContext): MethodRun {
  requireKinds(ctx.target, ['traps'], 'M15');
  const { setup, budget, rng, init, options: o } = ctx;
  let traps = trapsOf(ctx.target);
  const charge: number | null = o.charge ?? null;
  if (charge !== null) {
    if (!Number.isInteger(charge) || charge === 0) throw new Error(`charge must be a non-zero integer, got ${charge}`);
    traps = traps.map(() => ({ charge }));
  }
  if (!traps.charge.some((c) => c !== 0)) throw new Error('M15 needs at least one trap with a non-zero charge (Trap.charge or the charge keyword)');
  const res = yield* gs.runTraps('M15', setup, traps, budget, rng, init, 'point', gs.ruleGsw, {});
  res.meta.traps = traps;
  res.fields = pointTrapFields(res.phi, setup, traps);
  return res;
}

// ---- M16 ----

/** Minimum-cost assignment of every row to a distinct column (`n <= m`): the column of each row and the total cost. */
export function hungarian(cost: ArrayLike<number>, n: number, m: number): { cols: number[]; total: number } {
  if (n === 0 || n > m || cost.length !== n * m) throw new Error(`cost must be an n x m matrix with 1 <= n <= m, got shape (${n}, ${m})`);
  for (let i = 0; i < cost.length; i++) if (!Number.isFinite(cost[i])) throw new Error('cost must be finite');
  const a = (i: number, j: number): number => cost[(i - 1) * m + (j - 1)];
  const u = new Float64Array(n + 1), v = new Float64Array(m + 1);
  const p = new Int32Array(m + 1), way = new Int32Array(m + 1);
  for (let i = 1; i <= n; i++) {
    p[0] = i;
    let j0 = 0;
    const minv = new Float64Array(m + 1).fill(Infinity);
    const used = new Uint8Array(m + 1);
    for (;;) {
      used[j0] = 1;
      const i0 = p[j0];
      for (let j = 1; j <= m; j++) {
        if (used[j]) continue;
        const cur = a(i0, j) - u[i0] - v[j];
        if (cur < minv[j]) {
          minv[j] = cur;
          way[j] = j0;
        }
      }
      let j1 = 0, delta = Infinity;
      for (let j = 1; j <= m; j++) if (!used[j] && minv[j] < delta) { delta = minv[j]; j1 = j; }
      for (let j = 0; j <= m; j++) {
        if (used[j]) {
          u[p[j]] += delta;
          v[j] -= delta;
        } else if (j > 0) minv[j] -= delta;
      }
      j0 = j1;
      if (p[j0] === 0) break;
    }
    while (j0) {
      const j1 = way[j0];
      p[j0] = p[j1];
      j0 = j1;
    }
  }
  const cols = new Array<number>(n).fill(0);
  for (let j = 1; j <= m; j++) if (p[j]) cols[p[j] - 1] = j - 1;
  return { cols, total: cols.reduce((s, c, i) => s + a(i + 1, c + 1), 0) };
}

/** Atom index of every target by the Hungarian algorithm on the cost `d^alpha`. */
export function assign(targets: ArrayLike<[number, number]>, atoms: ArrayLike<[number, number]>, alpha = 1.5): number[] {
  if (!(Number.isFinite(alpha) && alpha > 0)) throw new Error(`alpha must be finite and positive, got ${alpha}`);
  const n = targets.length, m = atoms.length;
  const c = new Float64Array(n * m);
  for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) c[i * m + j] = Math.hypot(targets[i][0] - atoms[j][0], targets[i][1] - atoms[j][1]) ** alpha;
  return hungarian(c, n, m).cols;
}

const orient = (p: number[], q: number[], r: number[]): number => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);

function pathsCross(p1: number[], p2: number[], q1: number[], q2: number[], eps = 1e-9): boolean {
  const d1 = orient(q1, q2, p1), d2 = orient(q1, q2, p2), d3 = orient(p1, p2, q1), d4 = orient(p1, p2, q2);
  if (d1 * d2 < -eps && d3 * d4 < -eps) return true;
  if (Math.abs(d1) <= eps && Math.abs(d2) <= eps) {
    const axis = Math.abs(p2[0] - p1[0]) >= Math.abs(p2[1] - p1[1]) ? 0 : 1;
    const [a0, a1] = [p1[axis], p2[axis]].sort((x, y) => x - y);
    const [b0, b1] = [q1[axis], q2[axis]].sort((x, y) => x - y);
    return Math.min(a1, b1) - Math.max(a0, b0) > eps;
  }
  return false;
}

/** Number of pairs of straight paths `starts[i] -> ends[i]` that cross or overlap along a segment. */
export function countCrossings(starts: number[][], ends: number[][]): number {
  let c = 0;
  for (let i = 0; i < starts.length; i++) for (let j = i + 1; j < starts.length; j++) if (pathsCross(starts[i], ends[i], starts[j], ends[j])) c++;
  return c;
}

function* m16(ctx: RunContext): MethodRun {
  requireKinds(ctx.target, ['traps'], 'M16');
  const { setup, budget, rng, options: o } = ctx;
  const atoms: TrapSet | undefined = o.atoms;
  if (!atoms) throw new Error('M16 needs atoms: the TrapSet of the loaded atom positions');
  const tgt = trapsOf(ctx.target);
  const alpha: number = o.alpha ?? 1.5;
  const nFix: number = o.nFix ?? 12;
  if (atoms.length < tgt.length) throw new Error(`fewer atoms (${atoms.length}) than targets (${tgt.length}): the sort cannot fill every target`);
  const b = focalBinM(setup);
  const step: number = o.maxStepBins ?? setup.pad;
  if (!(Number.isFinite(step) && step > 0)) throw new Error(`max_step_bins must be finite and positive, got ${o.maxStepBins}`);
  const tXY: [number, number][] = Array.from(tgt.xM, (x, i) => [x / b, tgt.yM[i] / b]);
  const aXY: [number, number][] = Array.from(atoms.xM, (x, i) => [x / b, atoms.yM[i] / b]);
  const f = assign(tXY, aXY, alpha);
  const startXY = f.map((j) => aXY[j]), endXY = tXY;
  const crossings = countCrossings(startXY, endXY);
  const dist = startXY.map((s, i) => Math.hypot(endXY[i][0] - s[0], endXY[i][1] - s[1]));
  const nSteps = Math.max(1, Math.ceil(Math.max(...dist) / step));
  const moved = dist.map((d) => d > 1e-9);
  const make = (xy: number[][]): TrapSet => new TrapSet(tgt.traps.map((t, i) => ({ ...t, xM: xy[i][0] * b, yM: xy[i][1] * b, zM: 0 })));
  const tsStart = make(startXY), tsEnd = make(endXY);

  function* wgs(ts: TrapSet): Generator<HistoryEntry, ReturnType<typeof pointFields>> {
    let form: gs.Form = 'fft';
    try {
      gs.checkOnBins(setup, ts);
    } catch {
      form = 'point';
    }
    const r = yield* gs.runTraps('M07', setup, ts, budget, rng, null, form, gs.ruleWgsFixed, { nFix }, { nFix });
    return pointFields(r.fields);
  }
  const r0 = yield* wgs(tsStart);
  const r1 = yield* wgs(tsEnd);
  const dpsi = r1.psi.map((p, i) => wrapPi(p - r0.psi[i]));
  const rec = new Recorder(budget, tgt.weight);
  const frames: Float64Array[] = [], seq: TrapSet[] = [], vs: Cx[] = [];
  for (let s = 0; s <= nSteps; s++) {
    const w = s / nSteps;
    const xy = startXY.map((p, i) => [p[0] + w * (endXY[i][0] - p[0]), p[1] + w * (endXY[i][1] - p[1])]);
    const ts = make(xy);
    const c = polar(r0.amp.map((a0, i) => a0 + w * (r1.amp[i] - a0)), r0.psi.map((p0, i) => p0 + w * dpsi[i]));
    const phi = angle(pointTrapBackproject(c, setup, ts));
    const v = pointTrapFields(phi, setup, ts);
    yield rec.add(s + 1, v);
    frames.push(phi);
    seq.push(ts);
    vs.push(v);
  }
  const M = tgt.length;
  const minRatio = new Float64Array(M);
  for (let t = 0; t < M; t++) {
    const inten = vs.map((v) => v[2 * t] ** 2 + v[2 * t + 1] ** 2);
    minRatio[t] = Math.min(...inten) / Math.max(inten.reduce((a, x) => a + x, 0) / inten.length, 1e-300);
  }
  return {
    phi: frames[frames.length - 1], history: rec.history, fields: vs[vs.length - 1],
    meta: { method: 'M16', frames, nSteps, assignment: f, minRatio, moved, crossings, trapSequence: seq, alpha, maxStepBins: step },
  };
}

/** Amplitude and phase of interleaved complex trap fields. */
function pointFields(v: Cx): { amp: Float64Array; psi: Float64Array } {
  const n = v.length / 2;
  return { amp: Float64Array.from({ length: n }, (_, i) => Math.hypot(v[2 * i], v[2 * i + 1])), psi: angle(v) };
}

const S = (id: string, name: string, family: string, targets: readonly ('traps' | 'field')[], dims: readonly (2 | 3)[]) => ({ id, name, family, lane: 'live' as const, targets, dims });

export const controlMethods: MethodModule[] = [
  { spec: S('M12', 'Closed-loop weighted GS on an emulated camera', 'control', ['traps'], [2]), run: m12 },
  { spec: S('M14', 'Zernike correction and sensorless modal recovery', 'control', ['traps'], [2, 3]), run: m14 },
  { spec: S('M15', 'Laguerre-Gaussian vortex traps', 'GS', ['traps'], [2, 3]), run: m15 },
  { spec: S('M16', 'Hungarian assignment and linear phase interpolation', 'control', ['traps'], [2]), run: m16 },
];
