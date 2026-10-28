/**
 * Optical setup, SLM grid, input beam and focal sampling.
 *
 * Python counterpart: `core/geometry.py` (the focal-sampling derivation and its sources are documented there; one FFT
 * bin of the zero-padded transform is `lambda f / (pad N p)`, the unaliased half-window `lambda f / (2 p)`).
 * Units are SI (metres, radians). Arrays are row-major, indexed `[iy * n + ix]`.
 */
export interface Setup {
  wavelengthM: number;
  focalM: number;
  na: number;
  nImm: number;
  /** SLM side in pixels (square). */
  nPix: number;
  pitchM: number;
  /** Integer padding factor: the FFT grid is `pad * nPix`. */
  pad: number;
  beam: 'gaussian' | 'flat';
  waistFrac: number;
}

const pos = (name: string, v: number): void => {
  if (typeof v !== 'number' || !Number.isFinite(v) || v <= 0) throw new Error(`${name} must be a finite positive number, got ${v}`);
};

/** Validated setup (the rules of the Python `Setup` constructor, same messages). */
export function makeSetup(s: Partial<Setup> & Pick<Setup, 'wavelengthM' | 'focalM' | 'na' | 'nImm' | 'nPix' | 'pitchM'>): Setup {
  const out: Setup = { pad: 2, beam: 'gaussian', waistFrac: 1, ...s };
  for (const k of ['wavelengthM', 'focalM', 'na', 'pitchM', 'waistFrac'] as const) pos(k, out[k]);
  pos('nImm', out.nImm);
  if (out.nImm < 1) throw new Error(`n_imm must be >= 1, got ${out.nImm}`);
  if (out.na > out.nImm) throw new Error(`na ${out.na} cannot exceed the immersion index ${out.nImm}`);
  for (const k of ['nPix', 'pad'] as const) {
    if (!Number.isInteger(out[k]) || out[k] < 1) throw new Error(`${k} must be a positive integer, got ${out[k]}`);
  }
  if (out.beam !== 'gaussian' && out.beam !== 'flat') throw new Error(`beam must be 'gaussian' or 'flat', got ${out.beam}`);
  return out;
}

export const nFft = (s: Setup): number => s.pad * s.nPix;

/** Pixel-centre coordinates along one axis, `(i - (n - 1) / 2) p`, metres. */
export function slmAxis(s: Setup): Float64Array {
  const c = new Float64Array(s.nPix);
  for (let i = 0; i < s.nPix; i++) c[i] = (i - (s.nPix - 1) / 2) * s.pitchM;
  return c;
}

/** Input amplitude `A_j` on the SLM grid, normalised so that `sum A_j^2 = nPix^2` (algorithms D1.0). */
export function inputAmplitude(s: Setup): Float64Array {
  const n = s.nPix;
  const a = new Float64Array(n * n);
  if (s.beam === 'flat') return a.fill(1);
  const c = slmAxis(s);
  const w = (s.waistFrac * n * s.pitchM) / 2;
  let sum = 0;
  for (let iy = 0; iy < n; iy++) {
    for (let ix = 0; ix < n; ix++) {
      const v = Math.exp(-(c[ix] ** 2 + c[iy] ** 2) / w ** 2);
      a[iy * n + ix] = v;
      sum += v * v;
    }
  }
  const k = Math.sqrt((n * n) / sum);
  for (let i = 0; i < a.length; i++) a[i] *= k;
  return a;
}

/** One FFT bin in the focal plane, metres. */
export const focalBinM = (s: Setup): number => (s.wavelengthM * s.focalM) / (s.pad * s.nPix * s.pitchM);

/** Unaliased half-window `lambda f / (2 p)`, metres. */
export const halfFieldM = (s: Setup): number => (s.wavelengthM * s.focalM) / (2 * s.pitchM);

export function umToBin(s: Setup, xUm: number): number {
  if (!Number.isFinite(xUm)) throw new Error(`position must be finite, got ${xUm}`);
  return (xUm * 1e-6) / focalBinM(s);
}

export function binToUm(s: Setup, k: number): number {
  if (!Number.isFinite(k)) throw new Error(`bin must be finite, got ${k}`);
  return k * focalBinM(s) * 1e6;
}

export const TWO_PI = 2 * Math.PI;

/** Python-style modulo of a float by a positive modulus (result in `[0, m)`). */
export function pmod(x: number, m: number): number {
  let r = x % m;
  if (r !== 0 && r < 0) r += m;
  return r;
}

/** Wrap to `[0, 2 pi)` as float64 (the convention of every displayed phase). */
export function wrapPhase(phi: ArrayLike<number>): Float64Array {
  const out = new Float64Array(phi.length);
  for (let i = 0; i < out.length; i++) {
    const r = pmod(phi[i], TWO_PI);
    out[i] = r >= TWO_PI ? 0 : r;
  }
  return out;
}
