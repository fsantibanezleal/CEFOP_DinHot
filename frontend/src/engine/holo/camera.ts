/**
 * Emulated camera for closed-loop methods: per-trap gain error, additive noise, blur and edge roll-off.
 *
 * Python counterpart: `core/camera.py`. EMULATION, not a model of a specific sensor: every error is a parameter with a stated
 * meaning (gain `exp(s z - s^2 / 2)` from a stream seeded by `(seed, trap id)`, additive Gaussian noise in the units of `I_m`
 * from the camera's own stream, Gaussian blur of sigma `blurBins` over a `+-ceil(3 sigma)` window, the pixel-aperture roll-off).
 * The seeds are mixed with 32-bit integer arithmetic exactly as Python does modulo 2^32.
 */
import type { Cx } from './fft';
import { sinc1d } from './device';
import { trapBins } from './forward';
import { type Setup, nFft } from './geometry';
import { Rng } from './rng';
import type { TrapSet } from './traps';

export class EmulatedCamera {
  readonly seed: number;
  readonly gainRms: number;
  readonly noiseRms: number;
  readonly blurBins: number;
  readonly rolloff: boolean;
  readonly fillFactor: number;
  private readonly noise: Rng;

  constructor(seed: number, o: { gainRms?: number; noiseRms?: number; blurBins?: number; rolloff?: boolean; fillFactor?: number } = {}) {
    const gainRms = o.gainRms ?? 0.05, noiseRms = o.noiseRms ?? 0, blurBins = o.blurBins ?? 0, fillFactor = o.fillFactor ?? 1;
    for (const [name, v] of [['gain_rms', gainRms], ['noise_rms', noiseRms], ['blur_bins', blurBins]] as const) {
      if (!(Number.isFinite(v) && v >= 0)) throw new Error(`${name} must be finite and >= 0, got ${v}`);
    }
    if (!(Number.isFinite(fillFactor) && fillFactor > 0 && fillFactor <= 1)) throw new Error('fill_factor must be in (0, 1]');
    new Rng(seed); // validates the seed
    this.seed = seed;
    this.gainRms = gainRms;
    this.noiseRms = noiseRms;
    this.blurBins = blurBins;
    this.rolloff = o.rolloff ?? true;
    this.fillFactor = fillFactor;
    this.noise = new Rng((Math.imul(seed, 0x9e3779b1) + 0x1234567) >>> 0);
  }

  /** The fixed gain of one trap id. */
  gain(trapId: number): number {
    const s = this.gainRms;
    if (s === 0) return 1;
    const z = new Rng((Math.imul(this.seed, 0x9e3779b1) + Math.imul(trapId + 1, 0x85ebca6b)) >>> 0).normal();
    return Math.exp(s * z - 0.5 * s * s);
  }

  /** Measured trap intensities (units of `I_m = |V|^2`) from the centred focal field `e`. */
  measure(e: Cx, setup: Setup, traps: TrapSet, rng: Rng | null = null): Float64Array {
    const m = nFft(setup);
    if (e.length !== 2 * m * m) throw new Error(`focal field must have shape (${m}, ${m})`);
    const k = setup.pad ** 2 / setup.nPix ** 2;
    const inten = (iy: number, ix: number): number => (e[2 * (iy * m + ix)] ** 2 + e[2 * (iy * m + ix) + 1] ** 2) * k;
    const { iy, ix } = trapBins(setup, traps);
    const vals = new Float64Array(traps.length);
    if (this.blurBins > 0) {
      const r = Math.ceil(3 * this.blurBins);
      const g1 = Float64Array.from({ length: 2 * r + 1 }, (_, i) => Math.exp(-0.5 * ((i - r) / this.blurBins) ** 2));
      for (let t = 0; t < vals.length; t++) {
        const a = iy[t], b = ix[t];
        let num = 0, den = 0;
        for (let y = Math.max(a - r, 0); y < Math.min(a + r + 1, m); y++) {
          for (let x = Math.max(b - r, 0); x < Math.min(b + r + 1, m); x++) {
            const w = g1[y - a + r] * g1[x - b + r];
            num += w * inten(y, x);
            den += w;
          }
        }
        vals[t] = num / den;
      }
    } else {
      for (let t = 0; t < vals.length; t++) vals[t] = inten(iy[t], ix[t]);
    }
    if (this.rolloff) {
      const s = Float64Array.from(sinc1d(setup, this.fillFactor), (v) => v * v);
      for (let t = 0; t < vals.length; t++) vals[t] *= s[iy[t]] * s[ix[t]];
    }
    for (let t = 0; t < vals.length; t++) vals[t] *= this.gain(traps.ids[t]);
    if (this.noiseRms > 0) {
      const z = (rng ?? this.noise).normalArray(vals.length);
      for (let t = 0; t < vals.length; t++) vals[t] += this.noiseRms * z[t];
    }
    for (let t = 0; t < vals.length; t++) vals[t] = Math.max(vals[t], 0);
    return vals;
  }
}
