// Every case, read from its committed artifacts and compared with the theory. No number on this page is typed
// in: the table and the chart are computed from the index, the manifests and the traces at load time (T13).
import { Callout, Cite, DocPage, DocSection, Equation, Figure, PlotCard, Tabs, formatNumber, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import { loadAllCases, useArtifact, type Loaded } from '../api/artifacts';
import { finalSize, simulate } from '../engine/sir';
import { FlowFigure } from '../content/figures';
import { P, useT } from '../content/bi';
import { ReadinessNote } from '../readiness/ReadinessNote';

const IMMUNE = [0, 0.3, 0.6];
const ARTIFACT_ROWS = ['case-index', 'case-manifest', 'trace'];

/** What stands where the cases would be: the loading line, the error, or not available yet with the reason. */
function Pending({ all }: { all: Loaded<{ cases: unknown[] }> }) {
  const lang = useShellLang();
  const t = useT();
  if (all.state === 'unavailable') return <p className="caos-pending" data-state="unavailable">{all.reason[lang]}</p>;
  if (all.state === 'error') return <p className="caos-pending" data-state="error">{all.error}</p>;
  if (all.state === 'ready') {
    return <p className="caos-pending" data-state="unavailable">{t('Not available yet: no case of this build has its artifacts.', 'Aún no disponible: ningún caso de esta versión tiene sus artefactos.')}</p>;
  }
  return <p className="caos-pending" data-state="loading">{t('Loading the artifacts', 'Cargando los artefactos')}</p>;
}

export function Experiments() {
  const lang = useShellLang();
  const t = useT();
  const all = useArtifact((s) => loadAllCases(s), []);
  const rows = useMemo(() => {
    if (all.state !== 'ready') return null;
    if (!all.data.cases.length) return null;
    return all.data.cases.map(({ manifest: m, trace }) => {
      const r0 = m.params.beta / m.params.gamma;
      return { m, r0, s: trace.summary, z: finalSize(r0) };
    });
  }, [all]);
  const chart = useMemo(() => {
    if (!rows) return null;
    const grid = Array.from({ length: 61 }, (_, k) => Math.round((0.4 + k * 0.1) * 100) / 100);
    const xs = [...new Set([...grid, ...rows.map((r) => Math.round(r.r0 * 100) / 100)])].sort((a, b) => a - b);
    const caseAt = new Map(rows.map((r) => [Math.round(r.r0 * 100) / 100, r.s.attack_rate]));
    return { xs, theory: xs.map(finalSize), cases: xs.map((x) => caseAt.get(x) ?? null) };
  }, [rows]);

  return (
    <DocPage wide title={{ en: 'Experiments', es: 'Experimentos' }} lede={t('The questions the example answers, one per tab: what each case shows, how a run compares with the final-size relation, how much immunity stops an outbreak, and the metrics, the held-out protocol and the data behind them.', 'Las preguntas que responde el ejemplo, una por pestaña: qué muestra cada caso, cómo se compara una corrida con la relación de tamaño final, cuánta inmunidad detiene un brote, y las métricas, el protocolo con datos reservados y los datos detrás de ellas.')}>
      <Tabs
        ariaLabel={t('Experiments', 'Experimentos')}
        tabs={[
          { id: 'cases', label: t('Cases', 'Casos'), content: <>
              <DocSection title={{ en: 'The cases', es: 'Los casos' }} area="question" refs={['km1927']}>
                <P
                  en="Each row is one case of the registry: its reproduction number, the peak and the attack rate of its committed trace, the share the final-size relation predicts for a fully run epidemic, and what a reader should expect to see."
                  es="Cada fila es un caso del registro: su número reproductivo, el pico y la tasa de ataque de su traza comprometida, la fracción que predice la relación de tamaño final para una epidemia completa, y lo que el lector debería esperar ver."
                />
                <P
                  en="The question each case answers is different. The sub-critical case asks whether the engine keeps an epidemic from starting below the threshold; the epidemic and the fast-burn cases ask whether it reaches the final size and how early the peak comes; the slow-spread case asks what the horizon hides near the threshold; and the control asks whether nothing happens when nothing is seeded."
                  es="La pregunta que responde cada caso es distinta. El caso subcrítico pregunta si el motor impide que empiece una epidemia bajo el umbral; los casos de epidemia y de combustión rápida preguntan si se alcanza el tamaño final y cuán temprano llega el pico; el de propagación lenta pregunta qué oculta el horizonte cerca del umbral; y el control pregunta si no pasa nada cuando no se siembra nada."
                />
                <ReadinessNote ids={ARTIFACT_ROWS} />
                {all.state === 'ready' && all.data.absent.map((a) => (
                  <p key={a.caseId} className="caos-pending" data-state="unavailable">
                    {a.title[lang]}: {a.reason[lang]}
                  </p>
                ))}
                {rows ? (
                  <table className="caos-table" data-state="ready">
                    <thead>
                      <tr>
                        <th>{t('Case', 'Caso')}</th>
                        <th>R0</th>
                        <th>{t('Peak infected', 'Pico de contagiados')}</th>
                        <th>{t('Peak day', 'Día del pico')}</th>
                        <th>{t('Attack rate', 'Tasa de ataque')}</th>
                        <th>{t('Final size', 'Tamaño final')}</th>
                        <th className="caos-col-text">{t('Expected', 'Esperado')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((r) => (
                        <tr key={r.m.case_id}>
                          <td>{r.m.title[lang]}</td>
                          <td>{formatNumber(r.r0, lang, { decimals: 2 })}</td>
                          <td>{formatNumber(r.s.peak_I, lang, { decimals: 0 })}</td>
                          <td>{formatNumber(r.s.t_peak, lang, { decimals: 1 })}</td>
                          <td>{formatNumber(r.s.attack_rate, lang, { percent: true, decimals: 1 })}</td>
                          <td>{formatNumber(r.z, lang, { percent: true, decimals: 1 })}</td>
                          <td className="caos-col-text">{r.m.expected_band[lang]}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <Pending all={all} />
                )}
              </DocSection>
          </> },
          { id: 'theory', label: t('Against the theory', 'Contra la teoría'), content: <>
              <DocSection title={{ en: 'Against the theory', es: 'Contra la teoría' }} area="question" refs={['km1927', 'miller2012']}>
                <P
                  en="The curve is the final-size relation; the points are the cases as baked, at the end of their horizon. A point on the curve is an epidemic that ran to its end. A point below it ran out of time (the slow-spread case, close to the threshold) or never started (the control without an initial infection)."
                  es="La curva es la relación de tamaño final; los puntos son los casos tal como se precalcularon, al final de su horizonte. Un punto sobre la curva es una epidemia que llegó a su fin. Un punto bajo ella se quedó sin tiempo (el caso de propagación lenta, cerca del umbral) o nunca empezó (el control sin contagio inicial)."
                />
                <P
                  en="The distance between a point and the curve is the answer to the question, case by case. It is zero within the rounding of the trace when the run ended inside its horizon, and it is not a fault of the engine when it is not: the cases that fall short are exactly those the horizon or the threshold explains, and the table of the previous tab says which."
                  es="La distancia entre un punto y la curva es la respuesta a la pregunta, caso por caso. Es cero dentro del redondeo de la traza cuando la corrida terminó dentro de su horizonte, y no es una falla del motor cuando no lo es: los casos que quedan cortos son exactamente los que el horizonte o el umbral explican, y la tabla de la pestaña anterior dice cuáles."
                />
                {chart ? (
                  <PlotCard title={{ en: 'Attack rate against R0', es: 'Tasa de ataque contra R0' }} lane="replay" provenance="synthetic">
                    <UPlotChart
                      title={{ en: 'Attack rate against R0', es: 'Tasa de ataque contra R0' }}
                      height={320}
                      x={{ values: chart.xs, label: { en: 'Basic reproduction number', es: 'Número reproductivo básico' } }}
                      y={{ label: { en: 'Attack rate', es: 'Tasa de ataque' }, range: [0, 1] }}
                      series={[
                        { label: { en: 'Final-size relation', es: 'Relación de tamaño final' }, values: chart.theory, color: '--color-accent' },
                        { label: { en: 'Baked cases', es: 'Casos precalculados' }, values: chart.cases, color: '--color-magenta', mode: 'points' },
                      ]}
                    />
                  </PlotCard>
                ) : (
                  <Pending all={all} />
                )}
              </DocSection>
          </> },
          { id: 'immunity', label: t('Immunity', 'Inmunidad'), content: <>
              <DocSection title={{ en: 'How much immunity is enough', es: 'Cuánta inmunidad basta' }} area="question" refs={['diekmann1990', 'vdd2002']}>
                <P
                  en={<>The question is the one a planner asks: if a share of the population is immune before the outbreak, how much of the rest is still infected? The engine is re-run in this browser for every case with none, thirty and sixty percent of the susceptible moved to the recovered at the start, and the attack rate is shown beside the immune share that the threshold relation says is enough <Cite id="diekmann1990" />.</>}
                  es={<>La pregunta es la que se hace un planificador: si una fracción de la población es inmune antes del brote, ¿cuánta del resto se contagia aún? El motor se vuelve a correr en este navegador para cada caso con cero, treinta y sesenta por ciento de los susceptibles pasados a recuperados al inicio, y la tasa de ataque se muestra junto a la fracción inmune que la relación de umbral dice que basta <Cite id="diekmann1990" />.</>}
                />
                <P
                  en={<>Below the threshold share the epidemic is smaller but still happens; above it the infection dies out almost at once <Cite id="vdd2002" />. A case whose reproduction number is at or below one needs no immunity at all, so its row reads the same in every column. The numbers are computed on this page from the committed parameters and the live engine, and none is typed in.</>}
                  es={<>Bajo la fracción umbral la epidemia es menor pero igual ocurre; sobre ella la infección se extingue casi de inmediato <Cite id="vdd2002" />. Un caso cuyo número reproductivo es igual o menor que uno no necesita inmunidad alguna, así que su fila se lee igual en cada columna. Los números se calculan en esta página a partir de los parámetros comprometidos y el motor en vivo, y ninguno está escrito a mano.</>}
                />
                {rows ? (
                  <table className="caos-table" data-state="ready">
                    <thead>
                      <tr>
                        <th>{t('Case', 'Caso')}</th>
                        <th>R0</th>
                        <th>{t('Immune share that is enough', 'Fracción inmune suficiente')}</th>
                        {IMMUNE.map((v) => (
                          <th key={v}>{t(`Attack rate at ${Math.round(v * 100)}% immune`, `Tasa de ataque con ${Math.round(v * 100)}% inmune`)}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((r) => (
                        <tr key={r.m.case_id}>
                          <td>{r.m.title[lang]}</td>
                          <td>{formatNumber(r.r0, lang, { decimals: 2 })}</td>
                          <td>{r.r0 > 1 ? formatNumber(1 - 1 / r.r0, lang, { percent: true, decimals: 1 }) : t('none needed', 'ninguna')}</td>
                          {IMMUNE.map((v) => (
                            <td key={v}>{formatNumber(simulate({ ...r.m.params, vaccinated: v }).attackRate, lang, { percent: true, decimals: 1 })}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <Pending all={all} />
                )}
              </DocSection>
          </> },
          { id: 'metrics', label: t('Metrics', 'Métricas'), content: <>
              <DocSection title={{ en: 'The metrics', es: 'Las métricas' }} area="metrics" refs={['km1927']}>
                <P
                  en={<>Two numbers judge a run on this page. The attack rate is the share of the population ever infected, the recovered count at the end over N; it is compared with the final size that the relation of Kermack and McKendrick fixes <Cite id="km1927" />. The gap between them is what the Against the theory tab plots, and it is zero for a run that ended inside its horizon.</>}
                  es={<>Dos números juzgan una corrida en esta página. La tasa de ataque es la fracción de la población que llegó a contagiarse, la cuenta de recuperados al final sobre N; se compara con el tamaño final que fija la relación de Kermack y McKendrick <Cite id="km1927" />. La brecha entre ambos es lo que grafica la pestaña Contra la teoría, y es cero para una corrida que terminó dentro de su horizonte.</>}
                />
                <Equation tex="a = \frac{R(T)}{N}, \qquad \delta = a - z, \qquad z = 1 - e^{-R_0 z}" caption={t('The attack rate a at the horizon T, and its gap δ from the final size z.', 'La tasa de ataque a en el horizonte T, y su brecha δ respecto del tamaño final z.')} />
                <Equation tex="\mathrm{RMSE} = \sqrt{\frac{1}{n} \sum_{j=1}^{n} \left( \hat{y}_j - y_j \right)^2}, \qquad R^2 = 1 - \frac{\sum_j (\hat{y}_j - y_j)^2}{\sum_j (y_j - \bar{y})^2}" caption={t('The held-out error of the learned surrogate on the peak share: root-mean-square error and the coefficient of determination, over n sets.', 'El error reservado del sustituto aprendido sobre la fracción del pico: error cuadrático medio y coeficiente de determinación, sobre n conjuntos.')} />
                <P
                  en="No percentage error is used. The peak share of a sub-critical draw is close to zero, and an error divided by a number near zero grows without bound whatever the model does, so it would punish a good fit and reward a bad one. The metrics are those of the pipeline's evaluation stage, written into each manifest."
                  es="No se usa error porcentual. La fracción del pico de un sorteo subcrítico es cercana a cero, y un error dividido por un número cercano a cero crece sin límite haga lo que haga el modelo, de modo que castigaría un buen ajuste y premiaría uno malo. Las métricas son las de la etapa de evaluación del pipeline, escritas en cada manifiesto."
                />
              </DocSection>
          </> },
          { id: 'protocol', label: t('Protocol', 'Protocolo'), content: <>
              <DocSection title={{ en: 'The protocol', es: 'El protocolo' }} area="protocol" noRefsReason={{ en: 'Describes this build.', es: 'Describe esta compilación.' }}>
                <P
                  en="The learned surrogate is trained on the four cases of the registry that start with an infection and judged on twenty parameter sets drawn from a generator seeded with the bake seed plus a fixed offset. The held-out sets never enter the fit, and the same draw is used for the analytic baseline, so the comparison is leakage-safe and repeatable."
                  es="El sustituto aprendido se entrena con los cuatro casos del registro que parten con una infección y se juzga en veinte conjuntos de parámetros sorteados con un generador sembrado con la semilla del precálculo más un desplazamiento fijo. Los conjuntos reservados nunca entran al ajuste, y el mismo sorteo se usa para la línea base analítica, así que la comparación no tiene fuga y es repetible."
                />
                <Figure caption={t('The held-out protocol, and the anti-pattern it forbids: scoring the model on the cases it was fitted to.', 'El protocolo con datos reservados, y el antipatrón que prohíbe: puntuar el modelo en los casos con que se ajustó.')}>
                  <FlowFigure stages={[t('Four training cases', 'Cuatro casos de entrenamiento'), t('Fit the surrogate', 'Ajustar el sustituto'), t('Twenty new sets', 'Veinte conjuntos nuevos'), t('Score on those only', 'Puntuar sólo en esos')]} label={t('The held-out protocol', 'El protocolo con datos reservados')} tone="warn" />
                </Figure>
                <Callout variant="honest" title={t('The forbidden shortcut', 'El atajo prohibido')}>
                  {t('Scoring the four fitted cases would give a near-perfect error and mean nothing: four points fit four coefficients. Only the held-out draw is reported.', 'Puntuar los cuatro casos ajustados daría un error casi perfecto y no significaría nada: cuatro puntos ajustan cuatro coeficientes. Sólo se informa el sorteo reservado.')}
                </Callout>
              </DocSection>
          </> },
          { id: 'datasets', label: t('Datasets', 'Datos'), content: <>
              <DocSection title={{ en: 'The datasets', es: 'Los conjuntos de datos' }} area="datasets" noRefsReason={{ en: 'Describes the data of this build.', es: 'Describe los datos de esta compilación.' }}>
                <P
                  en="There is no external dataset. Every case is a set of parameters written in the registry, and every number on the site is computed from them, so there is nothing to redistribute and nothing to license beyond the repository itself. A product that reads real data states its source, its redistribution class and its status here, in the same table."
                  es="No hay conjunto de datos externo. Cada caso es un conjunto de parámetros escrito en el registro, y cada número del sitio se calcula a partir de ellos, de modo que no hay nada que redistribuir ni licenciar más allá del propio repositorio. Un producto que lee datos reales declara aquí su fuente, su clase de redistribución y su estado, en la misma tabla."
                />
                <table className="caos-table" data-state="ready">
                  <thead>
                    <tr>
                      <th>{t('Data', 'Datos')}</th>
                      <th className="caos-col-text">{t('Origin', 'Origen')}</th>
                      <th className="caos-col-text">{t('Redistribution', 'Redistribución')}</th>
                      <th>{t('Status', 'Estado')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{t('Five cases', 'Cinco casos')}</td>
                      <td className="caos-col-text">{t('Synthetic parameters in the registry', 'Parámetros sintéticos en el registro')}</td>
                      <td className="caos-col-text">{t('Free: part of this repository', 'Libre: parte de este repositorio')}</td>
                      <td>{t('live', 'en vivo')}</td>
                    </tr>
                    <tr>
                      <td>{t('Twenty held-out sets', 'Veinte conjuntos reservados')}</td>
                      <td className="caos-col-text">{t('Seeded synthetic draw', 'Sorteo sintético con semilla')}</td>
                      <td className="caos-col-text">{t('Free: regenerated by the bake', 'Libre: se regenera en el precálculo')}</td>
                      <td>{t('live', 'en vivo')}</td>
                    </tr>
                    <tr>
                      <td>{t('Real outbreak records', 'Registros de brotes reales')}</td>
                      <td className="caos-col-text">{t('None used', 'Ninguno usado')}</td>
                      <td className="caos-col-text">{t('Not applicable', 'No aplica')}</td>
                      <td>{t('roadmap', 'hoja de ruta')}</td>
                    </tr>
                  </tbody>
                </table>
              </DocSection>
          </> },
        ]}
      />
    </DocPage>
  );
}
