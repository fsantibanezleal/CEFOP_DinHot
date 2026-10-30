// Parity of the engine core (RNG, geometry, traps, forward models, metrics) with the Python engine: every expected value is read
// from tests/fixtures/engine/*.json, written by data-pipeline/pipeline/stages/engine_reference.py (catalog row engine-reference).
import { describe, expect, it } from 'vitest';
import { angularSpectrum, axialCut, fftFocalField, fftInverse, pointTrapBackproject, pointTrapFields, trapBins, trapFieldsFromFft } from './forward';
import { binToUm, focalBinM, halfFieldM, inputAmplitude, nFft, umToBin, wrapPhase } from './geometry';
import { efficiency, ghostFraction, powerBudget, relStd, trapIntensities, uniformity, zeroOrderFraction } from './metrics';
import { Rng } from './rng';
import { OutOfFieldError, checkInField, hexLattice, lattice3d, randomMinSpacing, ring, snapToBins, squareGrid } from './traps';
import { close, dec, load, same, setupFrom, trapsFrom } from './parity.helpers';
import { readFileSync } from 'node:fs';

describe('rng: bit exact with Python', () => {
  const doc = load('rng.stream');
  doc.cases.forEach((c, k) => {
    it(`seed ${c.inputs.seed}`, () => {
      const r = new Rng(c.inputs.seed);
      same(Array.from({ length: c.outputs.u32.length }, () => r.nextU32()), c.outputs.u32, 'u32');
      const u = new Rng(c.inputs.seed);
      const uni = Array.from({ length: c.outputs.uniform.length }, () => u.uniform());
      same(uni, c.outputs.uniform, `uniform ${k}`); // exact: top 24 bits over 2^24
      const n = new Rng(c.inputs.seed);
      close(Array.from({ length: c.outputs.normal.length }, () => n.normal()), c.outputs.normal, doc.tolerance, 'normal');
      close(new Rng(c.inputs.seed).phases(c.outputs.phases.length), c.outputs.phases, doc.tolerance, 'phases');
    });
  });
  it('reproduces the committed rng-reference.json stream', () => {
    const ref = JSON.parse(readFileSync(new URL('../../../../tests/fixtures/rng-reference.json', import.meta.url), 'utf8'));
    const r = new Rng(ref.seed);
    same(Array.from({ length: ref.u32.length }, () => r.nextU32()), ref.u32, 'u32');
  });
  it('rejects a seed out of range', () => {
    expect(() => new Rng(-1)).toThrow('seed must be an integer in [0, 2^32)');
    expect(() => new Rng(2 ** 32)).toThrow();
    expect(() => new Rng(1.5)).toThrow();
  });
});

describe('geometry', () => {
  const doc = load('geometry.setup_functions');
  doc.cases.forEach((c, k) => {
    if (c.inputs.setup) {
      it(`setup ${k}`, () => {
        const s = setupFrom(c.inputs.setup);
        close(inputAmplitude(s), dec(c.outputs.input_amplitude), doc.tolerance, 'input_amplitude');
        close([focalBinM(s)], [c.outputs.focal_bin_m], doc.tolerance, 'focal_bin_m');
        close([halfFieldM(s)], [c.outputs.half_field_m], doc.tolerance, 'half_field_m');
        expect(nFft(s)).toBe(c.outputs.n_fft);
        close(c.inputs.um.map((v: number) => umToBin(s, v)), c.outputs.um_to_bin, doc.tolerance, 'um_to_bin');
        close(c.inputs.bins.map((v: number) => binToUm(s, v)), c.outputs.bin_to_um, doc.tolerance, 'bin_to_um');
      });
    } else {
      it('wrapPhase', () => {
        close(wrapPhase(c.inputs.values), c.outputs.wrap_phase, doc.tolerance, 'wrap_phase');
      });
    }
  });
});

describe('traps', () => {
  const doc = load('traps.generators');
  const arrays = (t: ReturnType<typeof trapsFrom>) => ({ x: t.xM, y: t.yM, z: t.zM });
  doc.cases.forEach((c) => {
    const g = c.inputs.generator as string;
    it(g, () => {
      if (g === 'check_in_field') {
        const s = setupFrom(c.inputs.setup);
        let err: unknown = null;
        try { checkInField(s, trapsFrom(c.inputs.traps)); } catch (e) { err = e; }
        expect(err).toBeInstanceOf(OutOfFieldError);
        const e = err as OutOfFieldError, ref = c.outputs.error;
        expect(e.message).toBe(ref.message); // the same message, so the same message key in the workbench
        expect([e.trapId, e.axis]).toEqual([ref.trap_id, ref.axis]);
        close([e.boundM, e.valueM], [ref.bound_m, ref.value_m], doc.tolerance, 'bound/value');
        return;
      }
      const a = c.inputs.args;
      const out = c.outputs.traps;
      const t =
        g === 'square_grid' ? squareGrid(a.nx, a.ny, a.spacing_um)
          : g === 'hex_lattice' ? hexLattice(a.n, a.spacing_um)
            : g === 'ring' ? ring(a.n, a.radius_um)
              : g === 'lattice_3d' ? lattice3d(a.nx, a.ny, a.nz, a.spacing_um, a.dz_um)
                : g === 'random_min_spacing' ? randomMinSpacing(a.n, a.extent_um, a.min_spacing_um, new Rng(a.seed))
                  : snapToBins(setupFrom(c.inputs.setup), trapsFrom(c.inputs.traps));
      same(Array.from(t.ids), out.ids, `${g} ids`);
      close(arrays(t).x, out.x_m, doc.tolerance, `${g} x`);
      close(arrays(t).y, out.y_m, doc.tolerance, `${g} y`);
      close(arrays(t).z, out.z_m, doc.tolerance, `${g} z`);
    });
  });
});

describe('forward models', () => {
  it('point_trap_fields (plain, z, vortex, 64 flat)', () => {
    const doc = load('forward.point_trap_fields');
    for (const c of doc.cases) {
      const v = pointTrapFields(dec(c.inputs.phi), setupFrom(c.inputs.setup), trapsFrom(c.inputs.traps));
      close(v, dec(c.outputs.v), doc.tolerance, 'V_m');
    }
  });
  it('point_trap_backproject', () => {
    const doc = load('forward.point_trap_backproject');
    for (const c of doc.cases) {
      const f = pointTrapBackproject(dec(c.inputs.coeffs), setupFrom(c.inputs.setup), trapsFrom(c.inputs.traps));
      close(f, dec(c.outputs.field), doc.tolerance, 'F_j');
    }
  });
  it('fft_focal_field (orthonormal, Parseval, pad 2 and 3)', () => {
    const doc = load('forward.fft_focal_field');
    for (const c of doc.cases) {
      const s = setupFrom(c.inputs.setup);
      const e = fftFocalField(dec(c.inputs.phi), s);
      close(e, dec(c.outputs.e), doc.tolerance, 'E');
      let p = 0;
      for (let i = 0; i < e.length; i += 2) p += e[i] ** 2 + e[i + 1] ** 2;
      close([p], [c.outputs.parseval], { abs: 1e-9, rel: 1e-12 }, 'Parseval');
      expect(Math.abs(p - s.nPix ** 2)).toBeLessThan(1e-9 * s.nPix ** 2);
    }
  });
  it('fft_inverse', () => {
    const doc = load('forward.fft_inverse');
    for (const c of doc.cases) close(fftInverse(dec(c.inputs.e), setupFrom(c.inputs.setup)), dec(c.outputs.field), doc.tolerance, 'f_j');
  });
  it('trap_bins and trap_fields_from_fft', () => {
    const doc = load('forward.trap_fields_from_fft');
    for (const c of doc.cases) {
      const s = setupFrom(c.inputs.setup), t = trapsFrom(c.inputs.traps);
      const b = trapBins(s, t);
      same(Array.from(b.iy), c.outputs.bins[0], 'iy');
      same(Array.from(b.ix), c.outputs.bins[1], 'ix');
      close(trapFieldsFromFft(dec(c.inputs.e), s, t), dec(c.outputs.v), doc.tolerance, 'V_m');
    }
  });
  it('angular_spectrum', () => {
    const doc = load('forward.angular_spectrum');
    for (const c of doc.cases) close(angularSpectrum(dec(c.inputs.e), c.inputs.dz_m, setupFrom(c.inputs.setup)), dec(c.outputs.e), doc.tolerance, 'E(z)');
  });
  it('axial_cut (xz and yz planes)', () => {
    const doc = load('forward.axial_cut');
    for (const c of doc.cases) {
      const s = setupFrom(c.inputs.setup);
      const cut = axialCut(dec(c.inputs.phi), s, { xM: c.inputs.kw.x_m ?? null, yM: c.inputs.kw.y_m ?? null, zRangeM: c.inputs.z_range_m, nz: c.inputs.nz });
      close(cut.intensity, dec(c.outputs.intensity), doc.tolerance, 'intensity');
      close(cut.zM, dec(c.outputs.z_m), doc.tolerance, 'z');
      close(cut.lateralM, dec(c.outputs.lateral_m), doc.tolerance, 'lateral');
    }
  });
});

describe('metrics', () => {
  it('trap_metrics', () => {
    const doc = load('metrics.trap_metrics');
    for (const c of doc.cases) {
      const v = dec(c.inputs.v), w = c.inputs.weights;
      const raw = trapIntensities(v), rel = trapIntensities(v, w ?? undefined);
      close(raw, dec(c.outputs.intensities), doc.tolerance, 'I_m');
      close(rel, dec(c.outputs.weighted), doc.tolerance, 'I_m/w');
      close([efficiency(raw), uniformity(rel), relStd(rel)], [c.outputs.efficiency, c.outputs.uniformity, c.outputs.rel_std], doc.tolerance, 'e, u, sigma');
    }
  });
  it('power_budget, zero order, ghosts', () => {
    const doc = load('metrics.power_budget');
    for (const c of doc.cases) {
      const s = setupFrom(c.inputs.setup), t = trapsFrom(c.inputs.traps), e = dec(c.inputs.e);
      close([zeroOrderFraction(e, s)], [c.outputs.zero_order], doc.tolerance, 'zero order');
      for (const [key, got] of [['budget', powerBudget(e, s, t)], ['budget_r3', powerBudget(e, s, t, c.inputs.radius_bins)]] as const) {
        const ref = c.outputs[key];
        close([got.traps, got.zeroOrder, got.ghosts, got.remainder], [ref.traps, ref.zero_order, ref.ghosts, ref.remainder], doc.tolerance, key);
      }
      close([ghostFraction(e, s, t, c.inputs.radius_bins)], [c.outputs.ghost_r3], doc.tolerance, 'ghost');
    }
  });
  it('rejects undefined metrics like Python', () => {
    expect(() => uniformity([0, 0])).toThrow('uniformity is undefined when all intensities are zero');
    expect(() => relStd([0, 0])).toThrow('relative standard deviation is undefined when the mean intensity is zero');
  });
});
