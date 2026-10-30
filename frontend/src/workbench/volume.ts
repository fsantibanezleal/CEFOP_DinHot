// The focal volume from the engine's cuts (V6). The engine's client computes an axial cut through a trap: the xz plane at that trap's y, and
// (cuts.ts) the yz plane at its x. The volume of a trap array is sampled by those planes through every distinct row and column of traps,
// so each trap lies in at least two planes; the 3D view draws the voxels of those planes above a fraction of the peak. It is a sampling of
// the computed field, not an interpolation of it: between the planes nothing is drawn, and the card says so.
import type { Trap } from '../lib/contract.types';
import type { Plane } from './cuts';

export interface Slab {
  plane: Plane;
  /** Where the plane sits on its fixed axis: y for xz, x for yz, in micrometres. */
  posUm: number;
  trapId: number;
  /** `nz x nx` intensity relative to the mean trap (linear), row = z. */
  lin: Float32Array;
  nx: number;
  nz: number;
  zUm: [number, number];
  /** Focal bin, micrometres: the lateral coordinate of column `c` is `(c - floor(nx / 2)) * binUm`. */
  binUm: number;
}

export interface VolumePoints {
  /** x, y, z in micrometres (optical axis z), three floats per point. */
  xyz: Float32Array;
  /** The colour coordinate of each point, 0 to 1. */
  u: Float32Array;
  n: number;
  /** The peak the threshold is a fraction of, I_m units. */
  peak: number;
  /** Points kept per slab, in slab order. */
  perSlab: number[];
  /** True when the points were thinned to the cap. */
  thinned: boolean;
}

/** The distinct positions of the traps on the axis a plane fixes, each with the id of one trap there; thinned evenly above `cap`. */
export function slabPlan(traps: readonly Trap[], plane: Plane, cap: number): { posUm: number; trapId: number }[] {
  const seen = new Map<number, number>();
  for (const t of traps) {
    const pos = Math.round((plane === 'xz' ? t.y_um : t.x_um) * 1e3) / 1e3;
    if (!seen.has(pos)) seen.set(pos, t.id);
  }
  const all = [...seen.entries()].sort((a, b) => a[0] - b[0]).map(([posUm, trapId]) => ({ posUm, trapId }));
  if (all.length <= cap) return all;
  const out: { posUm: number; trapId: number }[] = [];
  for (let k = 0; k < cap; k++) out.push(all[Math.round((k * (all.length - 1)) / (cap - 1))]);
  return out;
}

/** The slab's lateral coordinate and z of a cell. */
export function cellUm(s: Slab, col: number, row: number): { lateral: number; z: number } {
  return { lateral: (col - Math.floor(s.nx / 2)) * s.binUm, z: s.nz > 1 ? s.zUm[0] + (row / (s.nz - 1)) * (s.zUm[1] - s.zUm[0]) : s.zUm[0] };
}

/** The peak of the volume over all the slabs. */
export function volumePeak(slabs: readonly Slab[]): number {
  let peak = 0;
  for (const s of slabs) for (let i = 0; i < s.lin.length; i++) if (s.lin[i] > peak) peak = s.lin[i];
  return peak;
}

/** The voxels of the slabs at or above `fraction` of the peak, at most `cap` (thinned by a fixed stride, so the same input draws the same). */
export function volumePoints(slabs: readonly Slab[], fraction: number, cap: number): VolumePoints {
  const peak = volumePeak(slabs);
  const cut = peak * fraction;
  const kept: { s: number; col: number; row: number; v: number }[] = [];
  const perSlabAll: number[] = [];
  slabs.forEach((s, si) => {
    let count = 0;
    if (cut > 0) {
      for (let row = 0; row < s.nz; row++) {
        for (let col = 0; col < s.nx; col++) {
          const v = s.lin[row * s.nx + col];
          if (v >= cut) {
            kept.push({ s: si, col, row, v });
            count++;
          }
        }
      }
    }
    perSlabAll.push(count);
  });
  const thinned = kept.length > cap;
  const stride = thinned ? kept.length / cap : 1;
  const n = thinned ? cap : kept.length;
  const xyz = new Float32Array(3 * n);
  const u = new Float32Array(n);
  const perSlab = new Array<number>(slabs.length).fill(0);
  for (let k = 0; k < n; k++) {
    const p = kept[Math.floor(k * stride)];
    const s = slabs[p.s];
    const { lateral, z } = cellUm(s, p.col, p.row);
    xyz[3 * k] = s.plane === 'xz' ? lateral : s.posUm;
    xyz[3 * k + 1] = s.plane === 'xz' ? s.posUm : lateral;
    xyz[3 * k + 2] = z;
    u[k] = peak > 0 ? Math.sqrt(Math.min(1, p.v / peak)) : 0;
    perSlab[p.s]++;
  }
  return { xyz, u, n, peak, perSlab, thinned };
}

/** The extent of the drawing: the larger of the half field of the traps and of the cut, in micrometres, per axis. */
export function volumeExtent(traps: readonly Trap[], slabs: readonly Slab[]): { x: number; y: number; z: number } {
  let x = 1;
  let y = 1;
  let z = 1;
  for (const t of traps) {
    x = Math.max(x, Math.abs(t.x_um));
    y = Math.max(y, Math.abs(t.y_um));
    z = Math.max(z, Math.abs(t.z_um));
  }
  for (const s of slabs) z = Math.max(z, Math.abs(s.zUm[0]), Math.abs(s.zUm[1]));
  return { x: x * 1.25, y: y * 1.25, z };
}
