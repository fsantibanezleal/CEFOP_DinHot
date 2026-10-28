// What the Experiments page loads, once, for all its topics: the case index with every manifest and trace, through the workbench's loaders
// (`api/artifacts.ts`, never a second loader). Each topic reads the same load, so switching topics never fetches a file twice. A case the
// readiness document lists as absent, or the index lists as refused, is not in `cases`: it is in `absent`, with its reason, and the
// cases that load still draw. A document that is missing or stale shows the readiness note in place of a chart, never an empty chart.
import { pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { createContext, useContext, type ReactNode } from 'react';
import { loadAllCases, useArtifact, type AbsentCase, type Loaded } from '../../api/artifacts';
import type { CaseIndex } from '../../lib/contract.types';
import { ReadinessNote } from '../../readiness/ReadinessNote';
import type { CaseView } from './data';

export interface Bundle {
  index: CaseIndex;
  cases: CaseView[];
  /** The refused or unavailable cases, in index order, with the reason the index or the readiness document gives. */
  absent: AbsentCase[];
}

async function loadBundle(signal: AbortSignal): Promise<Bundle> {
  const { index, cases, absent } = await loadAllCases(signal);
  const views: CaseView[] = [];
  // keep the index order, not the order the loads settled in
  for (const entry of index.cases) {
    const c = cases.find((x) => x.manifest.case_id === entry.case_id);
    if (c) views.push({ entry, manifest: c.manifest, trace: c.trace });
  }
  return { index, cases: views, absent };
}

const BundleContext = createContext<Loaded<Bundle>>({ state: 'loading' });

/** Loads the bundle once and hands it to every topic below. */
export function ExperimentsData({ children }: { children: ReactNode }) {
  const bundle = useArtifact(loadBundle, []);
  return <BundleContext.Provider value={bundle}>{children}</BundleContext.Provider>;
}

export const useBundle = (): Loaded<Bundle> => useContext(BundleContext);

const LOADING: BiText = { en: 'Loading the committed artifacts', es: 'Cargando los artefactos versionados' };

/** A sentence in the displayed language without the closing full stop the readiness reasons carry. */
const bare = (s: string): string => s.replace(/[.\s]+$/, '');

/** The rows of the catalog every data view of this page consumes. */
export const PAGE_ROWS = ['case-index', 'case-manifest', 'trace'];

/**
 * The frame of a data view: the readiness note of the catalog rows it reads, then its content when the data is there, else the state it
 * is in (loading, not available yet with the reason, or the error).
 */
export function DataView({ children }: { children: (b: Bundle) => ReactNode }) {
  const lang = useShellLang();
  const bundle = useBundle();
  let body: ReactNode;
  if (bundle.state === 'loading') {
    body = (
      <p className="caos-pending" data-state="loading">
        {pick(LOADING, lang)}
      </p>
    );
  } else if (bundle.state === 'unavailable') {
    body = (
      <p className="caos-pending" data-state="unavailable">
        {lang === 'es' ? `Aún no disponible: ${bare(bundle.reason.es)}.` : `Not available yet: ${bare(bundle.reason.en)}.`}
      </p>
    );
  } else if (bundle.state === 'error') {
    body = (
      <p className="caos-pending" data-state="error">
        {bundle.error}
      </p>
    );
  } else {
    body = children(bundle.data);
  }
  return (
    <>
      <ReadinessNote ids={PAGE_ROWS} />
      {body}
    </>
  );
}

/** A table that scrolls inside its own box on a narrow screen instead of widening the page. */
export function Scroll({ children }: { children: ReactNode }) {
  return <div style={{ overflowX: 'auto', minWidth: 0 }}>{children}</div>;
}
