/**
 * WGSL kernels of the optional WebGPU backend (float32).
 *
 * The 2D FFT is a Stockham radix-2 autosort transform (Govindaraju et al., "High performance discrete Fourier transforms on
 * graphics processors", SC 2008, the formulation of the ping-pong radix-2 stage): at stage `Ns = 1, 2, 4, ... , N / 2` thread `j`
 * reads `x[j]` and `x[j + N/2]`, multiplies the second by `exp(sign 2 pi i (j mod Ns) / (2 Ns))` and writes the two butterfly
 * outputs at `(j / Ns) 2 Ns + (j mod Ns)` and `+ Ns`; after `log2 N` stages the line is in natural order. One dispatch per stage per
 * axis (rows, then columns), as in the CPU plan of `fft.ts`.
 *
 * The WGS amplitude passes (`rule`) are the three rules the CPU path uses for the FFT form (`methods/gs.ts`): `gs` (mode 0),
 * `gsw` (mode 1, weights `w <- w <r> / r` from the second iteration on) and the phase-fixed `wgsFixed` (mode 2: the phase follows the field for the first `nFix`
 * iterations and is then frozen), evaluated by one workgroup that reduces the mean of `r = |V| / a` in shared memory.
 * `fill`, `gather`, `zero`, `scatter` and `phase` move data between the SLM phase, the padded focal grid and the trap list.
 */
export const COMPLEX_MUL = /* wgsl */ `
fn cmul(a: vec2<f32>, b: vec2<f32>) -> vec2<f32> {
  return vec2<f32>(a.x * b.x - a.y * b.y, a.x * b.y + a.y * b.x);
}
`;

export const STAGE = /* wgsl */ `
struct P { m: u32, ns: u32, axis: u32, pad0: u32, sign: f32, pad1: f32, pad2: f32, pad3: f32 };
@group(0) @binding(0) var<uniform> p: P;
@group(0) @binding(1) var<storage, read> src: array<vec2<f32>>;
@group(0) @binding(2) var<storage, read_write> dst: array<vec2<f32>>;

@compute @workgroup_size(256)
fn stage(@builtin(global_invocation_id) gid: vec3<u32>) {
  let hm = p.m / 2u;
  let t = gid.x;
  if (t >= p.m * hm) { return; }
  let line = t / hm;
  let j = t % hm;
  let k = j % p.ns;
  let base = (j / p.ns) * p.ns * 2u;
  let ang = p.sign * 6.283185307179586 * f32(k) / f32(p.ns * 2u);
  let tw = vec2<f32>(cos(ang), sin(ang));
  var ia: u32; var ib: u32; var oa: u32; var ob: u32;
  if (p.axis == 0u) {
    ia = line * p.m + j;
    ib = line * p.m + j + hm;
    oa = line * p.m + base + k;
    ob = oa + p.ns;
  } else {
    ia = j * p.m + line;
    ib = (j + hm) * p.m + line;
    oa = (base + k) * p.m + line;
    ob = (base + k + p.ns) * p.m + line;
  }
  let a = src[ia];
  let b0 = src[ib];
  let b = vec2<f32>(b0.x * tw.x - b0.y * tw.y, b0.x * tw.y + b0.y * tw.x);
  dst[oa] = a + b;
  dst[ob] = a - b;
}
`;

export const FILL = /* wgsl */ `
struct Q { m: u32, n: u32, count: u32, pad0: u32 };
@group(0) @binding(0) var<uniform> q: Q;
@group(0) @binding(1) var<storage, read> phi: array<f32>;
@group(0) @binding(2) var<storage, read> amp: array<f32>;
@group(0) @binding(3) var<storage, read_write> out: array<vec2<f32>>;

@compute @workgroup_size(256)
fn fill(@builtin(global_invocation_id) gid: vec3<u32>) {
  let t = gid.x;
  if (t >= q.m * q.m) { return; }
  let y = t / q.m;
  let x = t % q.m;
  if (y < q.n && x < q.n) {
    let i = y * q.n + x;
    out[t] = vec2<f32>(amp[i] * cos(phi[i]), amp[i] * sin(phi[i]));
  } else {
    out[t] = vec2<f32>(0.0, 0.0);
  }
}
`;

export const ZERO = /* wgsl */ `
struct Q { m: u32, n: u32, count: u32, pad0: u32 };
@group(0) @binding(0) var<uniform> q: Q;
@group(0) @binding(1) var<storage, read_write> out: array<vec2<f32>>;

@compute @workgroup_size(256)
fn zero(@builtin(global_invocation_id) gid: vec3<u32>) {
  let t = gid.x;
  if (t >= q.m * q.m) { return; }
  out[t] = vec2<f32>(0.0, 0.0);
}
`;

export const GATHER = /* wgsl */ `
${COMPLEX_MUL}
struct Q { m: u32, n: u32, count: u32, pad0: u32 };
@group(0) @binding(0) var<uniform> q: Q;
@group(0) @binding(1) var<storage, read> grid: array<vec2<f32>>;
@group(0) @binding(2) var<storage, read> idx: array<u32>;
@group(0) @binding(3) var<storage, read> gm: array<vec2<f32>>;
@group(0) @binding(4) var<storage, read_write> vout: array<vec2<f32>>;

// V_m = F[bin] * ramp * pad / (n_pix * N): the trap field read from the FFT-order grid
@compute @workgroup_size(256)
fn gather(@builtin(global_invocation_id) gid: vec3<u32>) {
  let i = gid.x;
  if (i >= q.count) { return; }
  vout[i] = cmul(grid[idx[i]], gm[i]);
}
`;

export const SCATTER = /* wgsl */ `
struct Q { m: u32, n: u32, count: u32, pad0: u32 };
@group(0) @binding(0) var<uniform> q: Q;
@group(0) @binding(1) var<storage, read> idx: array<u32>;
@group(0) @binding(2) var<storage, read> coef: array<vec2<f32>>;
@group(0) @binding(3) var<storage, read_write> dstgrid: array<vec2<f32>>;

@compute @workgroup_size(256)
fn scatter(@builtin(global_invocation_id) gid: vec3<u32>) {
  let i = gid.x;
  if (i >= q.count) { return; }
  dstgrid[idx[i]] = coef[i];
}
`;

export const RULE = /* wgsl */ `
${COMPLEX_MUL}
struct R { count: u32, mode: u32, k: u32, nfix: u32 };
@group(0) @binding(0) var<uniform> r: R;
@group(0) @binding(1) var<storage, read> v: array<vec2<f32>>;
@group(0) @binding(2) var<storage, read> a: array<f32>;
@group(0) @binding(3) var<storage, read_write> w: array<f32>;
@group(0) @binding(4) var<storage, read_write> psi: array<f32>;
@group(0) @binding(5) var<storage, read> rc: array<vec2<f32>>;
@group(0) @binding(6) var<storage, read_write> coef: array<vec2<f32>>;
var<workgroup> red: array<f32, 256>;

@compute @workgroup_size(256)
fn rule(@builtin(local_invocation_id) lid: vec3<u32>) {
  let tid = lid.x;
  var s = 0.0;
  for (var i = tid; i < r.count; i += 256u) {
    s += max(length(v[i]) / a[i], 1e-30);
  }
  red[tid] = s;
  workgroupBarrier();
  for (var st = 128u; st > 0u; st = st >> 1u) {
    if (tid < st) { red[tid] += red[tid + st]; }
    workgroupBarrier();
  }
  let mean = red[0] / f32(r.count);
  for (var i = tid; i < r.count; i += 256u) {
    let vi = v[i];
    let mag = length(vi);
    var ph = vec2<f32>(1.0, 0.0);
    if (mag > 1e-30) { ph = vi / mag; }
    let rr = max(mag / a[i], 1e-30);
    var c = vec2<f32>(0.0, 0.0);
    if (r.mode == 0u) {
      c = a[i] * ph;
    } else if (r.mode == 1u) {
      if (r.k > 1u) { w[i] = w[i] * mean / rr; }
      c = w[i] * ph;
    } else {
      if (r.k > 1u) { w[i] = w[i] * mean / rr; }
      let ang = atan2(vi.y, vi.x);
      var p = ang;
      if (r.k > r.nfix) { p = psi[i]; }
      if (r.k == r.nfix) { psi[i] = ang; }
      c = w[i] * a[i] * vec2<f32>(cos(p), sin(p));
    }
    coef[i] = cmul(c, rc[i]);
  }
}
`;

export const PHASE = /* wgsl */ `
struct Q { m: u32, n: u32, count: u32, pad0: u32 };
@group(0) @binding(0) var<uniform> q: Q;
@group(0) @binding(1) var<storage, read> grid: array<vec2<f32>>;
@group(0) @binding(2) var<storage, read_write> phi: array<f32>;

@compute @workgroup_size(256)
fn phase(@builtin(global_invocation_id) gid: vec3<u32>) {
  let t = gid.x;
  if (t >= q.n * q.n) { return; }
  let y = t / q.n;
  let x = t % q.n;
  let g = grid[y * q.m + x];
  phi[t] = atan2(g.y, g.x);
}
`;
