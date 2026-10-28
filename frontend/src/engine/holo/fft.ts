/**
 * FFT plans on interleaved Float64 complex arrays (`re` at 2k, `im` at 2k + 1), built on fft.js 4.0.4.
 *
 * Python counterpart: numpy.fft as used by `core/forward.py` (`fft_focal_field`, `fft_inverse`) and `core/device.py`.
 * fft.js handles powers of two only; every other length (the crosstalk grid `pad * n_pix * upsample` is a multiple of
 * 3 for the default upsample) goes through Bluestein's chirp-z algorithm on a power-of-two plan, so the result is
 * defined for every positive size like numpy's. `forward` is unscaled; `inverse` divides by `n` (numpy's `ifft`).
 * The orthonormal scalings of the engine are applied by the callers.
 */
import FFT from 'fft.js';

export type Cx = Float64Array;

const isPow2 = (n: number): boolean => n >= 1 && (n & (n - 1)) === 0;
const nextPow2 = (n: number): number => {
  let m = 1;
  while (m < n) m <<= 1;
  return m;
};

const cache = new Map<number, FftPlan>();

/** A cached plan for length `n`. */
export function plan(n: number): FftPlan {
  if (!Number.isInteger(n) || n < 1) throw new Error(`fft length must be a positive integer, got ${n}`);
  let p = cache.get(n);
  if (!p) {
    p = new FftPlan(n);
    cache.set(n, p);
  }
  return p;
}

export class FftPlan {
  readonly n: number;
  /** @internal */ readonly f: FFT | null = null;
  // Bluestein state (lengths that are not powers of two)
  /** @internal */ readonly m: number = 0;
  /** @internal */ readonly fm: FFT | null = null;
  /** @internal */ readonly chirp: Float64Array | null = null; // w_k = exp(-i pi k^2 / n)
  /** @internal */ readonly bf: Float64Array | null = null; // FFT of the conjugate chirp, zero padded to m
  /** @internal */ readonly ta: Float64Array | null = null;
  /** @internal */ readonly tb: Float64Array | null = null;

  constructor(n: number) {
    this.n = n;
    if (n === 1) return;
    if (isPow2(n)) {
      this.f = new FFT(n);
      return;
    }
    const m = nextPow2(2 * n - 1);
    this.m = m;
    this.fm = new FFT(m);
    const chirp = new Float64Array(2 * n);
    for (let k = 0; k < n; k++) {
      const kk = (k * k) % (2 * n); // keeps the argument small and exact
      const a = (-Math.PI * kk) / n;
      chirp[2 * k] = Math.cos(a);
      chirp[2 * k + 1] = Math.sin(a);
    }
    const b = new Float64Array(2 * m);
    b[0] = chirp[0];
    b[1] = -chirp[1];
    for (let k = 1; k < n; k++) {
      b[2 * k] = b[2 * (m - k)] = chirp[2 * k];
      b[2 * k + 1] = b[2 * (m - k) + 1] = -chirp[2 * k + 1];
    }
    const bf = new Float64Array(2 * m);
    this.fm.transform(bf, b);
    this.chirp = chirp;
    this.bf = bf;
    this.ta = new Float64Array(2 * m);
    this.tb = new Float64Array(2 * m);
  }

  /** `out = F(data)` (e^{-i}), unscaled. `out` and `data` must be different arrays of length `2 n`. */
  forward(data: Cx, out: Cx): void {
    const n = this.n;
    if (n === 1) {
      out[0] = data[0];
      out[1] = data[1];
      return;
    }
    if (this.f) {
      this.f.transform(out, data);
      return;
    }
    const { m, chirp, bf, ta, tb, fm } = this as unknown as { m: number; chirp: Float64Array; bf: Float64Array; ta: Float64Array; tb: Float64Array; fm: FFT };
    ta.fill(0);
    for (let k = 0; k < n; k++) {
      const cr = chirp[2 * k], ci = chirp[2 * k + 1], xr = data[2 * k], xi = data[2 * k + 1];
      ta[2 * k] = xr * cr - xi * ci;
      ta[2 * k + 1] = xr * ci + xi * cr;
    }
    fm.transform(tb, ta);
    for (let k = 0; k < m; k++) {
      const ar = tb[2 * k], ai = tb[2 * k + 1], br = bf[2 * k], bi = bf[2 * k + 1];
      ta[2 * k] = ar * br - ai * bi;
      ta[2 * k + 1] = ar * bi + ai * br;
    }
    fm.inverseTransform(tb, ta); // already divided by m
    for (let k = 0; k < n; k++) {
      const cr = chirp[2 * k], ci = chirp[2 * k + 1], yr = tb[2 * k], yi = tb[2 * k + 1];
      out[2 * k] = yr * cr - yi * ci;
      out[2 * k + 1] = yr * ci + yi * cr;
    }
  }

  /** `out = F^-1(data)` divided by `n` (numpy `ifft`). */
  inverse(data: Cx, out: Cx): void {
    const n = this.n;
    if (n === 1) {
      out[0] = data[0];
      out[1] = data[1];
      return;
    }
    if (this.f) {
      this.f.inverseTransform(out, data);
      return;
    }
    // ifft(x) = conj(fft(conj(x))) / n
    const tmp = new Float64Array(2 * n);
    for (let k = 0; k < n; k++) {
      tmp[2 * k] = data[2 * k];
      tmp[2 * k + 1] = -data[2 * k + 1];
    }
    this.forward(tmp, out);
    for (let k = 0; k < n; k++) {
      out[2 * k] /= n;
      out[2 * k + 1] = -out[2 * k + 1] / n;
    }
  }
}

/**
 * Strided 1D transforms over a block of an interleaved array: `count` lines of length `len`, line `l` starting at
 * complex element `start(l)` with complex stride `stride`. `inverse` is numpy's (divided by `len`).
 */
function lines(a: Cx, len: number, count: number, start: (l: number) => number, stride: number, inverse: boolean): void {
  const p = plan(len);
  const tin = new Float64Array(2 * len);
  const tout = new Float64Array(2 * len);
  for (let l = 0; l < count; l++) {
    const s0 = start(l);
    for (let k = 0, o = s0; k < len; k++, o += stride) {
      tin[2 * k] = a[2 * o];
      tin[2 * k + 1] = a[2 * o + 1];
    }
    if (inverse) p.inverse(tin, tout);
    else p.forward(tin, tout);
    for (let k = 0, o = s0; k < len; k++, o += stride) {
      a[2 * o] = tout[2 * k];
      a[2 * o + 1] = tout[2 * k + 1];
    }
  }
}

/**
 * In-place 2D transform of an `ny x nx` array (row-major), unscaled for the forward direction, divided by `nx ny` for
 * the inverse (numpy `fft2` / `ifft2`). `rowsActive` limits the first (row) stage to the first rows when the others are
 * known to be zero (a zero-padded input); `rowsFirst = false` runs the column stage first and then only the first
 * `rowsActive` rows (an output that is cropped afterwards). Both give the same values as the full transform on the
 * rows that matter.
 */
export function fft2(a: Cx, ny: number, nx: number, inverse: boolean, rowsActive = ny, rowsFirst = true): void {
  if (a.length !== 2 * ny * nx) throw new Error('fft2: array length does not match the shape');
  if (rowsFirst) {
    lines(a, nx, rowsActive, (l) => l * nx, 1, inverse);
    lines(a, ny, nx, (l) => l, nx, inverse);
  } else {
    lines(a, ny, nx, (l) => l, nx, inverse);
    lines(a, nx, rowsActive, (l) => l * nx, 1, inverse);
  }
}

/** In-place 3D transform of an `nz x ny x nx` array (numpy `fftn` / `ifftn`; inverse divided by the volume). */
export function fft3(a: Cx, nz: number, ny: number, nx: number, inverse: boolean): void {
  if (a.length !== 2 * nz * ny * nx) throw new Error('fft3: array length does not match the shape');
  lines(a, nx, nz * ny, (l) => l * nx, 1, inverse);
  lines(a, ny, nz * nx, (l) => Math.floor(l / nx) * ny * nx + (l % nx), nx, inverse);
  lines(a, nz, ny * nx, (l) => l, ny * nx, inverse);
}

/** 1D transform of a fresh copy (numpy `fft`/`ifft` of one vector). */
export function fft1(x: Cx, inverse = false): Cx {
  const n = x.length / 2;
  const out = new Float64Array(2 * n);
  const p = plan(n);
  if (inverse) p.inverse(x, out);
  else p.forward(x, out);
  return out;
}

/** numpy `fftfreq(n, d)` for the frequency of FFT-order index `k`. */
export function fftfreq(n: number, d: number): Float64Array {
  const out = new Float64Array(n);
  const half = Math.floor((n - 1) / 2) + 1;
  for (let i = 0; i < half; i++) out[i] = i / (n * d);
  for (let i = half; i < n; i++) out[i] = (i - n) / (n * d);
  return out;
}
