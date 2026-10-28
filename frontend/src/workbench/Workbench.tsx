// The App route (ADR-0016 s9, ADR-0071): one CaseWorkbench. The rail holds the case picker, the variants, the two
// parameters of the live engine and its live values; the instrument holds the question groups. The replay lane is
// the committed trace of the case; the live lane is the TypeScript engine re-run with the rail's values.
// Focus mode (ADR-0070, shell 0.14.0) is on for every case: the `focus` prop puts a Focus button in the rail head that
// opens the open group in the full viewport (?focus=1 beside ?case= and ?view=); Escape or the exit button returns to the
// same case, group and sub-view. The template's gate runs with --require-focus, so an App built from it must set `focus`.
import { CaseWorkbench, Knob, Readout, useShellLang, useWorkbenchState, type CaseDef } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState } from 'react';
import { loadCase, loadIndex, useArtifact, type CaseData } from '../api/artifacts';
import { simulate } from '../engine/sir';
import { caseAbsent } from '../readiness/readiness';
import { useReadiness } from '../readiness/useReadiness';
import { COVERAGE, type Selection } from './model';
import { CompareView, ContextView, DynamicsView, UnavailableContext, ValidationView } from './views';

function LiveValues({ sel }: { sel: Selection | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  return (
    <Readout
      title={{ en: 'Live values', es: 'Valores en vivo' }}
      lane="live"
      provenance="synthetic"
      dataKey={stateKey}
      items={[
        { label: { en: 'Basic reproduction number', es: 'Número reproductivo básico' }, value: sel ? sel.beta / sel.gamma : null, unitless: true, format: { decimals: 2 }, good: 1, bad: 1.5, better: 'lower' },
        { label: { en: 'Peak infected', es: 'Pico de contagiados' }, value: sel ? sel.run.peakI : null, unit: { en: 'people', es: 'personas' }, format: { decimals: 0 } },
        { label: { en: 'Peak day', es: 'Día del pico' }, value: sel ? sel.run.tPeak : null, unit: 'd', format: { decimals: 1 } },
        { label: { en: 'Attack rate', es: 'Tasa de ataque' }, value: sel ? sel.run.attackRate : null, unitless: true, format: { percent: true, decimals: 1 } },
      ]}
    />
  );
}

export function Workbench() {
  const lang = useShellLang();
  const readiness = useReadiness();
  const index = useArtifact((s) => loadIndex(s), []);
  const [caseId, setCaseId] = useState<string | null>(null);
  const selected = caseId ?? (index.state === 'ready' ? index.data.default_case : null);
  const loaded = useArtifact((s) => (selected ? loadCase(selected, s) : new Promise<CaseData>(() => undefined)), [selected]);
  const [variant, setVariant] = useState<string>('v0');
  const [params, setParams] = useState<{ caseId: string; beta: number; gamma: number } | null>(null);

  // A new case starts from its own parameters (the rail shows when they were moved, and resets them).
  const data = loaded.state === 'ready' && loaded.data.manifest.case_id === selected ? loaded.data : null;
  useEffect(() => {
    if (data) setParams({ caseId: data.manifest.case_id, beta: data.manifest.params.beta, gamma: data.manifest.params.gamma });
  }, [data]);
  const knobs = params && data && params.caseId === data.manifest.case_id ? params : null;
  const coverage = COVERAGE.find((v) => v.id === variant)?.share ?? 0;

  const sel: Selection | null = useMemo(() => {
    if (!data || !knobs) return null;
    const run = simulate({ ...data.manifest.params, beta: knobs.beta, gamma: knobs.gamma, vaccinated: coverage });
    return { data, beta: knobs.beta, gamma: knobs.gamma, coverage, run };
  }, [data, knobs, coverage]);

  // A case the readiness document lists as absent stays in the selector, marked, so its reason can be read.
  const absent = lang === 'es' ? ' (aún no disponible)' : ' (not available yet)';
  const cases: CaseDef[] =
    index.state === 'ready'
      ? index.data.cases.map((c) => ({ id: c.case_id, name: c.title[lang] + (caseAbsent(readiness ?? null, c.case_id, c.manifest_path) ? absent : ''), category: c.category[lang] }))
      : [];
  const unavailable = index.state === 'unavailable' ? index.reason : loaded.state === 'unavailable' ? loaded.reason : null;
  const moved = data && knobs && (knobs.beta !== data.manifest.params.beta || knobs.gamma !== data.manifest.params.gamma);

  // An unavailable case has no parameters to show: its knobs would read 0, which is not data.
  const knobRail = unavailable ? (
    <p className="caos-pending" data-state="unavailable">
      {lang === 'es' ? 'Los parámetros de este caso aún no están disponibles.' : "This case's parameters are not available yet."}
    </p>
  ) : (
    <>
      <Knob
        id="beta"
        label={{ en: 'Contact rate', es: 'Tasa de contacto' }}
        hint={{ en: 'New infections per infected person per day, in a fully susceptible population.', es: 'Contagios nuevos por persona contagiada y por día, en una población totalmente susceptible.' }}
        value={knobs?.beta ?? 0}
        min={0.05}
        max={2}
        step={0.01}
        unit="1/d"
        disabled={!knobs}
        onChange={(beta) => knobs && setParams({ ...knobs, beta })}
      />
      <Knob
        id="gamma"
        label={{ en: 'Recovery rate', es: 'Tasa de recuperación' }}
        hint={{ en: 'The inverse of the mean infectious period.', es: 'El inverso del período infeccioso medio.' }}
        value={knobs?.gamma ?? 0}
        min={0.05}
        max={1}
        step={0.01}
        unit="1/d"
        disabled={!knobs}
        onChange={(gamma) => knobs && setParams({ ...knobs, gamma })}
      />
    </>
  );

  const rail = (
    <>
      {knobRail}
      {index.state === 'error' && <p role="alert">{index.error}</p>}
      <LiveValues sel={sel} />
    </>
  );

  return (
    <UnavailableContext.Provider value={unavailable}>
    <CaseWorkbench
      caseId={selected ?? ''}
      source={data?.manifest.real_or_synthetic}
      cases={{
        cases,
        selectedId: selected ?? '',
        onSelect: (id) => {
          setCaseId(id);
          setVariant('v0');
        },
        layout: 'select',
        deepLink: true,
        modifiedFromId: moved ? selected : null,
        onResetToCanonical: () => data && setParams({ caseId: data.manifest.case_id, beta: data.manifest.params.beta, gamma: data.manifest.params.gamma }),
      }}
      controls={knobs ? { beta: knobs.beta, gamma: knobs.gamma } : {}}
      variants={{ variants: COVERAGE.map((v) => ({ id: v.id, label: v.label, note: v.note, lane: 'live' })), activeId: variant, onSelect: setVariant, title: { en: 'Immunisation', es: 'Inmunización' } }}
      rail={rail}
      focus
      groups={[
        { id: 'dynamics', label: { en: 'Dynamics', es: 'Dinámica' }, lane: 'live', provenance: 'synthetic', content: <DynamicsView sel={sel} /> },
        { id: 'validation', label: { en: 'Validation', es: 'Validación' }, lane: 'live', provenance: 'synthetic', content: <ValidationView sel={sel} /> },
      ]}
      compare={{ label: { en: 'Compare immunisation', es: 'Comparar inmunización' }, lane: 'live', provenance: 'synthetic', content: <CompareView sel={sel} /> }}
      context={{ content: <ContextView sel={sel} /> }}
    />
    </UnavailableContext.Provider>
  );
}
