// The committed bake of a case (data/derived), read from disk for the tests: the views are checked against the numbers of the real
// C02 and C08 artifacts, not against numbers invented for a fixture. Node only (the tests run in a node environment).
import { readFileSync } from 'node:fs';
import type { CaseData } from '../api/artifacts';
import type { CaseManifest, Trace } from '../lib/contract.types';
import { selectionFor } from './test-data';
import type { Selection } from './model';

const derived = (rel: string): string => new URL(`../../../data/derived/${rel}`, import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');

/** The manifest and trace the pipeline wrote for a case. */
export function realCase(caseId: string): CaseData {
  const manifest = JSON.parse(readFileSync(derived(`manifests/${caseId}.json`), 'utf8')) as CaseManifest;
  const trace = JSON.parse(readFileSync(derived(manifest.artifact.path), 'utf8')) as Trace;
  return { manifest, trace };
}

/** A replay-lane selection of a real case, as the workbench builds it with no live engine. */
export function realSelection(caseId: string, over: Partial<Selection> = {}): Selection {
  return selectionFor(realCase(caseId), over);
}
