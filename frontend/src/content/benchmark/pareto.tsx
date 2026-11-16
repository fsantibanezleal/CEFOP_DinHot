// The efficiency-uniformity plane (area `comparison`): per geometry, every method of the chosen cell as a point of (uniformity, efficiency) beside the
// continuation curve of B5, which the document stores as points, and the hypervolume test of B5 computed from both. The curve is the document's `pareto`
// array; the points are its rows; the dominance and the areas are computed here, in the browser, from those two.
import { Cite, ChipGroup, formatNumber, DocSection, PlotCard, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useState } from 'react';
import type { BenchmarkResults } from '../../lib/contract.types';
import { P } from '../bi';
import { b5Cells, budgetText, frontOf, hypervolume, nonDominated, pickRows, nameOf, isOverBudget, overBudgetText, KIND_ORDER, KIND_TEXT, verdictOf, type Lang } from './data';
import { CellControls, Note, Ready, TableWrap, useBench, useNum, useResolved } from './shared';

function ParetoBody({ res }: { res: BenchmarkResults }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const { n } = useNum();
  const { device, budget } = useResolved(res);
  const withFront = res.geometries.filter((g) => frontOf(res, g.id).length > 0);
  const [geo, setGeo] = useState<string>('');
  const geometry = withFront.find((g) => g.id === geo)?.id ?? withFront[0]?.id ?? res.geometries[0]?.id ?? '';
  if (!budget) return null;
  const cells = b5Cells(res, budget);
  const verdict = verdictOf(cells.map((c) => c.hvFront >= c.hvPublished));
  const rows = pickRows(res, geometry, device, budget, 'default');
  const front = frontOf(res, geometry);
  const pts = [
    ...rows.map((p) => ({ kind: p.kind ?? 'none', u: p.row.uniformity.median, e: p.row.efficiency.median, name: isOverBudget(p.row) ? `${nameOf(p.method, lang)} (${overBudgetText(p.row, lang)})` : nameOf(p.method, lang) })),
    ...front.map((p) => ({ kind: 'front' as const, u: p.u, e: p.e, name: `Efficiency-uniformity continuation, lambda ${formatNumber(p.lambda, lang, { digits: 3 })}` })),
  ];
  const xs = pts.map((p) => p.u);
  const kinds = [...KIND_ORDER, 'none' as const, 'front' as const].filter((k) => pts.some((p) => p.kind === k));
  const series = kinds.map((k) => ({
    id: k,
    label: k === 'front' ? { en: 'Efficiency-uniformity continuation (continuation over lambda)', es: 'Continuación eficiencia-uniformidad (continuación en lambda)' } : k === 'none' ? { en: 'not on the ladder', es: 'fuera de la escalera' } : KIND_TEXT[k],
    mode: 'points' as const,
    size: k === 'front' ? 7 : 10,
    values: pts.map((p) => (p.kind === k ? p.e : null)),
  }));
  const nd = nonDominated(pts.filter((p) => p.kind !== 'front').map((p) => ({ e: p.e, u: p.u }))).length;
  const hvAll = hypervolume(rows.map((p) => ({ e: p.row.efficiency.median, u: p.row.uniformity.median })));
  return (
    <>
      <CellControls res={res} prefix="pareto" showView={false} />
      {withFront.length > 1 ? (
        <ChipGroup
          id="pareto-geometry"
          label={{ en: 'Geometry', es: 'Geometría' }}
          options={withFront.map((g) => ({ id: g.id, label: { en: g.id, es: g.id }, hint: g.name }))}
          value={geometry}
          onChange={setGeo}
        />
      ) : null}
      {front.length === 0 ? (
        <p className="caos-pending" data-state="unavailable">
          {es ? 'El documento no trae una curva de continuación eficiencia-uniformidad para ninguna geometría; la comparación de hipervolumen no puede hacerse.' : 'The document holds no efficiency-uniformity continuation curve for any geometry; the hypervolume comparison cannot be made.'}
        </p>
      ) : null}
      {pts.length > 0 ? (
        <PlotCard
          title={{ en: `Efficiency against uniformity, ${geometry}`, es: `Eficiencia contra uniformidad, ${geometry}` }}
          lane="offline"
          provenance="synthetic"
          note={{
            en: `Methods at ${budgetText(budget).en}, parameters at their paper defaults. The efficiency-uniformity continuation is computed on the ideal device whatever device is chosen. Up and to the right is better on both axes.`,
            es: `Métodos con ${budgetText(budget).es}, con los parámetros por defecto de su artículo. La continuación eficiencia-uniformidad se calcula sobre el dispositivo ideal sea cual sea el elegido. Arriba y a la derecha es mejor en ambos ejes.`,
          }}
        >
          <UPlotChart
            title={{ en: `Efficiency against uniformity, ${geometry}`, es: `Eficiencia contra uniformidad, ${geometry}` }}
            height={340}
            x={{ label: { en: 'Uniformity', es: 'Uniformidad' }, values: xs, format: { digits: 3 } }}
            y={{ label: { en: 'Efficiency', es: 'Eficiencia' }, format: { digits: 3 } }}
            series={series}
            solo
            readout={(i) => {
              const p = pts[i];
              return p ? `${p.name}: ${es ? 'eficiencia' : 'efficiency'} ${formatNumber(p.e, lang, { digits: 3 })}, ${es ? 'uniformidad' : 'uniformity'} ${formatNumber(p.u, lang, { digits: 3 })}` : '';
            }}
          />
        </PlotCard>
      ) : null}
      <p className="caos-plot-note" lang={lang}>
        {es
          ? `En ${geometry}, ${nd} de los ${rows.length} métodos de esta celda no están dominados por otro; el hipervolumen del conjunto de sus puntos es ${n(hvAll)}.`
          : `On ${geometry}, ${nd} of the ${rows.length} methods of this cell are not dominated by another; the hypervolume of the set of their points is ${n(hvAll)}.`}
      </p>
      {cells.length > 0 ? (
        <TableWrap>
          <table className="caos-table" data-state="ready" data-table="bs5">
            <caption>
              {es
                ? `La prueba de continuación eficiencia-uniformidad en cada geometría con curva de continuación, con ${budgetText(budget).es}: el hipervolumen de la continuación eficiencia-uniformidad contra el de la unión de los puntos de Gerchberg-Saxton, aditivo adaptativo generalizado, el método de GS ponderado y búsqueda directa (el criterio de la escalera), y qué puntos de esos cuatro domina algún punto de la continuación.`
                : `The efficiency-uniformity continuation test on each geometry with a continuation curve, at ${budgetText(budget).en}: the hypervolume of the efficiency-uniformity continuation against that of the union of the Gerchberg-Saxton, generalized adaptive additive, the weighted GS method and direct search points (the ladder's criterion), and which of those four points some continuation point dominates.`}
            </caption>
            <thead>
              <tr>
                <th className="caos-col-text">{es ? 'Geometría' : 'Geometry'}</th>
                <th>{es ? 'Puntos de la continuación' : 'Continuation points'}</th>
                <th>{es ? 'HV de la continuación' : 'HV of the continuation'}</th>
                <th>{es ? 'HV de los cuatro puntos publicados' : 'HV of the four published points'}</th>
                <th className="caos-col-text">{es ? 'Puntos dominados' : 'Points dominated'}</th>
                <th className="caos-col-text">{es ? 'Resultado' : 'Result'}</th>
              </tr>
            </thead>
            <tbody>
              {cells.map((c) => (
                <tr key={c.geometry} data-geometry={c.geometry}>
                  <td className="caos-col-text">{c.geometry}</td>
                  <td>{c.nFront}</td>
                  <td>{n(c.hvFront, 4)}</td>
                  <td>{n(c.hvPublished, 4)}</td>
                  <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                    {c.dominated.length ? c.dominated.map((m) => nameOf(m, lang)).join(', ') : es ? 'ninguno' : 'none'}
                    {c.missing.length ? <span className="caos-plot-note" style={{ display: 'block' }}>{es ? 'sin fila: ' : 'no row: '}{c.missing.map((m) => nameOf(m, lang)).join(', ')}</span> : null}
                  </td>
                  <td className="caos-col-text">{c.hvFront >= c.hvPublished ? (es ? 'la continuación es mayor o igual' : 'continuation at least as large') : es ? 'la continuación es menor' : 'continuation smaller'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      ) : null}
      <p className="caos-plot-note" lang={lang} data-verdict={verdict}>
        {verdictLine(verdict, es)}
      </p>
    </>
  );
}

export function verdictLine(v: ReturnType<typeof verdictOf>, es: boolean): string {
  switch (v) {
    case 'supported':
      return es ? 'Veredicto de continuación eficiencia-uniformidad en esta celda: sustentado en todas las geometrías con curva de continuación.' : 'Verdict of efficiency-uniformity continuation in this cell: supported on every geometry with a continuation curve.';
    case 'partly':
      return es ? 'Veredicto de continuación eficiencia-uniformidad en esta celda: sustentado en algunas geometrías y no en otras.' : 'Verdict of efficiency-uniformity continuation in this cell: supported on some geometries and not on others.';
    case 'not-supported':
      return es ? 'Veredicto de continuación eficiencia-uniformidad en esta celda: no sustentado en ninguna geometría con curva de continuación.' : 'Verdict of efficiency-uniformity continuation in this cell: not supported on any geometry with a continuation curve.';
    default:
      return es ? 'Veredicto de continuación eficiencia-uniformidad en esta celda: sin datos (el documento no trae curva de continuación o faltan los métodos del criterio).' : 'Verdict of efficiency-uniformity continuation in this cell: no data (the document holds no continuation curve or lacks the methods of the criterion).';
  }
}

export function ParetoTopic() {
  const { data } = useBench();
  return (
    <DocSection title={{ en: 'Efficiency-uniformity continuation against the single points', es: 'Continuación eficiencia-uniformidad frente a los puntos sueltos' }} id="pareto" area="comparison" refs={['dileonardo2007']}>
      <P
        en={
          <>
            Every method trades efficiency against uniformity, and the published tables give each one a single trade-off point at the weight or mixing parameter its authors chose <Cite id="dileonardo2007" />. Efficiency-uniformity continuation traces the trade-off by a weighted-cost continuation over a trade-off parameter, so the question the chart answers is where the single points of the other methods sit relative to the points of that continuation on the same task. A point below and to the left of a continuation point gives up light or uniformity that the continuation shows can be kept. The continuation points are not a non-dominated set: some of them are dominated by points of other methods, which is why the table below counts the dominated points and the chart shows every method. The gain of the continuation over the union of the published points is small and shrinks at a stricter reference point, because it lies on the efficient side of the trade-off, where the uniformity falls far below one.
 </>
        }
        es={
          <>
            Cada método intercambia eficiencia por uniformidad, y las tablas publicadas dan a cada uno un solo punto de ese intercambio, en el peso o el parámetro de mezcla que eligieron sus autores <Cite id="dileonardo2007" />. Continuación eficiencia-uniformidad traza el intercambio por una continuación de costo ponderado sobre un parámetro de intercambio, de modo que la pregunta que responde el gráfico es dónde quedan los puntos sueltos de los demás métodos respecto de los puntos de esa continuación en la misma tarea. Un punto abajo y a la izquierda de un punto de la continuación cede luz o uniformidad que la continuación muestra que puede conservarse. Los puntos de la continuación no forman un conjunto no dominado: algunos están dominados por puntos de otros métodos, y por eso la tabla de abajo cuenta los puntos dominados y el gráfico muestra todos los métodos. La ganancia de la continuación sobre la unión de los puntos publicados es pequeña y se reduce con un punto de referencia más estricto, porque está en el lado eficiente del compromiso, donde la uniformidad cae muy por debajo de uno.
 </>
        }
      />
      <Note ids={['benchmark-results']} />
      <Ready a={data.results}>{(res) => <ParetoBody res={res} />}</Ready>
    </DocSection>
  );
}

