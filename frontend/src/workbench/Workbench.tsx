// The App route (ADR-0016 s9, ADR-0071, ADR-0070): one CaseWorkbench for DinHot. The rail holds the case picker, the method (the
// variant: which algorithm made the hologram), the device, the live-run controls, the view controls, the trap editor, the
// aberration and particle controls and the live values, in sections of a rail that never scrolls; the instrument holds five
// groups of views of the computed hologram and its physics, and the context write-up (six peers, the shell's maximum). The
// replay lane is the committed trace; the live lane is the TypeScript engine (unit T1) re-run with the rail's values, and where it
// is absent the replay answers and every card says so. Focus mode (ADR-0070) is on for every case.
import {
  CaseWorkbench,
  ChipGroup,
  Equation,
  Knob,
  Readout,
  formatNumber,
  useShellLang,
  type CaseDef,
  type RailSection,
} from '@fasl-work/caos-app-shell';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { loadCase, loadIndex, useArtifact, type CaseData } from '../api/artifacts';
import type { Text, Trap } from '../lib/contract.types';
import { baselineName, cghApplies } from '../lib/ort';
import { ReadinessNote } from '../readiness/ReadinessNote';
import { caseAbsent } from '../readiness/readiness';
import { useReadiness } from '../readiness/useReadiness';
import { ConvergenceGroup } from './ConvergenceGroup';
import type { DeviceStage } from './decode';
import { DynamicsGroup } from './DynamicsGroup';
import { laneOf } from './engine';
import { FocalGroup } from './FocalGroup';
import { HologramGroup } from './HologramGroup';
import { isShaped, methodLabel, replayMaps, replayResult, trapsOf, UnavailableContext, ViewContext, type DeviceChoice, type Region, type Selection } from './model';
import { paramsFor, useEngine, useGpuProbe, useLiveRun, useSlots, type GpuProbe } from './run';
import { addTrap, deleteTrap, moveTrap } from './traps';
import { TrapsGroup } from './TrapsGroup';
import { ActionsContext, CASE_ROWS, LOADING, localizeDecimals, Pending, type Actions, type EditMode } from './ui';
import { coeffArray, J_MAX } from './zernike';
import './workbench.css';

interface Rail {
  caseId: string;
  device: DeviceChoice;
  iterations: number;
  backend: 'auto' | 'cpu' | 'gpu';
  dbFloor: number;
  stage: DeviceStage;
  sortBy: 'id' | 'deviation';
  bandPct: number;
  trapId: number | null;
  powerMw: number;
  seed: number;
  fbStep: number;
  zmode: number;
  corrected: boolean;
  plane: 'xz' | 'yz';
  volThreshold: number;
  overrides: Record<number, number>;
  traps: Trap[] | null;
  region: Region | null;
  mode: EditMode;
}

function railOf(data: CaseData): Rail {
  const p = data.manifest.params;
  return {
    caseId: data.manifest.case_id,
    device: p.device ? 'case' : 'ideal',
    iterations: p.budget.iterations,
    backend: 'auto',
    dbFloor: -40,
    stage: 'ideal',
    sortBy: 'id',
    bandPct: 5,
    trapId: p.dynamics?.trap_id ?? trapsOf(data.manifest, data.trace)[0]?.id ?? null,
    powerMw: p.dynamics?.power_mw ?? 0,
    seed: data.manifest.seed,
    fbStep: data.trace.feedback?.steps[0]?.step ?? 0,
    zmode: 4,
    corrected: false,
    plane: 'xz',
    volThreshold: 0.2,
    overrides: {},
    traps: null,
    region: null,
    mode: 'inspect',
  };
}

const sameJson = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);


/** The first clause of an engine message, for a rail line a few words wide; the full text stays in the title and the backend hint. */
function shortReason(reason: string): string {
  const head = reason.split(/[:(]/)[0].trim();
  return head.length > 48 ? `${head.slice(0, 45).trim()}...` : head;
}
const backendReason = (reason: string | null): string | undefined => reason ?? undefined;

/** One line in the rail: which backend computed the picture on screen, or what the browser offers when nothing has run yet. */
function backendLine(lang: 'en' | 'es', used: 'cpu' | 'gpu' | null, gpu: GpuProbe | null, fallback: string | null): string {
  const es = lang === 'es';
  const name = used === 'gpu' ? 'WebGPU' : 'CPU';
  if (used) {
    if (fallback) return es ? `Calculado con ${name}. WebGPU no disponible: ${shortReason(fallback)}.` : `Computed on ${name}. WebGPU unavailable: ${shortReason(fallback)}.`;
    return es ? `Calculado con ${name}.` : `Computed on ${name}.`;
  }
  if (!gpu) return es ? 'Consultando WebGPU.' : 'Asking the browser for WebGPU.';
  if (gpu.ok) return es ? 'WebGPU disponible; el cálculo corre en CPU salvo que lo elija.' : 'WebGPU is available; the run uses it when it can.';
  return es ? `WebGPU no disponible: ${shortReason(gpu.reason)}. Se usa CPU.` : `WebGPU unavailable: ${shortReason(gpu.reason)}. CPU is used.`;
}

export function Workbench() {
  const lang = useShellLang();
  const readiness = useReadiness();
  const engine = useEngine();
  const gpu = useGpuProbe(engine);
  const index = useArtifact((s) => loadIndex(s), []);
  const [caseId, setCaseId] = useState<string | null>(null);
  const selected = caseId ?? (index.state === 'ready' ? index.data.default_case : null);
  const entry = index.state === 'ready' ? index.data.cases.find((c) => c.case_id === selected) : undefined;
  const refused = entry?.status === 'refused';
  const loaded = useArtifact((s) => (selected && !refused ? loadCase(selected, s) : new Promise<CaseData>(() => undefined)), [selected, refused]);
  const [methodId, setMethodId] = useState<string | null>(null);
  const [rail, setRail] = useState<Rail | null>(null);
  const [editError, setEditError] = useState<Text | null>(null);

  const data = loaded.state === 'ready' && loaded.data.manifest.case_id === selected ? loaded.data : null;
  useEffect(() => {
    if (data) {
      setRail(railOf(data));
      setMethodId(data.manifest.params.reference_method);
      setEditError(null);
    }
  }, [data]);
  const slots = useSlots(!!data && cghApplies(data.manifest.params.setup, trapsOf(data.manifest, data.trace), null).ok);
  const r = rail && data && rail.caseId === data.manifest.case_id ? rail : null;
  const method = data && methodId && data.manifest.params.methods.includes(methodId) ? methodId : (data?.manifest.params.reference_method ?? '');
  const patch = useCallback((p: Partial<Rail>) => setRail((cur) => (cur ? { ...cur, ...p } : cur)), []);

  const params = data?.manifest.params ?? null;
  const baseTraps = useMemo(() => (data ? trapsOf(data.manifest, data.trace) : []), [data]);
  const traps = r?.traps ?? baseTraps;
  const edited = !!r?.traps;
  const halfField = data?.trace.grid.half_field_um ?? 0;
  const shaped = data ? isShaped(data.manifest) : false;

  // The aberration as edited: the case's own, or none when corrected, then the reader's overrides.
  const coeffs = useMemo(() => {
    const c = r?.corrected ? new Array<number>(J_MAX).fill(0) : coeffArray(params?.aberration?.noll);
    for (const [j, v] of Object.entries(r?.overrides ?? {})) c[Number(j) - 1] = v;
    return c;
  }, [params, r?.corrected, r?.overrides]);
  const aberrationEdited = !!r && ((r.corrected && !!params?.aberration) || Object.keys(r.overrides).length > 0);
  const noll = useMemo(() => {
    const o: Record<string, number> = {};
    for (let j = 2; j <= J_MAX; j++) if (coeffs[j - 1] !== 0) o[String(j)] = coeffs[j - 1];
    return o;
  }, [coeffs]);

  const live = useLiveRun({
    data,
    methodId: method,
    device: r?.device ?? 'ideal',
    iterations: r?.iterations ?? 0,
    backend: r?.backend ?? 'auto',
    traps,
    edited,
    aberration: aberrationEdited ? noll : null,
    aberrationEdited,
    engine,
    slots,
  });

  const replay = useMemo(() => (data ? replayMaps(data.trace) : null), [data]);
  const replayRes = useMemo(() => (data ? replayResult(data.trace, method) : null), [data, method]);
  const liveMethods = useMemo(() => (engine?.available ? engine.client.liveMethods() : []), [engine]);

  const sel: Selection | null = useMemo(() => {
    if (!data || !r || !params || !replay) return null;
    return {
      data,
      methodId: method,
      device: r.device,
      deviceModel: r.device === 'case' ? params.device : null,
      traps,
      edited,
      trapId: r.trapId,
      region: r.region,
      maps: live.maps ?? replay,
      result: live.result ?? replayRes,
      iteration: r.iterations,
      dbFloor: r.dbFloor,
      aberration: coeffs,
      aberrationEdited,
      powerMw: r.powerMw,
      seed: r.seed,
      stage: r.stage,
      sortBy: r.sortBy,
      bandPct: r.bandPct,
      fbStep: r.fbStep,
      zmode: r.zmode,
      corrected: r.corrected,
      coeffKey: coeffs.join(','),
      plane: r.plane,
      volThreshold: r.volThreshold,
      slot: live.slot,
      running: live.running,
      progress: live.progress,
      liveError: live.error,
      cancelled: live.cancelled,
      runParams: paramsFor(data, { device: r.device, iterations: r.iterations, traps, edited, aberration: aberrationEdited ? noll : null, aberrationEdited }),
      engineAvailable: !!engine?.available,
      liveMethods,
    };
  }, [data, r, params, replay, replayRes, live, method, traps, edited, coeffs, aberrationEdited, noll, engine, liveMethods]);

  const actions: Actions = useMemo(
    () => ({
      mode: r?.mode ?? 'inspect',
      selectTrap: (id) => patch({ trapId: id }),
      setRegion: (region) => patch({ region }),
      addTrap: (x, y) => {
        const e = addTrap(traps, x, y, halfField);
        if ('error' in e) setEditError(e.error);
        else (setEditError(null), patch({ traps: e.traps, trapId: e.traps[e.traps.length - 1].id }));
      },
      moveTrap: (id, x, y) => {
        const e = moveTrap(traps, id, x, y, halfField);
        if ('error' in e) setEditError(e.error);
        else (setEditError(null), patch({ traps: e.traps, trapId: id }));
      },
      deleteTrap: (id) => {
        const e = deleteTrap(traps, id);
        if ('error' in e) setEditError(e.error);
        else (setEditError(null), patch({ traps: e.traps, trapId: r?.trapId === id ? (e.traps[0]?.id ?? null) : (r?.trapId ?? null) }));
      },
      editError,
      setIteration: (k) => patch({ iterations: k }),
      selectMode: (j) => patch({ zmode: j }),
      zmode: r?.zmode ?? 4,
      setCorrected: (on) => patch({ corrected: on, overrides: {} }),
      setCoeff: (j, v) => patch({ overrides: { ...(r?.overrides ?? {}), [j]: v } }),
      setPlane: (plane) => patch({ plane }),
      setVolThreshold: (volThreshold) => patch({ volThreshold }),
    }),
    [r?.mode, r?.zmode, r?.trapId, r?.overrides, traps, halfField, editError, patch],
  );

  // A case the readiness document lists as absent, or the index lists as refused, stays in the selector, marked, so its reason can be read.
  const absent = lang === 'es' ? ' (aún no disponible)' : ' (not available yet)';
  const refusedMark = lang === 'es' ? ' (rechazado)' : ' (refused)';
  const cases: CaseDef[] =
    index.state === 'ready'
      ? index.data.cases.map((c) => ({
          id: c.case_id,
          name: c.title[lang] + (c.status === 'refused' ? refusedMark : caseAbsent(readiness ?? null, c.case_id, c.path ?? '') ? absent : ''),
          category: c.category[lang],
        }))
      : [];
  const unavailable: Text | null =
    index.state === 'unavailable' ? index.reason : refused && entry?.reason ? entry.reason : loaded.state === 'unavailable' ? loaded.reason : null;

  const moved = !!(data && r && (edited || aberrationEdited || r.device !== (params?.device ? 'case' : 'ideal') || r.iterations !== params?.budget.iterations));
  const reset = () => data && (setRail(railOf(data)), setEditError(null));

  const metrics = sel?.result?.metrics ?? null;
  const lane = sel?.maps?.lane ?? 'replay';
  const prov = data?.manifest.real_or_synthetic ?? 'synthetic';

  const rails: RailSection[] = [];
  if (unavailable && !data) {
    rails.push({ id: 'unavailable', label: { en: 'Case', es: 'Caso' }, content: <p className="caos-pending" data-state="unavailable">{localizeDecimals(unavailable[lang], lang)}</p> });
  } else if (r && sel && data && params) {
    const n = traps.length;
    rails.push({
      id: 'run',
      label: { en: 'Run', es: 'Motor' },
      content: (
        <>
          {params.device ? (
            <ChipGroup
              id="device"
              label={{ en: 'SLM device', es: 'Dispositivo SLM' }}
              value={r.device}
              onChange={(v) => patch({ device: v as DeviceChoice })}
              options={[
                { id: 'ideal', label: { en: 'Ideal', es: 'Ideal' }, hint: { en: 'A perfect SLM: any phase, no crosstalk.', es: 'Un SLM perfecto: cualquier fase, sin diafonía.' } },
                { id: 'case', label: { en: 'Case device', es: 'Dispositivo del caso' }, hint: { en: 'Quantization, response curve, fill factor and crosstalk of this case.', es: 'Cuantización, curva de respuesta, factor de llenado y diafonía de este caso.' } },
              ]}
            />
          ) : (
            <p className="caos-plot-note">{lang === 'es' ? 'Este caso usa un SLM ideal (sin modelo del dispositivo).' : 'This case uses an ideal SLM (no device model).'}</p>
          )}
          <Knob
            id="iterations"
            label={{ en: 'Iterations', es: 'Iteraciones' }}
            hint={{ en: 'The budget of a live run; on the replay lane it is the iteration the convergence view reads.', es: 'El presupuesto de una corrida en vivo; en la reproducción es la iteración que lee la vista de convergencia.' }}
            value={r.iterations}
            min={1}
            max={Math.max(params.budget.iterations, sel.result?.history[sel.result.history.length - 1]?.iteration ?? 0, 10)}
            step={1}
            unit={{ en: 'iterations', es: 'iteraciones' }}
            format={{ decimals: 0 }}
            onChange={(v) => patch({ iterations: Math.round(v) })}
          />
          {engine?.available ? (
            <ChipGroup
              id="backend"
              label={{ en: 'Backend', es: 'Motor de cálculo' }}
              value={r.backend}
              onChange={(v) => patch({ backend: v as Rail['backend'] })}
              options={[
                { id: 'auto', label: { en: 'Auto', es: 'Auto' }, hint: { en: 'WebGPU when the browser offers it, else CPU.', es: 'WebGPU cuando el navegador lo ofrece, si no CPU.' } },
                { id: 'cpu', label: { en: 'CPU', es: 'CPU' } },
                { id: 'gpu', label: { en: 'WebGPU', es: 'WebGPU' }, hint: gpu ? (gpu.ok ? { en: `Adapter: ${gpu.adapter || 'unnamed'}.`, es: `Adaptador: ${gpu.adapter || 'sin nombre'}.` } : { en: `Not available here: ${gpu.reason}.`, es: `No disponible aquí: ${gpu.reason}.` }) : undefined },
              ]}
            />
          ) : (
            <p className="caos-plot-note">{lang === 'es' ? 'Motor en vivo: no está en esta versión; las vistas se reproducen de la generación.' : 'Live engine: not on this build; the views replay the bake.'}</p>
          )}
          {engine?.available && (live.running ? (
            // While a run is out the line gives way to the button that stops it, so the rail keeps its height.
            <button type="button" className="btn" onClick={live.cancel} data-cancel-run="" data-state="loading">
              {lang === 'es' ? 'Cancelar la corrida' : 'Cancel the run'}
            </button>
          ) : (
            <p className="caos-plot-note" data-backend={sel.maps?.backend ?? 'none'} title={backendReason(sel.maps?.fallbackReason ?? (gpu && !gpu.ok ? gpu.reason : null))}>
              {backendLine(lang, sel.maps?.lane === 'live' ? sel.maps.backend : null, gpu, sel.maps?.fallbackReason ?? null)}
            </p>
          ))}
        </>
      ),
    });
    rails.push({
      id: 'view',
      label: { en: 'View', es: 'Vista' },
      content: (
        <>
          {params.device && (
            <ChipGroup
              id="stage"
              label={{ en: 'Mask stage', es: 'Etapa de la máscara' }}
              value={r.stage}
              onChange={(v) => patch({ stage: v as DeviceStage })}
              options={[
                { id: 'ideal', label: { en: 'Ideal', es: 'Ideal' } },
                { id: 'quantized', label: { en: 'Quantized', es: 'Cuantizada' }, disabled: !params.device },
                { id: 'crosstalk', label: { en: 'Crosstalk', es: 'Diafonía' }, disabled: !params.device?.crosstalk },
              ]}
            />
          )}
          <Knob
            id="db-floor"
            label={{ en: 'Colour floor', es: 'Piso del color' }}
            hint={{ en: 'The lowest intensity the focal map shows, in dB against the mean trap. The bake stores down to its own floor.', es: 'La menor intensidad que muestra el mapa focal, en dB respecto de la trampa media. La generación guarda hasta su propio piso.' }}
            value={r.dbFloor}
            min={-60}
            max={-10}
            step={1}
            unit="dB"
            format={{ decimals: 0 }}
            onChange={(v) => patch({ dbFloor: v })}
          />
          <Knob
            id="band"
            label={{ en: 'Uniformity band', es: 'Banda de uniformidad' }}
            hint={{ en: 'A trap within this share of the mean intensity counts as uniform.', es: 'Una trampa dentro de esta fracción de la intensidad media cuenta como uniforme.' }}
            value={r.bandPct}
            min={1}
            max={25}
            step={1}
            unit="%"
            format={{ decimals: 0 }}
            onChange={(v) => patch({ bandPct: v })}
          />
          {params.dynamics && (
            <>
              <Knob
                id="power"
                label={{ en: 'Trap power', es: 'Potencia de la trampa' }}
                hint={{ en: 'The optical power in the simulated trap; the depth of every trap scales with it.', es: 'La potencia óptica en la trampa simulada; la profundidad de todas las trampas escala con ella.' }}
                value={r.powerMw}
                min={Math.max(0.01, params.dynamics.power_mw / 10)}
                max={params.dynamics.power_mw * 4}
                step={Math.max(0.01, params.dynamics.power_mw / 100)}
                unit="mW"
                format={{ decimals: 2 }}
                onChange={(v) => patch({ powerMw: v })}
              />
              <Knob
                id="seed"
                label={{ en: 'Seed', es: 'Semilla' }}
                hint={{ en: 'The random seed of the particle simulation; the same seed repeats the same trajectory.', es: 'La semilla aleatoria de la simulación de la partícula; la misma semilla repite la misma trayectoria.' }}
                value={r.seed % 1000}
                min={0}
                max={999}
                step={1}
                unit={{ en: 'seed', es: 'semilla' }}
                format={{ decimals: 0 }}
                onChange={(v) => patch({ seed: Math.round(v) })}
              />
            </>
          )}
        </>
      ),
    });
    rails.push({
      id: 'edit',
      label: { en: 'Edit', es: 'Editar' },
      content: (
        <>
          {shaped ? (
            <p className="caos-plot-note">{lang === 'es' ? 'Este caso apunta a un potencial con forma, no a una lista de trampas: el editor no aplica.' : 'This case targets a shaped potential, not a list of traps: the editor does not apply.'}</p>
          ) : (
            <ChipGroup
              id="edit-mode"
              label={{ en: `Trap editor: ${n} traps${edited ? ' (edited)' : ''}, field ±${formatNumber(halfField, 'en', { decimals: 1 })} um`, es: `Editor: ${n} trampas${edited ? ' (editadas)' : ''}, campo ±${formatNumber(halfField, 'es', { decimals: 1 })} um` }}
              value={r.mode}
              onChange={(v) => (setEditError(null), patch({ mode: v as EditMode }))}
              options={[
                { id: 'inspect', label: { en: 'Select', es: 'Elegir' }, hint: { en: 'Click a trap to select it; drag a box to select a region.', es: 'Pulse una trampa para elegirla; arrastre un recuadro para elegir una región.' } },
                { id: 'add', label: { en: 'Add', es: 'Añadir' }, hint: { en: 'Click the focal map to add a trap on the focal plane.', es: 'Pulse el mapa focal para agregar una trampa en el plano focal.' } },
                { id: 'move', label: { en: 'Move', es: 'Mover' }, hint: { en: 'Drag a trap on the focal map.', es: 'Arrastre una trampa en el mapa focal.' } },
                { id: 'delete', label: { en: 'Delete', es: 'Borrar' }, hint: { en: 'Click a trap to remove it.', es: 'Pulse una trampa para quitarla.' } },
              ]}
            />
          )}
          {n > 0 && (
            <Knob
              id="trap"
              label={{ en: 'Selected trap', es: 'Trampa' }}
              hint={{ en: 'The trap the profiles, the axial cut and the 3D view follow; clicking a trap on the map sets it too.', es: 'La trampa que siguen los perfiles, el corte axial y la vista 3D; pulsar una trampa en el mapa también la fija.' }}
              value={Math.max(0, traps.findIndex((t) => t.id === r.trapId)) + 1}
              min={1}
              max={Math.max(1, n)}
              step={1}
              unit={{ en: `of ${n}`, es: `de ${n}` }}
              format={{ decimals: 0 }}
              disabled={n < 2}
              onChange={(v) => patch({ trapId: traps[Math.round(v) - 1]?.id ?? null })}
            />
          )}
          {data.trace.feedback && (
            <Knob
              id="fb-step"
              label={{ en: 'Feedback step', es: 'Paso de realimentación' }}
              hint={{ en: 'The step of the camera loop the feedback view marks.', es: 'El paso del lazo de cámara que marca la vista de realimentación.' }}
              value={r.fbStep}
              min={data.trace.feedback.steps[0].step}
              max={data.trace.feedback.steps[data.trace.feedback.steps.length - 1].step}
              step={1}
              unit={{ en: 'step', es: 'paso' }}
              format={{ decimals: 0 }}
              onChange={(v) => patch({ fbStep: Math.round(v) })}
            />
          )}
        </>
      ),
    });
    rails.push({
      id: 'values',
      label: { en: 'Stats', es: 'Cifras' },
      content: (
        <>
          {index.state === 'error' && <p role="alert">{index.error}</p>}
          {loaded.state === 'error' && <p role="alert">{loaded.error}</p>}
          <Readout
            title={{ en: 'Hologram quality', es: 'Calidad del holograma' }}
            lane={sel.result?.lane ?? lane}
            provenance={prov}
            items={[
              { label: { en: 'Efficiency', es: 'Eficiencia' }, value: metrics?.efficiency ?? null, unitless: true, format: { percent: true, decimals: 1 }, better: 'higher', good: 0.8, bad: 0.4 },
              { label: { en: 'Uniformity', es: 'Uniformidad' }, value: metrics?.uniformity ?? null, unitless: true, format: { decimals: 3 }, better: 'higher', good: 0.95, bad: 0.8 },
              { label: { en: 'Relative spread', es: 'Dispersión relativa' }, value: metrics?.relStdPct ?? null, unit: '%', format: { decimals: 2 }, better: 'lower', good: 5, bad: 20 },
              { label: { en: 'Zero order', es: 'Orden cero' }, value: metrics?.zeroOrder ?? null, unitless: true, format: { percent: true, decimals: 1 } },
              { label: { en: 'Ghost light', es: 'Luz fantasma' }, value: metrics?.ghost ?? null, unitless: true, format: { percent: true, decimals: 1 } },
            ]}
          />
        </>
      ),
    });
  }

  const cghFit = data && slots.cgh?.answered === 'model' ? cghApplies(data.manifest.params.setup, traps, slots.cgh.card) : null;
  const variantOf = (id: string) => {
    const lane1 = laneOf(id, liveMethods);
    const slotNote =
      id === 'M17'
        ? slots.cgh?.answered === 'model'
          ? cghFit && !cghFit.ok
            ? { en: `${cghFit.reason.en} The baseline answers.`, es: `${cghFit.reason.es} Responde la línea base.` }
            : { en: 'The released cgh-net answers in your browser.', es: 'El cgh-net publicado responde en su navegador.' }
          : { en: `No released cgh-net: ${baselineName('cgh-net').en} answers.`, es: `No hay cgh-net publicado: responde ${baselineName('cgh-net').es}.` }
        : id === 'B3'
          ? slots.warm?.answered === 'model'
            ? { en: 'The released warm start feeds M07 its trap phases.', es: 'El arranque aprendido publicado entrega a M07 las fases de las trampas.' }
            : { en: `No released warm start: ${baselineName('warmstart-model').en}.`, es: `No hay arranque aprendido publicado: ${baselineName('warmstart-model').es}.` }
          : null;
    return {
      id,
      // The chip carries the id so twelve methods fit in a few rows (ADR-0071 rule 6); the note under the group names the active one in full.
      label: { en: id, es: id },
      lane: lane1,
      note: {
        en: slotNote ? `${methodLabel(id).en}. ${slotNote.en}` : methodLabel(id).en,
        es: slotNote ? `${methodLabel(id).es}. ${slotNote.es}` : methodLabel(id).es,
      },
    };
  };

  const hud = sel
    ? [
        { label: { en: 'Method', es: 'Método' }, value: sel.methodId },
        { label: { en: 'Efficiency', es: 'Eficiencia' }, value: metrics ? formatNumber(metrics.efficiency, lang, { percent: true, decimals: 1 }) : '-' },
        { label: { en: 'Uniformity', es: 'Uniformidad' }, value: metrics ? formatNumber(metrics.uniformity, lang, { decimals: 3 }) : '-' },
        { label: { en: 'Lane', es: 'Vía' }, value: lane === 'live' ? (lang === 'es' ? 'en vivo' : 'live') : lang === 'es' ? 'reproducción' : 'replay' },
      ]
    : undefined;

  return (
    <UnavailableContext.Provider value={unavailable}>
      <ViewContext.Provider value={sel}>
        <ActionsContext.Provider value={actions}>
          <CaseWorkbench
            caseId={selected ?? ''}
            source={data?.manifest.real_or_synthetic}
            cases={{
              cases,
              selectedId: selected ?? '',
              onSelect: (id) => {
                setCaseId(id);
                setMethodId(null);
              },
              layout: 'select',
              deepLink: true,
              modifiedFromId: moved ? selected : null,
              onResetToCanonical: reset,
            }}
            controls={
              r
                ? {
                    device: r.device,
                    iterations: r.iterations,
                    backend: r.backend,
                    dbFloor: r.dbFloor,
                    stage: r.stage,
                    sortBy: r.sortBy,
                    bandPct: r.bandPct,
                    trapId: r.trapId,
                    powerMw: r.powerMw,
                    seed: r.seed,
                    fbStep: r.fbStep,
                    zmode: r.zmode,
                    corrected: r.corrected,
                    plane: r.plane,
                    volThreshold: r.volThreshold,
                    coeffs: coeffs.join(','),
                    mode: r.mode,
                    traps: sameJson(traps, baseTraps) ? 'case' : traps.map((t) => `${t.id}:${t.x_um}:${t.y_um}`).join(','),
                  }
                : {}
            }
            variants={{
              // M17 is offered only where the three-plane cgh-net applies (128 x 128 SLM, padding 1, traps on its planes)
              variants: (params?.methods ?? []).filter((id) => id !== 'M17' || !data || cghApplies(data.manifest.params.setup, traps, slots.cgh?.card ?? null).ok).map(variantOf),
              activeId: method,
              onSelect: setMethodId,
              title: { en: 'Method', es: 'Método' },
            }}
            rail={rails.length ? rails : <p className="caos-pending" data-state="loading">…</p>}
            focus={{ hud }}
            groups={[
              { id: 'hologram', label: { en: 'Hologram', es: 'Holograma' }, lane, provenance: prov, content: <HologramGroup /> },
              { id: 'focal', label: { en: 'Focal plane', es: 'Plano focal' }, lane, provenance: prov, content: <FocalGroup /> },
              { id: 'traps', label: { en: 'Traps', es: 'Trampas' }, lane: sel?.result?.lane ?? lane, provenance: prov, content: <TrapsGroup /> },
              { id: 'convergence', label: { en: 'Convergence', es: 'Convergencia' }, lane: sel?.result?.lane ?? 'replay', provenance: prov, content: <ConvergenceGroup /> },
              { id: 'dynamics', label: { en: 'Dynamics', es: 'Dinámica' }, lane: 'replay', provenance: prov, content: <DynamicsGroup /> },
            ]}
            context={{ content: <ContextView sel={sel} /> }}
          />
        </ActionsContext.Provider>
      </ViewContext.Provider>
    </UnavailableContext.Provider>
  );
}

function ContextView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  if (!sel) {
    return (
      <>
        <ReadinessNote ids={CASE_ROWS} />
        <Pending label={LOADING} />
      </>
    );
  }
  const m = sel.data.manifest;
  const p = m.params;
  const s = p.setup;
  const n = (v: number, d = 2) => formatNumber(v, lang, { decimals: d });
  return (
    <>
      <ReadinessNote ids={[...CASE_ROWS, 'cgh-net', 'warmstart-model']} />
      <h2>{m.title[lang]}</h2>
      {/* the anchor first: its link sits at the top of the panel, clear of the Focus HUD at every size (CAOS_MANAGE shell-known-defects entry 50) */}
      <p>
        {t('Anchor', 'Ancla')}: {m.anchor.source[lang]}
        {m.anchor.url && (
          <>
            {' '}
            (<a href={m.anchor.url}>{m.anchor.url}</a>)
          </>
        )}
      </p>
      <p>
        {t('Category', 'Categoría')}: {m.category[lang]}. {t('What a reader should see', 'Lo que el lector debería ver')}: {m.expected_band[lang]}
      </p>
      <table className="caos-table">
        <tbody>
          <tr><td>{t('Wavelength', 'Longitud de onda')}</td><td>{n(s.wavelength_nm, 0)} nm</td></tr>
          <tr><td>{t('Focal length', 'Distancia focal')}</td><td>{n(s.focal_mm, 1)} mm</td></tr>
          <tr><td>{t('Numerical aperture', 'Apertura numérica')}</td><td>{n(s.na, 2)}</td></tr>
          <tr><td>{t('SLM', 'SLM')}</td><td>{s.n_pix} x {s.n_pix} {t('pixels at', 'píxeles con paso de')} {n(s.pitch_um, 1)} um</td></tr>
          <tr><td>{t('Focal bin', 'Bin focal')}</td><td>{n(sel.data.trace.grid.bin_um, 3)} um</td></tr>
          <tr><td>{t('Unaliased half-field', 'Medio campo sin solapamiento')}</td><td>{n(sel.data.trace.grid.half_field_um, 1)} um</td></tr>
          <tr><td>{t('Methods', 'Métodos')}</td><td>{p.methods.join(', ')}</td></tr>
          <tr><td>{t('Reference method', 'Método de referencia')}</td><td>{p.reference_method}</td></tr>
        </tbody>
      </table>
      <h3>{t('The model', 'El modelo')}</h3>
      <Equation
        tex="E(x', y') \propto \mathcal{F}\{ A(x, y)\, e^{i\varphi(x, y)} \}, \qquad \Delta x' = \frac{\lambda f}{N_{pad}\, p}, \qquad x'_{max} = \frac{\lambda f}{2p}"
        caption={t(
          'The scalar Fraunhofer field in the focal plane is the Fourier transform of the beam amplitude A times the SLM phase; the focal bin is the wavelength lambda times the focal length f over the padded SLM side (padding N_pad times N pixels of pitch p), and the unaliased half-field is lambda f over twice the pitch. A trap at or beyond it is refused.',
          'El campo escalar de Fraunhofer en el plano focal es la transformada de Fourier de la amplitud A del haz por la fase del SLM; el bin focal es la longitud de onda lambda por la distancia focal f sobre el lado del SLM con relleno (relleno N_pad veces N píxeles de paso p) y el medio campo sin solapamiento es lambda f sobre el doble del paso. Una trampa en ese límite o más allá se rechaza.',
        )}
      />
      <h3>{t('How to read the views', 'Cómo leer las vistas')}</h3>
      <p>
        {t(
          'Hologram shows the phase the SLM displays, what the device adds and the wavefront of the aberration. Focal plane shows where the light goes, with the trap editor on the map. Traps shows how uniform the traps are, their depth and the power budget. Convergence shows the metrics by iteration, the benchmark front and the camera loop. Dynamics shows a bead or an atom in the map and the rearrangement of an atom array. The method in the rail picks the algorithm; a method the browser engine can run is computed live, any other is replayed from the bake and says so.',
          'Holograma muestra la fase que presenta el SLM, lo que añade el dispositivo y el frente de onda de la aberración. Plano focal muestra a dónde va la luz, con el editor de trampas sobre el mapa. Trampas muestra qué tan uniformes son, su profundidad y el balance de potencia. Convergencia muestra las métricas por iteración, el frente del benchmark y el lazo de cámara. Dinámica muestra una microesfera o un átomo en el mapa y el reordenamiento de una matriz de átomos. El método del panel elige el algoritmo; el que el motor del navegador puede correr se calcula en vivo y cualquier otro se reproduce de la generación y lo dice.',
        )}
      </p>
      <p>
        {t('Engine', 'Motor')}: {m.engine.model}, {m.engine.package} {m.engine.version}. {t('Data', 'Datos')}: {m.real_or_synthetic === 'synthetic' ? t('synthetic', 'sintéticos') : t('real', 'reales')}.{' '}
        {t('Learned models', 'Modelos aprendidos')}: cgh-net {m.models['cgh-net'] ?? '-'}, warmstart-model {m.models['warmstart-model'] ?? '-'}.
      </p>
    </>
  );
}
