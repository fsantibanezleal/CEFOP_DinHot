// What the Experiments page reads from the committed bake: pure functions over the case index, the manifests and the traces
// (contracts case-index 1.0.0, case-manifest 1.0.0 and trace 1.0.0). No DinHot result is written in this module or in the page: a
// number shown is computed here from the artifact it comes from, and the unit test runs these functions on the committed bake.
// Sources of the definitions: `data-pipeline/pipeline/core/score.py` (what each slot of the manifest holds, shaped targets included),
// `core/expect.py` (the key rule of the expected ranges: `<method>.<metric>`, un-prefixed for the reference method) and
// `stages/dynamics.py` (the bead's expected corner frequency kappa / (2 pi gamma) with gamma = 6 pi eta r; the atom's expected
// radial frequency is written to the trace as `omega_r_hz`).
import type { CaseIndexEntry, CaseManifest, Trace } from '../../lib/contract.types';

/** One case as the page holds it: its index row, its manifest and its trace. */
export interface CaseView {
  entry: CaseIndexEntry;
  manifest: CaseManifest;
  trace: Trace;
}

export type Metric = 'efficiency' | 'uniformity' | 'rel_std_pct';
export const METRICS: Metric[] = ['efficiency', 'uniformity', 'rel_std_pct'];

/** A target that is a shaped potential rather than a list of traps: its two required slots carry the signal metrics (score.py). */
export const isShaped = (m: CaseManifest): boolean => m.params.target.kind !== 'traps';

export const trapCount = (m: CaseManifest): number => ('traps' in m.params.target ? m.params.target.traps.length : 0);

/** The manifest key of the expected range of a metric of a method; a shaped target's spread slot is its signal error. */
function rangeKeys(m: CaseManifest, method: string, metric: Metric): string[] {
  const names: string[] = metric === 'rel_std_pct' && isShaped(m) ? ['signal_rms_error_pct'] : [metric];
  return names.flatMap((n) => [`${method}.${n}`, ...(method === m.params.reference_method ? [n] : [])]);
}

/** The range the bake checked for a metric of a method, or null when the case declares none for it. */
export function rangeOf(m: CaseManifest, method: string, metric: Metric): [number, number] | null {
  for (const key of rangeKeys(m, method, metric)) {
    const r = m.expect[key];
    if (r && r.length === 2) return [r[0], r[1]];
  }
  return null;
}

/** The manifest rounds a value to six decimals while the bake checked the unrounded one, so a value is read as inside a range within that rounding. */
export const ROUNDING = 5e-7;
export const inside = (v: number, r: [number, number]): boolean => v >= r[0] - ROUNDING && v <= r[1] + ROUNDING;

/** How many of the checked metrics of a method fall inside their range: `{ ok, of }`; `of` is 0 when no range exists. */
export function rangeScore(m: CaseManifest, method: string): { ok: number; of: number } {
  const v = m.methods[method];
  if (!v) return { ok: 0, of: 0 };
  let ok = 0;
  let of = 0;
  for (const metric of METRICS) {
    const r = rangeOf(m, method, metric);
    if (!r) continue;
    of += 1;
    if (inside(v[metric], r)) ok += 1;
  }
  return { ok, of };
}

export const refOf = (m: CaseManifest) => m.methods[m.params.reference_method];

/** The camera loop of the trace: the measured spread by step. */
export const feedbackSteps = (t: Trace) => t.feedback?.steps ?? [];

const PN_PER_UM_TO_N_PER_M = 1e-6; // 1 pN/um = 1e-12 N / 1e-6 m

/**
 * The corner frequency the trap stiffness predicts and the one the spectrum shows, with their ratio (`fc_ratio` of the bake).
 * Bead: kappa / (2 pi gamma) with gamma = 6 pi eta r (stages/dynamics.py). Atom: the trace's omega_r_hz. Null when the case has no
 * particle, or the trace lacks the quantity the expectation needs.
 */
export function particleOracle(v: CaseView): { kind: 'bead' | 'atom'; measured: number; expected: number; ratio: number } | null {
  const d = v.trace.dynamics;
  const p = v.manifest.params.dynamics;
  if (!d || !p) return null;
  if (d.particle === 'bead') {
    if (d.kappa_pn_per_um === undefined || p.viscosity_pa_s === undefined || p.bead_radius_um === undefined) return null;
    const gamma = 6 * Math.PI * p.viscosity_pa_s * (p.bead_radius_um * 1e-6);
    const expected = (d.kappa_pn_per_um * PN_PER_UM_TO_N_PER_M) / (2 * Math.PI * gamma);
    return { kind: 'bead', measured: d.fc_hz, expected, ratio: d.fc_hz / expected };
  }
  if (d.omega_r_hz === undefined) return null;
  return { kind: 'atom', measured: d.fc_hz, expected: d.omega_r_hz, ratio: d.fc_hz / d.omega_r_hz };
}

/** The root-sum-square of the injected Zernike coefficients, in waves (the wavefront rms of the case card). */
export function aberrationRmsWaves(m: CaseManifest): number | null {
  const ab = m.params.aberration;
  if (!ab) return null;
  return Math.sqrt(Object.values(ab.noll).reduce((s, c) => s + c * c, 0));
}

/** The distinct planes of a trap target in um, ascending. */
export function planesUm(m: CaseManifest): number[] {
  if (!('traps' in m.params.target)) return [];
  return [...new Set(m.params.target.traps.map((t) => t.z_um))].sort((a, b) => a - b);
}

/** The numerical aperture the pupil defines, n_pix p / (2 f), and the depth-of-field estimate 2 lambda / NA^2 in um (card of C05). */
export function pupilDepthOfField(m: CaseManifest): { naPupil: number; dofUm: number } {
  const s = m.params.setup;
  const naPupil = (s.n_pix * s.pitch_um) / (2 * s.focal_mm * 1000);
  return { naPupil, dofUm: (2 * (s.wavelength_nm / 1000)) / (naPupil * naPupil) };
}

/** The smallest spacing between neighbouring traps of a regular grid, in um (the lattice constant); null for fewer than two traps. */
export function latticeUm(m: CaseManifest): number | null {
  if (!('traps' in m.params.target)) return null;
  const xs = [...new Set(m.params.target.traps.map((t) => t.x_um))].sort((a, b) => a - b);
  const ys = [...new Set(m.params.target.traps.map((t) => t.y_um))].sort((a, b) => a - b);
  const gaps = [xs, ys].flatMap((a) => a.slice(1).map((v, i) => v - a[i]));
  return gaps.length ? Math.min(...gaps) : null;
}

/** The method ids of a case that carry a metric, ordered as the manifest lists them. */
export const methodIds = (m: CaseManifest): string[] => Object.keys(m.methods);

/** The methods the bake could not register, named by the flags of the manifests ("methods not registered in this build: B3, M17"). */
export function unregisteredMethods(cases: CaseView[]): string[] {
  const ids = new Set<string>();
  for (const c of cases)
    for (const f of c.manifest.flags) {
      const m = /methods not registered in this build:\s*(.+)$/.exec(f.flag);
      if (m) m[1].split(',').forEach((x) => ids.add(x.trim()));
    }
  return [...ids].sort();
}

/** The flags a manifest carries that name a validity limit of the model, in the manifest's own words. */
export const validityFlags = (m: CaseManifest): string[] => m.flags.map((f) => f.flag).filter((f) => /beyond its validity/.test(f));

/** `{token}` placeholders of a template, replaced by the values; a token with no value is an error, never a blank. */
export function fill(template: string, values: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (_, k: string) => {
    if (!(k in values)) throw new Error(`experiments text: no value for {${k}} in "${template.slice(0, 60)}"`);
    return values[k];
  });
}

/** The tokens a template names. */
export const tokensOf = (template: string): string[] => [...template.matchAll(/\{(\w+)\}/g)].map((m) => m[1]);

/** The cases of the index, in order, grouped by the English category label. */
export function groupByCategory<T extends { entry: CaseIndexEntry }>(items: T[]): Map<string, T[]> {
  const out = new Map<string, T[]>();
  for (const it of items) {
    const k = it.entry.category.en;
    out.set(k, [...(out.get(k) ?? []), it]);
  }
  return out;
}
