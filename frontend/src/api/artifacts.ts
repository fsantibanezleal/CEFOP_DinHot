// The artifact layer (T3): every committed artifact is fetched from a root-absolute URL under the site's base, with
// ?v=VERSION so a new release never reads an old cached file, and must answer JSON: a static host answering a
// missing file with its HTML page would otherwise parse as an error far from the cause (failure classes 2, 9).
import { useEffect, useState } from 'react';
import type { CaseIndex, CaseManifest, Text, Trace } from '../lib/contract.types';
import { loadReadiness, unavailableRow } from '../readiness/readiness';

export class ArtifactError extends Error {}

/** The readiness document lists this artifact as absent: the view says not available yet, with the reason. */
export class ArtifactUnavailable extends Error {
  constructor(
    readonly path: string,
    readonly reason: Text,
  ) {
    super(`${path}: not available yet (${reason.en})`);
  }
}

/** Throws ArtifactUnavailable when the readiness document marks `path` absent; an unreadable document never does. */
async function requireAvailable(path: string): Promise<void> {
  const row = unavailableRow(await loadReadiness(), path);
  if (!row) return;
  const why = row.reason ?? { en: 'the pipeline did not write it', es: 'el pipeline no lo escribió' };
  throw new ArtifactUnavailable(path, {
    en: `${path} is not available yet: ${why.en}`,
    es: `${path} aún no está disponible: ${why.es}`,
  });
}

const DATA = `${import.meta.env.BASE_URL}data/`;

export async function getJSON<T>(rel: string, signal?: AbortSignal): Promise<T> {
  const url = `${DATA}${rel}?v=${encodeURIComponent(__APP_VERSION__)}`;
  const res = await fetch(url, { signal });
  if (!res.ok) throw new ArtifactError(`${rel}: HTTP ${res.status}`);
  const type = res.headers.get('content-type') ?? '';
  if (!type.includes('json')) throw new ArtifactError(`${rel}: answered ${type || 'no content type'}, not JSON`);
  return (await res.json()) as T;
}

const INDEX_PATH = 'manifests/index.json';

export async function loadIndex(signal?: AbortSignal): Promise<CaseIndex> {
  await requireAvailable(INDEX_PATH);
  return getJSON<CaseIndex>(INDEX_PATH, signal);
}

export async function loadManifest(caseId: string, signal?: AbortSignal): Promise<CaseManifest> {
  const path = `manifests/${caseId}.json`;
  await requireAvailable(path);
  return getJSON<CaseManifest>(path, signal);
}

export interface CaseData {
  manifest: CaseManifest;
  trace: Trace;
}

export async function loadCase(caseId: string, signal?: AbortSignal): Promise<CaseData> {
  const manifest = await loadManifest(caseId, signal);
  await requireAvailable(manifest.artifact.path);
  const trace = await getJSON<Trace>(manifest.artifact.path, signal);
  return { manifest, trace };
}

export interface AbsentCase {
  caseId: string;
  title: Text;
  reason: Text;
}

/**
 * Every case's manifest and trace, for the cross-case pages (Experiments, Benchmark). A case the readiness document
 * lists as absent is not in `cases`: it is in `absent`, with its reason, and the others still load.
 */
export async function loadAllCases(signal?: AbortSignal): Promise<{ index: CaseIndex; cases: CaseData[]; absent: AbsentCase[] }> {
  const index = await loadIndex(signal);
  const settled = await Promise.all(
    index.cases.map((c) =>
      loadCase(c.case_id, signal).then(
        (data) => ({ data }),
        (e: unknown) => {
          if (e instanceof ArtifactUnavailable) return { absent: { caseId: c.case_id, title: c.title, reason: e.reason } };
          throw e;
        },
      ),
    ),
  );
  const cases = settled.flatMap((r) => ('data' in r ? [r.data] : []));
  const absent = settled.flatMap((r) => ('absent' in r ? [r.absent] : []));
  return { index, cases, absent };
}

/** A loaded value with its declared state; views write `data-state` from it, and the gate waits on it. */
export type Loaded<T> =
  | { state: 'loading' }
  | { state: 'ready'; data: T }
  | { state: 'unavailable'; reason: Text }
  | { state: 'error'; error: string };

export function useArtifact<T>(load: (signal: AbortSignal) => Promise<T>, deps: unknown[]): Loaded<T> {
  const [value, setValue] = useState<Loaded<T>>({ state: 'loading' });
  useEffect(() => {
    const ctl = new AbortController();
    setValue({ state: 'loading' });
    load(ctl.signal).then(
      (data) => {
        if (!ctl.signal.aborted) setValue({ state: 'ready', data });
      },
      (e: unknown) => {
        if (ctl.signal.aborted) return;
        if (e instanceof ArtifactUnavailable) {
          setValue({ state: 'unavailable', reason: e.reason });
          return;
        }
        console.error(`[artifacts] ${String(e)}`);
        setValue({ state: 'error', error: String(e) });
      },
    );
    return () => ctl.abort();
    // the caller names the dependencies of its loader
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return value;
}
