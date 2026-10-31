// The comparison of the published and the proposed methods (area `comparison`): per geometry, the most uniform method of each kind at the cell the
// reader chose, and every proposed-method row against the strongest published row of the same cell (the same device, the same budget, the same
// parameter set), with the factor and the efficiency ratio. All read from the document.
import { BarChart, Cite, DocSection, PlotCard, useShellLang, type BarDatum } from '@fasl-work/caos-app-shell';
import type { BenchmarkResults } from '../../lib/contract.types';
import { P } from '../bi';
import { bestOfKind, bestPublished, budgetText, KIND_ORDER, KIND_TEXT, mostUniform, nameOf, pickRows, shownId, type Lang, type Picked } from './data';
import { CellControls, Note, Ready, TableWrap, KIND_LEGEND, KIND_TONE, useBench, useNum, useResolved } from './shared';

function KindBody({ res }: { res: BenchmarkResults }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const { n, pct } = useNum();
  const { device, view, budget } = useResolved(res);
  if (!budget) return null;
  const byGeometry = res.geometries.map((g) => ({ g, rows: pickRows(res, g.id, device, budget, view) }));
  const cell = (rows: Picked[], kind: (typeof KIND_ORDER)[number], key: string) => {
    const b = bestOfKind(rows, kind);
    return b ? (
      <td key={key} className="caos-col-text" style={{ whiteSpace: 'normal' }}>
        {shownId(b.method)} {b.params === 'tuned' ? (es ? '(ajustado)' : '(tuned)') : ''}
        <span className="caos-plot-note" style={{ display: 'block' }}>
          {pct(b.row.rel_std_pct.median)}, {es ? 'eficiencia' : 'efficiency'} {n(b.row.efficiency.median)}
        </span>
      </td>
    ) : (
      <td key={key} className="caos-col-text">{es ? 'sin filas' : 'no rows'}</td>
    );
  };
  // the proposed rows against the strongest published row of the same cell
  const pairs = byGeometry.flatMap(({ g, rows }) => {
    const base = bestPublished(rows);
    return rows
      .filter((p) => p.kind === 'proposed')
      .map((p) => ({ g, p, base }));
  });
  const bars: BarDatum[] = byGeometry.flatMap(({ g, rows }) =>
    KIND_ORDER.flatMap((kind) => {
      const b = bestOfKind(rows, kind);
      return b ? [{ id: `${g.id}-${kind}`, label: { en: `${g.id} ${KIND_TEXT[kind].en}`, es: `${g.id} ${KIND_TEXT[kind].es}` }, value: b.row.uniformity.median, tone: KIND_TONE[kind], hint: { en: `${shownId(b.method)} ${nameOf(b.method, 'en')}`, es: `${shownId(b.method)} ${nameOf(b.method, 'es')}` } }] : [];
    }),
  );
  const whole = byGeometry.flatMap(({ rows }) => rows);
  const overall = mostUniform(whole);
  return (
    <>
      <CellControls res={res} prefix="published-proposed" />
      <TableWrap>
        <table className="caos-table" data-state="ready" data-table="kind-summary">
          <caption>
            {es
              ? `El método publicado y el método propuesto más uniformes en cada geometría, con ${budgetText(budget).es} sobre el dispositivo ${device === 'ideal' ? 'ideal' : 'C08'}. La regla es la de la pestaña de cada geometría: la menor desviación estándar relativa entre los métodos que conservan al menos la mitad de la mejor eficiencia de su tipo de método. Un método ajustado se rotula como tal.`
              : `The most uniform published method and proposed method on each geometry, at ${budgetText(budget).en} on the ${device === 'ideal' ? 'ideal' : 'C08'} device. The rule is the one of each geometry tab: the lowest relative standard deviation among the methods that keep at least half of the best efficiency of their kind of method. A tuned method is labelled as such.`}
          </caption>
          <thead>
            <tr>
              <th className="caos-col-text">{es ? 'Geometría' : 'Geometry'}</th>
              {KIND_ORDER.map((k) => (
                <th key={k} className="caos-col-text">
                  {k === 'published' ? (es ? 'Mejor método publicado' : 'Best published method') : es ? 'Mejor método propuesto' : 'Best proposed method'}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {byGeometry.map(({ g, rows }) => (
              <tr key={g.id} data-geometry={g.id}>
                <td className="caos-col-text">
                  {g.id} {g.name[lang]}
                </td>
                {KIND_ORDER.map((k) => cell(rows, k, k))}
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
      {bars.length ? (
        <PlotCard title={{ en: 'Uniformity of the best published and proposed method', es: 'Uniformidad del mejor método publicado y propuesto' }} lane="offline" provenance="synthetic">
          <BarChart
            title={{ en: 'Uniformity of the best published and proposed method', es: 'Uniformidad del mejor método publicado y propuesto' }}
            orientation="horizontal"
            axis={{ label: { en: 'Uniformity (median)', es: 'Uniformidad (mediana)' }, format: { digits: 3 }, range: [0, 1] }}
            data={bars}
            legend={KIND_LEGEND}
          />
        </PlotCard>
      ) : null}
      <h3>{es ? 'Cada método propuesto frente al método publicado más fuerte de su celda' : 'Each proposed method against the strongest published method of its cell'}</h3>
      <P
        en="A proposed method's row is set against the most uniform row among all the published methods (M01 to M19) of its own cell, which is the strongest baseline that cell offers by the page's rule. The comparison is like with like: the same geometry, device, budget and parameter set, so a tuned proposed row stands against a tuned baseline and a default one against a default one; where the baseline has no tuned row in the cell, the row says so. The factor is the baseline's relative standard deviation over the challenger's and the efficiency ratio is the challenger's efficiency over the baseline's; a factor above 1 with a ratio near 1 is a gain that did not cost light."
        es="La fila de un método propuesto se contrasta con la fila más uniforme entre todos los métodos publicados (M01 a M19) de su propia celda, que es la línea base más fuerte que esa celda ofrece según la regla de la página. La comparación es de igual con igual: la misma geometría, dispositivo, presupuesto y conjunto de parámetros, de modo que una fila ajustada de un método propuesto se enfrenta a una línea base ajustada y una por defecto a una por defecto; donde la línea base no tiene fila ajustada en la celda, la fila lo dice. El factor es la desviación estándar relativa de la línea base sobre la del retador y la razón de eficiencia es la eficiencia del retador sobre la de la línea base; un factor mayor que 1 con una razón cercana a 1 es una ganancia que no costó luz."
      />
      {pairs.length === 0 ? (
        <p className="caos-pending" data-state="unavailable">
          {es ? 'Ningún método propuesto tiene filas en esta celda.' : 'No proposed method has rows in this cell.'}
        </p>
      ) : (
        <TableWrap>
          <table className="caos-table" data-state="ready" data-table="proposed-vs-published">
            <caption>
              {es
                ? 'Cada método propuesto contra la fila publicada más uniforme de la misma celda. Una celda sin fila publicada no se compara.'
                : 'Each proposed method against the most uniform published row of the same cell. A cell without a published row is not compared.'}
            </caption>
            <thead>
              <tr>
                <th className="caos-col-text">{es ? 'Geometría' : 'Geometry'}</th>
                <th className="caos-col-text">{es ? 'Retador' : 'Challenger'}</th>
                <th className="caos-col-text">{es ? 'Línea base más fuerte' : 'Strongest baseline'}</th>
                <th>{es ? 'Factor de uniformidad' : 'Uniformity factor'}</th>
                <th>{es ? 'Razón de eficiencia' : 'Efficiency ratio'}</th>
              </tr>
            </thead>
            <tbody>
              {pairs.map(({ g, p, base }) => {
                const factor = base && p.row.rel_std_pct.median > 0 ? base.row.rel_std_pct.median / p.row.rel_std_pct.median : null;
                const ratio = base && base.row.efficiency.median > 0 ? p.row.efficiency.median / base.row.efficiency.median : null;
                return (
                  <tr key={`${g.id}-${p.method}`}>
                    <td className="caos-col-text">{g.id}</td>
                    <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                      {shownId(p.method)} {p.params === 'tuned' ? (es ? '(ajustado)' : '(tuned)') : view === 'tuned' ? (es ? '(por defecto)' : '(default)') : ''}
                    </td>
                    <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                      {base ? `${shownId(base.method)} ${base.params === 'tuned' ? (es ? '(ajustado)' : '(tuned)') : view === 'tuned' ? (es ? '(por defecto)' : '(default)') : ''}` : es ? 'sin fila' : 'no row'}
                    </td>
                    <td>{n(factor)}</td>
                    <td>{n(ratio)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </TableWrap>
      )}
      <p className="caos-plot-note" lang={lang}>
        {overall
          ? es
            ? `En todo el documento, en esta celda, el método más uniforme es ${shownId(overall.method)} (${pct(overall.row.rel_std_pct.median)}).`
            : `Across every geometry of this cell the most uniform method is ${shownId(overall.method)} (${pct(overall.row.rel_std_pct.median)}).`
          : ''}
      </p>
    </>
  );
}

export function PublishedProposedTopic() {
  const { data } = useBench();
  return (
    <DocSection title={{ en: 'Published and proposed methods on the same matrix', es: 'Métodos publicados y propuestos sobre la misma matriz' }} id="published-proposed" area="comparison" refs={['kim2019', 'dileonardo2007']}>
      <P
        en={
          <>
            The benchmark puts the 19 published methods and the 5 methods DinHot proposes on the same data. The published methods are the ones every holographic trapping system implements and those the field&apos;s papers describe <Cite id="kim2019" />; the proposed ones are DinHot&apos;s own. What the page asks of the matrix is not which method is faster on one task but where each sits when the geometry, the device and the budget are held equal, and whether a proposed method beats the strongest published method of its cell by a gap that the quartiles of the geometry tabs can be read against.
          </>
        }
        es={
          <>
            El benchmark pone los 19 métodos publicados y los 5 métodos que propone DinHot sobre los mismos datos. Los publicados son los que implementa todo sistema de atrapamiento holográfico y los que describen los artículos del campo <Cite id="kim2019" />; los propuestos son propios de DinHot. Lo que la página le pide a la matriz no es qué método es más rápido en una tarea sino dónde se ubica cada uno cuando la geometría, el dispositivo y el presupuesto son iguales, y si un método propuesto supera al método publicado más fuerte de su celda por una diferencia frente a la cual pueden leerse los cuartiles de las pestañas de geometría.
          </>
        }
      />
      <Note ids={['benchmark-results']} />
      <Ready a={data.results}>{(res) => <KindBody res={res} />}</Ready>
    </DocSection>
  );
}
