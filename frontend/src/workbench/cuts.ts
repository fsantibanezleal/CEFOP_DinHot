// The axial cuts of a hologram, asked of the live engine. The engine's client offers the xz cut through a trap (the plane at that trap's
// y). The yz cut through a trap is the same cut of the transposed problem: the hologram transposed, every trap's x and y exchanged, so
// the plane the engine cuts is the original plane at the trap's x. That is exact for a square SLM with a beam symmetric in x and y (the
// engine's gaussian and flat beams are); the aberration, which is not symmetric, is added to the phase before the transposition and
// removed from the record. `cuts.test.ts` holds the identity against the engine's own yz cut.
import type { ParamsRecord } from '../lib/contract.types';
import { makeSetup } from '../engine/holo/geometry';
import { phaseFromCoeffs } from '../engine/holo/zernike';

export type Plane = 'xz' | 'yz';

export interface CutRequest {
  phase: Float64Array;
  params: ParamsRecord;
  trapId: number;
  nz: number;
}

/** `out[iy * n + ix] = a[ix * n + iy]` for an n by n array. */
export function transpose(a: ArrayLike<number>, n: number): Float64Array {
  const out = new Float64Array(n * n);
  for (let iy = 0; iy < n; iy++) for (let ix = 0; ix < n; ix++) out[iy * n + ix] = a[ix * n + iy];
  return out;
}

/** The Noll coefficients of a params record as the engine reads them (index = j - 1). */
function nollCoeffs(p: ParamsRecord): number[] {
  const noll = p.aberration?.noll ?? {};
  const top = Math.max(1, ...Object.keys(noll).map(Number));
  const c = new Array<number>(top).fill(0);
  for (const [k, v] of Object.entries(noll)) c[Number(k) - 1] = Number(v);
  return c;
}

/** The request for the engine's `axialCut` that yields the cut in `plane` through trap `trapId` of `phase` (an `n` by `n` SLM phase). */
export function cutRequest(plane: Plane, phase: ArrayLike<number>, n: number, params: ParamsRecord, trapId: number, nz: number): CutRequest {
  if (plane === 'xz') return { phase: Float64Array.from(phase), params, trapId, nz };
  if (params.target.kind !== 'traps') throw new Error('an axial cut needs a trap target');
  let phi = Float64Array.from(phase);
  if (params.aberration) {
    const s = params.setup;
    const setup = makeSetup({
      wavelengthM: s.wavelength_nm * 1e-9,
      focalM: s.focal_mm * 1e-3,
      na: s.na,
      nImm: s.n_imm,
      nPix: s.n_pix,
      pitchM: s.pitch_um * 1e-6,
      pad: s.pad,
      beam: s.beam.kind,
      waistFrac: 'waist_frac' in s.beam ? s.beam.waist_frac : 1,
    });
    const ab = phaseFromCoeffs(nollCoeffs(params), setup);
    phi = phi.map((v, i) => v + ab[i]);
  }
  const swapped = params.target.traps.map((t) => ({ ...t, x_um: t.y_um, y_um: t.x_um }));
  return { phase: transpose(phi, n), params: { ...params, aberration: null, target: { kind: 'traps', traps: swapped } }, trapId, nz };
}
