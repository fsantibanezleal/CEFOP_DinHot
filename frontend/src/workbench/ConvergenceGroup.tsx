// Group 4, Convergence: did the algorithm converge and what it traded (V4), the efficiency-uniformity front of the benchmark (B5) and
// the camera feedback loop that removes the non-uniformity the optics leave (V9).
import { PlotCard, SubTabs, ViewsRow } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import { loadBenchmark, useArtifact } from '../api/artifacts';
import { ReadinessNote } from '../readiness/ReadinessNote';
import { cardOf } from './HologramGroup';
import { historyAt, methodLabel, useSelection, type Selection } from './model';
import { Fill, LOADING, Pending, Unavailable, useActions, useFmt, useStateKey, useT } from './ui';

export function ConvergenceGroup() {
  const { t } = useT();
  const sel = useSelection();
  return (
    <SubTabs
      ariaLabel={t('Convergence views', 'Vistas de convergencia')}
      tabs={[
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
          <Unavailable reason={{ en: `The bake holds no iteration history for ${sel.methodId} on this case, and the live engine is not on this build.`, es: `La generación no guarda historial de iteraciones de ${sel.methodId} en este caso y el motor en vivo no está en esta versión.` }} />
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

export function ParetoView({ sel }: { sel: Selection }) {
  const { t, pick } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const c = cardOf(sel);
  const bench = useArtifact((s) => loadBenchmark(s), []);
  const shaped = useMemo(() => {
    if (bench.state !== 'ready') return null;
    const fronts = bench.data.pareto;
    const own = Object.entries(sel.data.manifest.methods).map(([id, m]) => ({ id, x: m.uniformity, y: m.efficiency }));
    const xs = [...new Set([...fronts.flatMap((f) => f.points.map((p) => p.uniformity)), ...own.map((o) => o.x)])].sort((a, b) => a - b);
    const col = (pts: { x: number; y: number }[]) => xs.map((x) => pts.find((p) => p.x === x)?.y ?? null);
    return {
      xs,
      series: [
        ...fronts.map((f) => ({
          label: { en: `${f.method} front, ${pick(bench.data.geometries.find((g) => g.id === f.geometry)?.name ?? { en: f.geometry, es: f.geometry })}`, es: `Frente ${f.method}, ${pick(bench.data.geometries.find((g) => g.id === f.geometry)?.name ?? { en: f.geometry, es: f.geometry })}` },
          values: col(f.points.map((p) => ({ x: p.uniformity, y: p.efficiency }))),
        })),
        { label: { en: 'Methods of this case', es: 'Métodos de este caso' }, values: col(own.map((o) => ({ x: o.x, y: o.y }))) },
      ],
      own,
    };
  }, [bench, sel.data.manifest.methods, pick]);
  const tones = ['--color-accent', '--color-good', '--color-warn', '--color-magenta', '--color-bad'] as const;
  return (
    <PlotCard
      fill
      title={{ en: 'Efficiency against uniformity', es: 'Eficiencia contra uniformidad' }}
      {...c}
      lane="replay"
      dataKey={stateKey}
      note={{
        en: 'The Pareto fronts of the benchmark (method B5, one per geometry) with the final point of every method this case ran. Up and to the right is better on both.',
        es: 'Los frentes de Pareto del benchmark (método B5, uno por geometría) con el punto final de cada método que corrió este caso. Arriba y a la derecha es mejor en ambos.',
      }}
    >
      <Fill rows={['benchmark-results']}>
        {bench.state === 'ready' && shaped ? (
          <UPlotChart
            height="fill"
            title={{ en: 'Efficiency against uniformity', es: 'Eficiencia contra uniformidad' }}
            x={{ values: shaped.xs, label: { en: 'Uniformity', es: 'Uniformidad' }, format: { decimals: 3 } }}
            y={{ label: { en: 'Efficiency', es: 'Eficiencia' }, format: { decimals: 3 } }}
            series={shaped.series.map((s, i) => ({ ...s, color: tones[i % tones.length], mode: 'points' as const, size: i === shaped.series.length - 1 ? 9 : 6 }))}
            readout={(k) => t(`uniformity ${fmt(shaped.xs[k], { decimals: 3 })}`, `uniformidad ${fmt(shaped.xs[k], { decimals: 3 })}`)}
          />
        ) : bench.state === 'unavailable' ? (
          <Unavailable reason={bench.reason} />
        ) : bench.state === 'error' ? (
          <p role="alert">{bench.error}</p>
        ) : (
          <Pending label={{ en: 'Loading the benchmark', es: 'Cargando el benchmark' }} />
        )}
      </Fill>
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
