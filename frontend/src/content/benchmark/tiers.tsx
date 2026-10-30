// The comparison of the three tiers (area `comparison`): per geometry, the most uniform method of each tier at the cell the reader chose,
// and every beyond-the-state-of-the-art row against the strongest state-of-the-art row of the same cell (the same device, the same budget,
// the same parameter set), with the factor and the efficiency ratio and whether the pair passes the tier's own test. All read from the document.
import { BarChart, Cite, DocSection, PlotCard, useShellLang, type BarDatum } from '@fasl-work/caos-app-shell';
import type { BenchmarkResults } from '../../lib/contract.types';
import { P } from '../bi';
import { bestOfTier, budgetText, mostUniform, nameOf, pickRows, shownId, TIER_NAME, TIER_ORDER, type Lang, type Picked } from './data';
import { CellControls, Note, Ready, TableWrap, TIER_LEGEND, TIER_TONE, useBench, useNum, useResolved } from './shared';

function TierBody({ res }: { res: BenchmarkResults }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const { n, pct } = useNum();
  const { device, view, budget } = useResolved(res);
  if (!budget) return null;
  const byGeometry = res.geometries.map((g) => ({ g, rows: pickRows(res, g.id, device, budget, view) }));
  const cell = (rows: Picked[], tier: (typeof TIER_ORDER)[number], key: string) => {
    const b = bestOfTier(rows, tier);
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
  // the beyond rows against the strongest state-of-the-art row of the same cell
  const pairs = byGeometry.flatMap(({ g, rows }) => {
    const sota = bestOfTier(rows, 'sota');
    return rows
      .filter((p) => p.tier === 'beyond')
      .map((p) => ({ g, p, sota }));
  });
  const bars: BarDatum[] = byGeometry.flatMap(({ g, rows }) =>
    TIER_ORDER.flatMap((tier) => {
      const b = bestOfTier(rows, tier);
      return b ? [{ id: `${g.id}-${tier}`, label: { en: `${g.id} ${TIER_NAME[tier].en}`, es: `${g.id} ${TIER_NAME[tier].es}` }, value: b.row.uniformity.median, tone: TIER_TONE[tier], hint: { en: `${shownId(b.method)} ${nameOf(b.method, 'en')}`, es: `${shownId(b.method)} ${nameOf(b.method, 'es')}` } }] : [];
    }),
  );
  const whole = byGeometry.flatMap(({ rows }) => rows);
  const overall = mostUniform(whole);
  return (
    <>
      <CellControls res={res} prefix="tiers" />
      <TableWrap>
        <table className="caos-table" data-state="ready" data-table="tier-summary">
          <caption>
            {es
              ? `El método más uniforme de cada nivel en cada geometría, con ${budgetText(budget).es} sobre el dispositivo ${device === 'ideal' ? 'ideal' : 'C08'}. La regla es la de la pestaña de cada geometría: la menor desviación estándar relativa entre los métodos que conservan al menos la mitad de la mejor eficiencia de su nivel. Un método ajustado se rotula como tal.`
              : `The most uniform method of each tier on each geometry, at ${budgetText(budget).en} on the ${device === 'ideal' ? 'ideal' : 'C08'} device. The rule is the one of each geometry tab: the lowest relative standard deviation among the methods that keep at least half of the best efficiency of their tier. A tuned method is labelled as such.`}
          </caption>
          <thead>
            <tr>
              <th className="caos-col-text">{es ? 'Geometría' : 'Geometry'}</th>
              {TIER_ORDER.map((t) => (
                <th key={t} className="caos-col-text">
                  {TIER_NAME[t][lang]}
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
                {TIER_ORDER.map((t) => cell(rows, t, t))}
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
      {bars.length ? (
        <PlotCard title={{ en: 'Uniformity of the best method of each tier', es: 'Uniformidad del mejor método de cada nivel' }} lane="offline" provenance="synthetic">
          <BarChart
            title={{ en: 'Uniformity of the best method of each tier', es: 'Uniformidad del mejor método de cada nivel' }}
            orientation="horizontal"
            axis={{ label: { en: 'Uniformity (median)', es: 'Uniformidad (mediana)' }, format: { digits: 3 }, range: [0, 1] }}
            data={bars}
            legend={TIER_LEGEND}
          />
        </PlotCard>
      ) : null}
      <h3>{es ? 'Cada método más allá del estado del arte frente al más fuerte del estado del arte' : 'Each beyond method against the strongest state-of-the-art method'}</h3>
      <P
        en="A beyond row is set against the most uniform state-of-the-art row of its own cell, which is the strongest baseline that cell offers by the page's rule. The comparison is like with like: the same geometry, device, budget and parameter set, so a tuned beyond row stands against a tuned baseline and a default one against a default one; where the baseline has no tuned row in the cell, the row says so. The factor is the baseline's relative standard deviation over the challenger's and the efficiency ratio is the challenger's efficiency over the baseline's; a factor above 1 with a ratio near 1 is a gain that did not cost light."
        es="Una fila de más allá se contrasta con la fila de estado del arte más uniforme de su propia celda, que es la línea base más fuerte que esa celda ofrece según la regla de la página. La comparación es de igual con igual: la misma geometría, dispositivo, presupuesto y conjunto de parámetros, de modo que una fila ajustada de más allá se enfrenta a una línea base ajustada y una por defecto a una por defecto; donde la línea base no tiene fila ajustada en la celda, la fila lo dice. El factor es la desviación estándar relativa de la línea base sobre la del retador y la razón de eficiencia es la eficiencia del retador sobre la de la línea base; un factor mayor que 1 con una razón cercana a 1 es una ganancia que no costó luz."
      />
      {pairs.length === 0 ? (
        <p className="caos-pending" data-state="unavailable">
          {es ? 'Ningún método del nivel más allá tiene filas en esta celda.' : 'No beyond-tier method has rows in this cell.'}
        </p>
      ) : (
        <TableWrap>
          <table className="caos-table" data-state="ready" data-table="beyond-vs-sota">
            <caption>
              {es
                ? 'Los métodos más allá del estado del arte contra la fila más uniforme del estado del arte de la misma celda. Una celda sin esa fila del estado del arte no se compara.'
                : 'The beyond-the-state-of-the-art methods against the most uniform state-of-the-art row of the same cell. A cell without such a state-of-the-art row is not compared.'}
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
              {pairs.map(({ g, p, sota }) => {
                const factor = sota && p.row.rel_std_pct.median > 0 ? sota.row.rel_std_pct.median / p.row.rel_std_pct.median : null;
                const ratio = sota && sota.row.efficiency.median > 0 ? p.row.efficiency.median / sota.row.efficiency.median : null;
                return (
                  <tr key={`${g.id}-${p.method}`}>
                    <td className="caos-col-text">{g.id}</td>
                    <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                      {shownId(p.method)} {p.params === 'tuned' ? (es ? '(ajustado)' : '(tuned)') : view === 'tuned' ? (es ? '(por defecto)' : '(default)') : ''}
                    </td>
                    <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                      {sota ? `${shownId(sota.method)} ${sota.params === 'tuned' ? (es ? '(ajustado)' : '(tuned)') : view === 'tuned' ? (es ? '(por defecto)' : '(default)') : ''}` : es ? 'sin fila' : 'no row'}
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

export function TiersTopic() {
  const { data } = useBench();
  return (
    <DocSection title={{ en: 'The three tiers on the same matrix', es: 'Los tres niveles sobre la misma matriz' }} id="tiers" area="comparison" refs={['kim2019', 'dileonardo2007']}>
      <P
        en={
          <>
            The ladder has three tiers and the benchmark puts them on the same data: the classical methods that every holographic trapping system implements, the state of the art of the field as its papers describe it <Cite id="kim2019" />, and DinHot&apos;s own proposals beyond it. What the page asks of the matrix is not which tier is faster on one task but where each tier sits when the geometry, the device and the budget are held equal, and whether a method of the beyond tier beats the strongest method of the tier below it by a gap that the quartiles of the geometry tabs can be read against.
          </>
        }
        es={
          <>
            La escalera tiene tres niveles y el benchmark los pone sobre los mismos datos: los métodos clásicos que todo sistema de atrapamiento holográfico implementa, el estado del arte del campo tal como lo describen sus artículos <Cite id="kim2019" />, y las propuestas propias de DinHot más allá de él. Lo que la página le pide a la matriz no es qué nivel es más rápido en una tarea sino dónde se ubica cada nivel cuando la geometría, el dispositivo y el presupuesto son iguales, y si un método del nivel más allá supera al método más fuerte del nivel inferior por una diferencia frente a la cual pueden leerse los cuartiles de las pestañas de geometría.
          </>
        }
      />
      <Note ids={['benchmark-results']} />
      <Ready a={data.results}>{(res) => <TierBody res={res} />}</Ready>
    </DocSection>
  );
}
