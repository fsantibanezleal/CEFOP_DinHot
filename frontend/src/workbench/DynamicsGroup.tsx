// Group 5, Dynamics: what a bead or an atom does in the computed map (V10), whether the trap stiffness it feels is the one the map
// predicts (V11: the power spectrum with its Lorentzian fit, and the position histogram against the Boltzmann distribution), and
// how long a rearrangement takes to a defect-free array (V12).
// Nothing here moves on arrival (G8): the trajectory and the rearrangement play on demand, pause when the window loses focus or the
// tab is hidden, and the scrub bar and the arrow keys step through them by hand.
import { PlotCard, SubTabs, usePausedViz, ViewsRow, Stage } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useEffect, useMemo, useRef, useState } from 'react';
import { INTENSITY_LUT } from './colormaps';
import { getEngine, type ParticleResult } from './engine';
import { Heatmap } from './HeatmapStage';
import { cardOf } from './HologramGroup';
import { histogram, useSelection, type Selection } from './model';
import { umToPixel } from './traps';
import { Fill, LOADING, Pending, Unavailable, useFmt, useStateKey, useT } from './ui';

const KB = 1.380649e-23;
const AMU = 1.66053906660e-27;

export function DynamicsGroup() {
  const { t } = useT();
  const sel = useSelection();
  return (
    <SubTabs
      ariaLabel={t('Dynamics views', 'Vistas de dinámica')}
      tabs={[
        { id: 'particle', label: t('Trapped particle', 'Partícula atrapada'), content: sel ? <ParticleView sel={sel} /> : <Pending label={LOADING} /> },
        { id: 'psd', label: t('Spectrum', 'Espectro'), content: sel ? <SpectrumView sel={sel} /> : <Pending label={LOADING} /> },
        { id: 'rearrangement', label: t('Rearrangement', 'Reordenamiento'), content: sel ? <RearrangementView sel={sel} /> : <Pending label={LOADING} /> },
      ]}
    />
  );
}

/** One trajectory of the trapped particle: displacements from the trap centre in micrometres, the spectrum and what produced it. */
export interface Trajectory {
  lane: 'live' | 'replay';
  xUm: ArrayLike<number>;
  yUm: ArrayLike<number>;
  dtS: number;
  fHz: ArrayLike<number>;
  p: ArrayLike<number>;
  fcHz: number;
  stiffness: { value: number; unit: string };
  /** Why a live simulation was asked for and not delivered (the baked trajectory is shown instead). */
  failed?: string | null;
  /** A live simulation is out: what is shown is the baked trajectory until it lands. */
  pending?: boolean;
}

/**
 * One simulation per distinct request, shared by every view that asks (the particle and the spectrum read the same trajectory): the
 * promise is kept by its key, the last few only. A request is never made at rest: only a change of seed, power, method or edits asks.
 */
const simulations = new Map<string, Promise<ParticleResult>>();
function simulate(key: string, run: () => Promise<ParticleResult>): Promise<ParticleResult> {
  const hit = simulations.get(key);
  if (hit) return hit;
  const p = run();
  simulations.set(key, p);
  p.catch(() => simulations.delete(key));
  while (simulations.size > 8) simulations.delete(simulations.keys().next().value as string);
  return p;
}

/** True while the rail asks for exactly what the bake simulated: its seed, its power, its hologram, no edits. */
export function atTheBake(sel: Selection): boolean {
  const dyn = sel.data.manifest.params.dynamics;
  return !!dyn && sel.maps?.lane === 'replay' && sel.seed === sel.data.manifest.seed && sel.powerMw === dyn.power_mw && !sel.edited && !sel.aberrationEdited && sel.device === (sel.data.manifest.params.device ? 'case' : 'ideal');
}

/**
 * The baked trajectory while the rail shows what the bake simulated, else the engine's: the particle in the local map of the hologram on
 * screen (live or the baked phase), at the rail's seed and power. The engine takes the phase and the case, so the map is the exact
 * point-trap one, not an interpolation of the sampled focal plane.
 */
export function useTrajectory(sel: Selection): Trajectory | null {
  const dyn = sel.data.trace.dynamics;
  const params = sel.data.manifest.params.dynamics;
  const maps = sel.maps;
  const [live, setLive] = useState<{ key: string; r: ParticleResult } | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const key = `${sel.data.manifest.case_id}|${maps?.method}|${maps?.lane}|${sel.device}|${sel.seed}|${sel.powerMw}|${sel.traps.map((t) => `${t.id},${t.x_um},${t.y_um},${t.z_um}`).join(';')}`;
  const wantLive = sel.engineAvailable && !!params && !!maps && !atTheBake(sel);
  useEffect(() => {
    if (!wantLive || !params || !maps) return;
    let on = true;
    setFailed(null);
    void getEngine().then(async (e) => {
      try {
        const focal = maps.focal ? Float32Array.from(maps.focal.db, (d) => 10 ** (d / 10)) : new Float32Array(0);
        const r = await simulate(key, () =>
          e.client.particle({
            focal,
            focalSize: maps.focal?.size ?? 0,
            binUm: maps.focal?.binUm ?? maps.binUm,
            dynamics: { ...params, power_mw: sel.powerMw },
            seed: sel.seed,
            phase: Float64Array.from(sel.device === 'case' && maps.displayed ? maps.displayed : maps.phase),
            params: sel.runParams,
          }),
        );
        if (on) setLive({ key, r });
      } catch (err) {
        // NotLive or a failed simulation: the baked trajectory answers and the view says why
        if (on) setFailed(String(err));
      }
    });
    return () => {
      on = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, wantLive]);
  if (wantLive && live?.key === key) {
    const r = live.r;
    return { lane: 'live', xUm: r.xUm, yUm: r.yUm, dtS: r.dtS, fHz: r.psd.fHz, p: r.psd.p, fcHz: r.fcHz, stiffness: r.stiffness, failed: null };
  }
  if (!dyn) return null;
  return {
    lane: 'replay',
    xUm: dyn.x_um,
    yUm: dyn.y_um,
    dtS: dyn.dt_s * dyn.t_decimation,
    fHz: dyn.psd.f_hz,
    p: dyn.psd.p,
    fcHz: dyn.fc_hz,
    stiffness: dyn.kappa_pn_per_um !== undefined ? { value: dyn.kappa_pn_per_um, unit: 'pN/um' } : { value: dyn.omega_r_hz ?? NaN, unit: 'Hz' },
    failed,
    pending: wantLive && !failed,
  };
}

const NO_DYNAMICS = {
  en: 'This case has no particle simulation (only the dynamics cases carry one). Pick a case of the Dynamics category to see it.',
  es: 'Este caso no tiene simulación de partícula (solo los casos de dinámica la tienen). Elija un caso de la categoría de dinámica para verla.',
};

export function ParticleView({ sel }: { sel: Selection }) {
  const { t, pick } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const c = cardOf(sel);
  const tr = useTrajectory(sel);
  const params = sel.data.manifest.params.dynamics;
  const focal = sel.maps?.focal ?? null;
  const [frame, setFrame] = useState(0);
  const n = tr ? Math.min(tr.xUm.length, tr.yUm.length) : 0;
  const frameRef = useRef(0);
  frameRef.current = frame;
  const viz = usePausedViz(
    (dt) => {
      const next = frameRef.current + Math.max(1, Math.round(dt / 8));
      if (next >= n - 1) {
        setFrame(n - 1);
        return false;
      }
      setFrame(next);
      return true;
    },
    { loop: false },
  );
  // Pause when the window loses focus (the shell already halts a hidden tab).
  useEffect(() => {
    const off = () => viz.pause();
    window.addEventListener('blur', off);
    return () => window.removeEventListener('blur', off);
  }, [viz]);
  useEffect(() => setFrame(0), [tr?.lane, tr?.xUm]);

  const trap = sel.traps.find((x) => x.id === params?.trap_id) ?? null;
  const trail = useMemo(() => {
    if (!tr || !focal || !trap) return null;
    const [cc, cr] = umToPixel(trap.x_um, trap.y_um, focal.size, focal.binUm);
    const col = new Float32Array(n);
    const row = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      col[i] = cc + tr.xUm[i] / focal.binUm;
      row[i] = cr + tr.yUm[i] / focal.binUm;
    }
    return { col, row };
  }, [tr, focal, trap, n]);

  if (!params) {
    return (
      <PlotCard fill title={{ en: 'Trapped particle', es: 'Partícula atrapada' }} {...c} dataKey={stateKey}>
        <Fill>
          <Unavailable reason={NO_DYNAMICS} />
        </Fill>
      </PlotCard>
    );
  }
  const bakedPower = params.power_mw;
  const what = { en: params.particle === 'bead' ? 'A bead' : 'An atom', es: params.particle === 'bead' ? 'Una microesfera' : 'Un átomo' };
  const holo = sel.maps?.lane === 'live' ? { en: `the live ${sel.maps.method} hologram`, es: `el holograma ${sel.maps.method} en vivo` } : { en: `the baked ${sel.maps?.method} hologram`, es: `el holograma ${sel.maps?.method} de la generación` };
  const where =
    tr?.lane === 'live'
      ? { en: `simulated now in your browser in the local map of ${holo.en}, seed ${sel.seed % 1000}, ${fmt(sel.powerMw, { decimals: 2 })} mW`, es: `simulado ahora en su navegador en el mapa local de ${holo.es}, semilla ${sel.seed % 1000}, ${fmt(sel.powerMw, { decimals: 2 })} mW` }
      : tr?.pending
        ? { en: 'the baked trajectory is shown while the engine simulates your settings', es: 'se muestra la trayectoria de la generación mientras el motor simula su configuración' }
        : tr?.failed
          ? { en: `the live simulation failed (${tr.failed}), so the baked trajectory is shown`, es: `falló la simulación en vivo (${tr.failed}), así que se muestra la trayectoria de la generación` }
          : !sel.engineAvailable && sel.powerMw !== bakedPower
            ? { en: `replayed from the bake at ${fmt(bakedPower, { decimals: 1 })} mW; the live engine is not on this build, so the rail power rescales depth only`, es: `reproducido de la generación con ${fmt(bakedPower, { decimals: 1 })} mW; el motor en vivo no está en esta versión, así que la potencia del panel solo reescala la profundidad` }
            : { en: 'replayed from the bake', es: 'reproducido de la generación' };
  const note = {
    en: `${what.en} in trap ${params.trap_id}, ${where.en}. Press play, or scrub; time ${fmt(((tr?.dtS ?? 0) * frame) * 1e3, { decimals: 2 })} ms.`,
    es: `${what.es} en la trampa ${params.trap_id}, ${where.es}. Pulse reproducir o recorra; tiempo ${fmt(((tr?.dtS ?? 0) * frame) * 1e3, { decimals: 2 })} ms.`,
  };
  return (
    <PlotCard fill title={{ en: 'Particle trajectory over the focal map', es: 'Trayectoria de la partícula sobre el mapa focal' }} {...c} lane={tr?.lane ?? 'replay'} dataKey={stateKey} note={note}>
      <Fill>
        <div className="dh-stack">
        <div className="dh-scrub">
          <button type="button" className="btn" aria-pressed={viz.playing} onClick={() => (frame >= n - 1 ? (setFrame(0), viz.restart()) : viz.toggle())}>
            {viz.playing ? t('Pause', 'Pausa') : t('Play', 'Reproducir')}
          </button>
          <label htmlFor="dh-particle-frame" className="sr-only">
            {t('Frame', 'Cuadro')}
          </label>
          <input
            id="dh-particle-frame"
            type="range"
            min={0}
            max={Math.max(0, n - 1)}
            value={frame}
            onChange={(e) => {
              viz.pause();
              setFrame(Number(e.target.value));
            }}
          />
          <output>{`${frame + 1} / ${n}`}</output>
        </div>
        <div className="dh-fill">
        {focal && trail ? (
          <Heatmap
            label={{ en: 'Focal map with the particle trajectory', es: 'Mapa focal con la trayectoria de la partícula' }}
            data={focal.db}
            cols={focal.size}
            rows={focal.size}
            lut={INTENSITY_LUT}
            range={[sel.dbFloor, 0]}
            trail={{ col: trail.col, row: trail.row, upto: frame }}
            describe={(col, row, v) => pick({ en: `bin (${col}, ${row}): ${fmt(v, { decimals: 1 })} dB`, es: `bin (${col}, ${row}): ${fmt(v, { decimals: 1 })} dB` })}
            summary={t(`Focal map ${focal.size} by ${focal.size} with the trajectory of ${n} samples of a ${params.particle}, now at sample ${frame + 1}.`, `Mapa focal de ${focal.size} por ${focal.size} con la trayectoria de ${n} muestras de ${params.particle === 'bead' ? 'una microesfera' : 'un átomo'}, ahora en la muestra ${frame + 1}.`)}
          />
        ) : (
          <Unavailable reason={tr ? { en: 'The focal map of this method is not available here, so the trajectory has nothing to be drawn over.', es: 'El mapa focal de este método no está disponible aquí, así que la trayectoria no tiene sobre qué dibujarse.' } : NO_DYNAMICS} />
        )}
        </div>
        </div>
      </Fill>
    </PlotCard>
  );
}

/** Least-squares amplitude of a Lorentzian A / (f^2 + fc^2) in log space, and the rms of the log10 residual. */
export function lorentzianFit(f: ArrayLike<number>, p: ArrayLike<number>, fc: number): { A: number; resid: number; fit: number[] } {
  let s = 0;
  let n = 0;
  for (let i = 0; i < f.length; i++) {
    if (p[i] > 0) {
      s += Math.log10(p[i] * (f[i] * f[i] + fc * fc));
      n++;
    }
  }
  const A = n ? 10 ** (s / n) : 0;
  const fit = Array.from({ length: f.length }, (_, i) => A / (f[i] * f[i] + fc * fc));
  let r = 0;
  for (let i = 0; i < f.length; i++) if (p[i] > 0 && fit[i] > 0) r += (Math.log10(p[i]) - Math.log10(fit[i])) ** 2;
  return { A, resid: Math.sqrt(r / Math.max(1, n)), fit };
}

/** The thermal standard deviation of a harmonic trap in micrometres: sqrt(kT / kappa) for a bead, sqrt(kT / (m omega^2)) for an atom. */
export function thermalSigmaUm(params: NonNullable<Selection['data']['manifest']['params']['dynamics']>, stiffness: { value: number; unit: string }): number {
  const kT = KB * params.temperature_k;
  if (params.particle === 'bead') return Math.sqrt(kT / (stiffness.value * 1e-12 / 1e-6)) * 1e6;
  const omega = 2 * Math.PI * stiffness.value;
  return (Math.sqrt(kT / ((params.mass_amu ?? 87) * AMU * omega * omega))) * 1e6;
}

export function SpectrumView({ sel }: { sel: Selection }) {
  const fmt = useFmt();
  const stateKey = useStateKey();
  const c = cardOf(sel);
  const tr = useTrajectory(sel);
  const params = sel.data.manifest.params.dynamics;
  const fit = useMemo(() => (tr ? lorentzianFit(tr.fHz, tr.p, tr.fcHz) : null), [tr]);
  const boltz = useMemo(() => {
    if (!tr || !params || !Number.isFinite(tr.stiffness.value)) return null;
    const x = Array.from(tr.xUm);
    const mean = x.reduce((a, v) => a + v, 0) / x.length;
    const varMeasured = x.reduce((a, v) => a + (v - mean) ** 2, 0) / x.length;
    const sigma = thermalSigmaUm(params, tr.stiffness);
    const lim = 4 * Math.max(sigma, Math.sqrt(varMeasured));
    const h = histogram(x, -lim, lim, 31);
    const w = (2 * lim) / 31;
    const expected = h.centres.map((u) => x.length * w * Math.exp(-(u * u) / (2 * sigma * sigma)) / (sigma * Math.sqrt(2 * Math.PI)));
    return { h, expected, sigma, ratio: varMeasured / (sigma * sigma) };
  }, [tr, params]);
  if (!tr || !params || !fit) {
    return (
      <PlotCard fill title={{ en: 'Power spectrum and Boltzmann check', es: 'Espectro de potencia y verificación de Boltzmann' }} {...c} dataKey={stateKey}>
        <Fill>
          <Unavailable reason={NO_DYNAMICS} />
        </Fill>
      </PlotCard>
    );
  }
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Power spectral density with its Lorentzian fit', es: 'Densidad espectral de potencia con su ajuste lorentziano' }}
        {...c}
        lane={tr.lane}
        dataKey={stateKey}
        note={{
          en: `Corner frequency ${fmt(tr.fcHz, { decimals: 1 })} Hz; ${params.particle === 'bead' ? 'stiffness' : 'radial frequency'} ${fmt(tr.stiffness.value, { decimals: 3 })} ${tr.stiffness.unit}. The fit is A / (f^2 + fc^2); residual ${fmt(fit.resid, { decimals: 2 })} decades rms.`,
          es: `Frecuencia de corte ${fmt(tr.fcHz, { decimals: 1 })} Hz; ${params.particle === 'bead' ? 'rigidez' : 'frecuencia radial'} ${fmt(tr.stiffness.value, { decimals: 3 })} ${tr.stiffness.unit}. El ajuste es A / (f^2 + fc^2); residuo ${fmt(fit.resid, { decimals: 2 })} décadas rms.`,
        }}
      >
        <Fill>
          <UPlotChart
            height="fill"
            title={{ en: 'Power spectral density, log-log', es: 'Densidad espectral de potencia, log-log' }}
            x={{ values: Array.from(tr.fHz), label: { en: 'Frequency', es: 'Frecuencia' }, unit: 'Hz', log: true }}
            y={{ label: { en: 'Power', es: 'Potencia' }, unit: 'um^2/Hz', log: true }}
            series={[
              { label: { en: 'Simulated', es: 'Simulado' }, values: Array.from(tr.p), color: '--color-accent', mode: 'points', size: 5 },
              { label: { en: 'Lorentzian fit', es: 'Ajuste lorentziano' }, values: fit.fit, color: '--color-warn' },
            ]}
            marks={[{ x: tr.fcHz, label: { en: 'fc', es: 'fc' } }]}
          />
        </Fill>
      </PlotCard>
      <PlotCard
        fill
        title={{ en: 'Position histogram against Boltzmann', es: 'Histograma de posiciones frente a Boltzmann' }}
        {...c}
        lane={tr.lane}
        dataKey={stateKey}
        note={
          boltz
            ? {
                en: `Equipartition: the measured variance is ${fmt(boltz.ratio, { decimals: 2 })} times the thermal value (kT over the stiffness; expected width ${fmt(boltz.sigma * 1e3, { decimals: 1 })} nm).`,
                es: `Equipartición: la varianza medida es ${fmt(boltz.ratio, { decimals: 2 })} veces la térmica (kT sobre la rigidez; ancho esperado ${fmt(boltz.sigma * 1e3, { decimals: 1 })} nm).`,
              }
            : undefined
        }
      >
        <Fill quiet>
          {boltz ? (
            <UPlotChart
              height="fill"
              title={{ en: 'Counts by x position, simulated and Boltzmann', es: 'Cuentas por posición x, simulado y Boltzmann' }}
              x={{ values: boltz.h.centres, label: { en: 'Displacement from the trap centre', es: 'Desplazamiento desde el centro de la trampa' }, unit: 'um', format: { decimals: 3 } }}
              y={{ label: { en: 'Samples', es: 'Muestras' }, format: { decimals: 0 } }}
              series={[
                { label: { en: 'Simulated', es: 'Simulado' }, values: boltz.h.counts, color: '--color-accent', dots: true },
                { label: { en: 'Boltzmann', es: 'Boltzmann' }, values: boltz.expected, color: '--color-warn', dash: [5, 4] },
              ]}
              marks={[{ x: 0, label: { en: 'centre', es: 'centro' } }]}
            />
          ) : (
            <Unavailable reason={{ en: 'The stiffness of this trap is not available, so the Boltzmann width cannot be computed.', es: 'La rigidez de esta trampa no está disponible, así que no se puede calcular el ancho de Boltzmann.' }} />
          )}
        </Fill>
      </PlotCard>
    </ViewsRow>
  );
}

export function RearrangementView({ sel }: { sel: Selection }) {
  const { t } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const c = cardOf(sel);
  const re = sel.data.trace.rearrangement;
  const [frame, setFrame] = useState(0);
  const n = re?.frames.length ?? 0;
  const ref = useRef(0);
  ref.current = frame;
  const viz = usePausedViz(
    (dt) => {
      const next = ref.current + Math.max(1, Math.round(dt / 120));
      if (next >= n - 1) {
        setFrame(n - 1);
        return false;
      }
      setFrame(next);
      return true;
    },
    { loop: false },
  );
  useEffect(() => {
    const off = () => viz.pause();
    window.addEventListener('blur', off);
    return () => window.removeEventListener('blur', off);
  }, [viz]);
  useEffect(() => setFrame(0), [sel.data.manifest.case_id]);
  if (!re || !n) {
    return (
      <PlotCard fill title={{ en: 'Rearrangement', es: 'Reordenamiento' }} {...c} lane="replay" dataKey={stateKey}>
        <Fill>
          <Unavailable reason={{ en: 'This case has no rearrangement sequence (only the rearrangement cases carry one). Pick a case of that category to see it.', es: 'Este caso no tiene secuencia de reordenamiento (solo los casos de reordenamiento la tienen). Elija un caso de esa categoría para verla.' }} />
        </Fill>
      </PlotCard>
    );
  }
  const f = re.frames[Math.min(frame, n - 1)];
  const occupied = new Set(f.occupied);
  const filling = re.filling;
  const filled = f.occupied.length;
  const target = sel.data.manifest.params.rearrangement?.target_ids.length ?? sel.traps.length;
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'Atoms and moves, frame by frame', es: 'Átomos y movimientos, cuadro a cuadro' }}
        {...c}
        lane="replay"
        dataKey={stateKey}
        note={{
          en: `Frame ${frame + 1} of ${n}, t = ${fmt(f.t_s * 1e3, { decimals: 1 })} ms: ${filled} of ${target} target sites occupied, ${f.moving.length} atoms in motion. Filled: an atom; hollow: a vacancy; dashed line: a move. Minimum transient survival ${fmt(re.min_transient, { decimals: 3 })}.`,
          es: `Cuadro ${frame + 1} de ${n}, t = ${fmt(f.t_s * 1e3, { decimals: 1 })} ms: ${filled} de ${target} sitios objetivo ocupados, ${f.moving.length} átomos en movimiento. Lleno: un átomo; hueco: una vacante; línea segmentada: un movimiento. Supervivencia transitoria mínima ${fmt(re.min_transient, { decimals: 3 })}.`,
        }}
      >
        <Fill>
          <div className="dh-stack">
          <div className="dh-scrub">
            <button type="button" className="btn" aria-pressed={viz.playing} onClick={() => (frame >= n - 1 ? (setFrame(0), viz.restart()) : viz.toggle())}>
              {viz.playing ? t('Pause', 'Pausa') : t('Play', 'Reproducir')}
            </button>
            <label htmlFor="dh-rearr-frame" className="sr-only">
              {t('Frame', 'Cuadro')}
            </label>
            <input
              id="dh-rearr-frame"
              type="range"
              min={0}
              max={n - 1}
              value={frame}
              onChange={(e) => {
                viz.pause();
                setFrame(Number(e.target.value));
              }}
            />
            <output>{`${frame + 1} / ${n}`}</output>
          </div>
          <div className="dh-fill">
            <Stage label={{ en: 'Rearrangement frame', es: 'Cuadro de reordenamiento' }}>
              {(size) => <RearrangeCanvas width={size.width} height={size.height} traps={sel.traps} occupied={occupied} moving={f.moving} selected={sel.trapId} label={t('Rearrangement frame', 'Cuadro de reordenamiento')} onStep={(d) => { viz.pause(); setFrame((k) => Math.max(0, Math.min(n - 1, k + d))); }} />}
            </Stage>
          </div>
          <table className="sr-only">
            <caption>{t('Occupied sites by frame', 'Sitios ocupados por cuadro')}</caption>
            <tbody>
              {re.frames.slice(0, 200).map((fr, i) => (
                <tr key={i}>
                  <th scope="row">{i + 1}</th>
                  <td>{fmt(fr.t_s * 1e3, { decimals: 1 })} ms</td>
                  <td>{fr.occupied.length}</td>
                  <td>{fr.moving.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </Fill>
      </PlotCard>
      <PlotCard fill title={{ en: 'Filling by round', es: 'Llenado por ronda' }} {...c} lane="replay" dataKey={stateKey}>
        <Fill quiet>
          <UPlotChart
            height="fill"
            title={{ en: 'Filling of the target by round', es: 'Llenado del objetivo por ronda' }}
            x={{ values: filling.map((_, i) => i), label: { en: 'Round', es: 'Ronda' }, format: { decimals: 0, grouping: false } }}
            y={{ label: { en: 'Filling', es: 'Llenado' }, format: { percent: true, decimals: 1 }, range: [0, 1] }}
            series={[{ label: { en: 'Filling', es: 'Llenado' }, values: filling, color: '--color-good', dots: true }]}
          />
        </Fill>
      </PlotCard>
    </ViewsRow>
  );
}

function RearrangeCanvas(props: {
  width: number;
  height: number;
  traps: Selection['traps'];
  occupied: Set<number>;
  moving: { from: number; to: number; x_um: number; y_um: number }[];
  selected: number | null;
  label: string;
  onStep: (d: number) => void;
}) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const { width, height, traps, occupied, moving, selected } = props;
  useEffect(() => {
    const cv = ref.current;
    const ctx = cv?.getContext('2d');
    if (!cv || !ctx) return;
    const dpr = window.devicePixelRatio || 1;
    cv.width = Math.round(width * dpr);
    cv.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const css = getComputedStyle(document.documentElement);
    const tok = (n: string) => css.getPropertyValue(n).trim() || '#888';
    const xs = traps.map((x) => x.x_um);
    const ys = traps.map((x) => x.y_um);
    const x0 = Math.min(...xs);
    const x1 = Math.max(...xs);
    const y0 = Math.min(...ys);
    const y1 = Math.max(...ys);
    const margin = 18;
    const span = Math.max(x1 - x0, y1 - y0, 1e-9);
    const s = Math.min((width - 2 * margin) / span, (height - 2 * margin) / span);
    const ox = (width - s * (x1 - x0)) / 2;
    const oy = (height - s * (y1 - y0)) / 2;
    const px = (x: number) => ox + (x - x0) * s;
    const py = (y: number) => oy + (y - y0) * s;
    const r = Math.max(3, Math.min(9, (s * (span / Math.sqrt(Math.max(traps.length, 1)))) * 0.28));
    const byId = new Map(traps.map((x) => [x.id, x]));
    ctx.lineWidth = 1.5;
    for (const m of moving) {
      const a = byId.get(m.from);
      const b = byId.get(m.to);
      if (!a || !b) continue;
      ctx.strokeStyle = tok('--color-warn');
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(px(a.x_um), py(a.y_um));
      ctx.lineTo(px(b.x_um), py(b.y_um));
      ctx.stroke();
    }
    ctx.setLineDash([]);
    for (const tr of traps) {
      ctx.beginPath();
      ctx.arc(px(tr.x_um), py(tr.y_um), r, 0, Math.PI * 2);
      if (occupied.has(tr.id)) {
        ctx.fillStyle = tok('--color-accent');
        ctx.fill();
      }
      ctx.strokeStyle = tr.id === selected ? tok('--color-fg') : tok('--color-fg-subtle');
      ctx.lineWidth = tr.id === selected ? 2.5 : 1;
      ctx.stroke();
    }
    for (const m of moving) {
      ctx.beginPath();
      ctx.arc(px(m.x_um), py(m.y_um), r * 0.8, 0, Math.PI * 2);
      ctx.fillStyle = tok('--color-warn');
      ctx.fill();
    }
  }, [width, height, traps, occupied, moving, selected]);
  return (
    <canvas
      ref={ref}
      tabIndex={0}
      role="img"
      aria-label={props.label}
      style={{ width, height, display: 'block' }}
      onKeyDown={(e) => {
        if (e.key === 'ArrowRight') (e.preventDefault(), props.onStep(1));
        else if (e.key === 'ArrowLeft') (e.preventDefault(), props.onStep(-1));
      }}
    />
  );
}

