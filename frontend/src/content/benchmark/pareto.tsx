// The Pareto fronts (area `comparison`): per geometry, every method of the chosen cell as a point of (uniformity, efficiency) beside the
// front of B5, which the document stores as a curve, and the hypervolume test of B5 computed from both. The front is the document's `pareto`
// array; the points are its rows; the dominance and the areas are computed here, in the browser, from those two.
import { Cite, ChipGroup, formatNumber, DocSection, PlotCard, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useState } from 'react';
import type { BenchmarkResults } from '../../lib/contract.types';
import { P } from '../bi';
import { b5Cells, budgetText, frontOf, hypervolume, nonDominated, pickRows, shownId, KIND_ORDER, KIND_TEXT, verdictOf, type Lang } from './data';
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
    ...rows.map((p) => ({ kind: p.kind ?? 'none', u: p.row.uniformity.median, e: p.row.efficiency.median, name: `${shownId(p.method)}` })),
    ...front.map((p) => ({ kind: 'front' as const, u: p.u, e: p.e, name: `B5, lambda ${formatNumber(p.lambda, lang, { digits: 3 })}` })),
  ];
  const xs = pts.map((p) => p.u);
  const kinds = [...KIND_ORDER, 'none' as const, 'front' as const].filter((k) => pts.some((p) => p.kind === k));
  const series = kinds.map((k) => ({
    id: k,
    label: k === 'front' ? { en: 'B5 front (continuation over lambda)', es: 'Frente de B5 (continuación en lambda)' } : k === 'none' ? { en: 'not on the ladder', es: 'fuera de la escalera' } : KIND_TEXT[k],
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
          {es ? 'El documento no trae un frente de B5 para ninguna geometría; la comparación de hipervolumen no puede hacerse.' : 'The document holds no B5 front for any geometry; the hypervolume comparison cannot be made.'}
        </p>
      ) : null}
      {pts.length > 0 ? (
        <PlotCard
          title={{ en: `Efficiency against uniformity, ${geometry}`, es: `Eficiencia contra uniformidad, ${geometry}` }}
          lane="offline"
          provenance="synthetic"
          note={{
            en: `Methods at ${budgetText(budget).en}, parameters at their paper defaults. The front of B5 is computed on the ideal device whatever device is chosen. Up and to the right is better on both axes.`,
            es: `Métodos con ${budgetText(budget).es}, con los parámetros por defecto de su artículo. El frente de B5 se calcula sobre el dispositivo ideal sea cual sea el elegido. Arriba y a la derecha es mejor en ambos ejes.`,
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
                ? `La prueba de B5 en cada geometría con frente, con ${budgetText(budget).es}: el hipervolumen del frente de B5 contra el de la unión de los puntos de M04, M05, M06 y M09 (el criterio de la escalera), y qué puntos de esos cuatro domina algún punto del frente.`
                : `The B5 test on each geometry with a front, at ${budgetText(budget).en}: the hypervolume of the B5 front against that of the union of the M04, M05, M06 and M09 points (the ladder's criterion), and which of those four points some front point dominates.`}
            </caption>
            <thead>
              <tr>
                <th className="caos-col-text">{es ? 'Geometría' : 'Geometry'}</th>
                <th>{es ? 'Puntos del frente' : 'Front points'}</th>
                <th>{es ? 'HV del frente' : 'HV of the front'}</th>
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
                    {c.dominated.length ? c.dominated.join(', ') : es ? 'ninguno' : 'none'}
                    {c.missing.length ? <span className="caos-plot-note" style={{ display: 'block' }}>{es ? 'sin fila: ' : 'no row: '}{c.missing.join(', ')}</span> : null}
                  </td>
                  <td className="caos-col-text">{c.hvFront >= c.hvPublished ? (es ? 'el frente es mayor o igual' : 'front at least as large') : es ? 'el frente es menor' : 'front smaller'}</td>
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
      return es ? 'Veredicto de B5 en esta celda: sustentado en todas las geometrías con frente.' : 'Verdict of B5 in this cell: supported on every geometry with a front.';
    case 'partly':
      return es ? 'Veredicto de B5 en esta celda: sustentado en algunas geometrías y no en otras.' : 'Verdict of B5 in this cell: supported on some geometries and not on others.';
    case 'not-supported':
      return es ? 'Veredicto de B5 en esta celda: no sustentado en ninguna geometría con frente.' : 'Verdict of B5 in this cell: not supported on any geometry with a front.';
    default:
      return es ? 'Veredicto de B5 en esta celda: sin datos (el documento no trae frente o faltan los métodos del criterio).' : 'Verdict of B5 in this cell: no data (the document holds no front or lacks the methods of the criterion).';
  }
}

export function ParetoTopic() {
  const { data } = useBench();
  return (
    <DocSection title={{ en: 'Pareto fronts: B5 against the single points', es: 'Frentes de Pareto: B5 frente a los puntos sueltos' }} id="pareto" area="comparison" refs={['dileonardo2007']}>
      <P
        en={
          <>
            Every method trades efficiency against uniformity, and the published tables give each one a single trade-off point at the weight or mixing parameter its authors chose <Cite id="dileonardo2007" />. B5 (engine id B5) computes the whole front by a continuation over a trade-off parameter, so the question the chart answers is where the single points of the other methods sit relative to the best trade-off attainable on the same task. A point under the front is a method that gives up light or uniformity that the front shows can be kept; a point on it is a trade-off that the front cannot improve on.
          </>
        }
        es={
          <>
            Cada método intercambia eficiencia por uniformidad, y las tablas publicadas dan a cada uno un solo punto de ese intercambio, en el peso o el parámetro de mezcla que eligieron sus autores <Cite id="dileonardo2007" />. B5 (identificador de motor B5) calcula el frente completo por continuación sobre un parámetro de intercambio, de modo que la pregunta que responde el gráfico es dónde quedan los puntos sueltos de los demás métodos respecto del mejor intercambio alcanzable en la misma tarea. Un punto bajo el frente es un método que cede luz o uniformidad que el frente muestra que puede conservarse; un punto sobre él es un intercambio que el frente no puede mejorar.
          </>
        }
      />
      <Note ids={['benchmark-results']} />
      <Ready a={data.results}>{(res) => <ParetoBody res={res} />}</Ready>
    </DocSection>
  );
}

