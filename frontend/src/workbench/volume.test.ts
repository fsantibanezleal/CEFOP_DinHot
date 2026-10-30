// The sampling of the focal volume by the engine's cuts: which planes, which voxels, where they sit.
import { describe, expect, it } from 'vitest';
import type { Trap } from '../lib/contract.types';
import { slabPlan, volumeExtent, volumePeak, volumePoints, type Slab } from './volume';

const trap = (id: number, x: number, y: number, z = 0): Trap => ({ id, x_um: x, y_um: y, z_um: z, weight: 1, charge: 0 });

function slab(plane: 'xz' | 'yz', posUm: number, cells: [number, number, number][], nx = 8, nz = 5): Slab {
  const lin = new Float32Array(nx * nz);
  for (const [row, col, v] of cells) lin[row * nx + col] = v;
  return { plane, posUm, trapId: 0, lin, nx, nz, zUm: [-4, 4], binUm: 0.5 };
}

describe('the planes that sample the volume', () => {
  const grid = [trap(0, -4, 0), trap(1, 4, 0), trap(2, -4, 6.9), trap(3, 4, 6.9), trap(4, 0, 13.8)];
  it('are the distinct rows for xz and the distinct columns for yz, sorted, with one trap id each', () => {
    expect(slabPlan(grid, 'xz', 9).map((p) => p.posUm)).toEqual([0, 6.9, 13.8]);
    expect(slabPlan(grid, 'yz', 9).map((p) => p.posUm)).toEqual([-4, 0, 4]);
    expect(slabPlan(grid, 'xz', 9).map((p) => p.trapId)).toEqual([0, 2, 4]);
  });
  it('are thinned evenly above the cap, keeping both ends', () => {
    const line = Array.from({ length: 20 }, (_, i) => trap(i, 0, i));
    const p = slabPlan(line, 'xz', 5);
    expect(p).toHaveLength(5);
    expect(p[0].posUm).toBe(0);
    expect(p[4].posUm).toBe(19);
  });
});

describe('the voxels drawn', () => {
  it('are those at or above the fraction of the peak, at the coordinates of their plane', () => {
    const a = slab('xz', 3, [[2, 4, 10], [0, 0, 6], [4, 7, 1]]); // z rows -4, -2, 0, 2, 4; column 4 is the centre
    const b = slab('yz', -2, [[2, 4, 8]]);
    expect(volumePeak([a, b])).toBe(10);
    const p = volumePoints([a, b], 0.5, 100);
    expect(p.n).toBe(3); // 10, 6 and 8 pass, 1 does not
    expect(p.perSlab).toEqual([2, 1]);
    // slab a, voxel (row 0, col 0), the first in row order: lateral (0 - 4) * 0.5 = -2, z = -4, plane y = 3
    expect(Array.from(p.xyz.slice(0, 3))).toEqual([-2, 3, -4]);
    // slab a, voxel (row 2, col 4), the peak: lateral 0, z 0
    expect(Array.from(p.xyz.slice(3, 6))).toEqual([0, 3, 0]);
    // slab b is a yz plane at x = -2: the lateral axis is y
    expect(Array.from(p.xyz.slice(6, 9))).toEqual([-2, 0, 0]);
    expect(p.u[1]).toBe(1); // the peak voxel has the top colour
    expect(p.thinned).toBe(false);
  });
  it('raising the threshold only removes voxels', () => {
    const a = slab('xz', 0, [[1, 1, 10], [2, 2, 5], [3, 3, 2]]);
    const counts = [0.1, 0.3, 0.6, 0.9].map((f) => volumePoints([a], f, 100).n);
    expect(counts).toEqual([3, 2, 1, 1]);
    for (let i = 1; i < counts.length; i++) expect(counts[i]).toBeLessThanOrEqual(counts[i - 1]);
  });
  it('thins to the cap by a fixed stride and says so, and a volume with no light draws nothing', () => {
    const cells: [number, number, number][] = [];
    for (let r = 0; r < 5; r++) for (let c = 0; c < 8; c++) cells.push([r, c, 1]);
    const p = volumePoints([slab('xz', 0, cells)], 0.5, 10);
    expect(p.n).toBe(10);
    expect(p.thinned).toBe(true);
    expect(volumePoints([slab('xz', 0, cells)], 0.5, 10).xyz).toEqual(p.xyz);
    const dark = volumePoints([slab('xz', 0, [])], 0.5, 10);
    expect(dark.n).toBe(0);
    expect(dark.peak).toBe(0);
  });
  it('the extent covers the traps and the z range of the cuts', () => {
    const e = volumeExtent([trap(0, -4, 2, 10)], [slab('xz', 0, [])]);
    expect(e.x).toBeCloseTo(5);
    expect(e.z).toBe(10);
  });
});
