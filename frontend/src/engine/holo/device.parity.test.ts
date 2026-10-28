// Parity of the device model, Zernike modes, elementary phases, emulated camera, trap physics and particle dynamics with the Python
// engine (reference values: tests/fixtures/engine/*.json written by pipeline/stages/engine_reference.py).
import { describe, expect, it } from 'vitest';
import { EmulatedCamera } from './camera';
import { crosstalk, crosstalkAdjoint, crosstalkKernel, deviceFocalField, displayedPhase, pixelEnvelope, quantize } from './device';
import { atomParams, atomTrajectory, beadParams, beadTrajectory, boltzmannCheck, fitLorentzian, psd } from './dynamics';
import { fftFocalField } from './forward';
import { gratingPhase, lensPhase, vortexPhase } from './modes';
import { Rng } from './rng';
import * as tp from './trapphys';
import { J_MAX, nollToNm, phaseFromCoeffs, rmsWaves, strehl, wavefrontWaves, zernikeName } from './zernike';
import { close, dec, deviceFrom, load, phaseClose, same, setupFrom, trapsFrom } from './parity.helpers';

describe('device model', () => {
  it('quantize: levels exact, phase to 1e-12', () => {
    const doc = load('device.quantize');
    for (const c of doc.cases) {
      const q = quantize(dec(c.inputs.phi), c.inputs.bit_depth);
      const levels = Array.from(q, (v) => Math.round((v / (2 * Math.PI)) * 2 ** c.inputs.bit_depth) % 2 ** c.inputs.bit_depth);
      same(levels, c.outputs.levels, 'levels');
      close(q, dec(c.outputs.phase), { abs: 1e-12, rel: 1e-12 }, 'quantized phase');
    }
  });
  it('displayed_phase: LUT, flicker through the portable RNG', () => {
    const doc = load('device.displayed_phase');
    for (const c of doc.cases) {
      const d = deviceFrom(c.inputs.device)!;
      const p = displayedPhase(dec(c.inputs.phi), d, c.inputs.seed === null ? null : new Rng(c.inputs.seed));
      phaseClose(p, dec(c.outputs.phase), 1e-9, 'displayed phase');
      close(p, dec(c.outputs.phase), { abs: 1e-9, rel: 0 }, 'displayed phase (plain)');
    }
  });
  it('flicker without an rng is refused (no hidden randomness)', () => {
    expect(() => displayedPhase(new Float64Array(4), deviceFrom({ bit_depth: null, crosstalk: null, upsample: 3, fill_factor: 1, flicker_rad: 0.1, lut_gamma: 1 })!, null)).toThrow('an rng is required');
  });
  it('crosstalk (upsample and blur, circular) and its adjoint', () => {
    const doc = load('device.crosstalk');
    for (const c of doc.cases) close(crosstalk(dec(c.inputs.phi), deviceFrom(c.inputs.device)!), dec(c.outputs.upsampled), doc.tolerance, 'crosstalk');
    const adj = load('device.crosstalk_adjoint');
    for (const c of adj.cases) {
      const d = deviceFrom(c.inputs.device)!, g = dec(c.inputs.g);
      const a = crosstalkAdjoint(g, d);
      close(a, dec(c.outputs.adjoint), adj.tolerance, 'adjoint');
      // the defining identity <crosstalk(phi), g> = <phi, adjoint(g)> checked on the reference phase
      const phi = dec(load('device.crosstalk').cases[adj.cases.indexOf(c)].inputs.phi);
      let lhs = 0, rhs = 0;
      const x = crosstalk(phi, d);
      for (let i = 0; i < x.length; i++) lhs += x[i] * g[i];
      for (let i = 0; i < phi.length; i++) rhs += phi[i] * a[i];
      close([lhs, rhs], [c.outputs.inner_lhs, c.outputs.inner_rhs], { abs: 1e-9, rel: 1e-12 }, 'adjoint identity vs reference');
      expect(Math.abs(lhs - rhs)).toBeLessThan(1e-9 * Math.max(1, Math.abs(lhs)));
    }
  });
  it('pixel envelope and crosstalk kernel', () => {
    const doc = load('device.pixel_envelope');
    for (const c of doc.cases) {
      if (c.inputs.kernel) {
        const k = c.inputs.kernel;
        close(crosstalkKernel(k.n_up, k.sigma, k.q, k.upsample), dec(c.outputs.kernel), doc.tolerance, 'kernel');
      } else close(pixelEnvelope(setupFrom(c.inputs.setup), deviceFrom(c.inputs.device)!), dec(c.outputs.envelope), doc.tolerance, 'envelope');
    }
  });
  it('device_focal_field: envelope path and the pruned upsampled path (non power-of-two FFT)', () => {
    const doc = load('device.device_focal_field');
    for (const c of doc.cases) {
      const e = deviceFocalField(dec(c.inputs.phi), setupFrom(c.inputs.setup), deviceFrom(c.inputs.device)!, new Rng(c.inputs.seed));
      close(e, dec(c.outputs.e), doc.tolerance, 'device focal field');
    }
  });
});

describe('zernike and elementary modes', () => {
  it('Noll indices and names', () => {
    const doc = load('zernike.noll_to_nm');
    const c = doc.cases[0];
    expect(c.inputs.j.map((j: number) => nollToNm(j))).toEqual(c.outputs.nm);
    expect(c.inputs.j.map((j: number) => zernikeName(j))).toEqual(c.outputs.names);
    expect(() => nollToNm(0)).toThrow('Noll index must be an integer in 1..21');
    expect(() => nollToNm(22)).toThrow();
    expect(J_MAX).toBe(21);
  });
  it('wavefront, phase, rms and Strehl', () => {
    const doc = load('zernike.wavefront');
    for (const c of doc.cases) {
      const s = setupFrom(c.inputs.setup);
      close(wavefrontWaves(c.inputs.coeffs, s), dec(c.outputs.waves), doc.tolerance, 'wavefront');
      close(phaseFromCoeffs(c.inputs.coeffs, s), dec(c.outputs.phase), doc.tolerance, 'phase');
      if (c.outputs.rms !== undefined) close([rmsWaves(c.inputs.coeffs), rmsWaves(c.inputs.coeffs, true), strehl(c.inputs.coeffs)], [c.outputs.rms, c.outputs.rms_piston, c.outputs.strehl], doc.tolerance, 'rms/strehl');
    }
  });
  it('vortex, lens and grating phases', () => {
    const doc = load('modes.phases');
    const c = doc.cases[0], s = setupFrom(c.inputs.setup);
    close(vortexPhase(s, c.inputs.charge, c.inputs.centre), dec(c.outputs.vortex), doc.tolerance, 'vortex');
    close(lensPhase(s, c.inputs.z_m), dec(c.outputs.lens), doc.tolerance, 'lens');
    close(gratingPhase(s, c.inputs.x_m, c.inputs.y_m), dec(c.outputs.grating), doc.tolerance, 'grating');
  });
});

describe('emulated camera', () => {
  it('gain per trap id, noise frames, blur, roll-off', () => {
    const doc = load('camera.measure');
    for (const c of doc.cases) {
      const k = c.inputs.camera;
      const cam = new EmulatedCamera(c.inputs.seed, { gainRms: k.gain_rms, noiseRms: k.noise_rms, blurBins: k.blur_bins, rolloff: k.rolloff, fillFactor: k.fill_factor });
      close([0, 1, 2, 3, 4].map((i) => cam.gain(i)), c.outputs.gains, doc.tolerance, 'gains');
      const s = setupFrom(c.inputs.setup), t = trapsFrom(c.inputs.traps), e = dec(c.inputs.e);
      const frames = [0, 1, 2].flatMap(() => Array.from(cam.measure(e, s, t)));
      close(frames, dec(c.outputs.frames), doc.tolerance, 'frames');
    }
  });
});

describe('trap physics', () => {
  it('Rayleigh bead and dipole trap formulas', () => {
    const doc = load('trapphys.formulas');
    const c = doc.cases[0], i = c.inputs, o = c.outputs;
    const a = tp.rayleighPolarizabilityFm2(i.radius_m, i.n_particle, i.n_medium);
    const [kxx, kyy] = tp.stiffnessMap(dec(i.map), 21, 21, i.spacing_m, i.scale, a);
    const depth = tp.dipoleTrapDepthJ(i.power_w, i.waist_m, i.omega0, i.gamma, i.delta);
    const t = { abs: 0, rel: 1e-12 };
    close([a, tp.gaussianPeakIntensityWPerM2(i.power_w, i.waist_m), tp.gaussianStiffnessNPerM(a, 1e10, i.waist_m), tp.gradientStiffnessNPerM(a, 1e12),
      tp.rayleighRangeM(i.waist_m, i.wavelength_m), tp.dipolePotentialJ(1e10, i.omega0, i.gamma, i.delta), tp.scatteringRatePerS(1e10, i.omega0, i.gamma, i.delta), depth],
    [o.alpha, o.i0, o.kappa_gauss, o.kappa, o.z_rayleigh, o.u_dip, o.gamma_sc, o.depth], t, 'formulas');
    close(kxx, dec(o.k_map_xx), t, 'k_xx');
    close(kyy, dec(o.k_map_yy), t, 'k_yy');
    close(tp.trapFrequenciesRadS(depth, i.mass_kg, i.waist_m, i.wavelength_m), o.freqs, t, 'trap frequencies');
    expect(() => tp.dipoleTrapDepthJ(i.power_w, i.waist_m, i.omega0, i.gamma, -i.delta)).toThrow('repulsive');
  });
});

describe('particle dynamics', () => {
  const traj = load('dynamics.trajectories').cases[0];
  const t = load('dynamics.trajectories').tolerance;
  const ax = dec(traj.inputs.axis_m), map = dec(traj.inputs.map);
  it('overdamped bead (Euler-Maruyama) follows the portable stream', () => {
    const b = traj.inputs.bead;
    const pos = beadTrajectory(map, ax, ax, beadParams({ depthJ: b.depth_J, gammaNsPerM: b.gamma, temperatureK: b.T, startM: b.start_m }), traj.inputs.n_steps, traj.inputs.dt_bead, new Rng(traj.inputs.seed_bead));
    close(pos, dec(traj.outputs.bead), t, 'bead trajectory');
  });
  it('underdamped atom (velocity Verlet with kicks)', () => {
    const a = traj.inputs.atom;
    const r = atomTrajectory(map, ax, ax, atomParams({ depthJ: a.depth_J, massKg: a.mass_kg, temperatureK: a.T, kickMPerS: a.kick, startM: a.start_m }), traj.inputs.n_steps, traj.inputs.dt_atom, new Rng(traj.inputs.seed_atom));
    close(r.pos, dec(traj.outputs.atom_pos), t, 'atom positions');
    close(r.vel, dec(traj.outputs.atom_vel), { abs: 1e-9, rel: 1e-9 }, 'atom velocities');
  });
  it('PSD and Lorentzian fit', () => {
    const doc = load('dynamics.psd_fit');
    const c = doc.cases[0];
    const { f, p } = psd(dec(c.inputs.x), c.inputs.dt, c.inputs.segments);
    close(f, dec(c.outputs.f), { abs: 1e-9, rel: 1e-12 }, 'f');
    close(p, dec(c.outputs.p), { abs: 0, rel: 1e-9 }, 'P');
    const fit = fitLorentzian(f.slice(0, c.inputs.fit_count), p.slice(0, c.inputs.fit_count));
    close([fit.fc, fit.d], [c.outputs.fc, c.outputs.d], { abs: 0, rel: 1e-8 }, 'fc, D');
  });
  it('Boltzmann check', () => {
    const doc = load('dynamics.boltzmann_check');
    const c = doc.cases[0];
    const k = c.inputs.k_N_per_m;
    const r = boltzmannCheck(dec(c.inputs.x), (v) => 0.5 * k * v * v, c.inputs.T, c.inputs.bins);
    close(r.empirical, dec(c.outputs.empirical), doc.tolerance, 'empirical');
    close(r.expected, dec(c.outputs.expected), doc.tolerance, 'expected');
    close([r.totalVariation], [c.outputs.total_variation], doc.tolerance, 'total variation');
  });
  it('rejects the cases Python rejects', () => {
    expect(() => psd([1, 2, 3], 1e-3, 8)).toThrow('the trace is too short');
    expect(() => fitLorentzian([1, 2], [1, 1])).toThrow('need at least 3');
    expect(() => beadParams({ depthJ: -1, gammaNsPerM: 1 })).toThrow('depth_J must be finite and positive');
    expect(fftFocalField).toBeTypeOf('function');
  });
});
