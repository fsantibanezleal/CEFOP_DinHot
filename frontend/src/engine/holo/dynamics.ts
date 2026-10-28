/**
 * Particle dynamics in a computed focal intensity map: overdamped bead, underdamped atom, PSD and calibration.
 *
 * Python counterpart: `core/dynamics.py` (recipe physics-viz D3.3 and its sources documented there). Draw order from the
 * portable RNG: atom initial velocity (2 normals), then the noise or kick block of `2 n` normals (x then y per step); the
 * block is always drawn. The PSD is the one-sided periodogram of Hann-windowed segments, averaged; `fitLorentzian` fits
 * `1 / P = a + b f^2` with weights `P^2`.
 */
import { fft1 } from './fft';
import { KB_J_PER_K } from './trapphys';
import type { Rng } from './rng';

const finpos = (name: string, v: number): number => {
  if (!(Number.isFinite(v) && v > 0)) throw new Error(`${name} must be finite and positive, got ${v}`);
  return v;
};

export interface BeadParams {
  depthJ: number;
  gammaNsPerM: number;
  temperatureK: number;
  startM: [number, number];
}

export interface AtomParams {
  depthJ: number;
  massKg: number;
  temperatureK: number;
  kickMPerS: number;
  startM: [number, number];
}

export function beadParams(p: Pick<BeadParams, 'depthJ' | 'gammaNsPerM'> & Partial<BeadParams>): BeadParams {
  const out: BeadParams = { temperatureK: 295, startM: [0, 0], ...p };
  finpos('depth_J', out.depthJ);
  finpos('gamma_Ns_per_m', out.gammaNsPerM);
  if (!(Number.isFinite(out.temperatureK) && out.temperatureK >= 0)) throw new Error('temperature_K must be finite and >= 0');
  return out;
}

export function atomParams(p: Pick<AtomParams, 'depthJ' | 'massKg'> & Partial<AtomParams>): AtomParams {
  const out: AtomParams = { temperatureK: 0, kickMPerS: 0, startM: [0, 0], ...p };
  finpos('depth_J', out.depthJ);
  finpos('mass_kg', out.massKg);
  if (!(Number.isFinite(out.temperatureK) && out.temperatureK >= 0)) throw new Error('temperature_K must be finite and >= 0');
  if (!(Number.isFinite(out.kickMPerS) && out.kickMPerS >= 0)) throw new Error('kick_m_per_s must be finite and >= 0');
  return out;
}

/** Normalised intensity map with bilinear-interpolated gradient (numpy `gradient`: central differences, one-sided edges). */
class Field {
  readonly x0: number;
  readonly y0: number;
  readonly dx: number;
  readonly dy: number;
  readonly nx: number;
  readonly ny: number;
  private readonly gx: Float64Array;
  private readonly gy: Float64Array;

  constructor(map: ArrayLike<number>, x: ArrayLike<number>, y: ArrayLike<number>) {
    const nx = x.length, ny = y.length;
    if (map.length !== ny * nx || Math.min(ny, nx) < 3) throw new Error('intensity_map must have shape (len(y), len(x)) with both at least 3');
    let peak = -Infinity;
    for (let i = 0; i < map.length; i++) {
      if (!Number.isFinite(map[i])) throw new Error('intensity_map must be finite');
      if (map[i] > peak) peak = map[i];
    }
    const uniform = (a: ArrayLike<number>): boolean => {
      const d0 = a[1] - a[0];
      for (let i = 1; i < a.length; i++) {
        const d = a[i] - a[i - 1];
        if (!(d > 0) || Math.abs(d - d0) > 1e-8 + 1e-5 * Math.abs(d0)) return false;
      }
      return true;
    };
    if (!uniform(x) || !uniform(y)) throw new Error('grid_m axes must be increasing and uniformly spaced');
    if (!(peak > 0)) throw new Error('intensity_map has no positive maximum');
    const f = Float64Array.from(map, (v) => v / peak);
    this.x0 = x[0];
    this.y0 = y[0];
    this.dx = x[1] - x[0];
    this.dy = y[1] - y[0];
    this.nx = nx;
    this.ny = ny;
    this.gx = new Float64Array(ny * nx);
    this.gy = new Float64Array(ny * nx);
    for (let iy = 0; iy < ny; iy++) {
      for (let ix = 0; ix < nx; ix++) {
        const q = iy * nx + ix;
        this.gx[q] = ix === 0 ? (f[q + 1] - f[q]) / (x[1] - x[0]) : ix === nx - 1 ? (f[q] - f[q - 1]) / (x[nx - 1] - x[nx - 2]) : (f[q + 1] - f[q - 1]) / (x[ix + 1] - x[ix - 1]);
        this.gy[q] = iy === 0 ? (f[q + nx] - f[q]) / (y[1] - y[0]) : iy === ny - 1 ? (f[q] - f[q - nx]) / (y[ny - 1] - y[ny - 2]) : (f[q + nx] - f[q - nx]) / (y[iy + 1] - y[iy - 1]);
      }
    }
  }

  /** Bilinear gradient `(dI/dx, dI/dy)` of the normalised map at the point (clamped to the grid). */
  grad(px: number, py: number, out: [number, number]): void {
    const u = Math.min(Math.max((px - this.x0) / this.dx, 0), this.nx - 1.000001);
    const v = Math.min(Math.max((py - this.y0) / this.dy, 0), this.ny - 1.000001);
    const i0 = Math.trunc(u), j0 = Math.trunc(v);
    const fu = u - i0, fv = v - j0;
    const w00 = (1 - fu) * (1 - fv), w10 = fu * (1 - fv), w01 = (1 - fu) * fv, w11 = fu * fv;
    const q = j0 * this.nx + i0, nx = this.nx;
    out[0] = w00 * this.gx[q] + w10 * this.gx[q + 1] + w01 * this.gx[q + nx] + w11 * this.gx[q + nx + 1];
    out[1] = w00 * this.gy[q] + w10 * this.gy[q + 1] + w01 * this.gy[q + nx] + w11 * this.gy[q + nx + 1];
  }
}

function steps(nSteps: number, dt: number): number {
  if (!Number.isInteger(nSteps) || nSteps < 1) throw new Error('n_steps must be a positive integer');
  finpos('dt', dt);
  return nSteps;
}

/** Positions `(n + 1) x 2` (row-major, metres) of an overdamped bead in the potential `-depth * I / I_max`. */
export function beadTrajectory(map: ArrayLike<number>, x: ArrayLike<number>, y: ArrayLike<number>, p: BeadParams, nSteps: number, dt: number, rng: Rng): Float64Array {
  const n = steps(nSteps, dt);
  const fld = new Field(map, x, y);
  const d = (KB_J_PER_K * p.temperatureK) / p.gammaNsPerM;
  const amp = Math.sqrt(2 * d * dt);
  const drift = (p.depthJ * dt) / p.gammaNsPerM;
  const zeta = rng.normalArray(2 * n);
  const out = new Float64Array(2 * (n + 1));
  let [px, py] = p.startM;
  out[0] = px;
  out[1] = py;
  const g: [number, number] = [0, 0];
  for (let k = 0; k < n; k++) {
    fld.grad(px, py, g);
    px += drift * g[0] + amp * zeta[2 * k];
    py += drift * g[1] + amp * zeta[2 * k + 1];
    out[2 * (k + 1)] = px;
    out[2 * (k + 1) + 1] = py;
  }
  return out;
}

/** Velocity-Verlet positions and velocities, each `(n + 1) x 2`, of an atom in `-depth * I / I_max`. */
export function atomTrajectory(map: ArrayLike<number>, x: ArrayLike<number>, y: ArrayLike<number>, p: AtomParams, nSteps: number, dt: number, rng: Rng): { pos: Float64Array; vel: Float64Array } {
  const n = steps(nSteps, dt);
  const fld = new Field(map, x, y);
  const kForce = p.depthJ / p.massKg;
  const vth = Math.sqrt((KB_J_PER_K * p.temperatureK) / p.massKg);
  const z0 = rng.normalArray(2);
  const kicks = rng.normalArray(2 * n);
  const pos = new Float64Array(2 * (n + 1)), vel = new Float64Array(2 * (n + 1));
  let [px, py] = p.startM;
  let vx = vth * z0[0], vy = vth * z0[1];
  pos[0] = px; pos[1] = py; vel[0] = vx; vel[1] = vy;
  const g: [number, number] = [0, 0];
  fld.grad(px, py, g);
  let ax = kForce * g[0], ay = kForce * g[1];
  for (let k = 0; k < n; k++) {
    const vxh = vx + 0.5 * dt * ax, vyh = vy + 0.5 * dt * ay;
    px += dt * vxh;
    py += dt * vyh;
    fld.grad(px, py, g);
    ax = kForce * g[0];
    ay = kForce * g[1];
    vx = vxh + 0.5 * dt * ax + kicks[2 * k] * p.kickMPerS;
    vy = vyh + 0.5 * dt * ay + kicks[2 * k + 1] * p.kickMPerS;
    pos[2 * (k + 1)] = px; pos[2 * (k + 1) + 1] = py; vel[2 * (k + 1)] = vx; vel[2 * (k + 1) + 1] = vy;
  }
  return { pos, vel };
}

/** One-sided PSD (units of `x^2 / Hz`): Hann-windowed periodograms of `segments` equal parts, averaged; no zero-frequency bin. */
export function psd(x: ArrayLike<number>, dt: number, segments = 8): { f: Float64Array; p: Float64Array } {
  finpos('dt', dt);
  if (!Number.isInteger(segments) || segments < 1) throw new Error('segments must be a positive integer');
  const nper = Math.floor(x.length / segments);
  if (nper < 4) throw new Error('the trace is too short for that number of segments');
  for (let i = 0; i < x.length; i++) if (!Number.isFinite(x[i])) throw new Error('x contains NaN or infinite values');
  const w = Float64Array.from({ length: nper }, (_, i) => 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (nper - 1)));
  let sw2 = 0;
  for (let i = 0; i < nper; i++) sw2 += w[i] ** 2;
  const nb = Math.floor(nper / 2) + 1;
  const acc = new Float64Array(nb);
  const buf = new Float64Array(2 * nper);
  for (let s = 0; s < segments; s++) {
    let mean = 0;
    for (let i = 0; i < nper; i++) mean += x[s * nper + i];
    mean /= nper;
    for (let i = 0; i < nper; i++) {
      buf[2 * i] = w[i] * (x[s * nper + i] - mean);
      buf[2 * i + 1] = 0;
    }
    const F = fft1(buf);
    for (let k = 0; k < nb; k++) acc[k] += F[2 * k] ** 2 + F[2 * k + 1] ** 2;
  }
  const p = new Float64Array(nb);
  for (let k = 0; k < nb; k++) p[k] = ((acc[k] / segments) * dt) / sw2;
  const last = nper % 2 === 0 ? nb - 1 : nb; // p[1:-1] doubles all but the Nyquist bin for even nper
  for (let k = 1; k < last; k++) p[k] *= 2;
  const f = Float64Array.from({ length: nb - 1 }, (_, i) => (i + 1) / (nper * dt));
  return { f, p: p.slice(1) };
}

/** Corner frequency `f_c` (Hz) and `D` (x^2/s) of `P1 = D / (pi^2 (f^2 + f_c^2))` (weighted LS of `1 / P = a + b f^2`). */
export function fitLorentzian(f: ArrayLike<number>, p: ArrayLike<number>): { fc: number; d: number } {
  if (f.length !== p.length || f.length < 3) throw new Error('need at least 3 matching frequency and positive finite PSD values');
  let sw = 0, su = 0, sy = 0, suu = 0, suy = 0;
  for (let i = 0; i < f.length; i++) {
    if (!(p[i] > 0) || !Number.isFinite(p[i])) throw new Error('need at least 3 matching frequency and positive finite PSD values');
    const y = 1 / p[i], u = f[i] ** 2, w = p[i] ** 2;
    sw += w; su += w * u; sy += w * y; suu += w * u * u; suy += w * u * y;
  }
  const den = sw * suu - su ** 2;
  if (den <= 0) throw new Error('degenerate frequency set');
  const b = (sw * suy - su * sy) / den;
  const a = (sy - b * su) / sw;
  if (!(a > 0 && b > 0)) throw new Error('no Lorentzian shape in the spectrum (non-positive intercept or slope)');
  return { fc: Math.sqrt(a / b), d: Math.PI ** 2 / b };
}

/** Total variation between the histogram of `x` and the Boltzmann density `exp(-U(x) / k_B T)` (1D, `U` a function). */
export function boltzmannCheck(x: ArrayLike<number>, potentialJ: (x: number) => number, temperatureK: number, bins = 40): { totalVariation: number; empirical: Float64Array; expected: Float64Array } {
  finpos('temperature_K', temperatureK);
  if (x.length < 10) throw new Error('need at least 10 finite positions');
  let lo = Infinity, hi = -Infinity;
  for (let i = 0; i < x.length; i++) {
    if (!Number.isFinite(x[i])) throw new Error('need at least 10 finite positions');
    if (x[i] < lo) lo = x[i];
    if (x[i] > hi) hi = x[i];
  }
  const edges = Float64Array.from({ length: bins + 1 }, (_, i) => (i === bins ? hi : lo + (i * (hi - lo)) / bins));
  const emp = new Float64Array(bins);
  for (let i = 0; i < x.length; i++) emp[Math.min(bins - 1, Math.floor(((x[i] - lo) / (hi - lo)) * bins))]++;
  let tot = 0;
  for (let b = 0; b < bins; b++) tot += emp[b];
  for (let b = 0; b < bins; b++) emp[b] /= tot;
  const sub: number[][] = [];
  let umin = Infinity;
  for (let b = 0; b < bins; b++) {
    const row = [];
    for (let s = 0; s < 9; s++) {
      const u = potentialJ(edges[b] + ((s + 0.5) / 9) * (edges[b + 1] - edges[b]));
      row.push(u);
      if (u < umin) umin = u;
    }
    sub.push(row);
  }
  const dens = Float64Array.from(sub, (row) => row.reduce((a, u) => a + Math.exp(-(u - umin) / (KB_J_PER_K * temperatureK)), 0) / 9);
  let ds = 0;
  for (let b = 0; b < bins; b++) ds += dens[b];
  const expected = dens.map((v) => v / ds);
  let tv = 0;
  for (let b = 0; b < bins; b++) tv += Math.abs(emp[b] - expected[b]);
  return { totalVariation: 0.5 * tv, empirical: emp, expected };
}
