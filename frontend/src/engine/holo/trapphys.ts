/**
 * Trap physics: gradient-force stiffness of a Rayleigh bead and dipole-trap depth and frequencies of an atom.
 *
 * Python counterpart: `core/trapphys.py` (equations and sources documented there: Bouloumis and Nic Chormaic arXiv 2001.07359
 * for the bead, Grimm, Weidemuller and Ovchinnikov 2000 for the atom). Names carry their units. Constants: SI 2019 exact
 * values and the CODATA 2018 value of eps0.
 */
export const C_M_PER_S = 299792458;
export const KB_J_PER_K = 1.380649e-23;
export const H_J_S = 6.62607015e-34;
export const HBAR_J_S = H_J_S / (2 * Math.PI);
export const EPS0_F_PER_M = 8.8541878128e-12;

function pos(name: string, v: number): number {
  if (!(typeof v === 'number' && Number.isFinite(v) && v > 0)) throw new Error(`${name} must be finite and positive, got ${v}`);
  return v;
}

/** `alpha_0 = 4 pi r^3 eps0 (eps_r - 1) / (eps_r + 2)` with `eps_r = (n_particle / n_medium)^2`. */
export function rayleighPolarizabilityFm2(radiusM: number, nParticle: number, nMedium: number): number {
  const r = pos('radius_m', radiusM), np = pos('n_particle', nParticle), nm = pos('n_medium', nMedium);
  const er = (np / nm) ** 2;
  return (4 * Math.PI * r ** 3 * EPS0_F_PER_M * (er - 1)) / (er + 2);
}

/** `kappa = -alpha / (2 c eps0) d^2 I / dx^2` along one axis. */
export const gradientStiffnessNPerM = (alphaFm2: number, curvatureWPerM4: number): number =>
  (-alphaFm2 / (2 * C_M_PER_S * EPS0_F_PER_M)) * curvatureWPerM4;

/** `I0 = 2 P / (pi w0^2)`. */
export const gaussianPeakIntensityWPerM2 = (powerW: number, waistM: number): number =>
  (2 * pos('power_w', powerW)) / (Math.PI * pos('waist_m', waistM) ** 2);

/** `kappa = 2 alpha I0 / (c eps0 w0^2)`. */
export const gaussianStiffnessNPerM = (alphaFm2: number, peakWPerM2: number, waistM: number): number =>
  (2 * alphaFm2 * peakWPerM2) / (C_M_PER_S * EPS0_F_PER_M * pos('waist_m', waistM) ** 2);

/** Local stiffness `[kappa_xx, kappa_yy]` (N/m) at every pixel of a focal intensity map (3-point central differences). */
export function stiffnessMap(
  map: ArrayLike<number>, ny: number, nx: number, spacingM: number, intensityScaleWPerM2: number, alphaFm2: number,
): [Float64Array, Float64Array] {
  if (map.length !== ny * nx || Math.min(ny, nx) < 3) throw new Error('intensity_map must be a finite 2D array of at least 3 x 3');
  for (let i = 0; i < map.length; i++) if (!Number.isFinite(map[i])) throw new Error('intensity_map must be a finite 2D array of at least 3 x 3');
  const dx = pos('spacing_m', spacingM), sc = pos('intensity_scale_W_per_m2', intensityScaleWPerM2);
  const ph = Float64Array.from(map, (v) => v * sc);
  const d2x = new Float64Array(ny * nx), d2y = new Float64Array(ny * nx);
  for (let iy = 0; iy < ny; iy++) {
    for (let ix = 1; ix < nx - 1; ix++) d2x[iy * nx + ix] = (ph[iy * nx + ix + 1] - 2 * ph[iy * nx + ix] + ph[iy * nx + ix - 1]) / dx ** 2;
    d2x[iy * nx] = d2x[iy * nx + 1];
    d2x[iy * nx + nx - 1] = d2x[iy * nx + nx - 2];
  }
  for (let ix = 0; ix < nx; ix++) {
    for (let iy = 1; iy < ny - 1; iy++) d2y[iy * nx + ix] = (ph[(iy + 1) * nx + ix] - 2 * ph[iy * nx + ix] + ph[(iy - 1) * nx + ix]) / dx ** 2;
    d2y[ix] = d2y[nx + ix];
    d2y[(ny - 1) * nx + ix] = d2y[(ny - 2) * nx + ix];
  }
  return [d2x.map((v) => gradientStiffnessNPerM(alphaFm2, v)), d2y.map((v) => gradientStiffnessNPerM(alphaFm2, v))];
}

/** `z_R = pi w0^2 / lambda`. */
export const rayleighRangeM = (waistM: number, wavelengthM: number): number => (Math.PI * pos('waist_m', waistM) ** 2) / pos('wavelength_m', wavelengthM);

function checkAtom(omega0: number, gamma: number, delta: number): [number, number] {
  const o = pos('omega0_rad_s', omega0), g = pos('gamma_rad_s', gamma);
  if (!Number.isFinite(delta) || delta === 0) throw new Error('delta_rad_s must be finite and non-zero');
  return [o, g];
}

/** `U_dip = (3 pi c^2 / (2 omega0^3)) (Gamma / Delta) I`; negative for red detuning. */
export function dipolePotentialJ(intensityWPerM2: number, omega0: number, gamma: number, delta: number): number {
  const [o, g] = checkAtom(omega0, gamma, delta);
  return ((3 * Math.PI * C_M_PER_S ** 2) / (2 * o ** 3)) * (g / delta) * intensityWPerM2;
}

/** `Gamma_sc = (3 pi c^2 / (2 hbar omega0^3)) (Gamma / Delta)^2 I`. */
export function scatteringRatePerS(intensityWPerM2: number, omega0: number, gamma: number, delta: number): number {
  const [o, g] = checkAtom(omega0, gamma, delta);
  return ((3 * Math.PI * C_M_PER_S ** 2) / (2 * HBAR_J_S * o ** 3)) * (g / delta) ** 2 * intensityWPerM2;
}

/** `U_hat = -U_dip(I0)` of a focused Gaussian beam; throws for blue detuning (no trap). */
export function dipoleTrapDepthJ(powerW: number, waistM: number, omega0: number, gamma: number, delta: number): number {
  const u = dipolePotentialJ(gaussianPeakIntensityWPerM2(powerW, waistM), omega0, gamma, delta);
  if (u >= 0) throw new Error('the dipole potential is repulsive (blue detuning): there is no trap');
  return -u;
}

/** `[omega_r, omega_z]`: `sqrt(4 U / (m w0^2))` and `sqrt(2 U / (m z_R^2))`. */
export function trapFrequenciesRadS(depthJ: number, massKg: number, waistM: number, wavelengthM: number): [number, number] {
  const d = pos('depth_J', depthJ), m = pos('mass_kg', massKg), w = pos('waist_m', waistM);
  const zr = rayleighRangeM(w, wavelengthM);
  return [Math.sqrt((4 * d) / (m * w ** 2)), Math.sqrt((2 * d) / (m * zr ** 2))];
}
