// V5, the method at work (ADR-0082, SDD visualization catalog row V5): the relative spread and the efficiency of the selected method
// iteration by iteration, with the iteration at which the phase is frozen marked, coupled to the focal plane and to the per-trap
// intensities at the iteration the reader scrubs. The scrub is the shell's shared cursor (`useLinkedView`), so the story and the App move
// the same value. The focal plane at iteration k is the engine's own run in the browser with the method's budget set to k, started 200 ms
// after the last scrub (LiveScheduler) and kept by its key: the bake records the spread and the efficiency per iteration but not the map.
// A method the engine does not port, or a build without the engine, shows the recorded history and says the map is the final one.
import { PlotCard, Stage, formatNumber, pick, useLinkedCursor, useLinkedView, useShellLang, type SceneCalloutDef } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import '../pages/story.css';
import type { EngineClient, RunResult } from '../engine/holo/client';
import { ReadinessNote } from '../readiness/ReadinessNote';
import { INTENSITY_LUT } from './colormaps';
import { CalloutHeader } from './CalloutHeader';
import { Heatmap, type HeatMark } from './HeatmapStage';
import { cardOf } from './HologramGroup';
import { historyAt, liveMaps, methodLabel, methodName, type HistoryPoint, type MapSet, type MethodResult, type Selection } from './model';
import { LIVE_DB_FLOOR } from './run';
import { LiveScheduler } from './scheduler';
import { umToPixel } from './traps';
import { CASE_ROWS, Pending, Unavailable, useStateKey } from './ui';

type Lang = 'en' | 'es';

/**
 * The iteration at which a method freezes its trap phases and only the weights go on changing. M07 is the weighted GS of Kim et al. 2019 with
 * the phase fixed after `nFix` iterations, 12 by default in the engine (`engine/holo/methods/baseline.ts`, `o.nFix ?? 12`; a test keeps the two
 * equal). The other methods of the ladder never freeze the phase.
 */
export const PHASE_FREEZE: Readonly<Record<string, number>> = { M07: 12 };
export const freezeIteration = (methodId: string): number | null => PHASE_FREEZE[methodId] ?? null;

/** The history point the cursor stands on: the last one at or before it, the last of the run when the cursor is unset or past it. */
export function pointAt(history: readonly HistoryPoint[], cursor: number | null): HistoryPoint | null {
  if (!history.length) return null;
  if (cursor === null) return history[history.length - 1];
  return historyAt(history, Math.max(history[0].iteration, cursor));
}

/** The engine request for the focal plane at iteration k: the case's record at the rail's device, the method's budget set to k. */
export function runRequestAt(sel: Selection, k: number) {
  return { params: sel.runParams, method: sel.methodId, options: { iterations: k, device: sel.device, backend: 'cpu' as const } };
}

export interface FocalAt {
  k: number;
  maps: MapSet;
  result: MethodResult;
  /** Wall-clock milliseconds the run took in this browser. */
  ms: number;
}

/** The focal plane of the method after k iterations, from the engine client given. Pure of React: the test drives it with a recorded client. */
export async function focalAtIteration(client: Pick<EngineClient, 'run'>, sel: Selection, k: number, now: () => number = () => performance.now()): Promise<FocalAt> {
  const t0 = now();
  const res: RunResult = await client.run(runRequestAt(sel, k));
  const ms = now() - t0;
  const { maps, result } = liveMaps(res, sel.traps, LIVE_DB_FLOOR);
  return { k, maps, result: { ...result, method: sel.methodId }, ms };
}

const modules = import.meta.glob<{ createEngineClient: () => EngineClient }>('../engine/holo/client.ts');
let client: Promise<EngineClient | null> | null = null;
/** The view's own engine client (its own worker): a scrub never cancels the run of the rail, and the rail never cancels a scrub. */
function ownClient(): Promise<EngineClient | null> {
  client ??= (async () => {
    const load = Object.values(modules)[0];
    if (!load) return null;
    try {
      return (await load()).createEngineClient();
    } catch {
      return null;
    }
  })();
  return client;
}

const CACHE = new Map<string, FocalAt>();
const CACHE_MAX = 64;
const keyOf = (sel: Selection, k: number) => `${sel.data.manifest.case_id}|${sel.methodId}|${sel.device}|${sel.edited ? sel.traps.map((t) => `${t.id},${t.x_um},${t.y_um}`).join(';') : 'case'}|${k}`;

/** Whether the live focal run is still to come: the page is not at rest until the engine has answered, and says so (a `loading` state the gate and a reader can see). */
export const focalPending = (focal: FocalState): boolean => focal.state === 'loading';

export type FocalState =
  | { state: 'unavailable'; reason: { en: string; es: string } }
  | { state: 'loading'; at: FocalAt | null }
  | { state: 'ready'; at: FocalAt }
  | { state: 'error'; error: string; at: FocalAt | null };

/** The focal plane at iteration k, debounced by the live scheduler, cancelled by the next scrub, kept by key. */
export function useFocalAtIteration(sel: Selection, k: number | null): FocalState {
  const [state, setState] = useState<FocalState>({ state: 'loading', at: null });
  const sched = useRef<LiveScheduler | null>(null);
  const lastAt = useRef<FocalAt | null>(null);
  useEffect(() => {
    const s = new LiveScheduler({ cancel: () => void ownClient().then((c) => c?.cancel()) });
    sched.current = s;
    return () => {
      s.dispose();
      sched.current = null;
    };
  }, []);
  const key = k === null ? null : keyOf(sel, k);
  useEffect(() => {
    const s = sched.current;
    if (!s || k === null || key === null) return;
    const hit = CACHE.get(key);
    if (hit) {
      s.cancel();
      lastAt.current = hit;
      setState({ state: 'ready', at: hit });
      return;
    }
    setState({ state: 'loading', at: lastAt.current });
    s.submit(async (isCurrent) => {
      try {
        const c = await ownClient();
        if (!isCurrent()) return;
        if (!c) {
          setState({ state: 'unavailable', reason: { en: 'the live engine is not on this build', es: 'el motor en vivo no está en esta versión' } });
          return;
        }
        if (!c.liveMethods().includes(sel.methodId)) {
          setState({ state: 'unavailable', reason: { en: `${methodLabel(sel.methodId).en} is not run in the browser`, es: `${methodLabel(sel.methodId).es} no se corre en el navegador` } });
          return;
        }
        const at = await focalAtIteration(c, sel, k);
        if (!isCurrent()) return;
        if (CACHE.size >= CACHE_MAX) CACHE.delete(CACHE.keys().next().value as string);
        CACHE.set(key, at);
        lastAt.current = at;
        setState({ state: 'ready', at });
      } catch (e) {
        if (!isCurrent()) return;
        setState({ state: 'error', error: String(e), at: lastAt.current });
      }
    });
    // `key` names every input of the run
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return state;
}

const f = (v: number | null | undefined, lang: Lang, d: number) => formatNumber(v ?? null, lang, { decimals: d });
/** A spread printed with two significant figures whatever its size (26.8, 0.014): the story spans four decades. */
export function spreadText(v: number, lang: Lang): string {
  if (!Number.isFinite(v)) return '-';
  const d = v >= 10 ? 1 : v >= 1 ? 2 : v <= 0 ? 2 : Math.min(4, Math.max(2, Math.ceil(-Math.log10(v)) + 1));
  return formatNumber(v, lang, { decimals: d });
}

/** The three callouts of the view at iteration k, each with its source field: spread, efficiency, and the phase-freeze iteration. */
export function methodCallouts(sel: Selection, k: number, lang: Lang): SceneCalloutDef[] {
  const h = sel.result?.history ?? [];
  const p = pointAt(h, k);
  const m = sel.methodId;
  const freeze = freezeIteration(m);
  const name = methodName(m);
  const spreadState = !p ? 'inactive' : p.relStdPct > 20 ? 'alarm' : p.relStdPct > 5 ? 'warning' : 'normal';
  return [
    {
      id: 'spread',
      eyebrow: { en: 'SPREAD', es: 'DISPERSIÓN' },
      value: p ? spreadText(p.relStdPct, lang) : '-',
      unit: '%',
      state: spreadState,
      anchor: { x: 0.3, y: 0.38 },
      source: { en: `${name.en}, iteration ${p?.iteration ?? '-'}: trace history[].rel_std_pct`, es: `${name.es}, iteración ${p?.iteration ?? '-'}: trace history[].rel_std_pct` },
    },
    {
      id: 'efficiency',
      eyebrow: { en: 'EFFICIENCY', es: 'EFICIENCIA' },
      value: p ? f(p.efficiency * 100, lang, 1) : '-',
      unit: '%',
      state: !p ? 'inactive' : p.efficiency >= 0.8 ? 'normal' : p.efficiency >= 0.4 ? 'warning' : 'alarm',
      anchor: { x: 0.3, y: 0.7 },
      source: { en: `${name.en}, iteration ${p?.iteration ?? '-'}: trace history[].efficiency`, es: `${name.es}, iteración ${p?.iteration ?? '-'}: trace history[].efficiency` },
    },
    freeze === null
      ? {
          id: 'freeze',
          eyebrow: { en: 'ITERATION', es: 'ITERACIÓN' },
          value: String(k),
          unit: { en: 'iterations, never frozen', es: 'iteraciones, nunca fijada' },
          state: 'selected',
          anchor: { x: 0.8, y: 0.3 },
          source: { en: `${name.en} updates the phase at every iteration`, es: `${name.es} actualiza la fase en cada iteración` },
        }
      : {
          id: 'freeze',
          eyebrow: { en: 'FREEZE AT', es: 'FIJA EN' },
          value: String(freeze),
          unit: { en: 'iteration', es: 'iteración' },
          state: k >= freeze ? 'selected' : 'normal',
          anchor: { x: 0.8, y: 0.3 },
          source: { en: `${name.en}: engine default n_fix (methods/baseline.ts)`, es: `${name.es}: n_fix por defecto del motor (methods/baseline.ts)` },
        },
  ];
}

const BAND_TONE = 'warn' as const;

/** The per-trap intensities and the focal map at iteration k, as the engine returned them, or the final ones of the bake. */
function pickMaps(sel: Selection, focal: FocalState): { maps: MapSet | null; trapI: readonly number[] | null; lane: 'live' | 'replay'; k: number | null } {
  const at = focal.state === 'ready' ? focal.at : focal.state === 'loading' || focal.state === 'error' ? focal.at : null;
  if (at) return { maps: at.maps, trapI: at.result.trapI, lane: 'live', k: at.k };
  return { maps: sel.maps, trapI: sel.result?.trapI ?? null, lane: 'replay', k: null };
}

export function MethodAtWorkView({ sel }: { sel: Selection }) {
  const lang = useShellLang() as Lang;
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const stateKey = useStateKey();
  const cursor = useLinkedView((s) => s.cursor);
  const scrub = useLinkedView((s) => s.scrub);
  const selectedId = useLinkedView((s) => s.selectedId);
  const select = useLinkedView((s) => s.select);
  const marker = useLinkedCursor().markerProps;
  const history = sel.result?.history ?? [];
  const point = pointAt(history, cursor);
  const k = point?.iteration ?? null;
  const focal = useFocalAtIteration(sel, k);
  const view = pickMaps(sel, focal);
  const c = cardOf(sel);
  const motionOk = typeof matchMedia === 'undefined' || !matchMedia('(prefers-reduced-motion: reduce)').matches;
  const [playing, setPlaying] = useState(false);
  const lastIteration = history.length ? history[history.length - 1].iteration : 0;
  // Play steps the cursor by one iteration once the focal plane of the current one is drawn (the engine takes 0.1 to 0.8 s on C02, so a fixed
  // pace would cancel its own runs); it stops at the end and on the pause control (WCAG 2.2.2: a run of more than five seconds can be paused).
  const settled = focal.state !== 'loading';
  useEffect(() => {
    if (!playing || !motionOk || !settled || k === null) return;
    const id = setTimeout(() => {
      if (k + 1 > lastIteration) setPlaying(false);
      else scrub(k + 1);
    }, 350);
    return () => clearTimeout(id);
  }, [playing, motionOk, settled, k, lastIteration, scrub]);
  const onPick = useCallback((i: number) => history[i] && scrub(history[i].iteration), [history, scrub]);

  const marks = useMemo(() => {
    const out: { x: number; label: { en: string; es: string } }[] = [];
    const fz = freezeIteration(sel.methodId);
    if (fz !== null && history.length && fz >= history[0].iteration && fz <= lastIteration) out.push({ x: fz, label: { en: 'phase frozen', es: 'fase fijada' } });
    if (k !== null) out.push({ x: k, label: { en: 'scrubbed', es: 'elegida' } });
    return out;
  }, [sel.methodId, history, lastIteration, k]);

  if (!history.length) {
    return (
      <PlotCard fill title={{ en: 'The method at work', es: 'El método trabajando' }} {...c} dataKey={stateKey}>
        <Unavailable reason={{ en: `The bake holds no iteration history for ${methodLabel(sel.methodId).en} on this case, so there is no iteration to scrub.`, es: `La generación no guarda historial de iteraciones de ${methodLabel(sel.methodId).es} en este caso, así que no hay iteración que recorrer.` }} />
      </PlotCard>
    );
  }
  const focalMap = view.maps?.focal ?? null;
  const size = focalMap?.size ?? 0;
  const bin = focalMap?.binUm ?? 1;
  // an array of dozens of traps would be one green block at this size: the selected trap is ringed, every trap of a small array
  const marksOnMap: HeatMark[] = focalMap
    ? sel.traps.filter((tr) => sel.traps.length <= 36 || String(tr.id) === selectedId).map((tr) => {
        const [col, row] = umToPixel(tr.x_um, tr.y_um, size, bin);
        const on = String(tr.id) === selectedId;
        return { id: tr.id, col, row, kind: 'ring', tone: on ? 'accent' : 'good', selected: on, label: on ? String(tr.id) : undefined };
      })
    : [];
  const trapI = view.trapI;
  const band = sel.bandPct / 100;
  const logSpread = history.every((p) => p.relStdPct > 0);
  // what the focal plane is, by the state of the live run: its own line under the controls, two lines high in every state, so that the
  // answer of the engine (a longer or a shorter sentence) never moves the charts above it (a change of height rebuilds a chart and
  // clears its crosshair)
  const focalLine = {
    en: `${
      focal.state === 'ready' ? `The focal plane and the trap intensities are the engine's run of ${focal.at.k} iterations in your browser (${f(focal.at.ms, 'en', 0)} ms).` : focal.state === 'unavailable' ? `The focal plane is the final one of the bake: ${focal.reason.en}.` : focal.state === 'error' ? `The engine failed (${focal.error}); the last map is kept.` : 'The engine is computing the focal plane at this iteration.'
    }`,
    es: `${
      focal.state === 'ready' ? `El plano focal y las intensidades de las trampas son la corrida del motor de ${focal.at.k} iteraciones en su navegador (${f(focal.at.ms, 'es', 0)} ms).` : focal.state === 'unavailable' ? `El plano focal es el final de la generación: ${focal.reason.es}.` : focal.state === 'error' ? `Falló el motor (${focal.error}); se conserva el último mapa.` : 'El motor está calculando el plano focal en esta iteración.'
    }`,
  };
  const note = {
    en: `${methodLabel(sel.methodId).en}, iteration ${k} of ${lastIteration}: spread ${spreadText(point!.relStdPct, 'en')} %, efficiency ${f(point!.efficiency * 100, 'en', 1)} %. Click a chart or move the slider to choose the iteration.`,
    es: `${methodLabel(sel.methodId).es}, iteración ${k} de ${lastIteration}: dispersión ${spreadText(point!.relStdPct, 'es')} %, eficiencia ${f(point!.efficiency * 100, 'es', 1)} %. Pulse un gráfico o mueva el control para elegir la iteración.`,
  };
  return (
    <PlotCard fill title={{ en: `${methodLabel(sel.methodId).en} at work`, es: `${methodLabel(sel.methodId).es} trabajando` }} {...c} lane={view.lane} dataKey={stateKey} note={note}>
      <ReadinessNote ids={CASE_ROWS} />
      <div className="dh-mw-box" data-caos-flow="" data-focal-state={focal.state} data-iteration={k ?? ''} {...marker}>
        <Stage label={{ en: 'Spread and efficiency by iteration, with the focal plane and the trap intensities at the chosen iteration', es: 'Dispersión y eficiencia por iteración, con el plano focal y las intensidades de las trampas en la iteración elegida' }}>
          {({ width, height }) =>
            width < 120 || height < 120 ? null : (
              <div className="dh-scene dh-mw">
                <CalloutHeader items={methodCallouts(sel, k!, lang)} />
                <div className="dh-mw-grid">
                  <div className="dh-mw-charts">
                    <div className="dh-mw-cell">
                      <UPlotChart
                        height="fill"
                        title={{ en: 'Relative spread by iteration', es: 'Dispersión relativa por iteración' }}
                        x={{ values: history.map((p) => p.iteration), label: { en: 'Iteration', es: 'Iteración' }, format: { decimals: 0, grouping: false } }}
                        y={{ label: { en: 'Relative spread', es: 'Dispersión relativa' }, unit: '%', format: { decimals: 3 }, log: logSpread }}
                        series={[{ label: { en: 'Relative spread', es: 'Dispersión relativa' }, values: history.map((p) => p.relStdPct), color: '--color-warn', dots: true }]}
                        marks={marks}
                        onPick={onPick}
                        readout={(i) => t(`iteration ${history[i].iteration}: spread ${spreadText(history[i].relStdPct, lang)} %`, `iteración ${history[i].iteration}: dispersión ${spreadText(history[i].relStdPct, lang)} %`)}
                      />
                    </div>
                    <div className="dh-mw-cell">
                      <UPlotChart
                        height="fill"
                        title={{ en: 'Efficiency by iteration', es: 'Eficiencia por iteración' }}
                        x={{ values: history.map((p) => p.iteration), label: { en: 'Iteration', es: 'Iteración' }, format: { decimals: 0, grouping: false } }}
                        y={{ label: { en: 'Efficiency', es: 'Eficiencia' }, format: { decimals: 3 } }}
                        series={[{ label: { en: 'Efficiency', es: 'Eficiencia' }, values: history.map((p) => p.efficiency), color: '--color-accent', dots: true }]}
                        marks={marks}
                        onPick={onPick}
                        readout={(i) => t(`iteration ${history[i].iteration}: efficiency ${f(history[i].efficiency, lang, 3)}`, `iteración ${history[i].iteration}: eficiencia ${f(history[i].efficiency, lang, 3)}`)}
                      />
                    </div>
                  </div>
                  <div className="dh-mw-maps">
                    <div className="dh-mw-cell" data-lane={view.lane}>
                      {focalMap ? (
                        <Heatmap
                          label={{ en: `Focal plane after ${view.k ?? 'the final'} iterations, intensity in dB`, es: `Plano focal tras ${view.k ?? 'las'} iteraciones, intensidad en dB` }}
                          data={focalMap.db}
                          cols={size}
                          rows={size}
                          lut={INTENSITY_LUT}
                          range={[sel.dbFloor, 0]}
                          marks={marksOnMap}
                          onPick={(col, row) => {
                            let best: number | null = null;
                            let bd = 4;
                            for (const tr of sel.traps) {
                              const [tc, tr2] = umToPixel(tr.x_um, tr.y_um, size, bin);
                              const d = Math.hypot(tc - col, tr2 - row);
                              if (d <= bd) {
                                bd = d;
                                best = tr.id;
                              }
                            }
                            select(best === null ? null : String(best), 'scene');
                          }}
                          describe={(col, row, v) => `bin (${col}, ${row}): ${f(v, lang, 1)} dB`}
                          summary={t(`Focal plane ${size} by ${size} after ${view.k ?? 'the final'} iterations of ${methodName(sel.methodId).en}, ${sel.traps.length} traps marked.`, `Plano focal ${size} por ${size} tras ${view.k ?? 'las'} iteraciones de ${methodName(sel.methodId).es}, ${sel.traps.length} trampas marcadas.`)}
                        />
                      ) : (
                        focal.state === 'loading' ? (
                          <Pending label={{ en: 'Computing the focal plane', es: 'Calculando el plano focal' }} />
                        ) : (
                          <Unavailable
                            reason={
                              focal.state === 'unavailable'
                                ? { en: `There is no focal plane to draw for this method on this case: ${focal.reason.en}, and the bake holds none for it.`, es: `No hay plano focal que dibujar para este método en este caso: ${focal.reason.es}, y la generación no guarda ninguno.` }
                                : { en: 'The engine failed and the bake holds no focal plane for this method.', es: 'Falló el motor y la generación no guarda un plano focal para este método.' }
                            }
                          />
                        )
                      )}
                    </div>
                    <div className="dh-mw-cell">
                      {trapI && trapI.length ? (
                        <UPlotChart
                          height="fill"
                          title={{ en: `Intensity of each trap over the mean${view.k ? `, iteration ${view.k}` : ', final'}`, es: `Intensidad de cada trampa sobre la media${view.k ? `, iteración ${view.k}` : ', final'}` }}
                          x={{ values: sel.traps.map((tr) => tr.id), label: { en: 'Trap', es: 'Trampa' }, format: { decimals: 0, grouping: false } }}
                          y={{ label: { en: 'Intensity over the mean', es: 'Intensidad sobre la media' }, format: { decimals: 2 } }}
                          series={[{ label: { en: 'Trap intensity', es: 'Intensidad de la trampa' }, values: [...trapI], color: '--color-accent', mode: 'points', size: 4 }]}
                          yMarks={[
                            { y: 1 + band, label: { en: 'band', es: 'banda' }, tone: BAND_TONE },
                            { y: 1 - band, tone: BAND_TONE },
                          ]}
                          onPick={(i) => select(String(sel.traps[i]?.id ?? ''), 'scene')}
                          readout={(i) => t(`trap ${sel.traps[i]?.id}: ${f(trapI[i], lang, 3)} of the mean`, `trampa ${sel.traps[i]?.id}: ${f(trapI[i], lang, 3)} de la media`)}
                        />
                      ) : (
                        <Unavailable reason={{ en: 'This run has no per-trap intensities.', es: 'Esta corrida no tiene intensidades por trampa.' }} />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )
          }
        </Stage>
      </div>
      <div className="dh-row" data-caos-plot-control="">
        <label className="dh-mw-scrub">
          {t('Iteration', 'Iteración')} <strong>{k}</strong>
          <input
            type="range"
            min={history[0].iteration}
            max={lastIteration}
            step={1}
            value={k ?? lastIteration}
            data-linked-cursor=""
            aria-label={t('Scrub the iteration of the method', 'Recorrer la iteración del método')}
            onChange={(e) => {
              setPlaying(false);
              scrub(Number(e.target.value));
            }}
          />
        </label>
        {motionOk ? (
          <button type="button" className="btn" aria-pressed={playing} onClick={() => (!playing && (k ?? 0) >= lastIteration ? (scrub(history[0].iteration), setPlaying(true)) : setPlaying((v) => !v))}>
            {playing ? t('Pause', 'Pausa') : t('Play the iterations', 'Reproducir las iteraciones')}
          </button>
        ) : (
          <span className="caos-plot-note">{t('Reduced motion: the iterations do not play; scrub them with the slider.', 'Movimiento reducido: las iteraciones no se reproducen; recórralas con el control.')}</span>
        )}
        <p className="caos-plot-note dh-mw-focal" role="status" data-state={focalPending(focal) ? 'loading' : undefined}>
          {pick(focalLine, lang)}
        </p>
      </div>
    </PlotCard>
  );
}
