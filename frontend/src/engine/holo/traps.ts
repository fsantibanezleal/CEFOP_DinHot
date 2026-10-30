/**
 * Trap descriptions, generators and the field-of-view check.
 *
 * Python counterpart: `core/traps.py`. A trap is a point in the focal volume: position (x, y, z) in metres, a target
 * weight and an optical vortex charge. Error messages are the Python messages (the same keys for the workbench).
 */
import { type Setup, TWO_PI, focalBinM, halfFieldM, pmod } from './geometry';
import type { Rng } from './rng';

/** Python's `f"{v:.3e}"`. */
export function fmtE3(v: number): string {
  const [m, e] = v.toExponential(3).split('e');
  const sign = e[0] === '-' ? '-' : '+';
  const digits = e.replace(/^[+-]/, '').padStart(2, '0');
  return `${m}e${sign}${digits}`;
}

/** A trap lies outside the unaliased field of view `+-lambda f / (2 p)` (case C11). */
export class OutOfFieldError extends Error {
  constructor(
    readonly trapId: number,
    readonly boundM: number,
    readonly valueM: number,
    readonly axis: string,
  ) {
    super(
      `trap ${trapId} has ${axis} = ${fmtE3(valueM)} m, outside the unaliased field of view ` +
        `(bound = ${fmtE3(boundM)} m = lambda f / (2 p))`,
    );
    this.name = 'OutOfFieldError';
  }
}

export interface Trap {
  id: number;
  xM: number;
  yM: number;
  zM: number;
  weight: number;
  charge: number;
}

/** A validated list of traps with array views. */
export class TrapSet {
  readonly traps: readonly Trap[];
  readonly ids: Int32Array;
  readonly xM: Float64Array;
  readonly yM: Float64Array;
  readonly zM: Float64Array;
  readonly weight: Float64Array;
  readonly charge: Int32Array;

  constructor(traps: Iterable<Partial<Trap> & Pick<Trap, 'id' | 'xM' | 'yM'>>) {
    const list: Trap[] = [...traps].map((t) => ({ zM: 0, weight: 1, charge: 0, ...t }));
    if (!list.length) throw new Error('a trap set needs at least one trap');
    const seen = new Set<number>();
    const dup = new Set<number>();
    for (const t of list) (seen.has(t.id) ? dup : seen).add(t.id);
    if (dup.size) throw new Error(`duplicate trap ids: [${[...dup].sort((a, b) => a - b).join(', ')}]`);
    for (const t of list) {
      if (![t.xM, t.yM, t.zM, t.weight].every(Number.isFinite)) throw new Error(`trap ${t.id}: position and weight must be finite`);
      if (t.weight <= 0) throw new Error(`trap ${t.id}: weight must be positive, got ${t.weight}`);
      if (!Number.isInteger(t.charge)) throw new Error(`trap ${t.id}: charge must be an integer`);
    }
    this.traps = list;
    this.ids = Int32Array.from(list, (t) => t.id);
    this.xM = Float64Array.from(list, (t) => t.xM);
    this.yM = Float64Array.from(list, (t) => t.yM);
    this.zM = Float64Array.from(list, (t) => t.zM);
    this.weight = Float64Array.from(list, (t) => t.weight);
    this.charge = Int32Array.from(list, (t) => t.charge);
  }

  get length(): number {
    return this.traps.length;
  }

  /** A copy with some fields replaced per trap by `f(trap, index)`. */
  map(f: (t: Trap, i: number) => Partial<Trap>): TrapSet {
    return new TrapSet(this.traps.map((t, i) => ({ ...t, ...f(t, i) })));
  }
}

function centred(xs: ArrayLike<number>, ys: ArrayLike<number>, zs?: ArrayLike<number>): TrapSet {
  return new TrapSet(Array.from({ length: xs.length }, (_, i) => ({ id: i, xM: xs[i], yM: ys[i], zM: zs ? zs[i] : 0 })));
}

function cnt(name: string, n: number): number {
  if (!Number.isInteger(n) || n < 1) throw new Error(`${name} must be a positive integer, got ${n}`);
  return n;
}

function fpos(name: string, v: number): number {
  if (!Number.isFinite(v) || v <= 0) throw new Error(`${name} must be finite and positive, got ${v}`);
  return v;
}

/** `nx * ny` traps on a square lattice centred on the axis, row-major ids. */
export function squareGrid(nx: number, ny: number, spacingUm: number): TrapSet {
  cnt('nx', nx);
  cnt('ny', ny);
  const s = fpos('spacing_um', spacingUm) * 1e-6;
  const xs: number[] = [];
  const ys: number[] = [];
  for (let j = 0; j < ny; j++) {
    for (let i = 0; i < nx; i++) {
      xs.push((i - (nx - 1) / 2) * s);
      ys.push((j - (ny - 1) / 2) * s);
    }
  }
  return centred(xs, ys);
}

const round6 = (v: number): number => Number(v.toFixed(6));

/** The `n` hexagonal-lattice sites nearest to the centre (centre first, then rings by angle). */
export function hexLattice(n: number, spacingUm: number): TrapSet {
  cnt('n', n);
  const s = fpos('spacing_um', spacingUm) * 1e-6;
  const r = Math.ceil(Math.sqrt(n)) + 2;
  const pts: [number, number, number, number][] = [];
  for (let a = -r; a <= r; a++) {
    for (let b = -r; b <= r; b++) {
      const x = s * (a + 0.5 * b);
      const y = s * (Math.sqrt(3) / 2) * b;
      pts.push([round6(Math.hypot(x, y) / s), round6(pmod(Math.atan2(y, x), TWO_PI)), x, y]);
    }
  }
  pts.sort((p, q) => p[0] - q[0] || p[1] - q[1] || p[2] - q[2] || p[3] - q[3]);
  const sel = pts.slice(0, n);
  return centred(sel.map((p) => p[2]), sel.map((p) => p[3]));
}

/** `n` traps equally spaced on a circle of the given radius. */
export function ring(n: number, radiusUm: number): TrapSet {
  cnt('n', n);
  const rad = fpos('radius_um', radiusUm) * 1e-6;
  const th = Array.from({ length: n }, (_, i) => (2 * Math.PI * i) / n);
  return centred(th.map((t) => rad * Math.cos(t)), th.map((t) => rad * Math.sin(t)));
}

/** `n` traps uniform in a square of side `extentUm`, each at least `minSpacingUm` from the others (rejection sampling). */
export function randomMinSpacing(n: number, extentUm: number, minSpacingUm: number, rng: Rng): TrapSet {
  cnt('n', n);
  const ext = fpos('extent_um', extentUm) * 1e-6;
  const mn = fpos('min_spacing_um', minSpacingUm) * 1e-6;
  const pts: [number, number][] = [];
  let attempts = 0;
  while (pts.length < n) {
    if (attempts > 2000 * n) throw new Error(`cannot place ${n} traps with spacing ${minSpacingUm} um in ${extentUm} um`);
    attempts++;
    const x = (rng.uniform() - 0.5) * ext;
    const y = (rng.uniform() - 0.5) * ext;
    if (pts.every(([px, py]) => Math.hypot(x - px, y - py) >= mn)) pts.push([x, y]);
  }
  return centred(pts.map((p) => p[0]), pts.map((p) => p[1]));
}

/** Square in x, y with `spacingUm` and `nz` planes `dzUm` apart, centred. */
export function lattice3d(nx: number, ny: number, nz: number, spacingUm: number, dzUm: number): TrapSet {
  cnt('nx', nx);
  cnt('ny', ny);
  cnt('nz', nz);
  const s = fpos('spacing_um', spacingUm) * 1e-6;
  const dz = fpos('dz_um', dzUm) * 1e-6;
  const xs: number[] = [];
  const ys: number[] = [];
  const zs: number[] = [];
  for (let k = 0; k < nz; k++)
    for (let j = 0; j < ny; j++)
      for (let i = 0; i < nx; i++) {
        xs.push((i - (nx - 1) / 2) * s);
        ys.push((j - (ny - 1) / 2) * s);
        zs.push((k - (nz - 1) / 2) * dz);
      }
  return centred(xs, ys, zs);
}

/** numpy `rint`: round half to even. */
export function rint(v: number): number {
  const f = Math.floor(v);
  const d = v - f;
  if (d < 0.5) return f;
  if (d > 0.5) return f + 1;
  return f % 2 === 0 ? f : f + 1;
}

/** Move each trap in x, y to the nearest FFT bin (z, weight and charge unchanged). */
export function snapToBins(setup: Setup, traps: TrapSet): TrapSet {
  const b = focalBinM(setup);
  return traps.map((t) => ({ xM: rint(t.xM / b) * b, yM: rint(t.yM / b) * b }));
}

/** Throw `OutOfFieldError` (first offending trap id and the bound) if any |x| or |y| >= the half-field. */
export function checkInField(setup: Setup, traps: TrapSet): void {
  const bound = halfFieldM(setup);
  for (const t of traps.traps) {
    for (const [axis, v] of [['x', t.xM], ['y', t.yM]] as const) {
      if (Math.abs(v) >= bound) throw new OutOfFieldError(t.id, bound, v, axis);
    }
  }
}
