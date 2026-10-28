// Pure decoding and display maths of the workbench: the trace's compact encodings (base64 bytes, run-length shapes), their
// physical units, and the device effects the Hologram group shows on the phase mask (quantization, the response curve and the
// pixel crosstalk). Nothing here touches the DOM, so every function is unit-tested (decode.test.ts).
//
// The device model is the engine's (data-pipeline/pipeline/model/holo/core/device.py): wrap, quantize to 2^b levels, the
// response 2 pi (phi / 2 pi)^gamma, then the crosstalk blur K = F^-1 { exp[-(|kx|^q + |ky|^q) / sigma^q] } on the phase
// upsampled to upsample x upsample samples per pixel (k in cycles per SLM pixel). The kernel is separable, so the blur read at
// each SLM pixel centre is a separable convolution of the phase with 1D weights; flicker is a random kick and is not drawn.
import type { Device } from '../lib/contract.types';

export const TWO_PI = 2 * Math.PI;

/** Standard base64 to bytes. */
export function b64ToU8(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

/** The trace's shape mask: alternating run lengths, false first (core/trace.py), expanded to `total` cells. */
export function decodeRle(runs: readonly number[], total: number): Uint8Array {
  const out = new Uint8Array(total);
  let at = 0;
  let on = 0;
  for (const run of runs) {
    if (!Number.isInteger(run) || run < 0) throw new Error(`mask_rle: run ${run} is not a count`);
    if (on) out.fill(1, at, Math.min(total, at + run));
    at += run;
    on ^= 1;
  }
  if (at !== total) throw new Error(`mask_rle covers ${at} cells, the crop has ${total}`);
  return out;
}

/** The phase byte (256 levels over [0, 2 pi)) as radians. */
export function phaseFromU8(u8: Uint8Array): Float32Array {
  const out = new Float32Array(u8.length);
  for (let i = 0; i < u8.length; i++) out[i] = (u8[i] / 256) * TWO_PI;
  return out;
}

/** The focal byte (db_floor..0 mapped to 0..255) as dB relative to the mean trap. */
export function dbFromU8(u8: Uint8Array, dbFloor: number): Float32Array {
  const out = new Float32Array(u8.length);
  for (let i = 0; i < u8.length; i++) out[i] = dbFloor * (1 - u8[i] / 255);
  return out;
}

/** The axial byte map (z rows by x columns) in the same dB scale as the focal map. */
export const axialDb = dbFromU8;

/** Linear intensities as dB relative to `ref`, floored at `dbFloor` (the engine's focal map is linear; the trace's is dB). */
export function linearToDb(linear: ArrayLike<number>, ref: number, dbFloor: number): Float32Array {
  const out = new Float32Array(linear.length);
  const r = ref > 0 ? ref : 1;
  for (let i = 0; i < linear.length; i++) out[i] = Math.max(dbFloor, Math.min(0, 10 * Math.log10(Math.max(linear[i], 1e-300) / r)));
  return out;
}

export const wrap2pi = (p: number): number => ((p % TWO_PI) + TWO_PI) % TWO_PI;

/** The level (0 to 2^bits - 1) the device shows for a phase: nearest of 2^bits equally spaced levels. */
export function levelOf(phase: number, bits: number): number {
  const levels = 2 ** bits;
  return Math.floor((wrap2pi(phase) / TWO_PI) * levels + 0.5) % levels;
}

/** Round the phase to the nearest of 2^bits levels (device.quantize). */
export function quantizePhase(phase: Float32Array, bits: number): Float32Array {
  const levels = 2 ** bits;
  const out = new Float32Array(phase.length);
  for (let i = 0; i < phase.length; i++) out[i] = levelOf(phase[i], bits) * (TWO_PI / levels);
  return out;
}

/** The response curve of the device: 2 pi (phi / 2 pi)^gamma. */
export function applyResponse(phase: Float32Array, gamma: number): Float32Array {
  if (gamma === 1) return phase;
  const out = new Float32Array(phase.length);
  for (let i = 0; i < phase.length; i++) out[i] = TWO_PI * (phase[i] / TWO_PI) ** gamma;
  return out;
}

/**
 * The crosstalk kernel read at SLM pixel offsets -reach..reach: w[d] = sum over the `upsample` samples of a pixel of the 1D kernel
 * k(s) = (1/n) sum_m exp[-(|m| upsample / n)^q / sigma^q] cos(2 pi m s / n) with n = upsample * pixels. The 2D kernel is k(x)k(y),
 * so the blurred phase at a pixel centre is the phase convolved with w along rows and then columns. The weights are normalised to
 * sum 1 (the kernel has unit sum; truncating at `reach` pixels loses a negligible tail).
 */
export function crosstalkWeights(sigma: number, q: number, upsample: number, pixels: number, reach = 4): Float64Array {
  const n = Math.max(upsample * pixels, upsample * (2 * reach + 1));
  const transfer = new Float64Array(n / 2 + 1);
  for (let m = 0; m <= n / 2; m++) transfer[m] = Math.exp(-(((m * upsample) / n) ** q) / sigma ** q);
  const sample = (s: number): number => {
    let acc = transfer[0];
    for (let m = 1; m < n / 2; m++) acc += 2 * transfer[m] * Math.cos((TWO_PI * m * s) / n);
    acc += transfer[n / 2] * Math.cos(Math.PI * s);
    return acc / n;
  };
  const w = new Float64Array(2 * reach + 1);
  let sum = 0;
  for (let d = -reach; d <= reach; d++) {
    // the pixel centre sits at the middle sample; each pixel is `upsample` samples wide
    let acc = 0;
    for (let u = 0; u < upsample; u++) acc += sample(d * upsample + u - (upsample - 1) / 2);
    w[d + reach] = acc;
    sum += acc;
  }
  for (let i = 0; i < w.length; i++) w[i] /= sum;
  return w;
}

/** Separable circular convolution of an n x n map with the 1D weights (rows, then columns). */
export function separableBlur(map: Float32Array, n: number, w: Float64Array): Float32Array {
  const reach = (w.length - 1) / 2;
  const tmp = new Float32Array(map.length);
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      let acc = 0;
      for (let d = -reach; d <= reach; d++) acc += w[d + reach] * map[y * n + ((x + d + n) % n)];
      tmp[y * n + x] = acc;
    }
  }
  const out = new Float32Array(map.length);
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      let acc = 0;
      for (let d = -reach; d <= reach; d++) acc += w[d + reach] * tmp[((y + d + n) % n) * n + x];
      out[y * n + x] = acc;
    }
  }
  return out;
}

export type DeviceStage = 'ideal' | 'quantized' | 'crosstalk';

/** The phase of the mask at a device stage: the ideal phase, quantized (and through the response curve), or then blurred by the pixel crosstalk. */
export function stagePhase(phase: Float32Array, n: number, device: Device | null, stage: DeviceStage): Float32Array {
  if (!device || stage === 'ideal') return phase;
  let p = phase;
  if (device.bit_depth !== null) p = quantizePhase(p, device.bit_depth);
  p = applyResponse(p, device.lut_gamma);
  if (stage === 'crosstalk' && device.crosstalk) {
    p = separableBlur(p, n, crosstalkWeights(device.crosstalk.sigma_per_px, device.crosstalk.q, device.upsample, n));
  }
  return p;
}

/** The wrapped difference b - a in (-pi, pi]. */
export function phaseDifference(a: Float32Array, b: Float32Array): Float32Array {
  const out = new Float32Array(a.length);
  for (let i = 0; i < a.length; i++) {
    let d = b[i] - a[i];
    d -= TWO_PI * Math.round(d / TWO_PI);
    out[i] = d;
  }
  return out;
}

/** Local grating period (in pixels) along x at (row, col): the inverse of the phase gradient in cycles per pixel; Infinity on a flat patch. */
export function gratingPeriodPx(phase: Float32Array, n: number, row: number, col: number): number {
  const a = phase[row * n + col];
  const b = phase[row * n + Math.min(n - 1, col + 1)];
  let d = b - a;
  d -= TWO_PI * Math.round(d / TWO_PI);
  const cycles = Math.abs(d) / TWO_PI;
  return cycles < 1e-9 ? Infinity : 1 / cycles;
}

// ---- closed forms of the device effects (r2-gaps D4; each one named with its source in the view) ----

const sinc = (x: number): number => (x === 0 ? 1 : Math.sin(Math.PI * x) / (Math.PI * x));

/** First-order efficiency of a stepped grating with N phase levels over 2 pi: sinc^2(1/N) (Moreno et al., Eq. 6). */
export const quantizationEfficiency = (levels: number): number => sinc(1 / levels) ** 2;

/** Efficiency of an SLM of fill factor f: f^2, the scalar result of the Rydberg-lattice optics note (arXiv:1512.06241). */
export const fillFactorEfficiency = (fill: number): number => fill * fill;

/** The intensity roll-off at the edge of the unaliased window from the square pixel aperture: sinc^2(sqrt(fill) / 2) (device.py, derived). */
export const apertureEnvelopeAtEdge = (fill: number): number => sinc(Math.sqrt(fill) / 2) ** 2;
