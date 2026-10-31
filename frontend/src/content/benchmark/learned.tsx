// The learned models (area `comparison`: a learned model and a published baseline on the same data): the held-out metrics of the slots in the
// model-metrics document, which model answered each slot (the released one or its baseline) as the readiness document says, the M17 row beside
// its baseline M19 in the benchmark matrix and in the baked C14 case, and the measured negative of the warm-start slot.
import { Cite, DocSection, useShellLang } from '@fasl-work/caos-app-shell';
import type { BenchmarkResults, CaseManifest, ModelMetrics } from '../../lib/contract.types';
import { P } from '../bi';
import { modelAnswers } from '../../readiness/readiness';
import { useReadiness } from '../../readiness/useReadiness';
import { budgetText, CRITERIA, pickRows, shownId, type Lang } from './data';
import { CellControls, Note, Pending, Ready, TableWrap, useBench, useNum, useResolved } from './shared';
import { WARM } from './warm';

function Answers({ slot }: { slot: 'cgh-net' | 'warmstart-model' }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const doc = useReadiness();
  if (doc === undefined) return null;
  const who = modelAnswers(doc, slot);
  const base = slot === 'cgh-net' ? 'M19' : (es ? 'el arranque aleatorio de M07' : 'the random start of M07');
  return (
    <span data-slot={slot} data-answers={who}>
      {who === 'model' ? (es ? 'responde el modelo publicado' : 'the released model answers') : es ? `responde la línea base (${base})` : `the baseline answers (${base})`}
    </span>
  );
}

function MetricsTable({ metrics }: { metrics: ModelMetrics }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const { n } = useNum();
  const cgh = metrics.slots['cgh-net'];
  const warm = metrics.slots['warmstart-model'];
  return (
    <TableWrap>
      <table className="caos-table" data-state="ready" data-table="learned-metrics">
        <caption>
          {es
            ? `Las métricas reservadas de los espacios de modelo en la versión ${metrics.engine_version} del motor, leídas del documento de métricas. Un espacio sin modelo publicado no tiene entrada; el documento de disponibilidad dice qué modelo responde.`
            : `The held-out metrics of the model slots at engine version ${metrics.engine_version}, read from the metrics document. A slot with no released model has no entry; the readiness document says which model answers.`}
        </caption>
        <thead>
          <tr>
            <th className="caos-col-text">{es ? 'Espacio' : 'Slot'}</th>
            <th className="caos-col-text">{es ? 'Quién responde' : 'Who answers'}</th>
            <th>{es ? 'Reservados' : 'Held out'}</th>
            <th className="caos-col-text">{es ? 'Medida' : 'Measure'}</th>
            <th>{es ? 'Mediana [Q1, Q3]' : 'Median [Q1, Q3]'}</th>
            <th className="caos-col-text">{es ? 'Línea base' : 'Baseline'}</th>
          </tr>
        </thead>
        <tbody>
          {cgh ? (
            <>
              <tr data-slot="cgh-net">
                <td className="caos-col-text" rowSpan={2}>cgh-net (M17)</td>
                <td className="caos-col-text" rowSpan={2}><Answers slot="cgh-net" /></td>
                <td rowSpan={2}>{cgh.held_out_n}</td>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>{es ? 'exactitud sobre la de la línea base, con el mismo reloj' : 'accuracy over the baseline at the same wall-clock'}</td>
                <td>
                  {n(cgh.accuracy_vs_gs.median, 4)} [{n(cgh.accuracy_vs_gs.q1, 4)}, {n(cgh.accuracy_vs_gs.q3, 4)}]
                </td>
                <td className="caos-col-text" rowSpan={2}>{cgh.baseline} {es ? '(GS multiplano)' : '(multi-plane GS)'}</td>
              </tr>
              <tr>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>{es ? 'tiempo de una solución en la comparación (ms)' : 'time of one solve in the comparison (ms)'}</td>
                <td>
                  {n(cgh.time_ms.median, 4)} [{n(cgh.time_ms.q1, 4)}, {n(cgh.time_ms.q3, 4)}]
                </td>
              </tr>
            </>
          ) : (
            <tr data-slot="cgh-net">
              <td className="caos-col-text">cgh-net (M17)</td>
              <td className="caos-col-text"><Answers slot="cgh-net" /></td>
              <td colSpan={4} className="caos-col-text">{es ? 'Sin entrada en el documento de métricas: no hay modelo publicado.' : 'No entry in the metrics document: no released model.'}</td>
            </tr>
          )}
          {warm ? (
            <tr data-slot="warmstart-model">
              <td className="caos-col-text">warmstart-model (B3)</td>
              <td className="caos-col-text"><Answers slot="warmstart-model" /></td>
              <td>{warm.held_out_n}</td>
              <td className="caos-col-text">{es ? 'iteraciones hasta 1 por ciento, modelo' : 'iterations to 1 percent, model'}</td>
              <td>{n(warm.iterations_to_1pct.model.median)} [{n(warm.iterations_to_1pct.model.q1)}, {n(warm.iterations_to_1pct.model.q3)}]</td>
              <td className="caos-col-text">{es ? 'arranque aleatorio de M07' : 'M07 random start'}: {n(warm.iterations_to_1pct.random.median)}</td>
            </tr>
          ) : (
            <tr data-slot="warmstart-model">
              <td className="caos-col-text">warmstart-model (B3)</td>
              <td className="caos-col-text"><Answers slot="warmstart-model" /></td>
              <td colSpan={4} className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                {es ? 'Sin entrada: no hay modelo publicado.' : 'No entry: no released model.'}
                {WARM ? (es ? ` Se entrenó y se rechazó: mediana de ${n(WARM.metrics.iterations_to_1pct.model.median)} iteraciones contra ${n(WARM.metrics.iterations_to_1pct.random.median)} del arranque aleatorio (${n(WARM.ratio_random_over_model_median_iterations)} veces; el criterio pide ${CRITERIA.b3.iterationFactor}).` : ` It was trained and rejected: median ${n(WARM.metrics.iterations_to_1pct.model.median)} iterations against ${n(WARM.metrics.iterations_to_1pct.random.median)} from the random start (${n(WARM.ratio_random_over_model_median_iterations)} times; the criterion asks for ${CRITERIA.b3.iterationFactor}).`) : ''}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </TableWrap>
  );
}

/** M17 beside its baseline M19, in the matrix cells that hold both and in the baked C14 case. */
function PairTable({ res, c14 }: { res: BenchmarkResults; c14: CaseManifest | undefined }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const { n } = useNum();
  const { device, view, budget } = useResolved(res);
  const rows = budget
    ? res.geometries.flatMap((g) => {
        const picked = pickRows(res, g.id, device, budget, view);
        const a = picked.find((p) => p.method === 'M17');
        const b = picked.find((p) => p.method === 'M19');
        return a && b ? [{ g, a, b }] : [];
      })
    : [];
  const m17 = c14?.methods.M17;
  const m19 = c14?.methods.M19;
  const same = m17 && m19 ? ['efficiency', 'uniformity', 'rel_std_pct'].every((k) => Math.abs((m17 as never)[k] - (m19 as never)[k]) < 5e-4 * Math.max(1, Math.abs((m19 as never)[k]))) : false;
  return (
    <>
      <CellControls res={res} prefix="learned" />
      {rows.length === 0 ? (
        <p className="caos-pending" data-state="unavailable">
          {es ? `Ninguna geometría del documento tiene filas de M17 y de M19 con ${budget ? budgetText(budget).es : 'este presupuesto'} sobre este dispositivo.` : `No geometry of the document has rows of both M17 and M19 at ${budget ? budgetText(budget).en : 'this budget'} on this device.`}
        </p>
      ) : (
        <TableWrap>
          <table className="caos-table" data-state="ready" data-table="m17-m19">
            <caption>
              {es ? 'M17 y su línea base M19 en la matriz, con la misma geometría, dispositivo y presupuesto.' : 'M17 and its baseline M19 in the matrix, on the same geometry, device and budget.'}
            </caption>
            <thead>
              <tr>
                <th className="caos-col-text">{es ? 'Geometría' : 'Geometry'}</th>
                <th className="caos-col-text">{es ? 'Método' : 'Method'}</th>
                <th>{es ? 'Eficiencia' : 'Efficiency'}</th>
                <th>{es ? 'Uniformidad' : 'Uniformity'}</th>
                <th>{es ? 'Desv. est. relativa (%)' : 'Rel. std (%)'}</th>
                <th>{es ? 'Tiempo (s)' : 'Time (s)'}</th>
              </tr>
            </thead>
            <tbody>
              {rows.flatMap(({ g, a, b }) =>
                [a, b].map((p) => (
                  <tr key={`${g.id}-${p.method}`}>
                    <td className="caos-col-text">{g.id}</td>
                    <td className="caos-col-text">{shownId(p.method)}</td>
                    <td>{n(p.row.efficiency.median)}</td>
                    <td>{n(p.row.uniformity.median)}</td>
                    <td>{n(p.row.rel_std_pct.median)}</td>
                    <td>{n(p.row.time_s.median)}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </TableWrap>
      )}
      {m17 && m19 ? (
        <p className="caos-plot-note" lang={lang} data-case="C14">
          {es
            ? `En el caso C14 generado, M17 tiene eficiencia ${n(m17.efficiency)}, uniformidad ${n(m17.uniformity)} y desviación estándar relativa ${n(m17.rel_std_pct)} por ciento, y M19 ${n(m19.efficiency)}, ${n(m19.uniformity)} y ${n(m19.rel_std_pct)}.`
            : `In the baked case C14, M17 has efficiency ${n(m17.efficiency)}, uniformity ${n(m17.uniformity)} and relative standard deviation ${n(m17.rel_std_pct)} percent, and M19 ${n(m19.efficiency)}, ${n(m19.uniformity)} and ${n(m19.rel_std_pct)}.`}
          {same ? (es ? ' Las dos filas coinciden en los dígitos mostrados, de modo que esa fila de caso no mide la red: lo que la mide son las métricas reservadas de la tabla anterior.' : ' The two rows agree to the digits shown, so that case row does not measure the network: what measures it is the held-out metrics of the table above.') : ''}
        </p>
      ) : null}
    </>
  );
}

export function LearnedTopic() {
  const { data } = useBench();
  return (
    <DocSection title={{ en: 'Learned models against their published baselines', es: 'Modelos aprendidos frente a sus líneas base publicadas' }} id="learned" area="comparison" refs={['eybposh2020', 'whyte2005']}>
      <P
        en={
          <>
            DinHot has two learned slots. The multi-plane network of M17 is built in the setting of DeepCGH <Cite id="eybposh2020" />: three plane amplitudes in, one phase out, trained without labels on a loss that is the accuracy itself, and judged against the volumetric GS of Whyte and Courtial <Cite id="whyte2005" /> given the same wall-clock. The warm-start network of B3 predicts the starting trap phases of the phase-fixed WGS. A learned slot is shown only against its published baseline on held-out volumes or geometries, never against a number from a paper, and the table says which model answered: the released network, or the baseline that answers when the slot is in training state.
          </>
        }
        es={
          <>
            DinHot tiene dos espacios aprendidos. La red multiplano de M17 se construye en el planteamiento de DeepCGH <Cite id="eybposh2020" />: tres amplitudes de plano de entrada, una fase de salida, entrenada sin etiquetas con una pérdida que es la propia exactitud, y se juzga contra el GS volumétrico de Whyte y Courtial <Cite id="whyte2005" /> con el mismo reloj. La red de arranque de B3 predice las fases iniciales de las trampas del WGS de fase fija. Un espacio aprendido se muestra solo frente a su línea base publicada sobre volúmenes o geometrías reservados, nunca contra un número de un artículo, y la tabla dice qué modelo respondió: la red publicada, o la línea base que responde cuando el espacio está en estado de entrenamiento.
          </>
        }
      />
      <Note ids={['cgh-net', 'warmstart-model', 'model-metrics']} />
      <Ready a={data.metrics}>{(m) => <MetricsTable metrics={m} />}</Ready>
      <P
        en="The accuracy is the mean over the planes of the overlap between the target and the reconstructed intensity, so a ratio above 1 means the network's hologram matches the target better than the baseline's at the same wall-clock. The ratio is a median over the held-out volumes with its quartiles; the volumes are generated before the final training run and are never part of it. A ratio near 1 would be a tie, and the benchmark would say so as it says the negative of the warm start."
        es="La exactitud es la media sobre los planos del traslape entre el objetivo y la intensidad reconstruida, de modo que una razón mayor que 1 significa que el holograma de la red se parece más al objetivo que el de la línea base con el mismo reloj. La razón es una mediana sobre los volúmenes reservados con sus cuartiles; los volúmenes se generan antes de la corrida final de entrenamiento y nunca forman parte de ella. Una razón cercana a 1 sería un empate, y el benchmark lo diría como dice el negativo del arranque aprendido."
      />
      {data.results.state === 'ready' ? <PairTable res={data.results.data} c14={data.c14.state === 'ready' ? data.c14.data : undefined} /> : <Pending of={data.results} />}
    </DocSection>
  );
}
