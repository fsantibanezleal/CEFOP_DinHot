// What each case costs: the committed artifact against its byte budget, the surrogate's held-out error, and the
// live engine timed in this browser against the run budget the lane gate set. Every number is read from the
// artifacts or measured here; none is typed in.
import { Callout, Cite, DocPage, DocSection, Knob, PlotCard, Verdict, formatNumber, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useEffect, useMemo, useState } from 'react';
import { loadAllCases, useArtifact, type CaseData, type Loaded } from '../api/artifacts';
import { simulate } from '../engine/sir';
import { P, useT } from '../content/bi';
import { ReadinessNote } from '../readiness/ReadinessNote';

/** The classical baseline of the surrogate: the analytic peak infected share for a vanishing initial infection. */
const baselinePeak = (r0: number) => (r0 > 1 ? 1 - (1 + Math.log(r0)) / r0 : 0);
/** The engine's peak infected share for a reproduction number, on the example's population, recovery rate and horizon. */
const enginePeak = (r0: number) => {
  const run = simulate({ beta: r0 * 0.2, gamma: 0.2, N: 100000, I0: 50, days: 160 });
  return run.peakI / 100000;
};

interface Timing {
  caseId: string;
  medianMs: number;
}

/**
 * Times the live engine on every case, after the page has rendered, outside any animation frame. A browser coarsens
 * its clock (to 0.1 ms or more), so each sample times a batch of runs long enough to measure, and the median of seven
 * samples is divided back to one run.
 */
function useTimings(cases: CaseData[] | null): Timing[] | null {
  const [out, setOut] = useState<Timing[] | null>(null);
  useEffect(() => {
    if (!cases) return;
    const id = window.setTimeout(() => {
      setOut(
        cases.map(({ manifest }) => {
          let batch = 1;
          for (;;) {
            const t0 = performance.now();
            for (let k = 0; k < batch; k += 1) simulate(manifest.params);
            if (performance.now() - t0 >= 20 || batch >= 1 << 16) break;
            batch *= 2;
          }
          const runs: number[] = [];
          for (let k = 0; k < 7; k += 1) {
            const t0 = performance.now();
            for (let j = 0; j < batch; j += 1) simulate(manifest.params);
            runs.push((performance.now() - t0) / batch);
          }
          runs.sort((a, b) => a - b);
          return { caseId: manifest.case_id, medianMs: runs[3] };
        }),
      );
    }, 0);
    return () => window.clearTimeout(id);
  }, [cases]);
  return out;
}

const ARTIFACT_ROWS = ['case-index', 'case-manifest', 'trace'];

/** What stands where the cases would be: loading, the error, or not available yet with the reason. */
function Pending({ all, wait }: { all: Loaded<{ cases: unknown[] }>; wait: string }) {
  const lang = useShellLang();
  const t = useT();
  if (all.state === 'unavailable') return <p className="caos-pending" data-state="unavailable">{all.reason[lang]}</p>;
  if (all.state === 'error') return <p className="caos-pending" data-state="error">{all.error}</p>;
  if (all.state === 'ready') {
    return <p className="caos-pending" data-state="unavailable">{t('Not available yet: no case of this build has its artifacts.', 'Aún no disponible: ningún caso de esta versión tiene sus artefactos.')}</p>;
  }
  return <p className="caos-pending" data-state="loading">{wait}</p>;
}

export function Benchmark() {
  const lang = useShellLang();
  const t = useT();
  const all = useArtifact((s) => loadAllCases(s), []);
  const cases = all.state === 'ready' && all.data.cases.length ? all.data.cases : null;
  const timings = useTimings(cases);
  const ready = cases && timings;
  const [liveR0, setLiveR0] = useState(2.75);
  const live = useMemo(() => ({ engine: enginePeak(liveR0), base: baselinePeak(liveR0) }), [liveR0]);
  const robustness = useMemo(() => {
    const xs = Array.from({ length: 56 }, (_, k) => Math.round((0.5 + k * 0.1) * 100) / 100);
    return { xs, engine: xs.map(enginePeak), baseline: xs.map(baselinePeak) };
  }, []);
  const worst = ready ? Math.max(...cases.map((c, i) => timings[i].medianMs / c.manifest.gate.run_ms_budget)) : 0;

  return (
    <DocPage wide title={{ en: 'Benchmark', es: 'Benchmark' }} lede={t('What each case costs and how well the models do, baked and live: the budgets of the live lane, the held-out error of the learned surrogate, its comparison with the analytic baseline, where that baseline degrades, and a panel that runs the engine in your browser.', 'Lo que cuesta cada caso y cuán bien lo hacen los modelos, precalculado y en vivo: los presupuestos del carril en vivo, el error reservado del sustituto aprendido, su comparación con la línea base analítica, dónde se degrada esa línea base, y un panel que corre el motor en su navegador.')}>
      <DocSection title={{ en: 'Budgets and timings', es: 'Presupuestos y tiempos' }} noRefsReason={{ en: 'Measures this build.', es: 'Mide esta compilación.' }}>
        <P
          en="The pipeline's lane gate decides, per case, whether the live engine may re-run it in the browser: the engine must be light, the committed trace small, and the run fast. This page reads each budget from the manifest and measures the live engine here, as the median of seven timed batches of runs, so the verdict is about this browser on this device."
          es="La compuerta de carril del pipeline decide, por caso, si el motor en vivo puede volver a correrlo en el navegador: el motor debe ser liviano, la traza comprometida pequeña y la corrida rápida. Esta página lee cada presupuesto desde el manifiesto y mide aquí el motor en vivo, como la mediana de siete lotes de corridas medidos, así que el veredicto es sobre este navegador en este dispositivo."
        />
        <ReadinessNote ids={ARTIFACT_ROWS} />
        {all.state === 'ready' && all.data.absent.map((a) => (
          <p key={a.caseId} className="caos-pending" data-state="unavailable">
            {a.title[lang]}: {a.reason[lang]}
          </p>
        ))}
        {ready ? (
          <>
            <PlotCard title={{ en: 'The live lane on this device', es: 'El carril en vivo en este dispositivo' }} lane="live" provenance="synthetic">
              <Verdict
                title={{ en: 'Run budget', es: 'Presupuesto de corrida' }}
                tone={worst <= 1 ? 'good' : 'bad'}
                verdict={
                  worst <= 1
                    ? { en: `Every case runs within its budget; the slowest uses ${formatNumber(worst, 'en', { percent: true, digits: 2 })} of it.`, es: `Cada caso corre dentro de su presupuesto; el más lento usa ${formatNumber(worst, 'es', { percent: true, digits: 2 })} de él.` }
                    : { en: 'A case exceeds its run budget on this device: the live lane would be slow here.', es: 'Un caso excede su presupuesto de corrida en este dispositivo: el carril en vivo sería lento aquí.' }
                }
              />
            </PlotCard>
            <table className="caos-table" data-state="ready">
              <thead>
                <tr>
                  <th>{t('Case', 'Caso')}</th>
                  <th>{t('Lane', 'Carril')}</th>
                  <th>{t('Trace (bytes)', 'Traza (bytes)')}</th>
                  <th>{t('Byte budget', 'Presupuesto de bytes')}</th>
                  <th>{t('Live run (ms)', 'Corrida en vivo (ms)')}</th>
                  <th>{t('Run budget (ms)', 'Presupuesto de corrida (ms)')}</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((c, i) => (
                  <tr key={c.manifest.case_id}>
                    <td>{c.manifest.title[lang]}</td>
                    <td>{c.manifest.lane === 'live' ? t('live', 'en vivo') : t('precompute', 'precálculo')}</td>
                    <td>{formatNumber(c.manifest.artifact.bytes, lang, { decimals: 0 })}</td>
                    <td>{formatNumber(c.manifest.gate.trace_bytes_budget, lang, { decimals: 0 })}</td>
                    <td>{formatNumber(timings[i].medianMs, lang, { digits: 3 })}</td>
                    <td>{formatNumber(c.manifest.gate.run_ms_budget, lang, { decimals: 0 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : (
          <Pending all={all} wait={t('Loading the artifacts and timing the live engine', 'Cargando los artefactos y midiendo el motor en vivo')} />
        )}
      </DocSection>
      <DocSection title={{ en: 'The surrogate', es: 'El sustituto' }} area="results" noRefsReason={{ en: 'Measures this build.', es: 'Mide esta compilación.' }}>
        <P
          en="The pipeline also trains a small surrogate that predicts the peak share from the case parameters, and evaluates it on twenty held-out parameter sets drawn with a seed disjoint from training. It is there to show where a learned model sits in the pipeline; its error is reported, not hidden."
          es="El pipeline también entrena un sustituto pequeño que predice la fracción del pico a partir de los parámetros del caso, y lo evalúa en veinte conjuntos de parámetros reservados, sorteados con una semilla disjunta del entrenamiento. Está ahí para mostrar dónde se ubica un modelo aprendido en el pipeline; su error se reporta, no se oculta."
        />
        <ReadinessNote ids={['surrogate-model']} />
        {cases ? (
          (() => {
            const sets = [...new Set(cases.map((c) => JSON.stringify(c.manifest.metrics)))];
            const m = cases[0].manifest.metrics;
            return (
              <>
                {sets.length > 1 && (
                  <Verdict
                    title={{ en: 'One evaluation per bake', es: 'Una evaluación por precálculo' }}
                    tone="bad"
                    verdict={{ en: `The manifests carry ${sets.length} different evaluations: some were written by a different run than the release bake.`, es: `Los manifiestos traen ${sets.length} evaluaciones distintas: algunos los escribió una corrida distinta del precálculo de la versión.` }}
                  />
                )}
                <table className="caos-table" data-state="ready">
                  <thead>
                    <tr>
                      <th>{t('Evaluation', 'Evaluación')}</th>
                      <th>{t('Held-out R squared', 'R cuadrado reservado')}</th>
                      <th>{t('Held-out RMSE', 'RMSE reservado')}</th>
                      <th>{t('Held-out sets', 'Conjuntos reservados')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{t('This bake, all cases', 'Este precálculo, todos los casos')}</td>
                      <td>{formatNumber(m.surrogate_peakfrac_r2 ?? null, lang, { decimals: 4 })}</td>
                      <td>{formatNumber(m.surrogate_peakfrac_rmse ?? null, lang, { decimals: 5 })}</td>
                      <td>{formatNumber(m.n_holdout ?? null, lang, { decimals: 0 })}</td>
                    </tr>
                  </tbody>
                </table>
              </>
            );
          })()
        ) : (
          <Pending all={all} wait={t('Loading the artifacts', 'Cargando los artefactos')} />
        )}
      </DocSection>
      <DocSection title={{ en: 'Learned model and baseline', es: 'Modelo aprendido y línea base' }} area="comparison" refs={['km1927', 'hethcote2000']}>
        <P
          en={<>The learned surrogate has a classical competitor that needs no training: the analytic peak share of the model <Cite id="km1927" />. The table puts the peak share of each baked case beside that formula, so the gap is the baseline's error against the engine on the same five cases. The surrogate's own held-out error, measured on twenty other sets, is the first table of this page.</>}
          es={<>El sustituto aprendido tiene un competidor clásico que no necesita entrenamiento: la fracción analítica del pico del modelo <Cite id="km1927" />. La tabla pone la fracción del pico de cada caso precalculado junto a esa fórmula, de modo que la brecha es el error de la línea base contra el motor en los mismos cinco casos. El error reservado del propio sustituto, medido en otros veinte conjuntos, es la primera tabla de esta página.</>}
        />
        <P
          en={<>The two errors are not on the same sets, and the page does not pretend they are: five baked cases against twenty draws from the held-out generator. The control case starts with no infection at all, so its peak is zero and the formula, which assumes one, is wrong there by construction. For the other four the table shows how far the formula departs from the engine <Cite id="hethcote2000" />, the part a learned model can absorb and a formula cannot.</>}
          es={<>Los dos errores no son sobre los mismos conjuntos, y la página no finge que lo sean: cinco casos precalculados contra veinte sorteos del generador reservado. El caso de control parte sin ninguna infección, así que su pico es cero y la fórmula, que supone una, se equivoca allí por construcción. En los otros cuatro la tabla muestra cuánto se aparta la fórmula del motor <Cite id="hethcote2000" />, la parte que un modelo aprendido puede absorber y una fórmula no.</>}
        />
        {cases ? (
          <table className="caos-table" data-state="ready">
            <thead>
              <tr>
                <th>{t('Case', 'Caso')}</th>
                <th>R0</th>
                <th>{t('Engine peak share', 'Fracción del pico, motor')}</th>
                <th>{t('Analytic baseline', 'Línea base analítica')}</th>
                <th>{t('Difference', 'Diferencia')}</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => {
                const r0 = c.manifest.params.beta / c.manifest.params.gamma;
                const eng = c.trace.summary.peak_I / c.manifest.params.N;
                const base = baselinePeak(r0);
                return (
                  <tr key={c.manifest.case_id}>
                    <td>{c.manifest.title[lang]}</td>
                    <td>{formatNumber(r0, lang, { decimals: 2 })}</td>
                    <td>{formatNumber(eng, lang, { percent: true, decimals: 2 })}</td>
                    <td>{formatNumber(base, lang, { percent: true, decimals: 2 })}</td>
                    <td>{formatNumber(base - eng, lang, { percent: true, decimals: 2 })}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <Pending all={all} wait={t('Loading the artifacts', 'Cargando los artefactos')} />
        )}
      </DocSection>
      <DocSection title={{ en: 'Where the baseline degrades', es: 'Dónde se degrada la línea base' }} area="robustness" refs={['vdd2002']}>
        <P
          en={<>The curve is the honest part of the comparison: the engine's peak share and the baseline's, for reproduction numbers from one half to six, computed in this browser. Across the whole range the baseline stays close to the engine and sits slightly below it, and the gap grows with R0, because the real starting infection and the quarter-day step matter more when the outbreak is fast <Cite id="vdd2002" />. The live panel below gives the exact difference for any value.</>}
          es={<>La curva es la parte honesta de la comparación: la fracción del pico del motor y la de la línea base, para números reproductivos de un medio a seis, calculadas en este navegador. En todo el rango la línea base se mantiene cerca del motor y queda algo por debajo, y la brecha crece con R0, porque la infección inicial real y el paso de un cuarto de día pesan más cuando el brote es rápido <Cite id="vdd2002" />. El panel en vivo de abajo da la diferencia exacta para cualquier valor.</>}
        />
        <PlotCard title={{ en: 'Peak infected share against R0', es: 'Fracción de contagiados en el pico contra R0' }} lane="live" provenance="synthetic">
          <UPlotChart
            title={{ en: 'Peak infected share against R0', es: 'Fracción de contagiados en el pico contra R0' }}
            height={300}
            x={{ values: robustness.xs, label: { en: 'Basic reproduction number', es: 'Número reproductivo básico' } }}
            y={{ label: { en: 'Peak infected share', es: 'Fracción de contagiados en el pico' }, range: [0, 0.6] }}
            series={[
              { label: { en: 'Engine', es: 'Motor' }, values: robustness.engine, color: '--color-accent' },
              { label: { en: 'Analytic baseline', es: 'Línea base analítica' }, values: robustness.baseline, color: '--color-magenta' },
            ]}
          />
        </PlotCard>
      </DocSection>
      <DocSection title={{ en: 'Try a reproduction number', es: 'Probar un número reproductivo' }} area="live" noRefsReason={{ en: 'Runs the engine of this build in the browser.', es: 'Corre el motor de esta compilación en el navegador.' }}>
        <P
          en="Move the slider and the engine runs in this browser with the example's population, recovery rate and horizon, while the analytic baseline answers from the formula alone. The inputs are the example's synthetic parameters, not real records, and nothing leaves the page. The difference is the error the baseline would make for that reproduction number."
          es="Mueva el control y el motor corre en este navegador con la población, la tasa de recuperación y el horizonte del ejemplo, mientras la línea base analítica responde sólo con la fórmula. Las entradas son los parámetros sintéticos del ejemplo, no registros reales, y nada sale de la página. La diferencia es el error que cometería la línea base para ese número reproductivo."
        />
        <Knob id="bench-r0" label={{ en: 'Basic reproduction number R0', es: 'Número reproductivo básico R0' }} value={liveR0} min={0.5} max={6} step={0.05} onChange={setLiveR0} format={{ decimals: 2 }} />
        <table className="caos-table" data-state="ready">
          <thead>
            <tr>
              <th>{t('Engine peak share', 'Fracción del pico, motor')}</th>
              <th>{t('Analytic baseline', 'Línea base analítica')}</th>
              <th>{t('Difference', 'Diferencia')}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{formatNumber(live.engine, lang, { percent: true, decimals: 2 })}</td>
              <td>{formatNumber(live.base, lang, { percent: true, decimals: 2 })}</td>
              <td>{formatNumber(live.base - live.engine, lang, { percent: true, decimals: 2 })}</td>
            </tr>
          </tbody>
        </table>
      </DocSection>
      <DocSection title={{ en: 'Where each row comes from', es: 'De dónde viene cada fila' }} area="provenance" noRefsReason={{ en: 'Describes the data of this build.', es: 'Describe los datos de esta compilación.' }}>
        <P
          en="Every row above is traceable to its origin. The cases are synthetic parameter sets in the registry; the difficulty of each is its reproduction number, from a sub-critical case that never grows to a fast burn that peaks in under two weeks; and the data are free to redistribute because they are generated by this repository, with no third-party records."
          es="Cada fila de arriba se puede rastrear hasta su origen. Los casos son conjuntos sintéticos de parámetros en el registro; la dificultad de cada uno es su número reproductivo, desde un caso subcrítico que nunca crece hasta una combustión rápida que llega a su pico en menos de dos semanas; y los datos son libres de redistribuir porque los genera este repositorio, sin registros de terceros."
        />
        {cases ? (
          <table className="caos-table" data-state="ready">
            <thead>
              <tr>
                <th>{t('Case', 'Caso')}</th>
                <th>{t('Data', 'Datos')}</th>
                <th>{t('Difficulty (R0)', 'Dificultad (R0)')}</th>
                <th className="caos-col-text">{t('Redistribution', 'Redistribución')}</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.manifest.case_id}>
                  <td>{c.manifest.title[lang]}</td>
                  <td>{c.manifest.real_or_synthetic === 'synthetic' ? t('synthetic', 'sintéticos') : c.manifest.real_or_synthetic}</td>
                  <td>{formatNumber(c.manifest.params.beta / c.manifest.params.gamma, lang, { decimals: 2 })}</td>
                  <td className="caos-col-text">{t('Free: generated by this repository', 'Libre: la genera este repositorio')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <Pending all={all} wait={t('Loading the artifacts', 'Cargando los artefactos')} />
        )}
      </DocSection>
      <DocSection title={{ en: 'What this benchmark does not show', es: 'Lo que este benchmark no muestra' }} area="caveat" noRefsReason={{ en: 'States the limits of this page.', es: 'Declara los límites de esta página.' }}>
        <Callout variant="honest" title={t('A comparison of two models of the same model', 'Una comparación de dos modelos del mismo modelo')}>
          {t('The truth on this page is the example engine, not an outbreak. The tables say how well a formula and a fitted curve imitate it, on synthetic cases; they say nothing about accuracy on a real epidemic, and the timings are those of this device only.', 'La verdad en esta página es el motor del ejemplo, no un brote. Las tablas dicen cuán bien lo imitan una fórmula y una curva ajustada, en casos sintéticos; no dicen nada sobre la exactitud en una epidemia real, y los tiempos son sólo los de este dispositivo.')}
        </Callout>
      </DocSection>
    </DocPage>
  );
}
