/**
 * Portable pseudo-random generator: xoshiro128** seeded by SplitMix32 (ADR-0054: no global RNG anywhere).
 *
 * Python counterpart: `data-pipeline/pipeline/model/holo/core/rng.py` (the algorithm, the references and the draw
 * order are documented there). The u32 stream and the uniforms are bit exact with Python (integer arithmetic modulo
 * 2^32 and an exact division by 2^24); the normals use `log`, `cos` and `sin` of float64 and agree to about 1e-15.
 * Draw order is part of the contract: `uniform` takes one u32; `normal` takes two uniforms per pair (Box-Muller,
 * `u1 = 1 - uniform`, cosine value first, sine value cached); arrays are filled in C order by successive scalar draws.
 */
const TWO24 = 16777216;

export class Rng {
  private s0: number;
  private s1: number;
  private s2: number;
  private s3: number;
  private cache: number | null = null;

  constructor(seed: number) {
    if (!Number.isInteger(seed) || seed < 0 || seed > 0xffffffff) {
      throw new Error(`seed must be an integer in [0, 2^32), got ${seed}`);
    }
    let a = seed >>> 0;
    const next = (): number => {
      a = (a + 0x9e3779b9) >>> 0;
      let t = (a ^ (a >>> 16)) >>> 0;
      t = Math.imul(t, 0x21f0aaad) >>> 0;
      t = (t ^ (t >>> 15)) >>> 0;
      t = Math.imul(t, 0x735a2d97) >>> 0;
      return (t ^ (t >>> 15)) >>> 0;
    };
    this.s0 = next();
    this.s1 = next();
    this.s2 = next();
    this.s3 = next();
    if ((this.s0 | this.s1 | this.s2 | this.s3) === 0) this.s0 = 1; // the all-zero state is forbidden
  }

  nextU32(): number {
    let s2 = this.s2, s3 = this.s3;
    const s0 = this.s0, s1 = this.s1;
    const x = Math.imul(s1, 5) >>> 0;
    const rot = ((x << 7) | (x >>> 25)) >>> 0;
    const result = Math.imul(rot, 9) >>> 0;
    const t = (s1 << 9) >>> 0;
    s2 = (s2 ^ s0) >>> 0;
    s3 = (s3 ^ s1) >>> 0;
    const n1 = (s1 ^ s2) >>> 0;
    const n0 = (s0 ^ s3) >>> 0;
    s2 = (s2 ^ t) >>> 0;
    s3 = ((s3 << 11) | (s3 >>> 21)) >>> 0;
    this.s0 = n0;
    this.s1 = n1;
    this.s2 = s2;
    this.s3 = s3;
    return result;
  }

  /** Uniform in [0, 1): the top 24 bits of a u32 over 2^24. */
  uniform(): number {
    return (this.nextU32() >>> 8) / TWO24;
  }

  /** Standard normal by Box-Muller; the second value of each pair is cached. */
  normal(): number {
    if (this.cache !== null) {
      const z = this.cache;
      this.cache = null;
      return z;
    }
    const u1 = 1 - this.uniform();
    const u2 = this.uniform();
    const r = Math.sqrt(-2 * Math.log(u1));
    const a = 2 * Math.PI * u2;
    this.cache = r * Math.sin(a);
    return r * Math.cos(a);
  }

  uniformArray(n: number): Float64Array {
    const out = new Float64Array(count(n));
    for (let i = 0; i < out.length; i++) out[i] = this.uniform();
    return out;
  }

  normalArray(n: number): Float64Array {
    const out = new Float64Array(count(n));
    for (let i = 0; i < out.length; i++) out[i] = this.normal();
    return out;
  }

  /** `n` phases uniform in [0, 2 pi). */
  phases(n: number): Float64Array {
    const out = this.uniformArray(n);
    for (let i = 0; i < out.length; i++) out[i] = 2 * Math.PI * out[i];
    return out;
  }
}

function count(n: number): number {
  if (!Number.isInteger(n) || n < 0) throw new Error(`count must be a non-negative integer, got ${n}`);
  return n;
}
