// Zernike aberrations in Noll order, orthonormal over the unit disc: a port of data-pipeline/pipeline/model/holo/core/zernike.py
// (same definitions, same j = 1..21), so the wavefront, the rms and the Strehl the Aberrations view shows are the engine's.
// Coefficients are in waves; the rms wavefront error is the root sum of squares of the coefficients without piston.
import type { Text } from '../lib/contract.types';

export const J_MAX = 21;

const NAMES: Record<number, Text> = {
  1: { en: 'piston', es: 'pistón' },
  2: { en: 'tip', es: 'inclinación x' },
  3: { en: 'tilt', es: 'inclinación y' },
  4: { en: 'defocus', es: 'desenfoque' },
  5: { en: 'oblique astigmatism', es: 'astigmatismo oblicuo' },
  6: { en: 'vertical astigmatism', es: 'astigmatismo vertical' },
  7: { en: 'vertical coma', es: 'coma vertical' },
  8: { en: 'horizontal coma', es: 'coma horizontal' },
  9: { en: 'vertical trefoil', es: 'trébol vertical' },
  10: { en: 'oblique trefoil', es: 'trébol oblicuo' },
  11: { en: 'primary spherical', es: 'esférica primaria' },
};

export function nollToNm(j: number): [number, number] {
  if (!Number.isInteger(j) || j < 1 || j > J_MAX) throw new Error(`Noll index must be an integer in 1..${J_MAX}, got ${j}`);
  let n = 0;
  while (((n + 1) * (n + 2)) / 2 < j) n++;
  const k = j - (n * (n + 1)) / 2 - 1;
  const mAbs = n % 2 === 0 ? 2 * Math.floor((k + 1) / 2) : 2 * Math.floor(k / 2) + 1;
  if (mAbs === 0) return [n, 0];
  return [n, j % 2 === 0 ? mAbs : -mAbs];
}

export function zernikeName(j: number): Text {
  if (NAMES[j]) return NAMES[j];
  const [n, m] = nollToNm(j);
  return { en: `Z(${n},${m})`, es: `Z(${n},${m})` };
}

const fact = (k: number): number => (k <= 1 ? 1 : k * fact(k - 1));

function radial(n: number, mAbs: number, rho: number): number {
  let out = 0;
  for (let s = 0; s <= (n - mAbs) / 2; s++) {
    out += ((-1) ** s * fact(n - s)) / (fact(s) * fact((n + mAbs) / 2 - s) * fact((n - mAbs) / 2 - s)) * rho ** (n - 2 * s);
  }
  return out;
}

/** The orthonormal mode j (unit rms over the disc) at (rho, theta); zero outside the disc. */
export function zernike(j: number, rho: number, theta: number): number {
  if (rho > 1) return 0;
  const [n, m] = nollToNm(j);
  const norm = m === 0 ? Math.sqrt(n + 1) : Math.sqrt(2 * (n + 1));
  const ang = m === 0 ? 1 : m > 0 ? Math.cos(m * theta) : Math.sin(-m * theta);
  return norm * radial(n, Math.abs(m), rho) * ang;
}

/** Coefficients keyed by Noll index (the params record's `aberration.noll`, keys are strings "2".."21") as a dense array, index j - 1. */
export function coeffArray(noll: Record<string, number> | undefined): number[] {
  const c = new Array<number>(J_MAX).fill(0);
  for (const [k, v] of Object.entries(noll ?? {})) {
    const j = Number(k);
    if (j >= 1 && j <= J_MAX) c[j - 1] = v;
  }
  return c;
}

/** The wavefront in waves on an n x n grid over the pupil (the SLM disc inscribed in the square); pixels outside the disc are NaN so a map leaves them blank. */
export function wavefrontWaves(coeffs: readonly number[], n: number): Float32Array {
  const out = new Float32Array(n * n);
  const c = (n - 1) / 2;
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const px = (x - c) / (n / 2);
      const py = (y - c) / (n / 2);
      const rho = Math.hypot(px, py);
      if (rho > 1) {
        out[y * n + x] = NaN;
        continue;
      }
      const theta = Math.atan2(py, px);
      let w = 0;
      for (let j = 1; j <= coeffs.length; j++) if (coeffs[j - 1] !== 0) w += coeffs[j - 1] * zernike(j, rho, theta);
      out[y * n + x] = w;
    }
  }
  return out;
}

/** Root sum of squares of the coefficients, piston excluded (it does not blur). */
export function rmsWaves(coeffs: readonly number[]): number {
  let s = 0;
  for (let j = 2; j <= coeffs.length; j++) s += coeffs[j - 1] ** 2;
  return Math.sqrt(s);
}

/** The Marechal approximation exp[-(2 pi sigma_W)^2]. */
export const strehl = (coeffs: readonly number[]): number => Math.exp(-((2 * Math.PI * rmsWaves(coeffs)) ** 2));

/** The Marechal limit: a diffraction-limited wavefront has rms below 1/14 wave (Strehl above 0.8). */
export const MARECHAL_RMS_WAVES = 1 / 14;
