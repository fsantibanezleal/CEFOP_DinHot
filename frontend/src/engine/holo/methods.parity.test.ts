// Parity of every live method with the Python engine, run on the same seeded inputs: the phase, the per-iteration history and
// the final fields are read from tests/fixtures/engine/methods.*.json and live.*.json (written by the Python methods).
import { describe, expect, it } from 'vitest';
import { EmulatedCamera } from './camera';
import { getMethod, liveMethodIds } from './methods';
import { assign, countCrossings, hungarian, ringPhaseProfile } from './methods/control';
import { Rng } from './rng';
import { NotLive, drain, makeBudget, type Result, type RunContext, type Target } from './types';
import { TrapSet } from './traps';
import { close, dec, deviceFrom, load, phaseClose, same, setupFrom, trapsFrom, type RefCase } from './parity.helpers';

const camel = (k: string): string => k.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
const HIST: Record<string, string> = { rel_std: 'relStd', rel_std_true: 'relStdTrue', coef_rms_error: 'coefRmsError' };

/** Build the run context of a reference case (the Python keywords become camelCase options). */
function ctxOf(c: RefCase): RunContext {
  const i = c.inputs;
  const target: Target = i.target.kind === 'traps'
    ? { kind: 'traps', traps: trapsFrom(i.target.traps) }
    : { kind: 'field', amplitude: dec(i.target.amplitude), mask: Uint8Array.from(dec(i.target.mask)) };
  const options: Record<string, any> = {};
  for (const [k, v] of Object.entries(i.options ?? {})) if (!(v === null && k === 'camera')) options[camel(k)] = v; // a null keyword is meaningful (start_waves=None)
  if (i.atoms) options.atoms = trapsFrom(i.atoms);
  if (i.camera) options.camera = new EmulatedCamera(i.camera.seed, { gainRms: i.camera.gain_rms, noiseRms: i.camera.noise_rms, rolloff: i.camera.rolloff });
  return {
    setup: setupFrom(i.setup), target, device: deviceFrom(i.device ?? null), budget: makeBudget(i.iterations), rng: new Rng(i.seed),
    init: i.init ? dec(i.init) : null, options,
  };
}

interface Tol { phi: number; abs: number; rel: number }

function compare(name: string, res: Result, out: Record<string, any>, tol: Tol): void {
  phaseClose(res.phi, dec(out.phi), tol.phi, `${name} phi`);
  const h = out.history as Record<string, number[]>;
  expect(res.history.length, `${name} history length`).toBe(h.iteration.length);
  same(res.history.map((e) => e.iteration), h.iteration, `${name} iteration`);
  for (const key of Object.keys(h)) {
    if (key === 'iteration') continue;
    const ts = HIST[key] ?? key;
    close(res.history.map((e) => e[ts]), h[key], tol, `${name} history.${key}`);
  }
  close(res.fields, dec(out.fields), tol, `${name} fields`);
}

const TOL: Record<string, Tol> = {
  // observed worst case over the GS family, M01-M08, M19, M12, M14, M16 and the 256 x 256 grid: 7e-14 rad (phase), 2e-13 (history, fields);
  // 1e-9 rad / 1e-10 leaves four orders of margin for another libm or V8 version without hiding a real difference
  default: { phi: 1e-9, abs: 1e-10, rel: 1e-9 },
  // M10, M11 (Wolfe line search, Adam: a first-order iterate follows the gradient): observed worst case 1e-11 rad (live M11)
  gradient: { phi: 1e-8, abs: 1e-9, rel: 1e-8 },
};

function runDoc(fn: string, tol: Tol = TOL.default, perCase?: (c: RefCase, res: Result, k: number) => void): void {
  const doc = load(fn);
  doc.cases.forEach((c, k) => {
    it(`${fn} case ${k}: ${c.inputs.method} ${JSON.stringify(c.inputs.options ?? {}).slice(0, 80)}`, () => {
      const ctx = ctxOf(c);
      const res = drain(getMethod(c.inputs.method).run(ctx));
      compare(`${fn}#${k}`, res, c.outputs, tol);
      perCase?.(c, res, k);
    });
  });
}

describe('baseline methods', () => {
  for (const id of ['M01', 'M02', 'M03', 'M04', 'M05', 'M06', 'M07', 'M08']) describe(id, () => runDoc(`methods.${id}`));
  describe('M19', () => runDoc('methods.M19', TOL.default, (c, res) => {
    const snapped = trapsFrom(c.outputs.snapped);
    close((res.meta.snapped as TrapSet).xM, snapped.xM, { abs: 1e-12, rel: 1e-12 }, 'M19 snapped x');
    close((res.meta.snapped as TrapSet).zM, snapped.zM, { abs: 1e-12, rel: 1e-12 }, 'M19 snapped z');
    expect(res.meta.nz).toBe(c.outputs.nz);
  }));
});

describe('optimization methods (CG with strong-Wolfe line search, Adam)', () => {
  // A first-order optimizer follows the gradient: float64 differences of 1e-16 in the cost reach the iterate through the line search,
  // so its tolerance is looser than the GS family's (observed worst case in the T1 report).
  describe('M10', () => runDoc('methods.M10', TOL.gradient));
  describe('M11', () => runDoc('methods.M11', TOL.gradient));
});

describe('control methods', () => {
  describe('M12 closed loop on the emulated camera', () => runDoc('methods.M12', TOL.default));
  describe('M14 Zernike', () => {
    const doc = load('methods.M14');
    doc.cases.forEach((c, k) => {
      it(`M14 case ${k} (${c.inputs.options.mode ?? 'recover'})`, () => {
        const res = drain(getMethod('M14').run(ctxOf(c)));
        const tol = TOL.default;
        compare(`M14#${k}`, res, c.outputs, tol);
        close(res.meta.coefficients as Float64Array, dec(c.outputs.coefficients), { abs: 1e-9, rel: 1e-9 }, 'M14 coefficients');
        close([res.meta.baseEfficiency as number, res.meta.uncorrectedEfficiency as number], [c.outputs.base_efficiency, c.outputs.uncorrected_efficiency], tol, 'M14 efficiencies');
      });
    });
  });
  describe('M15 vortex traps', () => runDoc('methods.M15', TOL.default, (c, res) => {
    if (!c.outputs.ring_profile) return;
    const p = ringPhaseProfile(res.phi, ctxOf(c).setup, (res.meta.traps as TrapSet).traps[c.inputs.ring.trap]);
    const r = c.outputs.ring_profile;
    close([p.winding, p.sign, p.radiusBins, p.maxError, p.rmsError, p.ringIntensity], [r.winding, r.sign, r.radius_bins, r.max_error, r.rms_error, r.ring_intensity], { abs: 1e-8, rel: 1e-8 }, 'ring profile');
  }));
  describe('M16 rearrangement', () => {
    const doc = load('methods.M16');
    doc.cases.forEach((c, k) => {
      it(`M16 case ${k}`, () => {
        const ctx = ctxOf(c);
        const res = drain(getMethod('M16').run(ctx));
        compare(`M16#${k}`, res, c.outputs, TOL.default);
        expect(res.meta.nSteps).toBe(c.outputs.n_steps);
        same(res.meta.assignment as number[], c.outputs.assignment, 'assignment');
        expect(res.meta.crossings).toBe(c.outputs.crossings);
        same((res.meta.moved as boolean[]).map(Number), (c.outputs.moved as boolean[]).map(Number), 'moved');
        close(res.meta.minRatio as Float64Array, dec(c.outputs.min_ratio), { abs: 1e-7, rel: 1e-7 }, 'min_ratio');
        const frames = res.meta.frames as Float64Array[];
        phaseClose(frames.flatMap((f) => Array.from(f)), dec(c.outputs.frames), 1e-6, 'frames');
      });
    });
  });
  it('Hungarian assignment and crossings agree with Python', () => {
    const doc = load('methods.assignment');
    for (const c of doc.cases) {
      if (c.inputs.cost) {
        const [n, m] = c.inputs.cost.shape;
        const r = hungarian(dec(c.inputs.cost), n, m);
        same(r.cols, c.outputs.cols, 'cols');
        close([r.total], [c.outputs.total], { abs: 1e-12, rel: 1e-12 }, 'total');
      } else {
        const t = dec(c.inputs.targets), a = dec(c.inputs.atoms);
        const pts = (v: Float64Array): [number, number][] => Array.from({ length: v.length / 2 }, (_, i) => [v[2 * i], v[2 * i + 1]]);
        same(assign(pts(t), pts(a), c.inputs.alpha), c.outputs.assign, 'assign');
        expect(countCrossings(pts(a).slice(0, 6), pts(t))).toBe(c.outputs.crossings);
      }
    }
  });
});

describe('live grid: 256 x 256 padded 2, 30 iterations (the lane budget grid)', () => {
  for (const id of ['M07', 'M06', 'M04']) describe(id, () => runDoc(`live.${id}`, { phi: 1e-6, abs: 1e-9, rel: 1e-8 }));
  describe('M11', () => runDoc('live.M11', TOL.gradient));
});

describe('the registry', () => {
  it('lists exactly the methods whose Python lane is live or both', () => {
    expect(liveMethodIds()).toEqual(['M01', 'M02', 'M03', 'M04', 'M05', 'M06', 'M07', 'M08', 'M10', 'M11', 'M12', 'M14', 'M15', 'M16', 'M19']);
  });
  it('raises NotLive (never a silent fallback) for a baked-only or unknown method', () => {
    for (const id of ['M09', 'M13', 'M18', 'B1', 'B2', 'B3', 'B4', 'B5', 'M99']) expect(() => getMethod(id)).toThrow(NotLive);
    try { getMethod('M09'); } catch (e) { expect((e as NotLive).method).toBe('M09'); expect((e as Error).message).toContain('replayed from the bake'); }
  });
  it('an out-of-field trap raises the Python error through the method', () => {
    const doc = load('traps.generators');
    const bad = doc.cases.find((c) => c.inputs.generator === 'check_in_field')!;
    const ctx: RunContext = {
      setup: setupFrom(bad.inputs.setup), target: { kind: 'traps', traps: trapsFrom(bad.inputs.traps) }, device: null, budget: makeBudget(2), rng: new Rng(1), init: null, options: {},
    };
    expect(() => drain(getMethod('M06').run(ctx))).toThrow(bad.outputs.error.message);
  });
  it('a wrong target kind names the supported kinds like Python', () => {
    const c = load('methods.M08').cases[0];
    const ctx = ctxOf(c);
    expect(() => drain(getMethod('M01').run(ctx))).toThrow("M01 supports the target kinds ['traps'], got 'field'");
  });
});
