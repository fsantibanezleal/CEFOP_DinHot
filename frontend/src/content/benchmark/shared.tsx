// What the sections of the Benchmark page share: the documents they read, loaded once for the page (the benchmark results, the model metrics,
// the manifests of the cases the claims are also read from and the case index), the reader's selection of device, parameter set and budget,
// and the states a section shows while a document is not there (the reason from the readiness document, never an empty chart).
import { ChipGroup, pick, useFormat, useShellLang, type BiText, type BarDatum } from '@fasl-work/caos-app-shell';
import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { loadBenchmark, loadIndex, loadManifest, loadModelMetrics, useArtifact, type Loaded } from '../../api/artifacts';
import type { BenchmarkResults, CaseIndex, CaseManifest, ModelMetrics } from '../../lib/contract.types';
import { ReadinessNote } from '../../readiness/ReadinessNote';
import { budgetId, budgetsOf, budgetText, parseBudget, type Budget, type Device, type Lang, type ParamsView, type Picked, TIER_NAME, TIER_SHORT } from './data';
import type { Tier } from '../methodology/ladder';

export interface BenchData {
  results: Loaded<BenchmarkResults>;
  metrics: Loaded<ModelMetrics>;
  index: Loaded<CaseIndex>;
  /** The manifest of C08 (the full crosstalk device) and of C14 (the volume case of the learned model): read, not required. */
  c08: Loaded<CaseManifest>;
  c14: Loaded<CaseManifest>;
}

export interface Selection {
  device: Device;
  view: ParamsView;
  /** A budget id (`iterations:30`); empty until the document is read, then the default of `defaultBudget`. */
  budget: string;
}
interface Ctx {
  data: BenchData;
  sel: Selection;
  set: (patch: Partial<Selection>) => void;
}

const BenchContext = createContext<Ctx | null>(null);

export function useBench(): Ctx {
  const ctx = useContext(BenchContext);
  if (!ctx) throw new Error('useBench: the Benchmark page provides the documents');
  return ctx;
}

// One fetch of the case index for the page, kept apart from the abort signal of the first section to unmount: the others wait on it.
let indexOnce: Promise<CaseIndex> | null = null;
const theIndex = (): Promise<CaseIndex> => {
  indexOnce ??= loadIndex().catch((e: unknown) => {
    indexOnce = null;
    throw e;
  });
  return indexOnce;
};

/** The budget the page opens on: 30 iterations (the budget of the cases) when the document has it, else the first one. */
export function defaultBudget(res: BenchmarkResults): Budget | null {
  const all = budgetsOf(res);
  return all.find((b) => b.kind === 'iterations' && b.value === 30) ?? all[0] ?? null;
}

/** Loads every document of the page once and hands it down with the reader's selection. */
export function BenchProvider({ children }: { children: ReactNode }) {
  const results = useArtifact((s) => loadBenchmark(s), []);
  const metrics = useArtifact((s) => loadModelMetrics(s), []);
  const index = useArtifact(() => theIndex(), []);
  const c08 = useArtifact((s) => loadManifest('C08_device_limited', s), []);
  const c14 = useArtifact((s) => loadManifest('C14_volume_learned', s), []);
  const [sel, setSel] = useState<Selection>({ device: 'ideal', view: 'default', budget: '' });
  const value = useMemo<Ctx>(
    () => ({ data: { results, metrics, index, c08, c14 }, sel, set: (patch) => setSel((s) => ({ ...s, ...patch })) }),
    [results, metrics, index, c08, c14, sel],
  );
  return <BenchContext.Provider value={value}>{children}</BenchContext.Provider>;
}

/** The selection with the budget resolved against the document (the stored one when the document has it, else the default). */
export function useResolved(res: BenchmarkResults): { device: Device; view: ParamsView; budget: Budget | null } {
  const { sel } = useBench();
  const all = budgetsOf(res);
  const chosen = all.find((b) => budgetId(b) === sel.budget) ?? defaultBudget(res);
  return { device: sel.device, view: sel.view, budget: chosen };
}

const WAIT: BiText = { en: 'Loading the artifacts', es: 'Cargando los artefactos' };

/** What stands where a document would be: loading, the error, or not available yet with the reason from the readiness document. */
export function Pending({ of, wait = WAIT }: { of: Loaded<unknown>; wait?: BiText }) {
  const lang = useShellLang();
  if (of.state === 'unavailable') {
    return (
      <p className="caos-pending" data-state="unavailable">
        {of.reason[lang]}
      </p>
    );
  }
  if (of.state === 'error') {
    return (
      <p className="caos-pending" data-state="error">
        {of.error}
      </p>
    );
  }
  return (
    <p className="caos-pending" data-state="loading">
      {pick(wait, lang)}
    </p>
  );
}

/** Renders `children` with the documents when all are there, else the state of the first one that is not. */
export function Ready<A, B = never>({ a, b, children }: { a: Loaded<A>; b?: Loaded<B>; children: (a: A, b: B) => ReactNode }) {
  const parts: Loaded<unknown>[] = [a, ...(b ? [b] : [])];
  const bad = parts.find((p) => p.state !== 'ready');
  if (bad) return <Pending of={bad} />;
  return <>{children((a as { data: A }).data, (b as { data: B } | undefined)?.data as B)}</>;
}

/** A table that scrolls inside its own box instead of widening the page. */
export function TableWrap({ children }: { children: ReactNode }) {
  return <div style={{ overflowX: 'auto', minWidth: 0 }}>{children}</div>;
}

export const WRAP = { overflowWrap: 'anywhere' } as const;

/** The three controls that choose the cell a table and its charts show: the device, the parameter set and the budget. */
export function CellControls({ res, prefix, showView = true }: { res: BenchmarkResults; prefix: string; showView?: boolean }) {
  const { set } = useBench();
  const { device, view, budget } = useResolved(res);
  const lang = useShellLang();
  const budgets = budgetsOf(res);
  return (
    <div className="caos-controls" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem 1.5rem', margin: '0.5rem 0' }}>
      <ChipGroup
        id={`${prefix}-device`}
        label={{ en: 'Device the hologram is scored against', es: 'Dispositivo contra el que se evalúa el holograma' }}
        options={[
          { id: 'ideal', label: { en: 'Ideal', es: 'Ideal' } },
          { id: 'device', label: { en: 'C08 device', es: 'Dispositivo C08' } },
        ]}
        value={device}
        onChange={(id) => set({ device: id as Device })}
      />
      {showView ? (
        <ChipGroup
          id={`${prefix}-params`}
          label={{ en: 'Parameters', es: 'Parámetros' }}
          options={[
            { id: 'default', label: { en: 'Default (paper)', es: 'Por defecto (artículo)' }, hint: { en: 'every method with the parameters of its paper', es: 'cada método con los parámetros de su artículo' } },
            { id: 'tuned', label: { en: 'Tuned (shared grid)', es: 'Ajustados (rejilla común)' }, hint: { en: 'the methods that declare a tuning grid, at their best grid point; the others stay at their default row, labelled', es: 'los métodos que declaran una rejilla de ajuste, en su mejor punto; los demás siguen en su fila por defecto, rotulada' } },
          ]}
          value={view}
          onChange={(id) => set({ view: id as ParamsView })}
        />
      ) : null}
      <ChipGroup
        id={`${prefix}-budget`}
        label={{ en: 'Budget', es: 'Presupuesto' }}
        options={budgets.map((b) => ({ id: budgetId(b), label: budgetText(b) }))}
        value={budget ? budgetId(budget) : ''}
        onChange={(id) => set({ budget: budgetId(parseBudget(id)) })}
      />
      <span className="caos-plot-note" lang={lang} style={{ alignSelf: 'center' }}>
        {lang === 'es' ? 'Medianas sobre las semillas; el intervalo es el cuartil 1 a 3.' : 'Medians over the seeds; the interval is quartile 1 to 3.'}
      </span>
    </div>
  );
}

/** The tone of a bar by tier, with the legend that names it. */
export const TIER_TONE: Record<Tier | 'none', BarDatum['tone']> = { classical: 'neutral', sota: 'accent', beyond: 'good', none: 'warn' };
export const TIER_LEGEND = (['classical', 'sota', 'beyond'] as Tier[]).map((t) => ({ tone: TIER_TONE[t] as NonNullable<BarDatum['tone']>, label: TIER_NAME[t] }));

/** A bar label that carries the parameter set it shows: a tuned result is never an unlabelled bar beside default ones. */
export function barLabel(p: Picked, id: string, view: ParamsView): BiText {
  const tag = p.params === 'tuned' ? { en: 'tuned', es: 'ajustado' } : view === 'tuned' ? { en: p.noTunedRow ? 'default, not tuned here' : 'default', es: p.noTunedRow ? 'por defecto, sin ajuste aquí' : 'por defecto' } : null;
  return tag ? { en: `${id} (${tag.en})`, es: `${id} (${tag.es})` } : { en: id, es: id };
}

/** Number formatting of the page: significant digits, the shell's decimal sign for the language. */
export function useNum() {
  const f = useFormat();
  return {
    n: (v: number | null | undefined, digits = 3) => f(v, { digits }),
    d: (v: number | null | undefined, decimals: number) => f(v, { decimals }),
    pct: (v: number | null | undefined, digits = 3) => (v === null || v === undefined ? f(v) : `${f(v, { digits })} %`),
  };
}

/** The note under a view that reads a catalog row: the readiness state, nothing when the row is available. */
export const Note = ReadinessNote;

export const tierText = (tier: Tier | null, lang: Lang, short = false): string => (tier === null ? '-' : (short ? TIER_SHORT : TIER_NAME)[tier][lang]);
