// One tab per geometry (area `results`): what every method scored on it at the cell the reader chose (device, parameter set, budget): the
// table with the median and the inter-quartile range of each metric, the cells the document lists as not run with their reasons, and the
// charts of efficiency, uniformity, relative standard deviation and time, coloured by kind. Everything is read from the benchmark document.
import { BarChart, Cite, formatNumber, DocSection, PlotCard, ViewsRow, useFormat, useShellLang, type BarDatum } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import type { BenchmarkResults } from '../../lib/contract.types';
import { P } from '../bi';
import type { Kind } from '../methodology/ladder';
import {
  bestOfKind,
  kindOf,
  budgetText,
  geometryOf,
  methodsIn,
  nameOf,
  shownId,
  skippedIn,
  KIND_ORDER,
  KIND_TEXT,
  type Lang,
  type Picked,
  pickRows,
  type Stat,
} from './data';
import { barLabel, CellControls, Note, Ready, TableWrap, KIND_LEGEND, KIND_TONE, useBench, useNum, useResolved, WRAP } from './shared';

/** The geometry tab -> the references of the published task it mirrors (the benchmark protocol's own sources). */
const GEOMETRY_REFS: Record<string, string> = { G1: 'dileonardo2007', G4: 'polin2005', G5: 'whyte2005', G6: 'kim2019', G7: 'pasienski2008' };

/** A relative standard deviation that is exactly 0 cannot sit on a log axis: it is drawn at this floor and the chart says so. */
const SIGMA_FLOOR = 1e-3;

/** A cell's median with its quartiles, as the table shows them. */
function StatCell({ s, digits = 3 }: { s: Stat; digits?: number }) {
  const { n } = useNum();
  return (
    <td>
      {n(s.median, digits)}
      <span className="caos-plot-note" style={{ display: 'block', whiteSpace: 'nowrap' }}>
        [{n(s.q1, digits)}, {n(s.q3, digits)}]
      </span>
    </td>
  );
}

function ParamsTag({ p, view }: { p: Picked; view: string }) {
  const es = useShellLang() === 'es';
  if (p.params === 'tuned') return <>{es ? 'ajustado (rejilla común)' : 'tuned (shared grid)'}</>;
  if (view === 'tuned') return <>{p.noTunedRow ? (es ? 'por defecto (sin fila ajustada en esta celda)' : 'default (no tuned row in this cell)') : es ? 'por defecto' : 'default'}</>;
  return <>{es ? 'por defecto (artículo)' : 'default (paper)'}</>;
}

export function MethodsTable({ res, geometry }: { res: BenchmarkResults; geometry: string }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const { device, view, budget } = useResolved(res);
  if (!budget) return null;
  const rows = pickRows(res, geometry, device, budget, view);
  const skipped = skippedIn(res, geometry);
  const g = geometryOf(res, geometry);
  return (
    <TableWrap>
      <table className="caos-table" data-state="ready" data-geometry={geometry}>
        <caption>
          {es
            ? `${geometry}, ${g?.name.es ?? ''}: cada método en ${budgetText(budget).es}, ${device === 'ideal' ? 'contra el dispositivo ideal' : 'contra el dispositivo C08'}. Mediana sobre las semillas y, debajo, el cuartil 1 y el 3. Eficiencia y uniformidad entre 0 y 1 (mayor es mejor); desviación estándar relativa en porcentaje (menor es mejor); el tiempo es de reloj de la máquina que corrió el benchmark.`
            : `${geometry}, ${g?.name.en ?? ''}: every method at ${budgetText(budget).en}, ${device === 'ideal' ? 'scored against the ideal device' : 'scored against the C08 device'}. Median over the seeds and, below it, quartiles 1 and 3. Efficiency and uniformity between 0 and 1 (higher is better); relative standard deviation in percent (lower is better); the time is wall-clock of the machine that ran the benchmark.`}
        </caption>
        <thead>
          <tr>
            <th className="caos-col-text">{es ? 'Tipo' : 'Kind'}</th>
            <th className="caos-col-text">{es ? 'Método' : 'Method'}</th>
            <th className="caos-col-text">{es ? 'Parámetros' : 'Parameters'}</th>
            <th>{es ? 'Eficiencia' : 'Efficiency'}</th>
            <th>{es ? 'Uniformidad' : 'Uniformity'}</th>
            <th>{es ? 'Desv. est. relativa (%)' : 'Rel. std (%)'}</th>
            <th>{es ? 'Tiempo (s)' : 'Time (s)'}</th>
            <th>{es ? 'Iteraciones' : 'Iterations'}</th>
            <th>{es ? 'Semillas' : 'Seeds'}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={`${p.method}-${p.params}`} data-method={p.method} data-tier={p.kind ?? 'none'} data-params={p.params}>
              <td className="caos-col-text">{p.kind ? KIND_TEXT[p.kind][lang] : '-'}</td>
              <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                {shownId(p.method)} {nameOf(p.method, lang)}
              </td>
              <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                <ParamsTag p={p} view={view} />
              </td>
              <StatCell s={p.row.efficiency} />
              <StatCell s={p.row.uniformity} />
              <StatCell s={p.row.rel_std_pct} />
              <StatCell s={p.row.time_s} />
              <StatCell s={p.row.iterations} digits={4} />
              <td>{p.row.n_seeds}</td>
            </tr>
          ))}
          {skipped.map((s) => (
            <tr key={`skip-${s.method}`} data-method={s.method} data-skipped="true">
              <td className="caos-col-text">{kindShort(s.method, lang)}</td>
              <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                {shownId(s.method)} {nameOf(s.method, lang)}
              </td>
              <td className="caos-col-text">{es ? 'no corrida' : 'not run'}</td>
              <td colSpan={6} className="caos-col-text" style={{ ...WRAP, whiteSpace: 'normal' }}>
                {s.reason[lang]}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}

const kindShort = (method: string, lang: Lang) => {
  const t = kindOf(method);
  return t ? KIND_TEXT[t][lang] : '-';
};

/** The bars of one metric, one per method, coloured by kind. */
function MetricBars({ rows, pick, title, axis, view }: { rows: Picked[]; pick: (p: Picked) => number; title: { en: string; es: string }; axis: { en: string; es: string }; view: string }) {
  const data: BarDatum[] = rows.map((p) => ({
    id: `${p.method}-${p.params}`,
    label: barLabel(p, p.method, view as 'default' | 'tuned'),
    value: pick(p),
    tone: KIND_TONE[p.kind ?? 'none'],
    hint: { en: `${shownId(p.method)} ${nameOf(p.method, 'en')}`, es: `${shownId(p.method)} ${nameOf(p.method, 'es')}` },
  }));
  return (
    <PlotCard title={title} lane="offline" provenance="synthetic">
      <BarChart title={title} orientation="horizontal" axis={{ label: axis, format: { digits: 3 }, range: [0, 1] }} data={data} legend={KIND_LEGEND} />
    </PlotCard>
  );
}

/** Points on a log axis, one series per kind, the methods as named ticks: relative standard deviation and time span decades. */
function LogPoints({ rows, pick, title, axis, unit, floor, view }: { rows: Picked[]; pick: (p: Picked) => number; title: { en: string; es: string }; axis: { en: string; es: string }; unit?: { en: string; es: string }; floor?: number; view: string }) {
  const lang = useShellLang() as Lang;
  const fl = useFormat()(floor, { digits: 3 });
  if (!rows.length) return null;
  const xs = rows.map((_, i) => i + 1);
  const val = (p: Picked) => Math.max(pick(p), floor ?? Number.MIN_VALUE);
  const tiers: (Kind | 'none')[] = [...KIND_ORDER, 'none'];
  const series = tiers
    .filter((t) => rows.some((p) => (p.kind ?? 'none') === t))
    .map((t) => ({
      id: t,
      label: t === 'none' ? { en: 'not on the ladder', es: 'fuera de la escalera' } : KIND_TEXT[t],
      mode: 'points' as const,
      size: 9,
      values: rows.map((p) => ((p.kind ?? 'none') === t ? val(p) : null)),
    }));
  const clamped = floor !== undefined && rows.some((p) => pick(p) < floor);
  return (
    <PlotCard
      title={title}
      lane="offline"
      provenance="synthetic"
      note={clamped ? { en: `A value below ${fl} is drawn at ${fl}: a log axis has no zero.`, es: `Un valor bajo ${fl} se dibuja en ${fl}: un eje logarítmico no tiene cero.` } : undefined}
    >
      <UPlotChart
        title={title}
        height={300}
        x={{ label: { en: 'Method', es: 'Método' }, values: xs, range: [0.5, rows.length + 0.5], ticks: rows.map((p, i) => ({ value: i + 1, label: barLabel(p, p.method, view as 'default' | 'tuned') })) }}
        y={{ label: axis, unit, log: true, format: { digits: 3 } }}
        series={series}
        solo
        readout={(i) => {
          const p = rows[i];
          if (!p) return '';
          return `${shownId(p.method)} ${nameOf(p.method, lang)}: ${formatNumber(pick(p), lang, { digits: 3 })}`;
        }}
      />
    </PlotCard>
  );
}

function Reading({ res, geometry }: { res: BenchmarkResults; geometry: string }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const { n, pct } = useNum();
  const { device, view, budget } = useResolved(res);
  if (!budget) return null;
  const rows = pickRows(res, geometry, device, budget, view);
  const parts = KIND_ORDER.map((kind) => {
    const b = bestOfKind(rows, kind);
    const nm = KIND_TEXT[kind][lang];
    const nmEs = kind === 'published' ? 'los métodos publicados' : 'los métodos propuestos';
    if (!b) return es ? `entre ${nmEs} no corrió ninguno en esta celda` : `no ${nm} method ran in this cell`;
    return es
      ? `entre ${nmEs} el más uniforme es ${shownId(b.method)} (${pct(b.row.rel_std_pct.median)}, con eficiencia ${n(b.row.efficiency.median)})`
      : `among the ${nm} methods the most uniform is ${shownId(b.method)} (${pct(b.row.rel_std_pct.median)}, at efficiency ${n(b.row.efficiency.median)})`;
  });
  return (
    <P
      en={`At ${budgetText(budget).en} on the ${device === 'ideal' ? 'ideal' : 'C08'} device, with ${view === 'default' ? 'every method at the default parameters of its paper' : 'the tuned rows where a method has one and its labelled default row where it has not'}, ${parts.join('; ')}. A method counts as the most uniform only if it keeps at least half of the best efficiency of its kind of method in the cell, so that a hologram that is uniform because it wastes the light does not take the place. The ranking is the one cell chosen above; the other budgets and the other device are one control away, and the whole matrix is in the table.`}
      es={`Con ${budgetText(budget).es} sobre el dispositivo ${device === 'ideal' ? 'ideal' : 'C08'}, con ${view === 'default' ? 'cada método en los parámetros por defecto de su artículo' : 'las filas ajustadas donde un método las tiene y su fila por defecto rotulada donde no'}, ${parts.join('; ')}. Un método cuenta como el más uniforme solo si conserva al menos la mitad de la mejor eficiencia de su tipo de método en la celda, de modo que un holograma uniforme porque desperdicia la luz no ocupa el lugar. La clasificación es la de la celda elegida arriba; los otros presupuestos y el otro dispositivo están a un control de distancia, y toda la matriz está en la tabla.`}
    />
  );
}

function GeometryBody({ res, geometry }: { res: BenchmarkResults; geometry: string }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const { device, view, budget } = useResolved(res);
  const g = geometryOf(res, geometry);
  const ran = new Set(res.rows.filter((r) => r.geometry === geometry).map((r) => r.method));
  const skipped = skippedIn(res, geometry);
  const all = methodsIn(res);
  // a group runs its seeds until the protocol's wall-clock bound (at least 2), so a cell holds between 2 and the protocol's seeds
  const seeds = res.rows.filter((r) => r.geometry === geometry).map((r) => r.n_seeds);
  const lo = seeds.length ? Math.min(...seeds) : res.protocol.seeds;
  const hi = seeds.length ? Math.max(...seeds) : res.protocol.seeds;
  const seedText = lo === hi ? { en: `${hi} seeds per cell`, es: `${hi} semillas por celda` }
    : { en: `${lo} to ${hi} seeds per cell (the protocol runs up to ${res.protocol.seeds}, within the wall-clock bound of a group)`,
        es: `${lo} a ${hi} semillas por celda (el protocolo corre hasta ${res.protocol.seeds}, dentro del límite de tiempo de un grupo)` };
  if (!g) {
    return (
      <p className="caos-pending" data-state="unavailable">
        {es ? `El documento no declara la geometría ${geometry}.` : `The document does not declare the geometry ${geometry}.`}
      </p>
    );
  }
  const rows = budget ? pickRows(res, geometry, device, budget, view) : [];
  return (
    <>
      <P
        en={`${g.id} is "${g.name.en}": ${g.n_traps} traps in ${g.dims} dimensions, run at the grids ${res.protocol.grids.join(', ')} with ${seedText.en}. ${ran.size} of the ${all.length} methods of the ladder have rows on it and ${skipped.length} are listed as not run, each with the reason its own specification gives (a target kind it does not accept, a dimension it does not cover, a device it cannot model).${g.n_traps === 0 ? ' A trap count of 0 marks a geometry that is a field and not a set of traps; its methods are the full-field ones.' : ''}`}
        es={`${g.id} es "${g.name.es}": ${g.n_traps} trampas en ${g.dims} dimensiones, corrida en las grillas ${res.protocol.grids.join(', ')} con ${seedText.es}. ${ran.size} de los ${all.length} métodos de la escalera tienen filas en ella y ${skipped.length} figuran como no corridos, cada uno con la razón que da su propia especificación (un tipo de objetivo que no acepta, una dimensión que no cubre, un dispositivo que no puede modelar).${g.n_traps === 0 ? ' Un número de trampas igual a 0 marca una geometría que es un campo y no un conjunto de trampas; sus métodos son los de campo completo.' : ''}`}
      />
      {GEOMETRY_REFS[geometry] ? (
        <P
          en={<>The task is set against the published one that the benchmark protocol names for it <Cite id={GEOMETRY_REFS[geometry]} />; the published values are not reproduced, because they were measured on other grids and budgets.</>}
          es={<>La tarea se contrasta con la publicada que el protocolo del benchmark nombra para ella <Cite id={GEOMETRY_REFS[geometry]} />; los valores publicados no se reproducen, porque se midieron en otras grillas y presupuestos.</>}
        />
      ) : null}
      <CellControls res={res} prefix={`g-${geometry}`} />
      <Reading res={res} geometry={geometry} />
      {rows.length === 0 ? (
        <p className="caos-pending" data-state="unavailable">
          {es ? 'Ningún método tiene filas en esta celda del documento; elija otro presupuesto o dispositivo.' : 'No method has rows in this cell of the document; choose another budget or device.'}
        </p>
      ) : null}
      <MethodsTable res={res} geometry={geometry} />
      {rows.length > 0 ? (
        <>
          <ViewsRow>
            <MetricBars rows={rows} pick={(p) => p.row.efficiency.median} title={{ en: `Efficiency by method, ${geometry}`, es: `Eficiencia por método, ${geometry}` }} axis={{ en: 'Efficiency (median)', es: 'Eficiencia (mediana)' }} view={view} />
            <MetricBars rows={rows} pick={(p) => p.row.uniformity.median} title={{ en: `Uniformity by method, ${geometry}`, es: `Uniformidad por método, ${geometry}` }} axis={{ en: 'Uniformity (median)', es: 'Uniformidad (mediana)' }} view={view} />
          </ViewsRow>
          <ViewsRow>
            <LogPoints rows={rows} pick={(p) => p.row.rel_std_pct.median} title={{ en: `Relative standard deviation by method, ${geometry}`, es: `Desviación estándar relativa por método, ${geometry}` }} axis={{ en: 'Relative standard deviation', es: 'Desviación estándar relativa' }} unit={{ en: '%', es: '%' }} floor={SIGMA_FLOOR} view={view} />
            <LogPoints rows={rows} pick={(p) => p.row.time_s.median} title={{ en: `Time by method, ${geometry}`, es: `Tiempo por método, ${geometry}` }} axis={{ en: 'Time (median)', es: 'Tiempo (mediana)' }} unit={{ en: 's', es: 's' }} view={view} />
          </ViewsRow>
        </>
      ) : null}
    </>
  );
}

/** The topic of one geometry. */
export function GeometryTopic({ id }: { id: string }) {
  const { data } = useBench();
  const es = useShellLang() === 'es';
  return (
    <DocSection
      title={{ en: `Geometry ${id}`, es: `Geometría ${id}` }}
      id={`geometry-${id}`}
      area="results"
      refs={GEOMETRY_REFS[id] ? [GEOMETRY_REFS[id]] : undefined}
      noRefsReason={GEOMETRY_REFS[id] ? undefined : { en: 'this geometry is defined by the protocol; no published task is set against it', es: 'esta geometría la define el protocolo; no hay una tarea publicada con la que se contraste' }}
    >
      <Note ids={['benchmark-results']} />
      <Ready a={data.results}>{(res) => <GeometryBody res={res} geometry={id} />}</Ready>
      <p className="caos-plot-note" lang={es ? 'es' : 'en'}>
        {es ? 'Los números de esta pestaña se leen del documento de resultados al cargar la página.' : 'The numbers on this tab are read from the results document when the page loads.'}
      </p>
    </DocSection>
  );
}
