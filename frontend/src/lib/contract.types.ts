// CONTRACT 1 and CONTRACT 2 mirror (the web side of data-pipeline/pipeline/io/contract.py and of the artifact writers: the
// trace, the manifest, the index, the benchmark results, the model card and metrics, the engine reference) and the
// readiness document. The types are GENERATED: contract.gen.ts comes from docs/contracts/api.openapi.json, whose
// components are the schema files of docs/contracts/schemas/ (ADR-0080 decision 2; `npm run contracts:types`, checked
// by `npm run build`). The names below are aliases of the generated types, never hand-written interfaces. The
// descriptors below describe the same keys at run time, and `satisfies` ties each descriptor to its generated type (a
// key added to or removed from a schema and not here fails `tsc`). contract.test.ts reads the committed artifacts and
// the provider tree against the descriptors in both directions, types included, so the pipeline cannot ship a shape
// the web does not read, and the web cannot read a key the pipeline does not write (T11).
import type { components } from './contract.gen';

type Schemas = components['schemas'];

/** Every reader-facing string is bilingual at the source. */
export type Text = Schemas['text'];

export type ParamsRecord = Schemas['ParamsRecord'];
export type Setup = Schemas['setup'];
export type Device = Schemas['device'];
export type Target = Schemas['target'];
export type Trap = Schemas['trap'];
export type Budget = Schemas['budget'];
export type Feedback = Schemas['feedback'];
export type Dynamics = Schemas['dynamics'];
export type Rearrangement = Schemas['rearrangement'];
export type Stat = Schemas['stat'];

export type Trace = Schemas['Trace'];
export type TraceSummary = Trace['summary'];
export type CaseManifest = Schemas['CaseManifest'];
export type ArtifactRef = CaseManifest['artifact'];
export type GateVerdict = CaseManifest['gate'];
export type CaseParams = CaseManifest['params'];
export type MethodVerdict = CaseManifest['methods'][string];
export type CaseIndex = Schemas['CaseIndex'];
export type CaseIndexEntry = CaseIndex['cases'][number];
export type BenchmarkResults = Schemas['BenchmarkResults'];
export type BenchmarkRow = BenchmarkResults['rows'][number];
export type ModelMetrics = Schemas['ModelMetrics'];
export type ModelCard = Schemas['ModelCard'];
export type EngineReference = Schemas['EngineReference'];
export type Readiness = Schemas['Readiness'];
export type ReadinessEntry = Readiness['contracts'][number];

/** The declared state of a catalog row (docs/contracts/catalog.md, Missing-data states). */
export type ContractState = ReadinessEntry['state'];

/** What served a catalog row in this build; null when nothing did. */
export type Provenance = NonNullable<ReadinessEntry['provenance']>;

/** The 503 body (state missing, with the reason) and the 404 body of the API (catalog row api). */
export type UnavailableBody = Schemas['UnavailableBody'];
export type NotFoundBody = Schemas['NotFoundBody'];

export const SCHEMAS = {
  trace: 'dinhot.trace/v1',
  manifest: 'dinhot.manifest/v1',
  index: 'dinhot.index/v1',
  benchmark: 'dinhot.benchmark/v1',
  modelCard: 'dinhot.model-card/v1',
  modelMetrics: 'dinhot.model-metrics/v1',
  engineReference: 'dinhot.engine-ref/v1',
  readiness: 'example.readiness/v1',
} as const satisfies {
  trace: Trace['schema'];
  manifest: CaseManifest['schema'];
  index: CaseIndex['schema'];
  benchmark: BenchmarkResults['schema'];
  modelCard: ModelCard['schema'];
  modelMetrics: ModelMetrics['schema'];
  engineReference: EngineReference['schema'];
  readiness: Readiness['schema'];
};

/** A run-time description of a value: a primitive, a bilingual text, an array of a kind, an object, a map, a kind that
 * may also be null (an optional bound, an absent reference), a kind whose key may be absent from its object (`optional`),
 * or one of several shapes (`oneOf`: a union such as the beam or the target). */
export type Kind =
  | 'string'
  | 'number'
  | 'integer'
  | 'boolean'
  | 'text'
  | { array: Kind }
  | { object: Record<string, Kind> }
  | { map: Kind }
  | { nullable: Kind }
  | { optional: Kind }
  | { oneOf: Kind[] };

const STAT: Kind = { object: { median: 'number', q1: 'number', q3: 'number' } satisfies Record<keyof Stat, Kind> };

export const TRAP = {
  id: 'integer',
  x_um: 'number',
  y_um: 'number',
  z_um: 'number',
  weight: 'number',
  charge: 'integer',
} satisfies Record<keyof Trap, Kind>;

/** The gaussian beam carries a waist; the flat beam does not. */
const BEAM: Kind = { oneOf: [{ object: { kind: 'string', waist_frac: 'number' } }, { object: { kind: 'string' } }] };

export const SETUP = {
  wavelength_nm: 'number',
  focal_mm: 'number',
  na: 'number',
  n_imm: 'number',
  n_pix: 'integer',
  pitch_um: 'number',
  pad: 'integer',
  beam: BEAM,
} satisfies Record<keyof Setup, Kind>;

export const DEVICE = {
  bit_depth: { nullable: 'integer' },
  crosstalk: { nullable: { object: { sigma_per_px: 'number', q: 'number' } } },
  upsample: 'integer',
  fill_factor: 'number',
  flicker_rad: 'number',
  lut_gamma: 'number',
} satisfies Record<keyof Device, Kind>;

/** A trap list or a shaped potential. */
export const TARGET: Kind = {
  oneOf: [
    { object: { kind: 'string', traps: { array: { object: TRAP } } } },
    {
      object: {
        kind: 'string',
        shape: 'string',
        radius_um: { optional: 'number' },
        width_um: { optional: 'number' },
        length_um: { optional: 'number' },
        signal_margin_bins: 'integer',
      },
    },
  ],
};

export const DYNAMICS = {
  particle: 'string',
  trap_id: 'integer',
  power_mw: 'number',
  bead_radius_um: { optional: 'number' },
  n_particle: { optional: 'number' },
  viscosity_pa_s: { optional: 'number' },
  temperature_k: 'number',
  mass_amu: { optional: 'number' },
  detuning_thz: { optional: 'number' },
  n_steps: 'integer',
  dt_s: 'number',
} satisfies Record<keyof Dynamics, Kind>;

export const FEEDBACK = {
  gain: 'number',
  steps: 'integer',
  camera: { object: { gain_rms: 'number', noise_rms: 'number', blur_bins: 'number' } },
} satisfies Record<keyof Feedback, Kind>;

export const REARRANGEMENT = {
  loading_p: 'number',
  target_ids: { array: 'integer' },
  alpha: 'number',
  steps_per_move: 'integer',
} satisfies Record<keyof Rearrangement, Kind>;

/** The fields of a case shared by the params record (contract 1) and the manifest's `params` (which has no case_id). */
export const PARAMS_FIELDS = {
  setup: { object: SETUP },
  device: { nullable: { object: DEVICE } },
  target: TARGET,
  aberration: { nullable: { object: { noll: { map: 'number' } } } },
  methods: { array: 'string' },
  reference_method: 'string',
  budget: { object: { iterations: 'integer', time_s: { nullable: 'number' } } satisfies Record<keyof Budget, Kind> },
  seed: 'integer',
  feedback: { nullable: { object: FEEDBACK } },
  dynamics: { nullable: { object: DYNAMICS } },
  rearrangement: { nullable: { object: REARRANGEMENT } },
  expect: { map: { array: 'number' } },
} satisfies Record<keyof CaseParams, Kind>;

export const PARAMS_RECORD = { case_id: 'string', ...PARAMS_FIELDS } satisfies Record<keyof ParamsRecord, Kind>;

export const TRACE_SUMMARY = { best_method: 'string', notes: 'text' } satisfies Record<keyof TraceSummary, Kind>;

export const TRACE = {
  schema: 'string',
  case_id: 'string',
  grid: { object: { n_pix: 'integer', pad: 'integer', bin_um: 'number', half_field_um: 'number' } },
  traps: { array: { object: TRAP } },
  shape: { nullable: { object: { kind: 'string', mask_rle: { array: 'integer' } } } },
  methods: {
    map: {
      object: {
        history: { array: { object: { iteration: 'integer', efficiency: 'number', uniformity: 'number', rel_std_pct: 'number' } } },
        final: {
          object: { efficiency: 'number', uniformity: 'number', rel_std_pct: 'number', zero_order: 'number', ghost: 'number' },
        },
        trap_intensity: { array: 'number' },
      },
    },
  },
  reference: {
    object: {
      method: 'string',
      phase_u8: 'string',
      focal: { object: { size: 'integer', bin_um: 'number', db_floor: 'number', intensity_db_u8: 'string' } },
      axial: { nullable: { object: { trap_id: 'integer', z_um: { array: 'number' }, nz: 'integer', nx: 'integer', xz_u8: 'string' } } },
    },
  },
  feedback: { nullable: { object: { steps: { array: { object: { step: 'integer', rel_std_pct: 'number', efficiency: 'number' } } } } } },
  dynamics: {
    nullable: {
      object: {
        particle: 'string',
        dt_s: 'number',
        t_decimation: 'integer',
        x_um: { array: 'number' },
        y_um: { array: 'number' },
        psd: { object: { f_hz: { array: 'number' }, p: { array: 'number' } } },
        fc_hz: 'number',
        kappa_pn_per_um: { optional: 'number' },
        omega_r_hz: { optional: 'number' },
        depth: { object: { value: 'number', unit: 'string' } },
      },
    },
  },
  rearrangement: {
    nullable: {
      object: {
        frames: {
          array: {
            object: {
              t_s: 'number',
              occupied: { array: 'integer' },
              moving: { array: { object: { from: 'integer', to: 'integer', x_um: 'number', y_um: 'number' } } },
            },
          },
        },
        filling: { array: 'number' },
        min_transient: 'number',
      },
    },
  },
  summary: { object: TRACE_SUMMARY },
} satisfies Record<keyof Trace, Kind>;

export const MANIFEST = {
  schema: 'string',
  case_id: 'string',
  title: 'text',
  category: 'text',
  real_or_synthetic: 'string',
  expected_band: 'text',
  engine: { object: { package: 'string', version: 'string', model: 'string' } },
  params: { object: PARAMS_FIELDS },
  seed: 'integer',
  artifact: { object: { path: 'string', format: 'string', trace_schema: 'string', bytes: 'integer' } satisfies Record<keyof ArtifactRef, Kind> },
  lane: 'string',
  gate: {
    object: {
      lane: 'string',
      pure_python: 'boolean',
      wheels: { array: 'string' },
      trace_bytes: 'integer',
      run_ms_budget: 'number',
      trace_bytes_budget: 'integer',
      reasons: { array: 'string' },
    } satisfies Record<keyof GateVerdict, Kind>,
  },
  flags: { array: { map: 'string' } },
  methods: {
    map: {
      object: {
        lane: 'string',
        efficiency: 'number',
        uniformity: 'number',
        rel_std_pct: 'number',
        zero_order: 'number',
        ghost: 'number',
        iterations: 'integer',
        converged: 'boolean',
      } satisfies Record<keyof MethodVerdict, Kind>,
    },
  },
  models: { map: 'string' },
  expect: { map: { array: 'number' } },
  anchor: { object: { source: 'text', url: { nullable: 'string' } } },
} satisfies Record<keyof CaseManifest, Kind>;

export const INDEX = {
  schema: 'string',
  engine_version: 'string',
  default_case: 'string',
  cases: {
    array: {
      object: {
        case_id: 'string',
        title: 'text',
        category: 'text',
        path: { nullable: 'string' },
        status: 'string',
        reason: { nullable: 'text' },
      } satisfies Record<keyof CaseIndexEntry, Kind>,
    },
  },
} satisfies Record<keyof CaseIndex, Kind>;

export const BENCHMARK = {
  schema: 'string',
  engine_version: 'string',
  protocol: {
    object: {
      grids: { array: 'integer' },
      seeds: 'integer',
      budgets: { object: { iterations: { array: 'integer' }, time_s: { array: 'number' } } },
      device: 'text',
    },
  },
  geometries: { array: { object: { id: 'string', name: 'text', n_traps: 'integer', dims: 'integer' } } },
  rows: {
    array: {
      object: {
        method: 'string',
        geometry: 'string',
        device: 'string',
        budget_kind: 'string',
        budget: 'number',
        params: 'string',
        n_seeds: 'integer',
        efficiency: STAT,
        uniformity: STAT,
        rel_std_pct: STAT,
        time_s: STAT,
        iterations: STAT,
      } satisfies Record<keyof BenchmarkRow, Kind>,
    },
  },
  pareto: {
    array: {
      object: {
        geometry: 'string',
        method: 'string',
        points: { array: { object: { lambda: 'number', efficiency: 'number', uniformity: 'number' } } },
      },
    },
  },
  skipped: { optional: { array: { object: { method: 'string', geometry: 'string', reason: 'text' } } } },
} satisfies Record<keyof BenchmarkResults, Kind>;

export const MODEL_METRICS = {
  schema: 'string',
  engine_version: 'string',
  slots: {
    object: {
      'cgh-net': {
        optional: { object: { held_out_n: 'integer', accuracy_vs_gs: STAT, time_ms: STAT, baseline: 'string' } },
      },
      'warmstart-model': {
        optional: {
          object: {
            held_out_n: 'integer',
            iterations_to_1pct: { object: { model: STAT, random: STAT } },
            final_rel_std_pct: { object: { model: STAT, random: STAT } },
          },
        },
      },
    },
  },
} satisfies Record<keyof ModelMetrics, Kind>;

const TENSOR: Kind = { object: { name: 'string', shape: { array: 'integer' }, dtype: 'string' } };

/** The card shared by cgh-net and warmstart-model; `grid` belongs to cgh-net only. */
export const MODEL_CARD = {
  schema: 'string',
  slot: 'string',
  onnx: 'string',
  sha256: 'string',
  bytes: 'integer',
  opset: 'integer',
  inputs: { array: TENSOR },
  outputs: { array: TENSOR },
  grid: { optional: 'integer' },
  trained_on: 'text',
  held_out: 'text',
  metrics_path: 'string',
} satisfies Record<keyof ModelCard, Kind>;

/** The inputs and outputs of a reference case are free objects (`{ object: {} }` accepts any keys): the parity test of
 * each engine function reads them by name. */
export const ENGINE_REFERENCE = {
  schema: 'string',
  engine_version: 'string',
  function: 'string',
  tolerance: { object: { abs: 'number', rel: 'number' } },
  cases: { array: { object: { inputs: { object: {} }, outputs: { object: {} } } } },
} satisfies Record<keyof EngineReference, Kind>;

/** The 503 body of the API: the state and the bilingual reason. */
export const UNAVAILABLE = { detail: { object: { state: 'string', reason: 'text' } } } satisfies Record<keyof UnavailableBody, Kind>;

export const READINESS = {
  schema: 'string',
  product_version: 'string',
  catalog_sha256: 'string',
  contracts: {
    array: {
      object: {
        id: 'string',
        version: 'string',
        status: 'string',
        provenance: { nullable: 'string' },
        state: 'string',
        reason: { nullable: 'text' },
        missing: { array: 'string' },
      } satisfies Record<keyof ReadinessEntry, Kind>,
    },
  },
} satisfies Record<keyof Readiness, Kind>;

/** Every way `value` departs from `kind`, with its path; empty when it conforms. Booleans are not numbers. An `optional`
 * kind is checked only where its key is present (an absent key is not a departure); a `oneOf` kind conforms when one
 * alternative leaves no departure, else the departures of the nearest alternative (the fewest) are reported. An object
 * with no declared key is a free object and accepts any keys. */
export function conform(value: unknown, kind: Kind, path = '$'): string[] {
  if (kind === 'string') return typeof value === 'string' ? [] : [`${path}: expected a string`];
  if (kind === 'number') return typeof value === 'number' && Number.isFinite(value) ? [] : [`${path}: expected a finite number`];
  if (kind === 'integer') return Number.isInteger(value) ? [] : [`${path}: expected an integer`];
  if (kind === 'boolean') return typeof value === 'boolean' ? [] : [`${path}: expected a boolean`];
  if (kind === 'text') return conform(value, { object: { en: 'string', es: 'string' } }, path);
  if ('nullable' in kind) return value === null ? [] : conform(value, kind.nullable, path);
  if ('optional' in kind) return conform(value, kind.optional, path);
  if ('oneOf' in kind) {
    const tries = kind.oneOf.map((alt) => conform(value, alt, path));
    return tries.some((t) => t.length === 0) ? [] : tries.reduce((best, t) => (t.length < best.length ? t : best));
  }
  if ('array' in kind) {
    if (!Array.isArray(value)) return [`${path}: expected an array`];
    return value.flatMap((v, i) => conform(v, kind.array, `${path}[${i}]`));
  }
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return [`${path}: expected an object`];
  const obj = value as Record<string, unknown>;
  if ('map' in kind) return Object.entries(obj).flatMap(([k, v]) => conform(v, kind.map, `${path}.${k}`));
  const want = Object.keys(kind.object);
  if (want.length === 0) return [];
  const isOptional = (k: string): boolean => {
    const sub = kind.object[k];
    return typeof sub === 'object' && 'optional' in sub;
  };
  const out = [
    ...want.filter((k) => !isOptional(k) && !(k in obj)).map((k) => `${path}.${k}: declared by the web, not written by the pipeline`),
    ...Object.keys(obj).filter((k) => !want.includes(k)).map((k) => `${path}.${k}: written by the pipeline, not declared by the web`),
  ];
  for (const k of want) if (k in obj) out.push(...conform(obj[k], kind.object[k], `${path}.${k}`));
  return out;
}
