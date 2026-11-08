// Group 4, Convergence: the method at work, coupled to the focal plane (V5), did the algorithm converge and what it traded (V4), the
// efficiency-uniformity front of the benchmark (B5) and the camera feedback loop that removes the non-uniformity the optics leave (V9).
import { ChipGroup, PlotCard, SubTabs, ViewsRow } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo, useState } from 'react';
import { loadBenchmark, useArtifact } from '../api/artifacts';
import { budgetId, budgetsOf, budgetText, frontOf, nameOf, parseBudget, pickRows, type Device } from '../content/benchmark/data';
import type { ChartSeries } from '@fasl-work/caos-app-shell/chart';
import { ReadinessNote } from '../readiness/ReadinessNote';
import { cardOf } from './HologramGroup';
import { MethodAtWorkView } from './MethodAtWork';
import { historyAt, is3D, methodLabel, methodName, useSelection, type Selection } from './model';
import { cellWithRows, intervalDots, openingCell, recommend, recommendationText, SERIES_COLORS, type Cell } from './pareto';
import { Fill, LOADING, Pending, Unavailable, useActions, useFmt, useStateKey, useT } from './ui';
import { useNav } from './nav';

export function ConvergenceGroup() {
  const { t } = useT();
  const sel = useSelection();
  const nav = useNav();
  return (
    <SubTabs
      ariaLabel={t('Convergence views', 'Vistas de convergencia')}
      value={nav?.tabs.convergence}
      onChange={nav ? (id) => nav.setTab('convergence', id) : undefined}
      tabs={[
        { id: 'method', label: t('Method at work', 'Método trabajando'), content: sel ? <MethodAtWorkView sel={sel} /> : <Pending label={LOADING} /> },
        { id: 'metrics', label: t('Metrics by iteration', 'Métricas por iteración'), content: sel ? <MetricsView sel={sel} /> : <Pending label={LOADING} /> },
        { id: 'pareto', label: t('Pareto front', 'Frente de Pareto'), content: sel ? <ParetoView sel={sel} /> : <Pending label={LOADING} /> },
        { id: 'camera', label: t('Camera feedback', 'Realimentación de cámara'), content: sel ? <CameraView sel={sel} /> : <Pending label={LOADING} /> },
      ]}
    />
  );
}

export function MetricsView({ sel }: { sel: Selection }) {
  const { t } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const act = useActions();
  const c = cardOf(sel);
  const r = sel.result;
  const verdict = sel.data.manifest.methods[sel.methodId];
  if (!r || !r.history.length) {
    return (
      <PlotCard fill title={{ en: 'Metrics by iteration', es: 'Métricas por iteración' }} {...c} dataKey={stateKey}>
        <Fill>
          <Unavailable reason={{ en: `The bake holds no iteration history for ${methodName(sel.methodId).en} on this case, and the live engine is not on this build.`, es: `La generación no guarda historial de iteraciones de ${methodName(sel.methodId).es} en este caso y el motor en vivo no está en esta versión.` }} />
        </Fill>
      </PlotCard>
    );
  }
  const h = r.history;
  const at = historyAt(h, sel.iteration);
  const last = h[h.length - 1];
  return (
    <PlotCard
      fill
      title={{ en: `${methodLabel(sel.methodId).en}: metrics by iteration`, es: `${methodLabel(sel.methodId).es}: métricas por iteración` }}
      {...c}
      lane={r.lane}
      dataKey={stateKey}
      note={{
        en: `At iteration ${at?.iteration}: efficiency ${fmt(at?.efficiency, { decimals: 3 })}, uniformity ${fmt(at?.uniformity, { decimals: 3 })}, relative spread ${fmt(at?.relStdPct, { decimals: 2 })} %. ${verdict ? (verdict.converged ? 'The run converged.' : 'The run stopped at its budget without converging.') : ''} Click the chart or move the rail knob to choose the iteration.`,
        es: `En la iteración ${at?.iteration}: eficiencia ${fmt(at?.efficiency, { decimals: 3 })}, uniformidad ${fmt(at?.uniformity, { decimals: 3 })}, dispersión relativa ${fmt(at?.relStdPct, { decimals: 2 })} %. ${verdict ? (verdict.converged ? 'La corrida convergió.' : 'La corrida terminó en su presupuesto sin converger.') : ''} Pulse el gráfico o mueva la perilla del panel para elegir la iteración.`,
      }}
    >
      <Fill>
        <UPlotChart
          height="fill"
          title={{ en: 'Efficiency, uniformity and relative spread by iteration', es: 'Eficiencia, uniformidad y dispersión relativa por iteración' }}
          x={{ values: h.map((p) => p.iteration), label: { en: 'Iteration', es: 'Iteración' }, format: { decimals: 0, grouping: false } }}
          y={{ label: { en: 'Fraction', es: 'Fracción' }, format: { decimals: 3 } }}
          series={[
            { label: { en: 'Efficiency', es: 'Eficiencia' }, values: h.map((p) => p.efficiency), color: '--color-accent' },
            { label: { en: 'Uniformity', es: 'Uniformidad' }, values: h.map((p) => p.uniformity), color: '--color-good' },
            { label: { en: 'Relative spread (fraction)', es: 'Dispersión relativa (fracción)' }, values: h.map((p) => p.relStdPct / 100), color: '--color-warn', dash: [5, 4] },
          ]}
          marks={[
            { x: at?.iteration ?? last.iteration, label: { en: 'selected', es: 'elegida' } },
            ...(verdict?.converged ? [{ x: last.iteration, label: { en: 'converged', es: 'convergió' } }] : []),
          ]}
          onPick={(k) => act.setIteration(h[k].iteration)}
          readout={(k) => t(`iteration ${h[k].iteration}: efficiency ${fmt(h[k].efficiency, { decimals: 3 })}, uniformity ${fmt(h[k].uniformity, { decimals: 3 })}, spread ${fmt(h[k].relStdPct, { decimals: 2 })} %`, `iteración ${h[k].iteration}: eficiencia ${fmt(h[k].efficiency, { decimals: 3 })}, uniformidad ${fmt(h[k].uniformity, { decimals: 3 })}, dispersión ${fmt(h[k].relStdPct, { decimals: 2 })} %`)}
        />
      </Fill>
    </PlotCard>
  );
}

/** A native select with its label, for a choice of more than a few (ADR-0071 rule 7). */
function Pick({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: { id: string; text: string }[] }) {
  return (
    <label>
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.text}
          </option>
        ))}
      </select>
    </label>
  );
}

type Kind = 'published' | 'proposed' | 'front' | 'case' | 'recommended';
interface Entry {
  x: number;
  y: number;
  kind: Kind;
  method?: string;
}

export function ParetoView({ sel }: { sel: Selection }) {
  const { t, pick, lang } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const actions = useActions();
  const c = cardOf(sel);
  const bench = useArtifact((s) => loadBenchmark(s), []);
  const [choice, setChoice] = useState<Cell | null>(null);
  const [chosen, setChosen] = useState<string | null>(null);
  // the methods cluster at the top of the uniformity range: by default the chart shows the more uniform half, so that the cluster is readable
  const [scope, setScope] = useState<'top' | 'all'>('top');
  const res = bench.state === 'ready' ? bench.data : null;
  const caseDevice: Device = sel.data.manifest.params.device ? 'device' : 'ideal';
  const wanted = useMemo(() => (res ? openingCell(res, { dims: is3D(sel.traps) ? 3 : 2, nTraps: sel.traps.length, device: caseDevice }) : null), [res, sel.traps, caseDevice]);
  const opening = useMemo(() => (res && wanted ? cellWithRows(res, wanted) : null), [res, wanted]);
  const cell = choice ?? opening;
  const rows = useMemo(() => (res && cell ? pickRows(res, cell.geometry, cell.device, cell.budget, 'default') : []), [res, cell]);
  const nearest = useMemo(() => (res && cell && !rows.length ? cellWithRows(res, cell) : null), [res, cell, rows.length]);
  const rec = useMemo(() => recommend(rows), [rows]);
  const geo = res && cell ? res.geometries.find((g) => g.id === cell.geometry) : undefined;
  const geoName = geo ? pick(geo.name) : (cell?.geometry ?? '');
  // the floor of the uniformity axis: the median uniformity of the cell's methods in the default scope, none when every method is shown
  const floor = useMemo(() => {
    if (scope === 'all' || rows.length < 6) return -Infinity;
    const u = rows.map((p) => p.row.uniformity.median).sort((a, b) => a - b);
    return Math.min(u[u.length >> 1], rec?.pick.row.uniformity.median ?? Infinity);
  }, [scope, rows, rec]);
  const dots = useMemo(() => intervalDots(rows.filter((p) => p.row.uniformity.median >= floor), 9), [rows, floor]);
  const hidden = rows.filter((p) => p.row.uniformity.median < floor).length;

  const chart = useMemo(() => {
    if (!res || !cell || !rows.length) return null;
    const entries: Entry[] = [];
    for (const p of rows) if (p.row.uniformity.median >= floor) entries.push({ x: p.row.uniformity.median, y: p.row.efficiency.median, kind: p.kind === 'proposed' ? 'proposed' : 'published', method: p.method });
    for (const p of frontOf(res, cell.geometry)) if (p.u >= floor) entries.push({ x: p.u, y: p.e, kind: 'front' });
    for (const [id, m] of Object.entries(sel.data.manifest.methods)) if (m.uniformity >= floor) entries.push({ x: m.uniformity, y: m.efficiency, kind: 'case', method: id });
    entries.sort((a, b) => a.x - b.x);
    const column = (k: Kind) => entries.map((e) => (e.kind === k ? e.y : null));
    const has = (k: Kind) => entries.some((e) => e.kind === k);
    const series: ChartSeries[] = [];
    if (has('published')) series.push({ label: { en: 'Published methods', es: 'Métodos publicados' }, values: column('published'), color: SERIES_COLORS.published, mode: 'points', size: 7 });
    if (has('proposed')) series.push({ label: { en: 'Proposed methods', es: 'Métodos propuestos' }, values: column('proposed'), color: SERIES_COLORS.proposed, mode: 'points', size: 8 });
    if (has('front')) series.push({ label: { en: `Pareto front of ${geoName}`, es: `Frente de Pareto de ${geoName}` }, values: column('front'), color: SERIES_COLORS.front, mode: 'points', size: 6 });
    if (has('case')) series.push({ label: { en: 'Methods of this case', es: 'Métodos de este caso' }, values: column('case'), color: SERIES_COLORS.case, mode: 'points', size: 10 });
    if (rec) series.push({ label: { en: `Recommended: ${nameOf(rec.pick.method, 'en')}`, es: `Recomendado: ${nameOf(rec.pick.method, 'es')}` }, values: [rec.pick.row.efficiency.median], x: [rec.pick.row.uniformity.median], color: SERIES_COLORS.recommended, mode: 'points', size: 16 });
    if (dots.x.length) series.push({ label: { en: 'Seed range, q1 to q3', es: 'Rango entre semillas, q1 a q3' }, values: dots.y, x: dots.x, color: SERIES_COLORS.spread, mode: 'points', size: 3 });
    return { entries, series };
  }, [res, cell, rows, rec, dots, geoName, floor, sel.data.manifest.methods]);

  const shown = chosen ?? rec?.pick.method ?? null;
  const shownRow = shown ? rows.find((p) => p.method === shown) : undefined;
  const ranInCase = shown ? sel.data.manifest.params.methods.includes(shown) : false;
  const readoutOf = (e: Entry): string => {
    if (e.kind === 'front') return t(`Pareto front: efficiency ${fmt(e.y * 100, { decimals: 1 })} %, uniformity ${fmt(e.x, { decimals: 3 })}`, `Frente de Pareto: eficiencia ${fmt(e.y * 100, { decimals: 1 })} %, uniformidad ${fmt(e.x, { decimals: 3 })}`);
    const row = e.kind === 'case' ? undefined : rows.find((p) => p.method === e.method);
    const name = nameOf(e.method ?? '', lang);
    const seeds = row ? t(`, ${row.row.n_seeds} seeds, spread ${fmt(row.row.rel_std_pct.median, { decimals: 2 })} %`, `, ${row.row.n_seeds} semillas, dispersión ${fmt(row.row.rel_std_pct.median, { decimals: 2 })} %`) : '';
    const where = e.kind === 'case' ? t(' in this case', ' en este caso') : '';
    return t(`${name}${where}: efficiency ${fmt(e.y * 100, { decimals: 1 })} %, uniformity ${fmt(e.x, { decimals: 3 })}${seeds}`, `${name}${where}: eficiencia ${fmt(e.y * 100, { decimals: 1 })} %, uniformidad ${fmt(e.x, { decimals: 3 })}${seeds}`);
  };

  const geometries = res?.geometries.map((g) => ({ id: g.id, text: `${pick(g.name)}${g.n_traps ? `, ${g.n_traps} ${t('traps', 'trampas')}` : ''}` })) ?? [];
  const budgets = res ? budgetsOf(res).map((b) => ({ id: budgetId(b), text: pick(budgetText(b)) })) : [];
  const set = (over: Partial<Cell>) => cell && setChoice({ ...cell, ...over });
  const cellWhy = choice
    ? t('A cell of your choice.', 'Una celda de su elección.')
    : geo
      ? t(`Closest benchmark geometry to this case: ${geoName}, ${geo.n_traps} traps.`, `Geometría del benchmark más cercana a este caso: ${geoName}, ${geo.n_traps} trampas.`)
      : '';
  return (
    <PlotCard
      fill
      title={{ en: 'Efficiency against uniformity', es: 'Eficiencia contra uniformidad' }}
      {...c}
      lane="replay"
      dataKey={stateKey}
      note={{
        en: 'Every method of one benchmark cell, its seed range, the Pareto front of the cell and this case’s own methods. Up and to the right is better on both.',
        es: 'Cada método de una celda del benchmark, su rango entre semillas, el frente de Pareto de la celda y los métodos de este caso. Arriba y a la derecha es mejor en ambos.',
      }}
    >
      <div className="dh-stack">
        <ReadinessNote ids={['benchmark-results']} />
        {res && cell ? (
            <div className="dh-pf" data-caos-flow="" data-pareto-cell={`${cell.geometry}|${cell.device}|${budgetId(cell.budget)}`}>
              <div className="dh-pf-controls">
                <Pick label={t('Geometry', 'Geometría')} value={cell.geometry} onChange={(v) => set({ geometry: v })} options={geometries} />
                <Pick label={t('SLM', 'SLM')} value={cell.device} onChange={(v) => set({ device: v as Device })} options={[{ id: 'ideal', text: t('Ideal', 'Ideal') }, { id: 'device', text: t('Modelled device', 'Dispositivo modelado') }]} />
                <Pick label={t('Budget', 'Presupuesto')} value={budgetId(cell.budget)} onChange={(v) => set({ budget: parseBudget(v) })} options={budgets} />
                <ChipGroup
                  id="pareto-scope"
                  label={{ en: 'Methods shown', es: 'Métodos mostrados' }}
                  value={scope}
                  onChange={(v) => setScope(v as 'top' | 'all')}
                  options={[
                    { id: 'top', label: { en: 'More uniform half', es: 'Mitad más uniforme' }, hint: { en: 'The methods at or above the median uniformity of the cell, where the front and the recommendation are.', es: 'Los métodos con la uniformidad mediana de la celda o más, donde están el frente y la recomendación.' } },
                    { id: 'all', label: { en: 'All', es: 'Todos' }, hint: { en: 'Every method of the cell, including the least uniform.', es: 'Todos los métodos de la celda, también los menos uniformes.' } },
                  ]}
                />
                <span data-pareto-why="">{cellWhy}{hidden > 0 ? ` ${t(`${hidden} of ${rows.length} methods are below the chart's range; choose All to see them.`, `${hidden} de ${rows.length} métodos quedan bajo el rango del gráfico; elija Todos para verlos.`)}` : ''}</span>
              </div>
              {chart ? (
                <div className="dh-pf-chart">
                  <UPlotChart
                    height="fill"
                    solo
                    title={{ en: 'Efficiency against uniformity, with the seed range of each method', es: 'Eficiencia contra uniformidad, con el rango entre semillas de cada método' }}
                    x={{ values: chart.entries.map((e) => e.x), label: { en: 'Uniformity', es: 'Uniformidad' }, format: { decimals: 3 } }}
                    y={{ label: { en: 'Efficiency', es: 'Eficiencia' }, format: { percent: true, decimals: 0 } }}
                    series={chart.series}
                    onPick={(k) => {
                      const m = chart.entries[k]?.method;
                      if (m) setChosen(m);
                    }}
                    readout={(k) => readoutOf(chart.entries[k])}
                  />
                </div>
              ) : (
                <div className="dh-pf-chart">
                  <Unavailable reason={{ en: `The benchmark holds no row for ${geoName} on this SLM and budget.`, es: `El benchmark no tiene filas de ${geoName} con este SLM y presupuesto.` }} />
                  {nearest && (
                    <button type="button" className="btn" data-nearest-cell="" onClick={() => setChoice(nearest)}>
                      {t(`Show the nearest cell that has rows: ${pick(res.geometries.find((g) => g.id === nearest.geometry)?.name ?? { en: nearest.geometry, es: nearest.geometry })}, ${pick(budgetText(nearest.budget))}`, `Mostrar la celda más cercana con filas: ${pick(res.geometries.find((g) => g.id === nearest.geometry)?.name ?? { en: nearest.geometry, es: nearest.geometry })}, ${pick(budgetText(nearest.budget))}`)}
                    </button>
                  )}
                </div>
              )}
              {rec && (
                <p className="dh-pf-take" data-recommended={rec.pick.method} role="status">
                  <strong>{t(`Recommended on ${geoName}: ${nameOf(rec.pick.method, 'en')}.`, `Recomendado en ${geoName}: ${nameOf(rec.pick.method, 'es')}.`)}</strong> {recommendationText(rec, lang)}
                </p>
              )}
              {shown && shownRow && (
                <div className="dh-pf-load">
                  <span>
                    {t(`Selected: ${nameOf(shown, 'en')}, efficiency ${fmt(shownRow.row.efficiency.median * 100, { decimals: 1 })} %, spread ${fmt(shownRow.row.rel_std_pct.median, { decimals: 2 })} %.`, `Elegido: ${nameOf(shown, 'es')}, eficiencia ${fmt(shownRow.row.efficiency.median * 100, { decimals: 1 })} %, dispersión ${fmt(shownRow.row.rel_std_pct.median, { decimals: 2 })} %.`)}
                  </span>
                  <button
                    type="button"
                    className="btn"
                    data-load-method={shown}
                    disabled={!ranInCase}
                    title={ranInCase ? undefined : t('This case did not run that method', 'Este caso no corrió ese método')}
                    onClick={() => actions.setMethod(shown)}
                  >
                    {t(`Load ${nameOf(shown, 'en')} into the App`, `Cargar ${nameOf(shown, 'es')} en la aplicación`)}
                  </button>
                  {!ranInCase && <span>{t('This case did not run that method; pick a case that did.', 'Este caso no corrió ese método; elija un caso que sí.')}</span>}
                </div>
              )}
            </div>
        ) : (
          <div className="dh-fill">
            {bench.state === 'unavailable' ? (
              <Unavailable reason={bench.reason} />
            ) : bench.state === 'error' ? (
              <p role="alert">{bench.error}</p>
            ) : res ? (
              <Unavailable reason={{ en: 'The benchmark holds no geometry with the dimensions of this case.', es: 'El benchmark no tiene una geometría con las dimensiones de este caso.' }} />
            ) : (
              <Pending label={{ en: 'Loading the benchmark', es: 'Cargando el benchmark' }} />
            )}
          </div>
        )}
      </div>
    </PlotCard>
  );
}

export function CameraView({ sel }: { sel: Selection }) {
  const fmt = useFmt();
  const stateKey = useStateKey();
  const c = cardOf(sel);
  const fb = sel.data.trace.feedback;
  if (!fb) {
    return (
      <PlotCard fill title={{ en: 'Camera feedback', es: 'Realimentación de cámara' }} {...c} lane="replay" dataKey={stateKey}>
        <Fill>
          <Unavailable reason={{ en: 'This case has no camera feedback loop (only the feedback cases run one). Pick a case of the Feedback category to see it.', es: 'Este caso no tiene lazo de realimentación de cámara (solo los casos con realimentación lo corren). Elija un caso de la categoría de realimentación para verlo.' }} />
        </Fill>
      </PlotCard>
    );
  }
  const steps = fb.steps;
  const at = steps.find((s) => s.step === sel.fbStep) ?? steps[0];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Relative spread by feedback step', es: 'Dispersión relativa por paso de realimentación' }}
        {...c}
        lane="replay"
        dataKey={stateKey}
        note={{
          en: `Step ${at.step}: ${fmt(at.rel_std_pct, { decimals: 2 })} % rms (start ${fmt(steps[0].rel_std_pct, { decimals: 2 })} %, end ${fmt(steps[steps.length - 1].rel_std_pct, { decimals: 2 })} %). Scrub with the feedback step knob.`,
          es: `Paso ${at.step}: ${fmt(at.rel_std_pct, { decimals: 2 })} % rms (inicio ${fmt(steps[0].rel_std_pct, { decimals: 2 })} %, fin ${fmt(steps[steps.length - 1].rel_std_pct, { decimals: 2 })} %). Recorra con la perilla del paso de realimentación.`,
        }}
      >
        <Fill>
          <UPlotChart
            height="fill"
            title={{ en: 'Relative spread of the trap intensities by step', es: 'Dispersión relativa de las intensidades por paso' }}
            x={{ values: steps.map((s) => s.step), label: { en: 'Feedback step', es: 'Paso de realimentación' }, format: { decimals: 0, grouping: false } }}
            y={{ label: { en: 'Relative spread', es: 'Dispersión relativa' }, unit: '%', format: { decimals: 2 } }}
            series={[{ label: { en: 'Relative spread', es: 'Dispersión relativa' }, values: steps.map((s) => s.rel_std_pct), color: '--color-warn', dots: true }]}
            marks={[{ x: at.step, label: { en: 'step', es: 'paso' } }]}
          />
        </Fill>
      </PlotCard>
      <PlotCard fill title={{ en: 'Efficiency by feedback step', es: 'Eficiencia por paso de realimentación' }} {...c} lane="replay" dataKey={stateKey}>
        <Fill quiet>
          <UPlotChart
            height="fill"
            title={{ en: 'Efficiency by feedback step', es: 'Eficiencia por paso de realimentación' }}
            x={{ values: steps.map((s) => s.step), label: { en: 'Feedback step', es: 'Paso de realimentación' }, format: { decimals: 0, grouping: false } }}
            y={{ label: { en: 'Efficiency', es: 'Eficiencia' }, format: { decimals: 3 } }}
            series={[{ label: { en: 'Efficiency', es: 'Eficiencia' }, values: steps.map((s) => s.efficiency), color: '--color-accent', dots: true }]}
            marks={[{ x: at.step, label: { en: 'step', es: 'paso' } }]}
          />
        </Fill>
      </PlotCard>
    </ViewsRow>
  );
}

export { ReadinessNote };
