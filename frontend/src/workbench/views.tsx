// The views of the selected case. Each is a PlotCard with its lane and provenance, keyed by the selection it shows;
// a view whose data is not there yet declares data-state="loading" (the gate waits for it, a reader sees why).
import {
  BarChart,
  Equation,
  PlotCard,
  SubTabs,
  Verdict,
  formatNumber,
  pick,
  useShellLang,
  useWorkbenchState,
  ViewsRow,
  type BiText,
} from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { atTimes, finalSize, simulate } from '../engine/sir';
import type { Text } from '../lib/contract.types';
import { ReadinessNote } from '../readiness/ReadinessNote';
import { COVERAGE, type Selection } from './model';

/** The reason the selected case is not available yet, when the readiness document says so; null otherwise. */
export const UnavailableContext = createContext<Text | null>(null);

function Pending({ label }: { label: BiText }) {
  const lang = useShellLang();
  const reason = useContext(UnavailableContext);
  // A case the readiness document lists as absent says so, with the reason: never an empty chart, never a spinner.
  if (reason) {
    return (
      <p className="caos-pending" data-state="unavailable">
        {reason[lang]}
      </p>
    );
  }
  return (
    <p className="caos-pending" data-state="loading">
      {pick(label, lang)}
    </p>
  );
}

/** The rows every view of the workbench consumes. The rail is at its measured height (ADR-0071 rule 6), so the note
 * sits in the open view: the first group (Dynamics) and the write-up (Context). */
const CASE_ROWS = ['case-index', 'case-manifest', 'trace'];

/** The readiness note above a filling view: the note takes its own line and the view the height that is left, so a
 * note never pushes the chart past its card (a note beside a `fill` chart clipped its legend). */
function NotedFill({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <ReadinessNote ids={CASE_ROWS} />
      <div style={{ flex: '1 1 0', minHeight: 0, position: 'relative' }}>{children}</div>
    </div>
  );
}

const LOADING: BiText = { en: 'Loading the case artifacts', es: 'Cargando los artefactos del caso' };

/** S, I and R of the live run, with the replay trace of the case dashed under the live infected curve. */
export function DynamicsView({ sel }: { sel: Selection | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const series = useMemo(() => {
    if (!sel) return null;
    const at = atTimes(sel.run, sel.data.trace.t);
    return { t: sel.data.trace.t, ...at, replayI: sel.data.trace.I };
  }, [sel]);
  return (
    <PlotCard
      fill
      title={{ en: 'Susceptible, infected and recovered over time', es: 'Susceptibles, contagiados y recuperados en el tiempo' }}
      lane="live"
      provenance="synthetic"
      dataKey={stateKey}
      note={{ en: 'Solid: the live run with the rail values. Dashed: the committed replay of the case.', es: 'Continua: la corrida en vivo con los valores del panel. Segmentada: la reproducción comprometida del caso.' }}
    >
      <NotedFill>
      {series ? (
        <UPlotChart
          title={{ en: 'SIR trajectory', es: 'Trayectoria SIR' }}
          height="fill"
          x={{ values: series.t, label: { en: 'Day', es: 'Día' }, unit: 'd' }}
          y={{ label: { en: 'People', es: 'Personas' } }}
          series={[
            { label: { en: 'Susceptible', es: 'Susceptibles' }, values: series.S, color: '--color-accent' },
            { label: { en: 'Infected', es: 'Contagiados' }, values: series.I, color: '--color-bad' },
            { label: { en: 'Recovered', es: 'Recuperados' }, values: series.R, color: '--color-good' },
            { label: { en: 'Infected (replay)', es: 'Contagiados (reproducción)' }, values: series.replayI, color: '--color-fg-subtle', dash: [6, 4], width: 1.5 },
          ]}
          marks={sel && sel.run.peakI > sel.data.manifest.params.I0 ? [{ x: sel.run.tPeak, label: { en: 'peak', es: 'pico' } }] : []}
        />
      ) : (
        <Pending label={LOADING} />
      )}
      </NotedFill>
    </PlotCard>
  );
}

/** Live against replay: the parity of the two engines, and the scientific check of the final size. */
export function ValidationView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  return (
    <SubTabs
      ariaLabel={pick({ en: 'Validation views', es: 'Vistas de validación' }, lang)}
      tabs={[
        { id: 'parity', label: pick({ en: 'Live against replay', es: 'En vivo contra reproducción' }, lang), content: <ParityView sel={sel} /> },
        { id: 'final-size', label: pick({ en: 'Final size', es: 'Tamaño final' }, lang), content: <FinalSizeView sel={sel} /> },
      ]}
    />
  );
}

function ParityView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const cmp = useMemo(() => {
    if (!sel) return null;
    const at = atTimes(sel.run, sel.data.trace.t);
    const diff = at.I.map((v, i) => v - sel.data.trace.I[i]);
    const worst = Math.max(...diff.map(Math.abs));
    const p = sel.data.manifest.params;
    const asBaked = sel.beta === p.beta && sel.gamma === p.gamma && sel.coverage === 0;
    return { diff, worst, asBaked };
  }, [sel]);
  if (!sel || !cmp) return <Pending label={LOADING} />;
  const s = sel.data.trace.summary;
  const expect = sel.data.manifest.expect;
  const metric = (key: string, label: BiText, replay: number, live: number, decimals: number) => {
    const range = expect[key];
    return {
      key,
      label,
      replay: formatNumber(replay, lang, { decimals }),
      live: formatNumber(live, lang, { decimals }),
      range: range ? `${formatNumber(range[0], lang, { decimals })} - ${formatNumber(range[1], lang, { decimals })}` : '',
      inside: range ? live >= range[0] && live <= range[1] : null,
    };
  };
  const rows = [
    metric('peak_I', { en: 'Peak infected', es: 'Pico de contagiados' }, s.peak_I, sel.run.peakI, 2),
    metric('t_peak', { en: 'Peak day', es: 'Día del pico' }, s.t_peak, sel.run.tPeak, 2),
    metric('attack_rate', { en: 'Attack rate', es: 'Tasa de ataque' }, s.attack_rate, sel.run.attackRate, 4),
  ];
  return (
    <>
      <PlotCard title={{ en: 'The two engines on this case', es: 'Los dos motores en este caso' }} lane="live" provenance="synthetic" dataKey={stateKey}>
        <Verdict
          compact
          title={{ en: 'Parity of the engines', es: 'Paridad de los motores' }}
          tone={cmp.asBaked ? (cmp.worst <= 0.0051 ? 'good' : 'bad') : 'neutral'}
          verdict={
            cmp.asBaked
              ? cmp.worst <= 0.0051
                ? { en: `The live engine reproduces the replay to ${formatNumber(cmp.worst, 'en', { decimals: 4 })} people (the trace rounding).`, es: `El motor en vivo reproduce la reproducción con ${formatNumber(cmp.worst, 'es', { decimals: 4 })} personas (el redondeo de la traza).` }
                : { en: 'The live engine departs from the replay: the two engines disagree.', es: 'El motor en vivo se aparta de la reproducción: los dos motores no coinciden.' }
              : { en: 'The rail values differ from the baked case, so the live run departs from the replay by design.', es: 'Los valores del panel difieren del caso precalculado, así que la corrida en vivo se aparta de la reproducción por diseño.' }
          }
        />
        <table className="caos-table">
          <thead>
            <tr>
              <th>{pick({ en: 'Summary', es: 'Resumen' }, lang)}</th>
              <th>{pick({ en: 'Replay (Python)', es: 'Reproducción (Python)' }, lang)}</th>
              <th>{pick({ en: 'Live (TypeScript)', es: 'En vivo (TypeScript)' }, lang)}</th>
              <th>{pick({ en: 'Expected range', es: 'Rango esperado' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key}>
                <td>{pick(r.label, lang)}</td>
                <td>{r.replay}</td>
                <td>{r.live}</td>
                <td>{r.range ? `${r.range} ${r.inside ? pick({ en: '(live inside)', es: '(en vivo dentro)' }, lang) : pick({ en: '(live outside)', es: '(en vivo fuera)' }, lang)}` : pick({ en: 'not stated', es: 'no declarado' }, lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </PlotCard>
      <PlotCard fill title={{ en: 'Infected, live minus replay', es: 'Contagiados, en vivo menos reproducción' }} lane="live" provenance="synthetic" dataKey={stateKey}>
        <UPlotChart
          title={{ en: 'Infected, live minus replay', es: 'Contagiados, en vivo menos reproducción' }}
          height="fill"
          x={{ values: sel.data.trace.t, label: { en: 'Day', es: 'Día' }, unit: 'd' }}
          y={{ label: { en: 'Difference', es: 'Diferencia' }, unit: { en: 'people', es: 'personas' } }}
          series={[{ label: { en: 'Live minus replay', es: 'En vivo menos reproducción' }, values: cmp.diff, color: '--color-magenta' }]}
        />
      </PlotCard>
    </>
  );
}

/** The final-size relation against the engine run to the case horizon, over a range of R0 around the case. */
function FinalSizeView({ sel }: { sel: Selection | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const curve = useMemo(() => {
    if (!sel) return null;
    const p = sel.data.manifest.params;
    const r0s = Array.from({ length: 49 }, (_, k) => 0.4 + k * 0.1);
    const theory = r0s.map(finalSize);
    const engine = r0s.map((r0) => simulate({ ...p, beta: r0 * sel.gamma, gamma: sel.gamma }).attackRate);
    const r0 = sel.beta / sel.gamma;
    return { r0s, theory, engine, r0, gap: Math.abs(sel.run.attackRate - finalSize(r0)) };
  }, [sel]);
  if (!sel || !curve) return <Pending label={LOADING} />;
  const days = sel.data.manifest.params.days;
  const seeded = sel.data.manifest.params.I0 > 0;
  return (
    <>
      {/* The verdict stands on its own above the chart: a titled card around one line would take the drawing's height. */}
      <Verdict
        compact
        title={{ en: 'Against the final-size relation', es: 'Contra la relación de tamaño final' }}
        tone={sel.coverage > 0 || !seeded ? 'neutral' : curve.gap <= 0.02 ? 'good' : 'warn'}
        verdict={
          !seeded
            ? { en: 'No initial infection: nothing spreads, while the relation assumes a seed of infection.', es: 'Sin contagio inicial: nada se propaga, mientras la relación supone una semilla de contagio.' }
            : sel.coverage > 0
            ? { en: 'Immunisation changes the initial susceptible share; the relation below is for a fully susceptible population.', es: 'La inmunización cambia la fracción susceptible inicial; la relación de abajo es para una población totalmente susceptible.' }
            : curve.gap <= 0.02
              ? { en: `The run ends within ${formatNumber(curve.gap * 100, 'en', { decimals: 1 })} points of the final size.`, es: `La corrida termina a ${formatNumber(curve.gap * 100, 'es', { decimals: 1 })} puntos del tamaño final.` }
              : { en: `The run is ${formatNumber(curve.gap * 100, 'en', { decimals: 1 })} points from the final size: the ${days}-day horizon ends first, or R0 is near 1.`, es: `La corrida está a ${formatNumber(curve.gap * 100, 'es', { decimals: 1 })} puntos del tamaño final: el horizonte de ${days} días termina antes, o R0 está cerca de 1.` }
        }
      />
      <PlotCard fill title={{ en: 'Share ever infected against R0', es: 'Fracción alguna vez contagiada contra R0' }} lane="live" provenance="synthetic" dataKey={stateKey}>
        <UPlotChart
          title={{ en: 'Share ever infected against R0', es: 'Fracción alguna vez contagiada contra R0' }}
          height="fill"
          x={{ values: curve.r0s, label: { en: 'Basic reproduction number', es: 'Número reproductivo básico' } }}
          y={{ label: { en: 'Attack rate', es: 'Tasa de ataque' }, range: [0, 1] }}
          series={[
            { label: { en: 'Final-size relation', es: 'Relación de tamaño final' }, values: curve.theory, color: '--color-accent' },
            { label: { en: `Engine at ${days} days`, es: `Motor a ${days} días` }, values: curve.engine, color: '--color-warn', dash: [5, 4] },
          ]}
          marks={[{ x: curve.r0, label: { en: 'this case', es: 'este caso' } }]}
        />
      </PlotCard>
    </>
  );
}

/** Peak and attack rate of the case under each immunisation variant, run live, on the shell's bar chart: margins
 * measured from the labels, the variant on screen highlighted, values in the interface language. */
export function CompareView({ sel }: { sel: Selection | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const rows = useMemo(() => {
    if (!sel) return null;
    const p = sel.data.manifest.params;
    return COVERAGE.map((v) => ({ v, run: simulate({ ...p, beta: sel.beta, gamma: sel.gamma, vaccinated: v.share }) }));
  }, [sel]);
  if (!sel || !rows) return <Pending label={LOADING} />;
  const bars = (value: (r: NonNullable<typeof rows>[number]) => number) =>
    rows.map((r) => ({ id: r.v.id, label: r.v.label, value: value(r), highlight: r.v.share === sel.coverage }));
  return (
    <ViewsRow>
      <PlotCard fill title={{ en: 'Attack rate by immunisation', es: 'Tasa de ataque por inmunización' }} lane="live" provenance="synthetic" dataKey={stateKey}>
        <BarChart
          height="fill"
          title={{ en: 'Attack rate by immunisation', es: 'Tasa de ataque por inmunización' }}
          axis={{ label: { en: 'Attack rate', es: 'Tasa de ataque' }, format: { percent: true, decimals: 1 } }}
          data={bars((r) => r.run.attackRate)}
        />
      </PlotCard>
      <PlotCard fill title={{ en: 'Peak infected by immunisation', es: 'Pico de contagiados por inmunización' }} lane="live" provenance="synthetic" dataKey={stateKey}>
        <BarChart
          height="fill"
          title={{ en: 'Peak infected by immunisation', es: 'Pico de contagiados por inmunización' }}
          axis={{ label: { en: 'Peak infected', es: 'Pico de contagiados' }, unit: { en: 'people', es: 'personas' }, format: { decimals: 0 } }}
          data={bars((r) => r.run.peakI)}
        />
      </PlotCard>
    </ViewsRow>
  );
}

/** The write-up of the case: what it is, its parameters, the model, what each view shows. */
export function ContextView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  if (!sel) return <Pending label={LOADING} />;
  const m = sel.data.manifest;
  const p = m.params;
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  return (
    <>
      <ReadinessNote ids={CASE_ROWS} />
      <h2>{m.title[lang]}</h2>
      <p>
        {t('Category', 'Categoría')}: {m.category[lang]}. {t('What a reader should see', 'Lo que el lector debería ver')}: {m.expected_band[lang]}
      </p>
      <table className="caos-table">
        <tbody>
          <tr><td>{t('Contact rate', 'Tasa de contacto')}</td><td>{formatNumber(p.beta, lang, { decimals: 2 })} 1/d</td></tr>
          <tr><td>{t('Recovery rate', 'Tasa de recuperación')}</td><td>{formatNumber(p.gamma, lang, { decimals: 2 })} 1/d</td></tr>
          <tr><td>{t('Basic reproduction number', 'Número reproductivo básico')}</td><td>{formatNumber(p.beta / p.gamma, lang, { decimals: 2 })}</td></tr>
          <tr><td>{t('Population', 'Población')}</td><td>{formatNumber(p.N, lang, { decimals: 0 })}</td></tr>
          <tr><td>{t('Initial infected', 'Contagiados iniciales')}</td><td>{formatNumber(p.I0, lang, { decimals: 0 })}</td></tr>
          <tr><td>{t('Horizon', 'Horizonte')}</td><td>{p.days} d</td></tr>
        </tbody>
      </table>
      <h3>{t('The model', 'El modelo')}</h3>
      <Equation
        tex="\frac{dS}{dt} = -\beta \frac{S I}{N}, \quad \frac{dI}{dt} = \beta \frac{S I}{N} - \gamma I, \quad \frac{dR}{dt} = \gamma I"
        caption={t('The SIR equations; both engines integrate them with forward Euler at a quarter-day step.', 'Las ecuaciones SIR; ambos motores las integran con Euler explícito a un paso de un cuarto de día.')}
      />
      <h3>{t('How to read the views', 'Cómo leer las vistas')}</h3>
      <p>
        {t(
          'Dynamics shows the live run with the rail values and, dashed, the replay the pipeline baked for this case. Validation compares the two engines on the baked parameters and the run against the final-size relation. Compare immunisation re-runs the case with a share of the population immune from the start; the herd threshold is 1 - 1/R0.',
          'Dinámica muestra la corrida en vivo con los valores del panel y, segmentada, la reproducción que el pipeline precalculó para este caso. Validación compara los dos motores con los parámetros precalculados y la corrida contra la relación de tamaño final. Comparar inmunización vuelve a correr el caso con una fracción de la población inmune desde el inicio; el umbral de rebaño es 1 - 1/R0.',
        )}
      </p>
      <p>
        {t('Engine', 'Motor')}: {m.engine.model}, {m.engine.package} {m.engine.version}. {t('Data', 'Datos')}: {m.real_or_synthetic === 'synthetic' ? t('synthetic', 'sintéticos') : t('real', 'reales')}.
      </p>
    </>
  );
}
