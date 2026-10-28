// Deterministic rich cases for the workbench's tests and for a visual check: the provider tree has one small fixture case, which
// draws none of the dynamics, rearrangement, feedback, axial or 3D views. These cases are built in memory, typed against the
// contract (tsc fails a field the schema does not have) and checked against the run-time descriptors in the tests, so a view is
// exercised on data of the shape the bake writes. The numbers are synthetic and carry no physics claim.
import type { CaseData } from '../api/artifacts';
import type { CaseManifest, Device, Trace, Trap } from '../lib/contract.types';

const b64 = (bytes: Uint8Array): string => {
  let s = '';
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
};

function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface RichOptions {
  id?: string;
  threeD?: boolean;
  device?: boolean;
  dynamics?: 'bead' | 'atom' | null;
  feedback?: boolean;
  rearrangement?: boolean;
  aberration?: boolean;
  nTraps?: number;
}

export const SIZE = 33;
export const BIN = 10.3906;

export function richCase(o: RichOptions = {}): CaseData {
  const id = o.id ?? 'R01_rich';
  const side = Math.round(Math.sqrt(o.nTraps ?? 16));
  const traps: Trap[] = [];
  for (let i = 0; i < side; i++) {
    for (let j = 0; j < side; j++) {
      const k = i * side + j;
      traps.push({ id: k, x_um: Number(((j - (side - 1) / 2) * 4 * BIN).toFixed(4)), y_um: Number(((i - (side - 1) / 2) * 4 * BIN).toFixed(4)), z_um: o.threeD ? [0, 2, 4][k % 3] : 0, weight: 1, charge: o.threeD && k % 5 === 0 ? 2 : 0 });
    }
  }
  const device: Device | null = o.device ? { bit_depth: 3, crosstalk: { sigma_per_px: 1.24, q: 1.8 }, upsample: 3, fill_factor: 0.85, flicker_rad: 0, lut_gamma: 1 } : null;
  const r = rng(7);
  const n = 64;
  const phase = new Uint8Array(n * n).map((_, i) => ((i % n) * 4 + Math.floor(i / n) * 2 + Math.floor(r() * 12)) % 256);
  const focal = new Uint8Array(SIZE * SIZE).fill(60);
  const centre = Math.floor(SIZE / 2);
  for (const t of traps) {
    const c = Math.round(t.x_um / BIN) + centre;
    const rw = Math.round(t.y_um / BIN) + centre;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      const x = c + dx;
      const y = rw + dy;
      if (x >= 0 && x < SIZE && y >= 0 && y < SIZE) focal[y * SIZE + x] = Math.max(focal[y * SIZE + x], 255 - 40 * (Math.abs(dx) + Math.abs(dy)));
    }
  }
  const dyn = o.dynamics ?? null;
  const trapI = (spread: number) => traps.map((_, i) => Number((1 + spread * Math.sin(i * 1.7)).toFixed(4)));
  const hist = (final: number) => Array.from({ length: 12 }, (_, k) => ({ iteration: k * 3, efficiency: 0.3 + 0.5 * (1 - Math.exp(-k / 4)), uniformity: Math.min(final, 0.4 + 0.6 * (1 - Math.exp(-k / 3))), rel_std_pct: 30 * Math.exp(-k / 3) + 2 }));
  const fin = (e: number, u: number) => ({ efficiency: e, uniformity: u, rel_std_pct: Number(((1 - u) * 60).toFixed(2)), zero_order: 0.02, ghost: 0.04 });
  const verdict = (e: number, u: number, lane: 'live' | 'baked', conv: boolean) => ({ lane, efficiency: e, uniformity: u, rel_std_pct: Number(((1 - u) * 60).toFixed(2)), zero_order: 0.02, ghost: 0.04, iterations: 30, converged: conv });
  const params: CaseManifest['params'] = {
    setup: { wavelength_nm: 1064, focal_mm: 10, na: 1.2, n_imm: 1.33, n_pix: 64, pitch_um: 8, pad: 2, beam: { kind: 'gaussian', waist_frac: 0.8 } },
    device,
    target: { kind: 'traps', traps },
    aberration: o.aberration ? { noll: { '4': 0.06, '6': 0.04, '8': -0.03 } } : null,
    methods: ['M04', 'M06', 'M17'],
    reference_method: 'M04',
    budget: { iterations: 30, time_s: null },
    seed: 20261028,
    feedback: o.feedback ? { gain: 0.7, steps: 6, camera: { gain_rms: 0.02, noise_rms: 0.01, blur_bins: 0.5 } } : null,
    dynamics: dyn
      ? { particle: dyn, trap_id: 5, power_mw: 10, temperature_k: dyn === 'bead' ? 295 : 0.0001, n_steps: 4000, dt_s: 1e-4, ...(dyn === 'bead' ? { bead_radius_um: 0.5, n_particle: 1.59, viscosity_pa_s: 0.00089 } : { mass_amu: 87, detuning_thz: -30 }) }
      : null,
    rearrangement: o.rearrangement ? { loading_p: 0.55, target_ids: traps.slice(0, 9).map((t) => t.id), alpha: 1.5, steps_per_move: 20 } : null,
    expect: { efficiency: [0.2, 1], rel_std_pct: [0, 40] },
  };
  const manifest: CaseManifest = {
    schema: 'dinhot.manifest/v1',
    case_id: id,
    title: { en: 'Rich test case', es: 'Caso de prueba completo' },
    category: { en: 'Test data', es: 'Datos de prueba' },
    real_or_synthetic: 'synthetic',
    expected_band: { en: 'A synthetic case that exercises every view.', es: 'Un caso sintético que ejercita cada vista.' },
    engine: { package: 'dinhot-holo', version: '0.00.000', model: 'scalar-fourier' },
    params,
    seed: 20261028,
    artifact: { path: `${id}/trace.json`, format: 'json', trace_schema: 'dinhot.trace/v1', bytes: 1 },
    lane: 'live',
    gate: { lane: 'live', pure_python: true, wheels: ['numpy'], trace_bytes: 1, run_ms_budget: 1500, trace_bytes_budget: 262144, reasons: [] },
    flags: [],
    methods: { M04: verdict(0.84, 0.93, 'live', false), M06: verdict(0.78, 0.97, 'baked', true), M17: verdict(0.7, 0.9, 'baked', false) },
    models: { 'cgh-net': 'baseline', 'warmstart-model': 'baseline' },
    expect: params.expect,
    anchor: { source: { en: 'No published result.', es: 'Sin resultado publicado.' }, url: null },
  };
  const trace: Trace = {
    schema: 'dinhot.trace/v1',
    case_id: id,
    grid: { n_pix: n, pad: 2, bin_um: BIN, half_field_um: 665 },
    traps,
    shape: null,
    methods: {
      M04: { history: hist(0.93), final: fin(0.84, 0.93), trap_intensity: trapI(0.08) },
      M06: { history: hist(0.97), final: fin(0.78, 0.97), trap_intensity: trapI(0.03) },
      M17: { history: [], final: fin(0.7, 0.9), trap_intensity: trapI(0.12) },
    },
    reference: {
      method: 'M04',
      phase_u8: b64(phase),
      focal: { size: SIZE, bin_um: BIN, db_floor: -40, intensity_db_u8: b64(focal) },
      axial: o.threeD ? { trap_id: 0, z_um: [-3, 8], nz: 24, nx: 17, xz_u8: b64(new Uint8Array(24 * 17).map((_, i) => 40 + Math.round(200 * Math.exp(-(((i % 17) - 8) ** 2 + (Math.floor(i / 17) - 8) ** 2) / 20)))) } : null,
    },
    feedback: o.feedback ? { steps: Array.from({ length: 6 }, (_, k) => ({ step: k, rel_std_pct: 19 * Math.exp(-k / 1.5) + 1.2, efficiency: 0.8 - 0.01 * k })) } : null,
    dynamics: dyn
      ? {
          particle: dyn,
          dt_s: 1e-4,
          t_decimation: 1,
          x_um: Array.from({ length: 400 }, (_, i) => 0.05 * Math.sin(i / 9) + 0.03 * Math.sin(i / 3.1)),
          y_um: Array.from({ length: 400 }, (_, i) => 0.04 * Math.cos(i / 7) + 0.02 * Math.sin(i / 2.3)),
          psd: { f_hz: Array.from({ length: 40 }, (_, i) => 10 * 1.2 ** i), p: Array.from({ length: 40 }, (_, i) => 1e-4 / ((10 * 1.2 ** i) ** 2 + 120 ** 2)) },
          fc_hz: 120,
          ...(dyn === 'bead' ? { kappa_pn_per_um: 10 } : { omega_r_hz: 80000 }),
          depth: { value: dyn === 'bead' ? 35 : 0.9, unit: dyn === 'bead' ? 'kT' : 'mK' },
        }
      : null,
    rearrangement: o.rearrangement
      ? {
          frames: Array.from({ length: 8 }, (_, k) => ({
            t_s: k * 0.05,
            occupied: traps.filter((_, i) => (i * 7 + k * 3) % 5 < 3 || k > 5).map((t) => t.id),
            moving: k % 2 ? [{ from: 0, to: 1, x_um: traps[0].x_um + 20, y_um: traps[0].y_um }] : [],
          })),
          filling: [0.55, 0.9, 0.985],
          min_transient: 0.93,
        }
      : null,
    summary: { best_method: 'M06', notes: { en: 'Synthetic.', es: 'Sintético.' } },
  };
  return { manifest, trace };
}

import { coeffArray } from './zernike';
import { replayMaps, replayResult, trapsOf, type Selection } from './model';

/** A Selection on the replay lane of a case, as the workbench builds it with no live engine; `over` replaces fields. */
export function selectionFor(data: CaseData, over: Partial<Selection> = {}): Selection {
  const p = data.manifest.params;
  return {
    data,
    methodId: p.reference_method,
    device: p.device ? 'case' : 'ideal',
    deviceModel: p.device,
    traps: trapsOf(data.manifest, data.trace),
    edited: false,
    trapId: p.dynamics?.trap_id ?? 0,
    region: null,
    maps: replayMaps(data.trace),
    result: replayResult(data.trace, p.reference_method),
    iteration: p.budget.iterations,
    dbFloor: -40,
    aberration: coeffArray(p.aberration?.noll),
    aberrationEdited: false,
    powerMw: p.dynamics?.power_mw ?? 0,
    seed: 1,
    stage: 'ideal',
    sortBy: 'id',
    bandPct: 5,
    fbStep: 0,
    zmode: 4,
    corrected: false,
    slot: null,
    running: false,
    progress: null,
    liveError: null,
    engineAvailable: false,
    liveMethods: [],
    ...over,
  };
}
