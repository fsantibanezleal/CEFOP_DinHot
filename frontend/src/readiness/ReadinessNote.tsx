// The inline note of a view: one bilingual line, inside the container the view already has (ADR-0071: no new row,
// no new page), naming the reason the readiness document gives for the rows the view consumes. An available view
// shows nothing; the text always comes from the document, never from a state typed in the view.
import { pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import type { Provenance, Text } from '../lib/contract.types';
import { useReadiness } from './useReadiness';
import { viewState, type ViewState } from './readiness';

type Lang = 'en' | 'es';

export const STATE_LABEL: Record<string, Text> = {
  available: { en: 'Available', es: 'Disponible' },
  partial: { en: 'Partial build', es: 'Versión parcial' },
  stale: { en: 'Stale bake', es: 'Generación desactualizada' },
  provider: { en: 'Provider', es: 'Proveedor' },
  training: { en: 'Model status', es: 'Estado del modelo' },
  missing: { en: 'Not available yet', es: 'Aún no disponible' },
  unknown: { en: 'Readiness unknown', es: 'Disponibilidad desconocida' },
};

export const PROVENANCE_LABEL: Record<Provenance, Text> = {
  real: { en: 'real', es: 'real' },
  stub: { en: 'stub', es: 'stub' },
  simulator: { en: 'simulator', es: 'simulador' },
  fixture: { en: 'fixture', es: 'datos de prueba' },
  baseline: { en: 'baseline', es: 'línea base' },
};

/** A provider reason names a file path: it wraps anywhere instead of widening the container (the gate's G5). */
export const WRAP = { overflowWrap: 'anywhere' } as const;

const UNKNOWN_REASON: Text = { en: 'the readiness document could not be read.', es: 'no se pudo leer el documento de disponibilidad.' };

/** The note for a reduced view state; renders nothing when the view is available. Pure: the test renders it. */
export function NoteLine({ view, lang }: { view: ViewState; lang: Lang }) {
  if (view.state === 'available') return null;
  if (view.state === 'unknown') {
    return (
      <p className="caos-plot-note" style={WRAP} data-readiness="unknown">
        {STATE_LABEL.unknown[lang]}: {UNKNOWN_REASON[lang]}
      </p>
    );
  }
  const reasons = new Map<string, string>();
  for (const row of view.rows) {
    if (!row.reason) continue;
    const text = row.reason[lang];
    const tag = row.provenance && row.state === 'training' ? ` (${PROVENANCE_LABEL[row.provenance][lang]})` : '';
    reasons.set(text, `${text}${tag}`);
  }
  const several = reasons.size > 1;
  const body = [...reasons.entries()].map(([text, shown]) => {
    const ids = view.rows.filter((r) => r.reason?.[lang] === text).map((r) => r.id).join(', ');
    return several ? `${ids}: ${shown}` : shown;
  });
  return (
    <p className="caos-plot-note" style={WRAP} data-readiness={view.state}>
      {STATE_LABEL[view.state][lang]}: {body.join(' ')}
    </p>
  );
}

/** The note for the catalog rows `ids`, from the readiness document; nothing while the document loads. */
export function ReadinessNote({ ids }: { ids: string[] }) {
  const lang = useShellLang();
  const doc = useReadiness();
  if (doc === undefined) return null;
  return <NoteLine view={viewState(doc, ids)} lang={lang} />;
}

export const pickText = (t: BiText, lang: Lang) => pick(t, lang);
