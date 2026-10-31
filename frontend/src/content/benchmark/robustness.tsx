// Robustness and degradation (area `robustness`): what the device costs each method (the same hologram scored against the ideal device and the C08
// device) and how fast each method converges with its budget (the relative standard deviation against the iteration budget). Both are read from
// the benchmark document; a method with a row on one side only is left out of the pair, never paired with another budget.
import { ChipGroup, Cite, DocSection, PlotCard, useFormat, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useState } from 'react';
import type { BenchmarkResults } from '../../lib/contract.types';
import { P } from '../bi';
import { budgetText, budgetsOf, geometryOf, nameOf, orderMethods, pickRows, shownId, kindOf, KIND_TEXT, type Budget, type Lang } from './data';
import { Note, Ready, TableWrap, useBench, useNum, useResolved, CellControls, spreadText } from './shared';

const FLOOR = 1e-3;

function GeometryChips({ res, value, onChange, id }: { res: BenchmarkResults; value: string; onChange: (g: string) => void; id: string }) {
  return (
    <ChipGroup
      id={id}
      label={{ en: 'Geometry', es: 'Geometría' }}
      options={res.geometries.map((g) => ({ id: g.id, label: { en: g.id, es: g.id }, hint: g.name }))}
      value={value}
      onChange={onChange}
    />
  );
}

function DeviceBody({ res }: { res: BenchmarkResults }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const { n } = useNum();
  const fl = useFormat()(FLOOR, { digits: 3 });
  const { budget } = useResolved(res);
  const [geo, setGeo] = useState('');
  const geometry = res.geometries.find((g) => g.id === geo)?.id ?? res.geometries[0]?.id ?? '';
  if (!budget) return null;
  const ideal = pickRows(res, geometry, 'ideal', budget, 'default');
  const dev = pickRows(res, geometry, 'device', budget, 'default');
  const pairs = ideal.flatMap((a) => {
    const b = dev.find((p) => p.method === a.method);
    return b ? [{ method: a.method, a, b }] : [];
  });
  const lost = ideal.filter((a) => !dev.some((p) => p.method === a.method)).map((a) => a.method);
  const g = geometryOf(res, geometry);
  const title = { en: `Relative standard deviation, ideal device and C08 device, ${geometry}`, es: `Desviación estándar relativa, dispositivo ideal y dispositivo C08, ${geometry}` };
  return (
    <>
      <GeometryChips res={res} value={geometry} onChange={setGeo} id="robust-geometry" />
      <CellControls res={res} prefix="robust" showView={false} />
      {pairs.length === 0 ? (
        <p className="caos-pending" data-state="unavailable">
          {es ? `Ningún método de ${geometry} tiene filas sobre ambos dispositivos con ${budgetText(budget).es}.` : `No method of ${geometry} has rows on both devices at ${budgetText(budget).en}.`}
        </p>
      ) : (
        <>
          <PlotCard
            title={title}
            lane="offline"
            provenance="synthetic"
            note={{
              en: `Each method's hologram scored against the ideal device and against the C08 device (4-bit phase, crosstalk, fill factor, flicker), at ${budgetText(budget).en}, default parameters. A value below ${fl} is drawn at ${fl}.`,
              es: `El holograma de cada método evaluado contra el dispositivo ideal y contra el dispositivo C08 (fase de 4 bits, diafonía, factor de llenado, parpadeo), con ${budgetText(budget).es} y parámetros por defecto. Un valor bajo ${fl} se dibuja en ${fl}.`,
            }}
          >
            <UPlotChart
              title={title}
              height={320}
              x={{ label: { en: 'Method', es: 'Método' }, values: pairs.map((_, i) => i + 1), range: [0.5, pairs.length + 0.5], ticks: pairs.map((p, i) => ({ value: i + 1, label: { en: p.method, es: p.method } })) }}
              y={{ label: { en: 'Relative standard deviation', es: 'Desviación estándar relativa' }, unit: { en: '%', es: '%' }, log: true, format: { digits: 3 } }}
              series={[
                { id: 'ideal', label: { en: 'ideal device', es: 'dispositivo ideal' }, mode: 'points', size: 10, values: pairs.map((p) => Math.max(p.a.row.rel_std_pct.median, FLOOR)) },
                { id: 'device', label: { en: 'C08 device', es: 'dispositivo C08' }, mode: 'points', size: 10, values: pairs.map((p) => Math.max(p.b.row.rel_std_pct.median, FLOOR)) },
              ]}
              solo
              readout={(i) => {
                const p = pairs[i];
                return p ? `${shownId(p.method)} ${nameOf(p.method, lang)}: ${es ? 'ideal' : 'ideal'} ${spreadText(p.a.row.rel_std_pct.median, lang)}, C08 ${spreadText(p.b.row.rel_std_pct.median, lang)}` : '';
              }}
            />
          </PlotCard>
          <TableWrap>
            <table className="caos-table" data-state="ready" data-table="degradation">
              <caption>
                {es
                  ? `Lo que el dispositivo le cuesta a cada método en ${geometry}${g ? `, ${g.name.es}` : ''}, con ${budgetText(budget).es}: el cociente de la desviación estándar relativa con el dispositivo sobre la ideal (mayor es peor) y el de las eficiencias.`
                  : `What the device costs each method on ${geometry}${g ? `, ${g.name.en}` : ''}, at ${budgetText(budget).en}: the ratio of the relative standard deviation with the device over the ideal one (higher is worse) and of the efficiencies.`}
              </caption>
              <thead>
                <tr>
                  <th className="caos-col-text">{es ? 'Método' : 'Method'}</th>
                  <th className="caos-col-text">{es ? 'Tipo' : 'Kind'}</th>
                  <th>{es ? 'Desv. est. rel. ideal (%)' : 'Rel. std ideal (%)'}</th>
                  <th>{es ? 'Desv. est. rel. C08 (%)' : 'Rel. std C08 (%)'}</th>
                  <th>{es ? 'Cociente de desviación' : 'Deviation ratio'}</th>
                  <th>{es ? 'Cociente de eficiencia' : 'Efficiency ratio'}</th>
                </tr>
              </thead>
              <tbody>
                {pairs.map((p) => {
                  const t = kindOf(p.method);
                  return (
                    <tr key={p.method}>
                      <td className="caos-col-text">{shownId(p.method)}</td>
                      <td className="caos-col-text">{t ? KIND_TEXT[t][lang] : '-'}</td>
                      <td>{n(p.a.row.rel_std_pct.median)}</td>
                      <td>{n(p.b.row.rel_std_pct.median)}</td>
                      <td>{p.a.row.rel_std_pct.median > 0 ? n(p.b.row.rel_std_pct.median / p.a.row.rel_std_pct.median) : '-'}</td>
                      <td>{p.a.row.efficiency.median > 0 ? n(p.b.row.efficiency.median / p.a.row.efficiency.median) : '-'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </TableWrap>
          {lost.length ? (
            <p className="caos-plot-note" lang={lang}>
              {es ? `Sin fila sobre el dispositivo en esta celda, y por eso fuera de la comparación: ${lost.map(shownId).join(', ')}.` : `No row on the device in this cell, and so left out of the comparison: ${lost.map(shownId).join(', ')}.`}
            </p>
          ) : null}
        </>
      )}
    </>
  );
}

function BudgetBody({ res }: { res: BenchmarkResults }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const { device } = useResolved(res);
  const fl = useFormat()(FLOOR, { digits: 3 });
  const [geo, setGeo] = useState('');
  const [kind, setKind] = useState('all');
  const geometry = res.geometries.find((g) => g.id === geo)?.id ?? res.geometries[0]?.id ?? '';
  const iters: Budget[] = budgetsOf(res).filter((b) => b.kind === 'iterations');
  const methods = [...new Set(res.rows.filter((r) => r.geometry === geometry && r.device === device && r.budget_kind === 'iterations' && r.params === 'default').map((r) => r.method))]
    .filter((m) => kind === 'all' || kindOf(m) === kind)
    .filter((m) => iters.filter((b) => res.rows.some((r) => r.method === m && r.geometry === geometry && r.device === device && r.budget_kind === 'iterations' && r.budget === b.value && r.params === 'default')).length >= 2)
    .sort(orderMethods);
  const title = { en: `Relative standard deviation against the iteration budget, ${geometry}`, es: `Desviación estándar relativa contra el presupuesto de iteraciones, ${geometry}` };
  return (
    <>
      <GeometryChips res={res} value={geometry} onChange={setGeo} id="budget-geometry" />
      <CellControls res={res} prefix="budget" showView={false} />
      <ChipGroup
        id="budget-kind"
        label={{ en: 'Kind of method', es: 'Tipo de método' }}
        options={[
          { id: 'all', label: { en: 'All', es: 'Todos' } },
          { id: 'published', label: KIND_TEXT.published },
          { id: 'proposed', label: KIND_TEXT.proposed },
        ]}
        value={kind}
        onChange={setKind}
      />
      {methods.length === 0 || iters.length < 2 ? (
        <p className="caos-pending" data-state="unavailable">
          {es ? 'Hacen falta al menos dos presupuestos de iteraciones con filas del mismo método para dibujar una curva.' : 'At least two iteration budgets with rows of the same method are needed to draw a curve.'}
        </p>
      ) : (
        <PlotCard
          title={title}
          lane="offline"
          provenance="synthetic"
          note={{
            en: `One curve per method, default parameters, ${device === 'ideal' ? 'ideal' : 'C08'} device. A one-shot method (an iteration count of 1 in the document) is flat by construction. A value below ${fl} is drawn at ${fl}.`,
            es: `Una curva por método, parámetros por defecto, dispositivo ${device === 'ideal' ? 'ideal' : 'C08'}. Un método de un solo paso (un conteo de iteraciones de 1 en el documento) es plano por construcción. Un valor bajo ${fl} se dibuja en ${fl}.`,
          }}
        >
          <UPlotChart
            title={title}
            height={340}
            x={{ label: { en: 'Iteration budget', es: 'Presupuesto de iteraciones' }, values: iters.map((b) => b.value), log: true, ticks: iters.map((b) => ({ value: b.value, label: { en: String(b.value), es: String(b.value) } })) }}
            y={{ label: { en: 'Relative standard deviation', es: 'Desviación estándar relativa' }, unit: { en: '%', es: '%' }, log: true, format: { digits: 3 } }}
            series={methods.map((m) => ({
              id: m,
              label: { en: `${shownId(m)} ${nameOf(m, 'en')}`, es: `${shownId(m)} ${nameOf(m, 'es')}` },
              mode: 'line' as const,
              dots: true,
              values: iters.map((b) => {
                const r = res.rows.find((x) => x.method === m && x.geometry === geometry && x.device === device && x.budget_kind === 'iterations' && x.budget === b.value && x.params === 'default');
                return r ? Math.max(r.rel_std_pct.median, FLOOR) : null;
              }),
            }))}
            solo
          />
        </PlotCard>
      )}
    </>
  );
}

export function DeviceTopic() {
  const { data } = useBench();
  return (
    <DocSection title={{ en: 'Degradation: what the device costs each method', es: 'Degradación: lo que el dispositivo le cuesta a cada método' }} id="robustness-device" area="robustness" refs={['schroff2023']} >
      <P
        en={
          <>
            A hologram that is uniform in the ideal model is not necessarily uniform on a device, and the size of the loss is a property of the method: a method that optimises its phase against the ideal propagation is scored by what quantization to four bits, the crosstalk between neighbouring pixels, the fill factor and the flicker do to it <Cite id="schroff2023" />. The chart puts each method&apos;s result against the ideal device beside its result against the C08 device, from the same seeds and the same budget, and the table gives the ratios. The degradation curve is honest because both sides are rows of the same document and a method that was not run on the device is named and left out, not paired with something else.
          </>
        }
        es={
          <>
            Un holograma uniforme en el modelo ideal no es necesariamente uniforme en un dispositivo, y el tamaño de la pérdida es una propiedad del método: un método que optimiza su fase contra la propagación ideal se evalúa por lo que le hacen la cuantización a cuatro bits, la diafonía entre píxeles vecinos, el factor de llenado y el parpadeo <Cite id="schroff2023" />. El gráfico pone el resultado de cada método contra el dispositivo ideal junto a su resultado contra el dispositivo C08, con las mismas semillas y el mismo presupuesto, y la tabla da los cocientes. La curva de degradación es honesta porque ambos lados son filas del mismo documento y un método que no se corrió sobre el dispositivo se nombra y se deja fuera, no se empareja con otra cosa.
          </>
        }
      />
      <Note ids={['benchmark-results']} />
      <Ready a={data.results}>{(res) => <DeviceBody res={res} />}</Ready>
    </DocSection>
  );
}

export function BudgetTopic() {
  const { data } = useBench();
  return (
    <DocSection title={{ en: 'Convergence: uniformity against the budget', es: 'Convergencia: uniformidad contra el presupuesto' }} id="robustness-budget" area="robustness" noRefsReason={{ en: 'the curves are read from the results document alone', es: 'las curvas se leen solo del documento de resultados' }}>
      <P
        en="A method is judged at a budget, and a method that wins at 10 iterations can lose at 100 or the reverse, so a single budget would hide the ordering that matters when the compute is fixed. The curves show the relative standard deviation of every method at each iteration budget of the protocol, in a log-log chart where a straight line is a power law of convergence; a method that stalls shows as a plateau, and the key lets one curve be soloed against the others without losing the context."
        es="Un método se juzga con un presupuesto, y un método que gana con 10 iteraciones puede perder con 100 o al revés, de modo que un solo presupuesto ocultaría el orden que importa cuando el cómputo es fijo. Las curvas muestran la desviación estándar relativa de cada método en cada presupuesto de iteraciones del protocolo, en un gráfico log-log donde una recta es una ley de potencias de convergencia; un método que se estanca se ve como una meseta, y la clave permite aislar una curva frente a las demás sin perder el contexto."
      />
      <Note ids={['benchmark-results']} />
      <Ready a={data.results}>{(res) => <BudgetBody res={res} />}</Ready>
    </DocSection>
  );
}
