/**
 * Zernike aberrations in Noll order, orthonormal over the unit disc.
 *
 * Python counterpart: `core/zernike.py` (definitions, the Noll rule for j = 12..21 and the UNVERIFIED sign conventions are
 * documented there; physics-viz D2.3). `Z_n^m = N R_n^|m|(rho) {cos(m theta) | sin(|m| theta)}`, `N = sqrt(2 (n + 1))` for
 * `m != 0`, `sqrt(n + 1)` for `m = 0`; the rms wavefront error is the root sum of squares of the coefficients (waves).
 */
import { type Setup, slmAxis, wrapPhase } from './geometry';

export const J_MAX = 21;

const NAMES: Record<number, string> = {
  1: 'piston', 2: 'tip', 3: 'tilt', 4: 'defocus', 5: 'oblique astigmatism', 6: 'vertical astigmatism',
  7: 'vertical coma', 8: 'horizontal coma', 9: 'vertical trefoil', 10: 'oblique trefoil', 11: 'primary spherical',
};

function checkJ(j: number): number {
  if (!Number.isInteger(j) || j < 1 || j > J_MAX) throw new Error(`Noll index must be an integer in 1..${J_MAX}, got ${j}`);
  return j;
}

/** Radial order `n` and signed azimuthal order `m` (m > 0 cos, m < 0 sin) of Noll index `j` (1..21). */
export function nollToNm(j: number): [number, number] {
  checkJ(j);
  let n = 0;
  while (((n + 1) * (n + 2)) / 2 < j) n++;
  const k = j - (n * (n + 1)) / 2 - 1;
  const mAbs = n % 2 === 0 ? 2 * Math.floor((k + 1) / 2) : 2 * Math.floor(k / 2) + 1;
  if (mAbs === 0) return [n, 0];
  return [n, j % 2 === 0 ? mAbs : -mAbs];
}

export function zernikeName(j: number): string {
  checkJ(j);
  if (NAMES[j]) return NAMES[j];
  const [n, m] = nollToNm(j);
  return `Z(${n},${m})`;
}

const fact = (k: number): number => (k <= 1 ? 1 : k * fact(k - 1));

function radial(n: number, mAbs: number, rho: number): number {
  let out = 0;
  for (let s = 0; s <= (n - mAbs) / 2; s++) {
    const c = ((-1) ** s * fact(n - s)) / (fact(s) * fact((n + mAbs) / 2 - s) * fact((n - mAbs) / 2 - s));
    out += c * rho ** (n - 2 * s);
  }
  return out;
}

/** Orthonormal Zernike mode `j` at one point; zero for `rho > 1`. */
export function zernike(j: number, rho: number, theta: number): number {
  const [n, m] = nollToNm(j);
  if (!(rho <= 1)) return 0;
  const norm = m === 0 ? Math.sqrt(n + 1) : Math.sqrt(2 * (n + 1));
  const ang = m === 0 ? 1 : m > 0 ? Math.cos(m * theta) : Math.sin(-m * theta);
  return norm * radial(n, Math.abs(m), rho) * ang;
}

function coeffs(c: ArrayLike<number>): Float64Array {
  if (c.length > J_MAX) throw new Error(`at most ${J_MAX} coefficients (Noll j = 1..${J_MAX}), got ${c.length}`);
  for (let i = 0; i < c.length; i++) if (!Number.isFinite(c[i])) throw new Error('coefficients must be finite');
  return Float64Array.from(c);
}

/** Unwrapped wavefront in waves on the SLM grid: `sum_j c_j Z_j`, Noll `j = index + 1`; the pupil is the inscribed disc. */
export function wavefrontWaves(coeffsWaves: ArrayLike<number>, setup: Setup): Float64Array {
  const c = coeffs(coeffsWaves);
  const n = setup.nPix, ax = slmAxis(setup);
  const r0 = (n * setup.pitchM) / 2;
  const w = new Float64Array(n * n);
  for (let j = 1; j <= c.length; j++) {
    if (c[j - 1] === 0) continue;
    for (let iy = 0; iy < n; iy++) {
      for (let ix = 0; ix < n; ix++) {
        const x = ax[ix], y = ax[iy];
        w[iy * n + ix] += c[j - 1] * zernike(j, Math.hypot(x, y) / r0, Math.atan2(y, x));
      }
    }
  }
  return w;
}

/** Phase in radians wrapped to `[0, 2 pi)`: `2 pi` times `wavefrontWaves`. */
export function phaseFromCoeffs(coeffsWaves: ArrayLike<number>, setup: Setup): Float64Array {
  const w = wavefrontWaves(coeffsWaves, setup);
  for (let i = 0; i < w.length; i++) w[i] *= 2 * Math.PI;
  return wrapPhase(w);
}

/** Root sum of squares of the coefficients, piston excluded unless asked. */
export function rmsWaves(coeffsWaves: ArrayLike<number>, includePiston = false): number {
  const c = coeffs(coeffsWaves);
  let s = 0;
  for (let i = includePiston ? 0 : 1; i < c.length; i++) s += c[i] ** 2;
  return Math.sqrt(s);
}

/** Marechal approximation `exp[-(2 pi sigma_W)^2]` (piston excluded). */
export function strehl(coeffsWaves: ArrayLike<number>): number {
  return Math.exp(-((2 * Math.PI * rmsWaves(coeffsWaves)) ** 2));
}
