// CONTRACT 2 mirror (the web side of data-pipeline/pipeline/core/{trace.py, manifest.py}) and the readiness document. The
// types are GENERATED: contract.gen.ts comes from docs/contracts/api.openapi.json, whose components are the schema
// files of docs/contracts/schemas/ (ADR-0080 decision 2; `npm run contracts:types`, checked by `npm run build`). The
// names below are aliases of the generated types, never hand-written interfaces. The descriptors below describe the
// same keys at run time, and `satisfies` ties each descriptor to its generated type (a key added to or removed from a
// schema and not here fails `tsc`). contract.test.ts reads the committed artifacts and the provider tree against the
// descriptors in both directions, types included, so the pipeline cannot ship a shape the web does not read, and the
// web cannot read a key the pipeline does not write (T11).
import type { components } from './contract.gen';

type Schemas = components['schemas'];

/** Every reader-facing string is bilingual at the source. */
export type Text = Schemas['text'];

export type Trace = Schemas['Trace'];
export type TraceSummary = Trace['summary'];
export type CaseManifest = Schemas['CaseManifest'];
export type ArtifactRef = CaseManifest['artifact'];
export type GateVerdict = CaseManifest['gate'];
export type CaseParams = CaseManifest['params'];
export type CaseIndex = Schemas['CaseIndex'];
export type CaseIndexEntry = CaseIndex['cases'][number];
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
  trace: 'example.trace/v1',
  manifest: 'example.manifest/v4',
  index: 'example.index/v2',
  readiness: 'example.readiness/v1',
} as const satisfies { trace: Trace['schema']; manifest: CaseManifest['schema']; index: CaseIndex['schema']; readiness: Readiness['schema'] };

/** A run-time description of a value: a primitive, a bilingual text, an array of a kind, an object, a map, or a
 * kind that may also be null (an optional bound, an absent reference). */
export type Kind =
  | 'string'
  | 'number'
  | 'integer'
  | 'boolean'
  | 'text'
  | { array: Kind }
  | { object: Record<string, Kind> }
  | { map: Kind }
  | { nullable: Kind };

export const TRACE_SUMMARY = { peak_I: 'number', t_peak: 'number', attack_rate: 'number' } satisfies Record<keyof TraceSummary, Kind>;

export const TRACE = {
  schema: 'string',
  case_id: 'string',
  t: { array: 'number' },
  S: { array: 'number' },
  I: { array: 'number' },
  R: { array: 'number' },
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
  params: { object: { beta: 'number', gamma: 'number', N: 'number', I0: 'number', days: 'integer' } satisfies Record<keyof CaseParams, Kind> },
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
  metrics: { map: 'number' },
  models: { map: 'string' },
  expect: { map: { array: 'number' } },
} satisfies Record<keyof CaseManifest, Kind>;

export const INDEX = {
  schema: 'string',
  engine_version: 'string',
  n_cases: 'integer',
  default_case: 'string',
  cases: { array: { object: { case_id: 'string', title: 'text', category: 'text', manifest_path: 'string' } satisfies Record<keyof CaseIndexEntry, Kind> } },
} satisfies Record<keyof CaseIndex, Kind>;

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

/** Every way `value` departs from `kind`, with its path; empty when it conforms. Booleans are not numbers. */
export function conform(value: unknown, kind: Kind, path = '$'): string[] {
  if (kind === 'string') return typeof value === 'string' ? [] : [`${path}: expected a string`];
  if (kind === 'number') return typeof value === 'number' && Number.isFinite(value) ? [] : [`${path}: expected a finite number`];
  if (kind === 'integer') return Number.isInteger(value) ? [] : [`${path}: expected an integer`];
  if (kind === 'boolean') return typeof value === 'boolean' ? [] : [`${path}: expected a boolean`];
  if (kind === 'text') return conform(value, { object: { en: 'string', es: 'string' } }, path);
  if ('nullable' in kind) return value === null ? [] : conform(value, kind.nullable, path);
  if ('array' in kind) {
    if (!Array.isArray(value)) return [`${path}: expected an array`];
    return value.flatMap((v, i) => conform(v, kind.array, `${path}[${i}]`));
  }
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return [`${path}: expected an object`];
  const obj = value as Record<string, unknown>;
  if ('map' in kind) return Object.entries(obj).flatMap(([k, v]) => conform(v, kind.map, `${path}.${k}`));
  const want = Object.keys(kind.object);
  const out = [
    ...want.filter((k) => !(k in obj)).map((k) => `${path}.${k}: declared by the web, not written by the pipeline`),
    ...Object.keys(obj).filter((k) => !want.includes(k)).map((k) => `${path}.${k}: written by the pipeline, not declared by the web`),
  ];
  for (const k of want) if (k in obj) out.push(...conform(obj[k], kind.object[k], `${path}.${k}`));
  return out;
}
