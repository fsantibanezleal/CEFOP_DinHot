// Group 3, Traps: are the traps uniform and which are worst (V3), what depth each one holds (V13) and where the optical power goes (V14).
// A bar is a trap: clicking one selects it (the selection key is the case, the method and the trap id) and the focal-plane map follows.
// Over 12 traps a bar chart would be unreadable, so the same values are drawn as a sorted curve.
// A shaped target has no traps: its views draw the potential itself, the focal intensity over the mean inside the shape.
import { BarChart, PlotCard, SubTabs, ViewsRow } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo, useState } from 'react';
import { INTENSITY_LUT } from './colormaps';
import { cardOf } from './HologramGroup';
import { Heatmap } from './HeatmapStage';
import { histogram, isShaped, trapDeviation, useSelection, type Selection } from './model';
import { umToPixel } from './traps';
import { Fill, LOADING, Pending, Unavailable, useActions, useFmt, useStateKey, useT } from './ui';

// More than this many bars put their id labels on top of each other (G10): a sorted-points chart carries the larger arrays.
const BARS_MAX = 12;

export function TrapsGroup() {
  const { t } = useT();
  const sel = useSelection();
  return (
    <SubTabs
      ariaLabel={t('Trap views', 'Vistas de las trampas')}
      tabs={[
        { id: 'uniformity', label: t('Per-trap intensity', 'Intensidad'), content: sel ? <IntensityView sel={sel} /> : <Pending label={LOADING} /> },
        { id: 'depth', label: t('Depth', 'Profundidad'), content: sel ? <DepthView sel={sel} /> : <Pending label={LOADING} /> },
        { id: 'budget', label: t('Power budget', 'Potencia'), content: sel ? <BudgetView sel={sel} /> : <Pending label={LOADING} /> },
      ]}
    />
  );
}

/** The per-trap values in the order the reader asked for, with the trap each belongs to. */
function ordered(sel: Selection, values: readonly number[]) {
  const items = sel.traps.map((tr, i) => ({ id: tr.id, v: values[i], inRegion: !!sel.region && inside(sel, tr.x_um, tr.y_um) }));
  return sel.sortBy === 'deviation' ? items.slice().sort((a, b) => Math.abs(b.v - 1) - Math.abs(a.v - 1)) : items;
}
function inside(sel: Selection, x: number, y: number): boolean {
  const r = sel.region;
  return !!r && x >= r.x0 && x <= r.x1 && y >= r.y0 && y <= r.y1;
}


/**
 * The trap views of a shaped target: no trap list, so the potential itself. Depth is proportional to intensity (Grimm et al. Eq. 12), so
 * the focal intensity over its mean inside the shape is the depth over the mean depth; the same map reads as either.
 */
function ShapedPotential({ sel, title, note }: { sel: Selection; title: { en: string; es: string }; note: { en: string; es: string } }) {
  const { t, pick } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const c = cardOf(sel);
  const focal = sel.maps?.focal ?? null;
  const ratio = useMemo(() => (focal ? Float32Array.from(focal.db, (d) => 10 ** (d / 10)) : null), [focal]);
  return (
    <PlotCard fill title={title} {...c} dataKey={stateKey} note={note}>
      <Fill>
        {focal && ratio ? (
          <Heatmap
            label={{ en: 'Focal intensity over the mean inside the shape', es: 'Intensidad focal sobre la media dentro de la forma' }}
            data={ratio}
            cols={focal.size}
            rows={focal.size}
            lut={INTENSITY_LUT}
            range={[0, 2]}
            describe={(col, row, v) => pick({ en: `bin (${col}, ${row}): ${fmt(v, { decimals: 3 })} of the mean`, es: `bin (${col}, ${row}): ${fmt(v, { decimals: 3 })} de la media` })}
            summary={t(`Focal intensity over the mean inside the shape, ${focal.size} by ${focal.size} bins, colour scale 0 to 2.`, `Intensidad focal sobre la media dentro de la forma, ${focal.size} por ${focal.size} bins, escala de color de 0 a 2.`)}
          />
        ) : (
          <Unavailable reason={{ en: `No focal map for ${sel.methodId} on this case.`, es: `No hay mapa focal de ${sel.methodId} en este caso.` }} />
        )}
      </Fill>
    </PlotCard>
  );
}

export function IntensityView({ sel }: { sel: Selection }) {
  const { t } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const act = useActions();
  const [sortBy, setSortBy] = useState<'id' | 'deviation'>('id');
  const trapI = sel.result?.trapI ?? null;
  const c = cardOf(sel);
  const band = sel.bandPct / 100;
  const stats = useMemo(() => (trapI ? trapDeviation(trapI) : null), [trapI]);
  const items = useMemo(() => (trapI ? ordered({ ...sel, sortBy }, trapI) : []), [sel, trapI, sortBy]);
  const hist = useMemo(() => (trapI ? histogram(trapI, Math.min(0.5, ...trapI), Math.max(1.5, ...trapI), 21) : null), [trapI]);
  const within = trapI ? trapI.filter((v) => Math.abs(v - 1) <= band).length : 0;
  const noTraps = !trapI || trapI.length === 0;
  if (noTraps && isShaped(sel.data.manifest)) {
    return (
      <ShapedPotential
        sel={sel}
        title={{ en: 'Intensity of the shaped potential', es: 'Intensidad del potencial con forma' }}
        note={{ en: 'A shaped target has no trap list: the map is the focal intensity over its mean inside the shape (1 is the mean; a uniform potential is one colour).', es: 'Un objetivo con forma no tiene lista de trampas: el mapa es la intensidad focal sobre su media dentro de la forma (1 es la media; un potencial uniforme es de un solo color).' }}
      />
    );
  }
  if (noTraps || !stats || !hist) {
    return (
      <PlotCard fill title={{ en: 'Per-trap intensity', es: 'Intensidad por trampa' }} {...c} dataKey={stateKey}>
        <Fill>
          <Unavailable reason={{ en: `The bake holds no per-trap intensities for ${sel.methodId} on this case (it records them for the methods it ran), and the live engine is not on this build.`, es: `La generación no guarda intensidades por trampa de ${sel.methodId} en este caso (las guarda para los métodos que corrió) y el motor en vivo no está en esta versión.` }} />
        </Fill>
      </PlotCard>
    );
  }
  const many = items.length > BARS_MAX;
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'Intensity of each trap against the mean', es: 'Intensidad de cada trampa respecto de la media' }}
        {...c}
        lane={sel.result?.lane ?? c.lane}
        dataKey={stateKey}
        actions={
          <button type="button" className="btn" aria-pressed={sortBy === 'deviation'} onClick={() => setSortBy(sortBy === 'id' ? 'deviation' : 'id')}>
            {sortBy === 'id' ? t('Sort by deviation', 'Ordenar por desviación') : t('Sort by id', 'Ordenar por id')}
          </button>
        }
        note={{
          en: `${within} of ${trapI.length} traps are within plus or minus ${fmt(sel.bandPct, { decimals: 0 })} % of the mean. Weakest ${fmt(stats.min, { decimals: 3 })}, strongest ${fmt(stats.max, { decimals: 3 })}, spread ${fmt(stats.rmsPct, { decimals: 2 })} % rms.`,
          es: `${within} de ${trapI.length} trampas están dentro de más o menos ${fmt(sel.bandPct, { decimals: 0 })} % de la media. Más débil ${fmt(stats.min, { decimals: 3 })}, más fuerte ${fmt(stats.max, { decimals: 3 })}, dispersión ${fmt(stats.rmsPct, { decimals: 2 })} % rms.`,
        }}
      >
        <Fill>
          {many ? (
            <UPlotChart
              height="fill"
              title={{ en: 'Trap intensity, sorted by deviation from the mean', es: 'Intensidad de las trampas, ordenada por desviación de la media' }}
              x={{ values: items.map((_, i) => i + 1), label: { en: 'Trap rank', es: 'Rango de la trampa' }, format: { decimals: 0 } }}
              y={{ label: { en: 'Intensity over the mean', es: 'Intensidad sobre la media' }, format: { decimals: 2 } }}
              series={[{ label: { en: 'Trap intensity', es: 'Intensidad de la trampa' }, values: items.map((i) => i.v), color: '--color-accent', mode: 'points', size: 4 }]}
              yMarks={[
                { y: 1 + band, label: { en: 'band', es: 'banda' }, tone: 'warn' },
                { y: 1 - band, tone: 'warn' },
                { y: 1, tone: 'neutral' },
              ]}
              onPick={(k) => act.selectTrap(items[k]?.id ?? null)}
              readout={(k) => t(`trap ${items[k]?.id}: ${fmt(items[k]?.v, { decimals: 3 })} of the mean`, `trampa ${items[k]?.id}: ${fmt(items[k]?.v, { decimals: 3 })} de la media`)}
            />
          ) : (
            <BarChart
              height="fill"
              orientation="horizontal"
              values
              title={{ en: 'Intensity of each trap over the mean', es: 'Intensidad de cada trampa sobre la media' }}
              axis={{ label: { en: 'Intensity over the mean', es: 'Intensidad sobre la media' }, unit: { en: 'ratio', es: 'razón' }, format: { decimals: 3 } }}
              onSelect={(id) => act.selectTrap(Number(id))}
              data={items.map((i) => ({
                id: String(i.id),
                label: { en: `${i.id}`, es: `${i.id}` },
                value: i.v,
                highlight: i.id === sel.trapId,
                tone: Math.abs(i.v - 1) <= band ? ('good' as const) : Math.abs(i.v - 1) <= 2 * band ? ('warn' as const) : ('bad' as const),
                hint: i.inRegion ? { en: 'inside the selected region', es: 'dentro de la región elegida' } : undefined,
              }))}
            />
          )}
        </Fill>
      </PlotCard>
      <PlotCard fill title={{ en: 'Histogram of trap intensities', es: 'Histograma de intensidades de las trampas' }} {...c} lane={sel.result?.lane ?? c.lane} dataKey={stateKey}>
        <Fill quiet>
          <UPlotChart
            height="fill"
            title={{ en: 'Number of traps by intensity over the mean', es: 'Número de trampas por intensidad sobre la media' }}
            x={{ values: hist.centres, label: { en: 'Intensity over the mean', es: 'Intensidad sobre la media' }, format: { decimals: 2 } }}
            y={{ label: { en: 'Traps', es: 'Trampas' }, format: { decimals: 0 } }}
            series={[{ label: { en: 'Traps', es: 'Trampas' }, values: hist.counts, color: '--color-accent', dots: true }]}
            marks={[{ x: 1, label: { en: 'mean', es: 'media' } }]}
          />
        </Fill>
      </PlotCard>
    </ViewsRow>
  );
}

export function DepthView({ sel }: { sel: Selection }) {
  const fmt = useFmt();
  const stateKey = useStateKey();
  const act = useActions();
  const c = cardOf(sel);
  const trapI = sel.result?.trapI ?? null;
  const dyn = sel.data.trace.dynamics;
  const params = sel.data.manifest.params.dynamics;
  const refTrap = params?.trap_id ?? null;
  const refIdx = refTrap === null ? -1 : sel.data.trace.traps.findIndex((x) => x.id === refTrap);
  // U is proportional to I (Grimm et al. Eq. 12) and, at one power, to the power: the depth of every trap scales from the simulated one.
  const scale = dyn && params && refIdx >= 0 && trapI ? (dyn.depth.value / (trapI[refIdx] || 1)) * (sel.powerMw / params.power_mw) : null;
  const values = trapI ? trapI.map((v) => (scale === null ? v : v * scale)) : null;
  const unit = scale === null ? { en: 'ratio to the mean', es: 'razón a la media' } : { en: dyn!.depth.unit, es: dyn!.depth.unit };
  const items = useMemo(() => (values ? sel.traps.map((tr, i) => ({ id: tr.id, v: values[i] })) : []), [sel.traps, values]);
  if ((!values || values.length === 0) && isShaped(sel.data.manifest)) {
    return (
      <ShapedPotential
        sel={sel}
        title={{ en: 'Depth of the shaped potential', es: 'Profundidad del potencial con forma' }}
        note={{ en: 'Depth is proportional to intensity, so the map of the intensity over its mean inside the shape is the depth over the mean depth.', es: 'La profundidad es proporcional a la intensidad, así que el mapa de la intensidad sobre su media dentro de la forma es la profundidad sobre la profundidad media.' }}
      />
    );
  }
  if (!values || values.length === 0) {
    return (
      <PlotCard fill title={{ en: 'Trap depth', es: 'Profundidad de las trampas' }} {...c} dataKey={stateKey}>
        <Fill>
          <Unavailable reason={{ en: `No per-trap intensities for ${sel.methodId} on this case, so no depth can be derived.`, es: `No hay intensidades por trampa de ${sel.methodId} en este caso, así que no se puede derivar la profundidad.` }} />
        </Fill>
      </PlotCard>
    );
  }
  const mean = values.reduce((a, v) => a + v, 0) / values.length;
  const rms = Math.sqrt(values.reduce((a, v) => a + (v - mean) ** 2, 0) / values.length);
  return (
    <PlotCard
      fill
      title={{ en: 'Depth of each trap', es: 'Profundidad de cada trampa' }}
      {...c}
      lane={sel.result?.lane ?? c.lane}
      dataKey={stateKey}
      note={{
        en: scale === null ? 'Depth is proportional to intensity; this case has no particle simulation, so it is shown as a ratio to the mean.' : `Scaled from the simulated trap ${refTrap} (${fmt(dyn!.depth.value, { decimals: 2 })} ${dyn!.depth.unit} at ${fmt(params!.power_mw, { decimals: 1 })} mW) to the rail power: depth is proportional to intensity and to power. Spread ${fmt((100 * rms) / mean, { decimals: 2 })} % rms.`,
        es: scale === null ? 'La profundidad es proporcional a la intensidad; este caso no tiene simulación de partícula, así que se muestra como razón a la media.' : `Escalada desde la trampa simulada ${refTrap} (${fmt(dyn!.depth.value, { decimals: 2 })} ${dyn!.depth.unit} con ${fmt(params!.power_mw, { decimals: 1 })} mW) a la potencia del panel: la profundidad es proporcional a la intensidad y a la potencia. Dispersión ${fmt((100 * rms) / mean, { decimals: 2 })} % rms.`,
      }}
    >
      <Fill>
        {items.length > BARS_MAX ? (
          <UPlotChart
            height="fill"
            title={{ en: 'Trap depth by trap id', es: 'Profundidad por identificador de trampa' }}
            x={{ values: items.map((i) => i.id), label: { en: 'Trap id', es: 'Identificador de trampa' }, format: { decimals: 0, grouping: false } }}
            y={{ label: { en: 'Depth', es: 'Profundidad' }, unit, format: { decimals: 2 } }}
            series={[{ label: { en: 'Depth', es: 'Profundidad' }, values: items.map((i) => i.v), color: '--color-accent', mode: 'points', size: 4 }]}
            yMarks={[{ y: mean, label: { en: 'mean', es: 'media' }, tone: 'neutral' }]}
            onPick={(k) => act.selectTrap(items[k]?.id ?? null)}
          />
        ) : (
          <BarChart
            height="fill"
            orientation="horizontal"
            values
            title={{ en: 'Depth of each trap', es: 'Profundidad de cada trampa' }}
            axis={{ label: { en: 'Depth', es: 'Profundidad' }, unit, format: { decimals: 3 } }}
            onSelect={(id) => act.selectTrap(Number(id))}
            data={items.map((i) => ({ id: String(i.id), label: { en: `${i.id}`, es: `${i.id}` }, value: i.v, highlight: i.id === sel.trapId }))}
          />
        )}
      </Fill>
    </PlotCard>
  );
}

export function BudgetView({ sel }: { sel: Selection }) {
  const { t } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const c = cardOf(sel);
  const m = sel.result?.metrics;
  if (!m) {
    return (
      <PlotCard fill title={{ en: 'Where the optical power goes', es: 'A dónde va la potencia óptica' }} {...c} dataKey={stateKey}>
        <Fill>
          <Unavailable reason={{ en: `No metrics for ${sel.methodId} on this case.`, es: `No hay métricas de ${sel.methodId} en este caso.` }} />
        </Fill>
      </PlotCard>
    );
  }
  const eff = m.efficiency;
  const zero = m.zeroOrder;
  const ghost = m.ghost;
  const other = Math.max(0, 1 - eff - zero - ghost);
  const steps: { id: string; label: { en: string; es: string }; from: number; to: number; value: number; tone: 'good' | 'warn' | 'bad' | 'neutral' }[] = [
    { id: 'traps', label: { en: 'Trap light', es: 'Luz en las trampas' }, from: 0, to: eff, value: eff, tone: 'good' },
    { id: 'zero', label: { en: 'Zero order', es: 'Orden cero' }, from: eff, to: eff + zero, value: zero, tone: 'warn' },
    { id: 'ghost', label: { en: 'Ghost and replicas', es: 'Fantasmas y réplicas' }, from: eff + zero, to: eff + zero + ghost, value: ghost, tone: 'bad' },
    { id: 'other', label: { en: 'Other losses', es: 'Otras pérdidas' }, from: eff + zero + ghost, to: eff + zero + ghost + other, value: other, tone: 'neutral' },
  ];
  return (
    <PlotCard
      fill
      title={{ en: 'Where the optical power goes', es: 'A dónde va la potencia óptica' }}
      {...c}
      lane={sel.result?.lane ?? c.lane}
      dataKey={stateKey}
      note={{
        en: `Fractions of the power reaching the image plane (efficiency as Schroff et al. Eq. 2, predicted). The chain adds to 1; other losses are what the metrics do not name.`,
        es: `Fracciones de la potencia que llega al plano imagen (eficiencia como en Schroff et al., Ec. 2, predicha). La cadena suma 1; otras pérdidas es lo que las métricas no nombran.`,
      }}
    >
      <Fill>
        <BarChart
          height="fill"
          orientation="vertical"
          title={{ en: 'Power budget as a chain from 0 to 1', es: 'Balance de potencia como cadena de 0 a 1' }}
          axis={{ label: { en: 'Fraction of the power', es: 'Fracción de la potencia' }, format: { decimals: 3 }, range: [0, 1] }}
          data={steps.map((s) => ({ id: s.id, label: s.label, value: s.value, span: [s.from, s.to] as [number, number], tone: s.tone, format: { percent: true, decimals: 1 } }))}
        />
        <span className="sr-only">{t(`Efficiency ${fmt(eff, { decimals: 3 })}`, `Eficiencia ${fmt(eff, { decimals: 3 })}`)}</span>
      </Fill>
    </PlotCard>
  );
}

export { umToPixel };
