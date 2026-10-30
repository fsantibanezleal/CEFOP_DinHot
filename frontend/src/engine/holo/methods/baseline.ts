/**
 * Baseline methods M01 to M08 and M19 (the live lane).
 *
 * Python counterparts: `methods/baseline/m01_superposition.py` to `m08_mraf.py` and `m19_multiplane.py` (each docstring
 * there carries the update rule, the dossier section and the published figures). Keywords (camelCase) in `ctx.options`:
 * M04 `form`, `startWaves`; M05 `alpha`, `form`, `scale`; M06 `form`; M07 `nFix`, `form`; M08 `mixing`, `startWaves`;
 * M19 `dzM`, `nz`.
 */
import { type Cx, fft3 } from '../fft';
import { pointTrapBackproject, pointTrapFields } from '../forward';
import { TWO_PI, focalBinM, inputAmplitude, pmod, slmAxis, wrapPhase } from '../geometry';
import type { MethodModule, MethodRun, RunContext } from '../types';
import { TrapSet, rint } from '../traps';
import { Recorder, ampTargets, angle, requireKinds, srStart, toCx, trapsOf } from './common';
import * as gs from './gs';

function fieldTarget(ctx: RunContext): Extract<RunContext['target'], { kind: 'field' }> {
  if (ctx.target.kind !== 'field') throw new Error('this method needs a shaped-field target');
  return ctx.target;
}

// ---- M01 / M02 / M03 ----

function* m01(ctx: RunContext): MethodRun {
  requireKinds(ctx.target, ['traps'], 'M01');
  const { setup, budget } = ctx, traps = trapsOf(ctx.target);
  const rec = new Recorder(budget, traps.weight);
  const phi = angle(pointTrapBackproject(toCx(ampTargets(traps)), setup, traps));
  const v = pointTrapFields(phi, setup, traps);
  yield rec.add(1, v);
  return { phi, history: rec.history, fields: v, meta: { method: 'M01' } };
}

function* m02(ctx: RunContext): MethodRun {
  requireKinds(ctx.target, ['traps'], 'M02');
  const { setup, budget, rng } = ctx, traps = trapsOf(ctx.target);
  const rec = new Recorder(budget, traps.weight);
  const phi = srStart(setup, traps, rng);
  const v = pointTrapFields(phi, setup, traps);
  yield rec.add(1, v);
  return { phi, history: rec.history, fields: v, meta: { method: 'M02' } };
}

/** The random partition of the pixels, one trap per pixel with equal share (a share proportional to the weight otherwise). */
function owners(nPix: number, weights: Float64Array, rng: RunContext['rng']): Int32Array {
  const n = nPix * nPix;
  const keys = rng.uniformArray(n);
  const order = Array.from({ length: n }, (_, i) => i).sort((a, b) => keys[a] - keys[b]); // stable
  let total = 0;
  for (const w of weights) total += w;
  const edges = new Float64Array(weights.length);
  let c = 0;
  for (let i = 0; i < weights.length; i++) {
    c += weights[i];
    edges[i] = rint((c / total) * n);
  }
  edges[edges.length - 1] = n;
  const owner = new Int32Array(n);
  let t = 0;
  for (let rank = 0; rank < n; rank++) {
    while (t < edges.length && edges[t] <= rank) t++; // searchsorted(edges, rank, side='right')
    owner[order[rank]] = t;
  }
  return owner;
}

function* m03(ctx: RunContext): MethodRun {
  requireKinds(ctx.target, ['traps'], 'M03');
  const { setup, budget, rng } = ctx, traps = trapsOf(ctx.target);
  const rec = new Recorder(budget, traps.weight);
  const n = setup.nPix;
  const owner = owners(n, traps.weight, rng);
  const ax = slmAxis(setup);
  const kg = TWO_PI / (setup.wavelengthM * setup.focalM);
  const kl = (Math.PI) / (setup.wavelengthM * setup.focalM ** 2);
  const phi = new Float64Array(n * n);
  for (let q = 0; q < n * n; q++) {
    const k = owner[q];
    if (k >= traps.length) continue; // an empty tail share never occurs; guard for rounding
    const x = ax[q % n], y = ax[Math.floor(q / n)];
    const wr = (v: number): number => {
      const r = pmod(v, TWO_PI);
      return r >= TWO_PI ? 0 : r;
    };
    let d = wr(kg * (x * traps.xM[k] + y * traps.yM[k]));
    if (traps.zM[k] !== 0) d += wr(kl * traps.zM[k] * (x * x + y * y));
    if (traps.charge[k] !== 0) d += wr(traps.charge[k] * Math.atan2(y, x));
    phi[q] = d;
  }
  const out = wrapPhase(phi);
  const v = pointTrapFields(out, setup, traps);
  yield rec.add(1, v);
  return { phi: out, history: rec.history, fields: v, meta: { method: 'M03', owner } };
}

// ---- M04 to M08 ----

function* m04(ctx: RunContext): MethodRun {
  const { setup, target, budget, rng, init, options: o } = ctx;
  const form = gs.checkForm(o.form ?? (target.kind === 'field' ? 'fft' : 'point'));
  const startWaves = o.startWaves === undefined ? gs.START_WAVES : o.startWaves;
  if (target.kind === 'field') {
    if (form !== 'fft') throw new Error("a shaped-field target needs form='fft'");
    return yield* gs.runField('M04', setup, target, budget, rng, init, 1, startWaves);
  }
  return yield* gs.runTraps('M04', setup, target.traps, budget, rng, init, form, gs.ruleGs, {});
}

function* m05(ctx: RunContext): MethodRun {
  requireKinds(ctx.target, ['traps'], 'M05');
  const { setup, budget, rng, init, options: o } = ctx;
  const alpha = o.alpha ?? 0.5, scale = o.scale ?? 'mean';
  if (!(alpha >= 0 && alpha <= 1)) throw new Error(`alpha must be in [0, 1], got ${alpha}`);
  if (scale !== 'mean' && scale !== 'absolute') throw new Error(`scale must be 'mean' or 'absolute', got '${scale}'`);
  return yield* gs.runTraps('M05', setup, trapsOf(ctx.target), budget, rng, init, gs.checkForm(o.form ?? 'point'), gs.ruleGaa, { alpha, scale }, { alpha, scale });
}

function* m06(ctx: RunContext): MethodRun {
  requireKinds(ctx.target, ['traps'], 'M06');
  const { setup, budget, rng, init, options: o } = ctx;
  return yield* gs.runTraps('M06', setup, trapsOf(ctx.target), budget, rng, init, gs.checkForm(o.form ?? 'point'), gs.ruleGsw, {});
}

function* m07(ctx: RunContext): MethodRun {
  requireKinds(ctx.target, ['traps'], 'M07');
  const { setup, budget, rng, init, options: o } = ctx;
  const nFix = o.nFix ?? 12;
  if (!Number.isInteger(nFix) || nFix < 1) throw new Error(`n_fix must be a positive integer, got ${nFix}`);
  const res = yield* gs.runTraps('M07', setup, trapsOf(ctx.target), budget, rng, init, gs.checkForm(o.form ?? 'fft'), gs.ruleWgsFixed, { nFix });
  const st = res.meta.state as gs.RuleState;
  res.meta.nFix = nFix;
  res.meta.psi = st.psi ?? st.psiLast;
  return res;
}

function* m08(ctx: RunContext): MethodRun {
  requireKinds(ctx.target, ['field'], 'M08');
  const { setup, budget, rng, init, options: o } = ctx;
  return yield* gs.runField('M08', setup, fieldTarget(ctx), budget, rng, init, o.mixing ?? 0.3, o.startWaves === undefined ? gs.START_WAVES : o.startWaves);
}

// ---- M19 ----

const nextPow2 = (n: number): number => 1 << Math.max(0, (n - 1).toString(2).length * (n > 1 ? 1 : 0));

function plan19(setup: RunContext['setup'], traps: TrapSet, dzIn: number | null, nzIn: number | null) {
  const zsAll = Array.from(traps.zM, (z) => rint(z * 1e12) / 1e12);
  const zs = [...new Set(zsAll)].sort((a, b) => a - b);
  let dz = dzIn;
  if (dz === null) {
    if (zs.length < 2) throw new Error('a target on a single depth needs dz_m (the axial voxel pitch in metres)');
    dz = Infinity;
    for (let i = 1; i < zs.length; i++) dz = Math.min(dz, zs[i] - zs[i - 1]);
  }
  if (!(Number.isFinite(dz) && dz > 0)) throw new Error(`dz_m must be finite and positive, got ${dz}`);
  const iz = Array.from(traps.zM, (z) => rint(z / (dz as number)));
  const maxIz = Math.max(...iz.map(Math.abs));
  const nz = nzIn ?? nextPow2(Math.max(32, 8 * maxIz + 1));
  if (nz < 2 * maxIz + 1) throw new Error(`nz = ${nz} cannot hold the plane indices up to ${maxIz}`);
  const n = setup.nPix;
  const dx = setup.pad * focalBinM(setup);
  const ix = Array.from(traps.xM, (x) => rint(x / dx)), iy = Array.from(traps.yM, (y) => rint(y / dx));
  if (Math.max(...ix.map(Math.abs)) >= n / 2 || Math.max(...iy.map(Math.abs)) >= n / 2) throw new Error('a trap lies outside the lateral voxel grid');
  const keys = new Set(ix.map((x, i) => `${x},${iy[i]},${iz[i]}`));
  if (keys.size !== traps.length) throw new Error('two traps fall on the same voxel; use a finer target or a smaller dz_m');
  const snapped = new TrapSet(traps.traps.map((t, i) => ({ ...t, xM: ix[i] * dx, yM: iy[i] * dx, zM: iz[i] * (dz as number) })));
  return { ix, iy, iz, snapped, dz: dz as number, nz };
}

function sphereIndex(setup: RunContext['setup'], dz: number, nz: number): Int32Array {
  const n = setup.nPix, ax = slmAxis(setup);
  const lamM = setup.wavelengthM / setup.nImm;
  const out = new Int32Array(n * n);
  for (let iy = 0; iy < n; iy++) {
    for (let ix = 0; ix < n; ix++) {
      const s = ((lamM * Math.hypot(ax[ix], ax[iy])) / (setup.wavelengthM * setup.focalM)) ** 2;
      if (s >= 1) throw new Error('the SLM aperture exceeds the propagating cone');
      out[iy * n + ix] = pmod(rint((nz * dz * (1 - Math.sqrt(1 - s))) / lamM), nz);
    }
  }
  return out;
}

function* m19(ctx: RunContext): MethodRun {
  requireKinds(ctx.target, ['traps'], 'M19');
  const { setup, budget, rng, init, options: o } = ctx;
  const traps = trapsOf(ctx.target), n = setup.nPix;
  const { ix, iy, iz, snapped, dz, nz } = plan19(setup, traps, o.dzM ?? null, o.nz ?? null);
  const zsph = sphereIndex(setup, dz, nz);
  // ramp over FFT-order frequencies kk = rint(fftfreq(n) * n): puts the lateral origin on the optical axis
  const rr = new Float64Array(n), ri = new Float64Array(n);
  for (let j = 0; j < n; j++) {
    const kk = j < Math.floor((n - 1) / 2) + 1 ? j : j - n;
    const a = (TWO_PI * ((n - 1) / 2) * kk) / n;
    rr[j] = Math.cos(a);
    ri[j] = Math.sin(a);
  }
  const amp = inputAmplitude(setup);
  const aM = ampTargets(traps);
  const M = traps.length;
  const tz = iz.map((v) => pmod(v, nz)), ty = iy.map((v) => pmod(v, n)), tx = ix.map((v) => pmod(v, n));
  const rec = new Recorder(budget, snapped.weight);
  let phi: Float64Array;
  if (init === null) phi = srStart(setup, snapped, rng);
  else {
    if (init.length !== n * n || !init.every(Number.isFinite)) throw new Error(`init must be a finite array of shape (${n}, ${n})`);
    phi = Float64Array.from(init);
  }
  let v: Cx = new Float64Array(0);
  const rampAt = (y: number, x: number): [number, number] => [rr[y] * rr[x] - ri[y] * ri[x], rr[y] * ri[x] + ri[y] * rr[x]];
  const scale = 1 / Math.sqrt(nz * n * n);
  let k = 0;
  for (;;) {
    k++;
    const vol: Cx = new Float64Array(2 * nz * n * n);
    for (let q = 0; q < n * n; q++) {
      const at = 2 * (zsph[q] * n * n + q);
      vol[at] = amp[q] * Math.cos(phi[q]);
      vol[at + 1] = amp[q] * Math.sin(phi[q]);
    }
    fft3(vol, nz, n, n, false); // unscaled; the ortho factor is applied where the values are read
    const ut: Cx = new Float64Array(2 * nz * n * n);
    for (let m = 0; m < M; m++) {
      const at = 2 * (tz[m] * n * n + ty[m] * n + tx[m]);
      const [pr, pi] = rampAt(ty[m], tx[m]);
      const ur = (vol[at] * pr - vol[at + 1] * pi) * scale, ui = (vol[at] * pi + vol[at + 1] * pr) * scale;
      const a = Math.hypot(ur, ui);
      const f = a > 1e-300 ? aM[m] / Math.max(a, 1e-300) : 0;
      // the unit phasor is 1 where the field is zero
      const cr = a > 1e-300 ? ur * f : aM[m], ci = a > 1e-300 ? ui * f : 0;
      // divide by the ramp (multiply by its conjugate: |ramp| = 1)
      ut[at] = cr * pr + ci * pi;
      ut[at + 1] = ci * pr - cr * pi;
    }
    fft3(ut, nz, n, n, true); // numpy ifftn divides by the volume; ortho wants 1 / sqrt(volume)
    const vv = Math.sqrt(nz * n * n);
    for (let q = 0; q < n * n; q++) {
      const at = 2 * (zsph[q] * n * n + q);
      phi[q] = Math.atan2(ut[at + 1] * vv, ut[at] * vv);
    }
    v = pointTrapFields(phi, setup, snapped);
    yield rec.add(k, v);
    if (rec.done(k)) break;
  }
  return { phi, history: rec.history, fields: v, meta: { method: 'M19', snapped, dzM: dz, nz, iterations: k } };
}

const mods = (m: MethodModule['spec'], run: MethodModule['run']): MethodModule => ({ spec: m, run });
const S = (id: string, name: string, family: string, lane: 'live' | 'both', targets: readonly ('traps' | 'field')[], dims: readonly (2 | 3)[]) => ({ id, name, family, lane, targets, dims });

export const baselineMethods: MethodModule[] = [
  mods(S('M01', 'Superposition of prisms and lenses', 'analytic', 'live', ['traps'], [2, 3]), m01),
  mods(S('M02', 'Random superposition', 'analytic', 'live', ['traps'], [2, 3]), m02),
  mods(S('M03', 'Random mask', 'analytic', 'live', ['traps'], [2, 3]), m03),
  mods(S('M04', 'Gerchberg-Saxton', 'GS', 'live', ['traps', 'field'], [2, 3]), m04),
  mods(S('M05', 'Generalized adaptive additive GS', 'GS', 'live', ['traps'], [2, 3]), m05),
  mods(S('M06', 'Weighted GS', 'GS', 'live', ['traps'], [2, 3]), m06),
  mods(S('M07', 'Phase-fixed weighted GS', 'GS', 'live', ['traps'], [2]), m07),
  mods(S('M08', 'Mixed-region amplitude freedom', 'GS', 'live', ['field'], [2]), m08),
  mods(S('M19', 'Volumetric 3D GS (multi-plane)', 'GS', 'both', ['traps'], [3]), m19),
];

