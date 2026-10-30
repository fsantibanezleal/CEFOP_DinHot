/**
 * SLM device model: phase quantization, phase-response LUT, flicker, pixel crosstalk and the pixel-aperture envelope.
 *
 * Python counterpart: `core/device.py` (the model, its sources and its UNVERIFIED items are documented there). A missing
 * device (`null`) is the ideal one. Order in `displayedPhase`: wrap, quantize to `2^b` levels, nonlinear response
 * `2 pi (level phase / 2 pi)^gamma`, additive Gaussian flicker of rms `flickerRad` per pixel (portable RNG), wrap.
 * Crosstalk: each SLM pixel is `upsample x upsample` samples blurred with `K = F^-1 exp[-(|kx|^q + |ky|^q) / sigma^q]`
 * (circular convolution; `k` in cycles per SLM pixel).
 */
import { type Cx, fft2, fftfreq, plan } from './fft';
import { fftFocalField } from './forward';
import { type Setup, TWO_PI, inputAmplitude, nFft, wrapPhase } from './geometry';
import type { Rng } from './rng';

export interface Device {
  bitDepth: number | null;
  /** `[sigma_per_px, q]` or null. */
  crosstalk: [number, number] | null;
  upsample: number;
  fillFactor: number;
  flickerRad: number;
  lutGamma: number;
}

/** Validated device (the rules and messages of the Python `Device`). Defaults: a real pixelated SLM, fill factor 1. */
export function makeDevice(d: Partial<Device> = {}): Device {
  const out: Device = { bitDepth: null, crosstalk: null, upsample: 3, fillFactor: 1, flickerRad: 0, lutGamma: 1, ...d };
  const b = out.bitDepth;
  if (b !== null && (!Number.isInteger(b) || b < 1 || b > 16)) throw new Error(`bit_depth must be an integer in 1..16 or None, got ${b}`);
  if (!Number.isInteger(out.upsample) || out.upsample < 1) throw new Error(`upsample must be a positive integer, got ${out.upsample}`);
  if (!(Number.isFinite(out.fillFactor) && out.fillFactor > 0 && out.fillFactor <= 1)) throw new Error(`fill_factor must be in (0, 1], got ${out.fillFactor}`);
  if (!(Number.isFinite(out.flickerRad) && out.flickerRad >= 0)) throw new Error(`flicker_rad must be finite and >= 0, got ${out.flickerRad}`);
  if (!(Number.isFinite(out.lutGamma) && out.lutGamma > 0)) throw new Error(`lut_gamma must be finite and > 0, got ${out.lutGamma}`);
  if (out.crosstalk !== null) {
    const [sigma, q] = out.crosstalk;
    if (!(Number.isFinite(sigma) && sigma > 0 && Number.isFinite(q) && q > 0)) throw new Error(`crosstalk sigma and q must be finite and positive, got [${out.crosstalk}]`);
  }
  return out;
}

/** Round the phase (wrapped to `[0, 2 pi)`) to the nearest of `2^bitDepth` equally spaced levels. */
export function quantize(phi: ArrayLike<number>, bitDepth: number): Float64Array {
  if (!Number.isInteger(bitDepth) || bitDepth < 1 || bitDepth > 16) throw new Error(`bit_depth must be an integer in 1..16, got ${bitDepth}`);
  const levels = 2 ** bitDepth;
  const w = wrapPhase(phi);
  const out = new Float64Array(w.length);
  for (let i = 0; i < w.length; i++) {
    const k = Math.floor((w[i] / TWO_PI) * levels + 0.5) % levels;
    out[i] = k * (TWO_PI / levels);
  }
  return out;
}

/** The phase the device really shows. `rng` is required only if `flickerRad > 0`. */
export function displayedPhase(phi: ArrayLike<number>, device: Device, rng: Rng | null): Float64Array {
  for (let i = 0; i < phi.length; i++) if (!Number.isFinite(phi[i])) throw new Error('phi contains NaN or infinite values');
  let p = wrapPhase(phi);
  if (device.bitDepth !== null) p = quantize(p, device.bitDepth);
  if (device.lutGamma !== 1) for (let i = 0; i < p.length; i++) p[i] = TWO_PI * (p[i] / TWO_PI) ** device.lutGamma;
  if (device.flickerRad > 0) {
    if (!rng) throw new Error('an rng is required when flicker_rad > 0 (ADR-0054: no hidden randomness)');
    const z = rng.normalArray(p.length);
    for (let i = 0; i < p.length; i++) p[i] += device.flickerRad * z[i];
  }
  return wrapPhase(p);
}

/** Crosstalk transfer function on an `nUp x nUp` grid (FFT order), real. */
export function crosstalkTransfer(nUp: number, sigma: number, q: number, upsample: number): Float64Array {
  const f = fftfreq(nUp, 1 / upsample);
  const k = Float64Array.from(f, Math.abs);
  const out = new Float64Array(nUp * nUp);
  const sq = sigma ** q;
  for (let iy = 0; iy < nUp; iy++) for (let ix = 0; ix < nUp; ix++) out[iy * nUp + ix] = Math.exp(-((k[iy] ** q + k[ix] ** q) / sq));
  return out;
}

/** The spatial kernel on an `nUp x nUp` grid: real, symmetric, origin at index (0, 0), sum 1. */
export function crosstalkKernel(nUp: number, sigma: number, q: number, upsample = 3): Float64Array {
  if (!Number.isInteger(nUp) || nUp < 1) throw new Error('n_up must be a positive integer');
  if (!(Number.isFinite(sigma) && sigma > 0 && Number.isFinite(q) && q > 0)) throw new Error('sigma and q must be finite and positive');
  const h = crosstalkTransfer(nUp, sigma, q, upsample);
  const a = new Float64Array(2 * nUp * nUp);
  for (let i = 0; i < h.length; i++) a[2 * i] = h[i];
  fft2(a, nUp, nUp, true);
  return Float64Array.from({ length: nUp * nUp }, (_, i) => a[2 * i]);
}

function upsampleGrid(phi: ArrayLike<number>, n: number, u: number): Float64Array {
  if (phi.length !== n * n) throw new Error('phi must be a square 2D array');
  const nu = n * u;
  const out = new Float64Array(nu * nu);
  for (let iy = 0; iy < nu; iy++) for (let ix = 0; ix < nu; ix++) out[iy * nu + ix] = phi[Math.floor(iy / u) * n + Math.floor(ix / u)];
  return out;
}

const side = (len: number): number => {
  const n = Math.round(Math.sqrt(len));
  if (n * n !== len) throw new Error('phi must be a square 2D array');
  return n;
};

/** Upsample each pixel to `u x u` samples and blur with the crosstalk kernel (if the device has one). */
export function crosstalk(phi: ArrayLike<number>, device: Device): Float64Array {
  const n = side(phi.length), u = device.upsample, nu = n * u;
  const up = upsampleGrid(phi, n, u);
  if (device.crosstalk === null) return up;
  const h = crosstalkTransfer(nu, device.crosstalk[0], device.crosstalk[1], u);
  const a = new Float64Array(2 * nu * nu);
  for (let i = 0; i < up.length; i++) a[2 * i] = up[i];
  fft2(a, nu, nu, false);
  for (let i = 0; i < h.length; i++) {
    a[2 * i] *= h[i];
    a[2 * i + 1] *= h[i];
  }
  fft2(a, nu, nu, true);
  return Float64Array.from({ length: nu * nu }, (_, i) => a[2 * i]);
}

/** Adjoint of `crosstalk`: gradient with respect to `phi` given the gradient `g` with respect to its output. */
export function crosstalkAdjoint(g: ArrayLike<number>, device: Device): Float64Array {
  const nu = side(g.length), u = device.upsample;
  if (nu % u) throw new Error(`g must be a square array whose side is a multiple of upsample (${u}), got (${nu}, ${nu})`);
  let gg = Float64Array.from(g);
  if (device.crosstalk !== null) {
    const h = crosstalkTransfer(nu, device.crosstalk[0], device.crosstalk[1], u);
    const a = new Float64Array(2 * nu * nu);
    for (let i = 0; i < gg.length; i++) a[2 * i] = gg[i];
    fft2(a, nu, nu, false);
    for (let i = 0; i < h.length; i++) {
      a[2 * i] *= h[i]; // H is real, so its conjugate is itself
      a[2 * i + 1] *= h[i];
    }
    fft2(a, nu, nu, true);
    gg = Float64Array.from({ length: nu * nu }, (_, i) => a[2 * i]);
  }
  const n = nu / u;
  const out = new Float64Array(n * n);
  for (let iy = 0; iy < nu; iy++) for (let ix = 0; ix < nu; ix++) out[Math.floor(iy / u) * n + Math.floor(ix / u)] += gg[iy * nu + ix];
  return out;
}

/** numpy `sinc(x)` = sin(pi x) / (pi x). */
export const sinc = (x: number): number => (x === 0 ? 1 : Math.sin(Math.PI * x) / (Math.PI * x));

/** `sinc(sqrt(fill) k / nFft)` along one focal axis (k = -nFft/2 ..). */
export function sinc1d(setup: Setup, fillFactor: number): Float64Array {
  const m = nFft(setup), h = Math.floor(m / 2);
  return Float64Array.from({ length: m }, (_, i) => sinc((Math.sqrt(fillFactor) * (i - h)) / m));
}

/** Intensity envelope of the square pixel aperture on the centred focal grid, `sinc^2 x sinc^2`, 1 at the centre. */
export function pixelEnvelope(setup: Setup, device: Device): Float64Array {
  const m = nFft(setup);
  const s = Float64Array.from(sinc1d(setup, device.fillFactor), (v) => v * v);
  const out = new Float64Array(m * m);
  for (let iy = 0; iy < m; iy++) for (let ix = 0; ix < m; ix++) out[iy * m + ix] = s[iy] * s[ix];
  return out;
}

/** The factor `sinc / Dirichlet` that exchanges the sample-and-hold of `u` samples per pixel for the pixel aperture. */
export function swapFactor(setup: Setup, device: Device): Float64Array {
  const m = nFft(setup), u = device.upsample, mu = m * u, h = Math.floor(m / 2);
  const env = sinc1d(setup, device.fillFactor);
  return Float64Array.from({ length: m }, (_, i) => {
    const k = i - h;
    const d = k === 0 ? 1 : Math.sin((Math.PI * k) / m) / (u * Math.sin((Math.PI * k) / mu));
    return env[i] / d;
  });
}

/** FFT-order indices of the focal window (`-(m/2)..m/2-1`) on the `mu` grid, and the linear phase on that window. */
export function windowIndex(setup: Setup, u: number): { idx: Int32Array; wr: Float64Array; wi: Float64Array } {
  const m = nFft(setup), mu = m * u, n = setup.nPix, h = Math.floor(m / 2);
  const idx = new Int32Array(m);
  const wr = new Float64Array(m), wi = new Float64Array(m);
  const lo = Math.floor(mu / 2) - h;
  for (let i = 0; i < m; i++) {
    idx[i] = (((i - h) % mu) + mu) % mu;
    const a = (TWO_PI * ((n * u - 1) / 2) * (lo + i - Math.floor(mu / 2))) / mu;
    wr[i] = Math.cos(a);
    wi[i] = Math.sin(a);
  }
  return { idx, wr, wi };
}

/**
 * Pruned zero-padded transform of the upsampled field `g` (`nu x nu` complex, `nu = nPix u`): only the `nu` non-zero rows and
 * the `m` wanted frequencies are computed. Returns the window `y * ramp / u` (before the sample-and-hold swap).
 * Python counterpart: `FocalForward.forward` in `methods/optim/_common.py` (equal to `device._upsampled_focal_field`).
 */
export function upsampledWindow(g: Cx, setup: Setup, u: number): Cx {
  const m = nFft(setup), n = setup.nPix, nu = n * u, mu = m * u;
  const { idx, wr, wi } = windowIndex(setup, u);
  const p = plan(mu);
  const tin = new Float64Array(2 * mu), tout = new Float64Array(2 * mu);
  const t1 = new Float64Array(2 * nu * m);
  for (let r = 0; r < nu; r++) {
    tin.fill(0);
    tin.set(g.subarray(2 * r * nu, 2 * (r + 1) * nu));
    p.forward(tin, tout);
    for (let c = 0; c < m; c++) {
      t1[2 * (r * m + c)] = tout[2 * idx[c]];
      t1[2 * (r * m + c) + 1] = tout[2 * idx[c] + 1];
    }
  }
  const out = new Float64Array(2 * m * m);
  const s = 1 / mu / u; // ortho over two axes is 1 / mu, and the finer grid carries a factor u
  for (let c = 0; c < m; c++) {
    tin.fill(0);
    for (let r = 0; r < nu; r++) {
      tin[2 * r] = t1[2 * (r * m + c)];
      tin[2 * r + 1] = t1[2 * (r * m + c) + 1];
    }
    p.forward(tin, tout);
    for (let r = 0; r < m; r++) {
      const yr = tout[2 * idx[r]] * s, yi = tout[2 * idx[r] + 1] * s;
      const pr = wr[r] * wr[c] - wi[r] * wi[c];
      const pi = wr[r] * wi[c] + wi[r] * wr[c];
      out[2 * (r * m + c)] = yr * pr - yi * pi;
      out[2 * (r * m + c) + 1] = yr * pi + yi * pr;
    }
  }
  return out;
}

/**
 * Focal field (`nFft x nFft`, centred, same scaling as `fftFocalField`) of what the device displays: the FFT of the
 * displayed phase times the pixel-aperture field envelope; with crosstalk the hologram is upsampled, blurred, transformed on
 * the finer grid and the sample-and-hold factor exchanged for the pixel aperture. `rng` is needed only for flicker.
 */
export function deviceFocalField(phi: ArrayLike<number>, setup: Setup, device: Device, rng: Rng | null): Cx {
  const disp = displayedPhase(phi, device, rng);
  const n = setup.nPix, m = nFft(setup);
  if (disp.length !== n * n) throw new Error(`phi must have shape (${n}, ${n})`);
  if (device.crosstalk === null) {
    const e = fftFocalField(disp, setup);
    const s = sinc1d(setup, device.fillFactor);
    for (let iy = 0; iy < m; iy++) {
      for (let ix = 0; ix < m; ix++) {
        const k = s[iy] * s[ix], o = 2 * (iy * m + ix);
        e[o] *= k;
        e[o + 1] *= k;
      }
    }
    return e;
  }
  const u = device.upsample, nu = n * u;
  const psi = crosstalk(disp, device);
  const amp = inputAmplitude(setup);
  const g = new Float64Array(2 * nu * nu);
  for (let iy = 0; iy < nu; iy++) {
    for (let ix = 0; ix < nu; ix++) {
      const a = amp[Math.floor(iy / u) * n + Math.floor(ix / u)], q = iy * nu + ix;
      g[2 * q] = a * Math.cos(psi[q]);
      g[2 * q + 1] = a * Math.sin(psi[q]);
    }
  }
  const e = upsampledWindow(g, setup, u);
  const sw = swapFactor(setup, device);
  for (let iy = 0; iy < m; iy++) {
    for (let ix = 0; ix < m; ix++) {
      const k = sw[iy] * sw[ix], o = 2 * (iy * m + ix);
      e[o] *= k;
      e[o + 1] *= k;
    }
  }
  return e;
}
