/**
 * Forward models: the point-trap (direct sum) form and the zero-padded FFT form, plus propagation.
 *
 * Python counterpart: `core/forward.py` (the conventions, equations and sources are documented there). Complex arrays are
 * interleaved Float64Arrays (`re`, `im`); the focal grid is `nFft x nFft`, centred, bin (0, 0) at index `nFft / 2`.
 * - Point-trap form: `V_m = (1 / N_pix) sum_j A_j exp(i (phi_j - Delta_j^m))`, `Delta_j^m` = lens + grating + vortex
 *   (algorithms D1.0, Di Leonardo et al. 2007 eqs (1) to (4)); `I_m = |V_m|^2`.
 * - FFT form: orthonormal zero-padded FFT of the SLM field times the linear phase that moves the origin to the optical axis;
 *   at a trap on a bin, `V_m = E[bin] pad / nPix` exactly.
 * - Angular spectrum (physics-viz D1.3): `H = exp(2 pi i (z / lambda) sqrt(1 - (lambda xi)^2))` for propagating components.
 */
import { type Cx, fft1, fft2, fftfreq } from './fft';
import { type Setup, TWO_PI, focalBinM, inputAmplitude, nFft, slmAxis } from './geometry';
import { type TrapSet, checkInField, rint } from './traps';

function checkPhi(phi: ArrayLike<number>, setup: Setup): void {
  if (phi.length !== setup.nPix * setup.nPix) {
    throw new Error(`phi must have shape (${setup.nPix}, ${setup.nPix}), got length ${phi.length}`);
  }
  for (let i = 0; i < phi.length; i++) if (!Number.isFinite(phi[i])) throw new Error('phi contains NaN or infinite values');
}

/** The complex SLM field `A_j exp(i phi_j)`. */
export function slmField(phi: ArrayLike<number>, setup: Setup, amp: Float64Array = inputAmplitude(setup)): Cx {
  checkPhi(phi, setup);
  const out = new Float64Array(2 * phi.length);
  for (let i = 0; i < phi.length; i++) {
    out[2 * i] = amp[i] * Math.cos(phi[i]);
    out[2 * i + 1] = amp[i] * Math.sin(phi[i]);
  }
  return out;
}

/** Per-trap 1D factors `exp(sign i (c_z x^2 + k x x_m))` for one axis position `pos`, as `cos`/`sin` arrays. */
function axisFactor(setup: Setup, c: Float64Array, zM: number, posM: number, sign: number, re: Float64Array, im: Float64Array): void {
  const lam = setup.wavelengthM, f = setup.focalM;
  const cz = (Math.PI * zM) / (lam * f * f);
  const k = (2 * Math.PI) / (lam * f);
  for (let i = 0; i < c.length; i++) {
    const a = cz * c[i] * c[i] + k * posM * c[i];
    re[i] = Math.cos(a);
    im[i] = sign * Math.sin(a);
  }
}

/** `Delta_j^m` for one trap on the full grid (used when a vortex is present). */
function denseDelay(setup: Setup, traps: TrapSet, m: number): Float64Array {
  const n = setup.nPix, c = slmAxis(setup);
  const lam = setup.wavelengthM, f = setup.focalM;
  const out = new Float64Array(n * n);
  const cz = (Math.PI * traps.zM[m]) / (lam * f * f);
  const k = (2 * Math.PI) / (lam * f);
  for (let iy = 0; iy < n; iy++) {
    for (let ix = 0; ix < n; ix++) {
      const x = c[ix], y = c[iy];
      out[iy * n + ix] = cz * (x * x + y * y) + k * (x * traps.xM[m] + y * traps.yM[m]) + traps.charge[m] * Math.atan2(y, x);
    }
  }
  return out;
}

/** `V_m = (1 / N_pix) sum_j f_j exp(-i Delta_j^m)` for an arbitrary complex SLM field (a vector of `2 M` interleaved). */
export function pointTrapProjection(field: Cx, setup: Setup, traps: TrapSet): Cx {
  checkInField(setup, traps);
  const n = setup.nPix;
  if (field.length !== 2 * n * n) throw new Error('field must be a finite complex array of shape (n_pix, n_pix)');
  const c = slmAxis(setup);
  const out = new Float64Array(2 * traps.length);
  const gxr = new Float64Array(n), gxi = new Float64Array(n), gyr = new Float64Array(n), gyi = new Float64Array(n);
  const n2 = n * n;
  for (let m = 0; m < traps.length; m++) {
    if (traps.charge[m] === 0) {
      axisFactor(setup, c, traps.zM[m], traps.xM[m], -1, gxr, gxi);
      axisFactor(setup, c, traps.zM[m], traps.yM[m], -1, gyr, gyi);
      let vr = 0, vi = 0;
      for (let iy = 0; iy < n; iy++) {
        let tr = 0, ti = 0;
        const row = 2 * iy * n;
        for (let ix = 0; ix < n; ix++) {
          const fr = field[row + 2 * ix], fi = field[row + 2 * ix + 1];
          tr += fr * gxr[ix] - fi * gxi[ix];
          ti += fr * gxi[ix] + fi * gxr[ix];
        }
        vr += gyr[iy] * tr - gyi[iy] * ti;
        vi += gyr[iy] * ti + gyi[iy] * tr;
      }
      out[2 * m] = vr / n2;
      out[2 * m + 1] = vi / n2;
    } else {
      const d = denseDelay(setup, traps, m);
      let vr = 0, vi = 0;
      for (let i = 0; i < n2; i++) {
        const cs = Math.cos(d[i]), sn = -Math.sin(d[i]);
        vr += field[2 * i] * cs - field[2 * i + 1] * sn;
        vi += field[2 * i] * sn + field[2 * i + 1] * cs;
      }
      out[2 * m] = vr / n2;
      out[2 * m + 1] = vi / n2;
    }
  }
  return out;
}

/** `V_m` of the hologram `phi` (point-trap form). */
export function pointTrapFields(phi: ArrayLike<number>, setup: Setup, traps: TrapSet, amp?: Float64Array): Cx {
  return pointTrapProjection(slmField(phi, setup, amp), setup, traps);
}

/** The SLM field `F_j = sum_m c_m exp(+i Delta_j^m)` (no `1 / N_pix`): the adjoint direction of the projection. */
export function pointTrapBackproject(coeffs: Cx, setup: Setup, traps: TrapSet): Cx {
  checkInField(setup, traps);
  if (coeffs.length !== 2 * traps.length) throw new Error(`coeffs must be a finite vector of length ${traps.length}`);
  for (let i = 0; i < coeffs.length; i++) if (!Number.isFinite(coeffs[i])) throw new Error(`coeffs must be a finite vector of length ${traps.length}`);
  const n = setup.nPix;
  const c = slmAxis(setup);
  const out = new Float64Array(2 * n * n);
  const gxr = new Float64Array(n), gxi = new Float64Array(n), gyr = new Float64Array(n), gyi = new Float64Array(n);
  for (let m = 0; m < traps.length; m++) {
    const cr = coeffs[2 * m], ci = coeffs[2 * m + 1];
    if (traps.charge[m] === 0) {
      axisFactor(setup, c, traps.zM[m], traps.xM[m], 1, gxr, gxi);
      axisFactor(setup, c, traps.zM[m], traps.yM[m], 1, gyr, gyi);
      for (let iy = 0; iy < n; iy++) {
        const tr = cr * gyr[iy] - ci * gyi[iy];
        const ti = cr * gyi[iy] + ci * gyr[iy];
        const row = 2 * iy * n;
        for (let ix = 0; ix < n; ix++) {
          out[row + 2 * ix] += tr * gxr[ix] - ti * gxi[ix];
          out[row + 2 * ix + 1] += tr * gxi[ix] + ti * gxr[ix];
        }
      }
    } else {
      const d = denseDelay(setup, traps, m);
      for (let i = 0; i < n * n; i++) {
        const cs = Math.cos(d[i]), sn = Math.sin(d[i]);
        out[2 * i] += cr * cs - ci * sn;
        out[2 * i + 1] += cr * sn + ci * cs;
      }
    }
  }
  return out;
}

/** Phase ramp `exp(+2 pi i c k / nFft)` along one focal axis (k = -nFft/2 .. nFft/2 - 1), as `re`, `im`. */
export function ramp(setup: Setup): { re: Float64Array; im: Float64Array } {
  const m = nFft(setup);
  const re = new Float64Array(m), im = new Float64Array(m);
  const c = (setup.nPix - 1) / 2;
  for (let j = 0; j < m; j++) {
    const a = (TWO_PI * c * (j - Math.floor(m / 2))) / m;
    re[j] = Math.cos(a);
    im[j] = Math.sin(a);
  }
  return { re, im };
}

/** Centred, zero-padded, orthonormal FFT of the SLM field: shape `nFft x nFft`, Parseval holds. */
export function fftFocalField(phi: ArrayLike<number>, setup: Setup, amp?: Float64Array): Cx {
  return fftFocalFieldOf(slmField(phi, setup, amp), setup);
}

/** Same as `fftFocalField` for an already built complex SLM field. */
export function fftFocalFieldOf(field: Cx, setup: Setup): Cx {
  const m = nFft(setup), n = setup.nPix, h = Math.floor(m / 2);
  const a = new Float64Array(2 * m * m);
  for (let iy = 0; iy < n; iy++) a.set(field.subarray(2 * iy * n, 2 * (iy + 1) * n), 2 * iy * m);
  fft2(a, m, m, false, n, true);
  const r = ramp(setup);
  const out = new Float64Array(2 * m * m);
  const s = 1 / m; // orthonormal: 1 / sqrt(m^2)
  for (let jy = 0; jy < m; jy++) {
    const sy = (jy - h + m) % m;
    for (let jx = 0; jx < m; jx++) {
      const sx = (jx - h + m) % m;
      const pr = r.re[jy] * r.re[jx] - r.im[jy] * r.im[jx];
      const pi = r.re[jy] * r.im[jx] + r.im[jy] * r.re[jx];
      const fr = a[2 * (sy * m + sx)] * s, fi = a[2 * (sy * m + sx) + 1] * s;
      const o = 2 * (jy * m + jx);
      out[o] = fr * pr - fi * pi;
      out[o + 1] = fr * pi + fi * pr;
    }
  }
  return out;
}

function checkFocal(e: Cx, setup: Setup): void {
  const m = nFft(setup);
  if (e.length !== 2 * m * m) throw new Error(`focal field must have shape (${m}, ${m}), got length ${e.length / 2}`);
}

/** Inverse of `fftFocalField` back to the SLM grid (complex field cropped to `nPix x nPix`). */
export function fftInverse(e: Cx, setup: Setup): Cx {
  checkFocal(e, setup);
  const m = nFft(setup), n = setup.nPix, h = Math.floor(m / 2);
  const r = ramp(setup);
  const a = new Float64Array(2 * m * m);
  for (let iy = 0; iy < m; iy++) {
    const sy = (iy + h) % m;
    for (let ix = 0; ix < m; ix++) {
      const sx = (ix + h) % m;
      const pr = r.re[sy] * r.re[sx] - r.im[sy] * r.im[sx];
      const pi = -(r.re[sy] * r.im[sx] + r.im[sy] * r.re[sx]); // conjugate of the ramp product
      const er = e[2 * (sy * m + sx)], ei = e[2 * (sy * m + sx) + 1];
      const o = 2 * (iy * m + ix);
      a[o] = er * pr - ei * pi;
      a[o + 1] = er * pi + ei * pr;
    }
  }
  fft2(a, m, m, true, n, false);
  const out = new Float64Array(2 * n * n);
  for (let iy = 0; iy < n; iy++) {
    for (let ix = 0; ix < n; ix++) {
      out[2 * (iy * n + ix)] = a[2 * (iy * m + ix)] * m; // fft2 inverse divides by m^2, orthonormal wants 1 / m
      out[2 * (iy * n + ix) + 1] = a[2 * (iy * m + ix) + 1] * m;
    }
  }
  return out;
}

/** Array indices `{iy, ix}` of the FFT bin nearest to each trap (throws `OutOfFieldError` if outside). */
export function trapBins(setup: Setup, traps: TrapSet): { iy: Int32Array; ix: Int32Array } {
  checkInField(setup, traps);
  const b = focalBinM(setup), h = Math.floor(nFft(setup) / 2);
  return {
    iy: Int32Array.from(traps.yM, (v) => rint(v / b) + h),
    ix: Int32Array.from(traps.xM, (v) => rint(v / b) + h),
  };
}

/** `V_m` read from the FFT field at the bin nearest to each trap: `E[bin] pad / nPix`. */
export function trapFieldsFromFft(e: Cx, setup: Setup, traps: TrapSet): Cx {
  checkFocal(e, setup);
  const { iy, ix } = trapBins(setup, traps);
  const m = nFft(setup), s = setup.pad / setup.nPix;
  const out = new Float64Array(2 * traps.length);
  for (let t = 0; t < traps.length; t++) {
    const o = 2 * (iy[t] * m + ix[t]);
    out[2 * t] = e[o] * s;
    out[2 * t + 1] = e[o + 1] * s;
  }
  return out;
}

/** `s = (lambda xi_y)^2 + (lambda xi_x)^2` is returned per axis pair on the fly: the propagation factor per bin. */
function transferParts(setup: Setup): { lam: number; sq: Float64Array } {
  const m = nFft(setup);
  const lam = setup.wavelengthM / setup.nImm;
  const xi = fftfreq(m, focalBinM(setup));
  const sq = new Float64Array(m);
  for (let i = 0; i < m; i++) sq[i] = (lam * xi[i]) ** 2;
  return { lam, sq };
}

/** Propagate a focal-plane field by `dzM` with the plain angular-spectrum transfer function (evanescent components removed). */
export function angularSpectrum(e: Cx, dzM: number, setup: Setup): Cx {
  checkFocal(e, setup);
  if (!Number.isFinite(dzM)) throw new Error('dz_m must be finite');
  const m = nFft(setup), h = Math.floor(m / 2);
  const { lam, sq } = transferParts(setup);
  const a = new Float64Array(2 * m * m);
  for (let iy = 0; iy < m; iy++) {
    for (let ix = 0; ix < m; ix++) {
      const so = 2 * (((iy + h) % m) * m + ((ix + h) % m));
      a.set([e[so], e[so + 1]], 2 * (iy * m + ix));
    }
  }
  fft2(a, m, m, false);
  for (let iy = 0; iy < m; iy++) {
    for (let ix = 0; ix < m; ix++) {
      const s = sq[iy] + sq[ix];
      const o = 2 * (iy * m + ix);
      if (s < 1) {
        const ph = 2 * Math.PI * (dzM / lam) * Math.sqrt(1 - s);
        const cs = Math.cos(ph), sn = Math.sin(ph);
        const ar = a[o], ai = a[o + 1];
        a[o] = ar * cs - ai * sn;
        a[o + 1] = ar * sn + ai * cs;
      } else {
        a[o] = 0;
        a[o + 1] = 0;
      }
    }
  }
  fft2(a, m, m, true);
  const out = new Float64Array(2 * m * m);
  for (let iy = 0; iy < m; iy++) {
    for (let ix = 0; ix < m; ix++) {
      const so = 2 * (iy * m + ix);
      const o = 2 * (((iy + h) % m) * m + ((ix + h) % m));
      out[o] = a[so];
      out[o + 1] = a[so + 1];
    }
  }
  return out;
}

export interface AxialCut {
  /** `nz x nFft` intensity in the units of `I_m = |V|^2`. */
  intensity: Float64Array;
  zM: Float64Array;
  lateralM: Float64Array;
  nz: number;
  nLateral: number;
}

/** numpy `linspace(a, b, n)`. */
export function linspace(a: number, b: number, n: number): Float64Array {
  const out = new Float64Array(n);
  if (n === 1) return out.fill(a);
  const step = (b - a) / (n - 1);
  for (let i = 0; i < n; i++) out[i] = a + i * step;
  out[n - 1] = b;
  return out;
}

/**
 * Intensity slice through the focal volume: `yM` given gives the xz plane, `xM` given the yz plane (exactly one).
 * Python counterpart: `forward.axial_cut` (the paraxial scalar model; z of a displaced trap exact for |z| << f).
 */
export function axialCut(
  phi: ArrayLike<number>,
  setup: Setup,
  opts: { xM?: number | null; yM?: number | null; zRangeM: [number, number]; nz: number },
): AxialCut {
  const xM = opts.xM ?? null, yM = opts.yM ?? null;
  if ((xM === null) === (yM === null)) throw new Error('give exactly one of x_m (yz plane) or y_m (xz plane)');
  const nz = opts.nz;
  if (!Number.isInteger(nz) || nz < 1) throw new Error('nz must be a positive integer');
  const [z0, z1] = opts.zRangeM;
  if (!(Number.isFinite(z0) && Number.isFinite(z1))) throw new Error('z_range_m must be finite');
  const posM = (yM ?? xM) as number;
  if (!Number.isFinite(posM)) throw new Error('the cut position must be finite');
  const m = nFft(setup), h = Math.floor(m / 2);
  const b = focalBinM(setup);
  const kFix = rint(posM / b);
  if (Math.abs(kFix) >= h) throw new Error('the cut lies outside the focal grid');
  const e = fftFocalField(phi, setup);
  // spec = fft2(ifftshift(e)) in FFT frequency order [ky, kx]
  const a = new Float64Array(2 * m * m);
  for (let iy = 0; iy < m; iy++) {
    for (let ix = 0; ix < m; ix++) {
      const so = 2 * (((iy + h) % m) * m + ((ix + h) % m));
      a.set([e[so], e[so + 1]], 2 * (iy * m + ix));
    }
  }
  fft2(a, m, m, false);
  const transposed = yM === null; // the fixed axis must be the first one
  const z = linspace(z0, z1, nz);
  const { lam, sq } = transferParts(setup);
  const ff = fftfreq(m, 1);
  const selR = new Float64Array(m), selI = new Float64Array(m);
  for (let i = 0; i < m; i++) {
    selR[i] = Math.cos(2 * Math.PI * ff[i] * kFix);
    selI[i] = Math.sin(2 * Math.PI * ff[i] * kFix);
  }
  const scale = setup.pad ** 2 / setup.nPix ** 2;
  const out = new Float64Array(nz * m);
  const row = new Float64Array(2 * m);
  const kz = new Float64Array(m * m);
  const prop = new Uint8Array(m * m);
  for (let ia = 0; ia < m; ia++) {
    for (let ib = 0; ib < m; ib++) {
      const s = sq[ia] + sq[ib];
      prop[ia * m + ib] = s < 1 ? 1 : 0;
      kz[ia * m + ib] = s < 1 ? Math.sqrt(1 - s) : 0;
    }
  }
  for (let iz = 0; iz < nz; iz++) {
    row.fill(0);
    const w = 2 * Math.PI * (z[iz] / lam);
    for (let ia = 0; ia < m; ia++) {
      for (let ib = 0; ib < m; ib++) {
        const q = ia * m + ib;
        if (!prop[q]) continue;
        const so = transposed ? 2 * (ib * m + ia) : 2 * q; // spec.T when the yz plane is asked
        const ph = w * kz[q];
        const hr = Math.cos(ph), hi = Math.sin(ph);
        const sr = a[so] * hr - a[so + 1] * hi;
        const si = a[so] * hi + a[so + 1] * hr;
        row[2 * ib] += selR[ia] * sr - selI[ia] * si;
        row[2 * ib + 1] += selR[ia] * si + selI[ia] * sr;
      }
    }
    for (let ib = 0; ib < 2 * m; ib++) row[ib] /= m;
    const line = fft1(row, true);
    for (let j = 0; j < m; j++) {
      const sj = (j - h + m) % m; // fftshift
      out[iz * m + j] = (line[2 * sj] ** 2 + line[2 * sj + 1] ** 2) * scale;
    }
  }
  const lateral = new Float64Array(m);
  for (let i = 0; i < m; i++) lateral[i] = (i - h) * b;
  return { intensity: out, zM: z, lateralM: lateral, nz, nLateral: m };
}
