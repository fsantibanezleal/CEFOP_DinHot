// The live lane of the workbench: the engine client, the two learned slots and one hook that turns the rail's values into a run.
// A run starts 200 ms after the last change of a control (scheduler.ts), is cancelled by the next change or by the Cancel button,
// reports its progress, and replaces the replay maps only when it finishes; until then, and wherever the engine cannot run the
// method, the committed trace answers and the cards say replay. A failure never blanks a view: it is kept as a message and the
// replay lane stays on screen.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { CaseData } from '../api/artifacts';
import { cghApplies, encodeCghTarget, loadSlot, predictCghPhase, predictWarmstart, type SlotAnswer, type SlotId } from '../lib/ort';
import type { ParamsRecord, Trap } from '../lib/contract.types';
import { entryFor, loadReadiness, modelAnswers } from '../readiness/readiness';
import { getEngine, NotLive, type Engine, type Progress } from './engine';
import { liveMaps, type DeviceChoice, type MapSet, type MethodResult } from './model';
import { LiveScheduler } from './scheduler';

export function useEngine(): Engine | null {
  const [engine, setEngine] = useState<Engine | null>(null);
  useEffect(() => {
    let live = true;
    void getEngine().then((e) => live && setEngine(e));
    return () => {
      live = false;
    };
  }, []);
  return engine;
}

export interface Slots {
  cgh: SlotAnswer | null;
  warm: SlotAnswer | null;
}

/**
 * Which model answers a slot. The readiness document decides first (catalog: Missing-data states): a slot it lists as training with the
 * baseline, provided by a provider or missing has no released model, and the site does not ask for a card it knows is not there (a 404
 * is a console error). Only a slot the document calls available, stale or training with a released model, or one it does not list, is
 * looked for: its card and graph are fetched and checked.
 */
async function answerOf(slot: SlotId): Promise<SlotAnswer> {
  const doc = await loadReadiness();
  const row = entryFor(doc, slot);
  if (row && modelAnswers(doc, slot) === 'baseline') {
    return { slot, answered: 'baseline', card: null, reason: row.reason ?? { en: 'No released model.', es: 'No hay un modelo publicado.' } };
  }
  return loadSlot(slot);
}

/** Which model answers each learned slot; null while the cards are being looked for. */
export function useSlots(): Slots {
  const [slots, setSlots] = useState<Slots>({ cgh: null, warm: null });
  useEffect(() => {
    let live = true;
    void Promise.all([answerOf('cgh-net'), answerOf('warmstart-model')]).then(([cgh, warm]) => live && setSlots({ cgh, warm }));
    return () => {
      live = false;
    };
  }, []);
  return slots;
}

export interface LiveInputs {
  data: CaseData | null;
  methodId: string;
  device: DeviceChoice;
  iterations: number;
  backend: 'auto' | 'cpu' | 'gpu';
  traps: Trap[];
  edited: boolean;
  aberration: Record<string, number> | null;
  aberrationEdited: boolean;
  engine: Engine | null;
  slots: Slots;
}

export interface LiveState {
  maps: MapSet | null;
  result: MethodResult | null;
  running: boolean;
  progress: Progress | null;
  error: string | null;
  /** The reader cancelled the run in flight: the replay lane answers until a control changes. */
  cancelled: boolean;
  /** The learned slot this method used and which model answered, for the label. */
  slot: { slot: 'cgh-net' | 'warmstart-model'; answered: 'model' | 'baseline' } | null;
}

/** The floor of a live focal map in dB: the display clips above it, so moving the floor knob never re-runs the engine. */
export const LIVE_DB_FLOOR = -60;

const IDLE: LiveState = { maps: null, result: null, running: false, progress: null, error: null, cancelled: false, slot: null };

export interface RailRun {
  device: DeviceChoice;
  iterations: number;
  traps: Trap[];
  edited: boolean;
  aberration: Record<string, number> | null;
  aberrationEdited: boolean;
}

/**
 * The params record the engine runs: the case's own, with the rail's device, iterations, trap list and aberration. Shared by the run, the
 * cuts and the particle, so a cut is always of the hologram the cards show, for the setup the reader chose.
 */
export function paramsFor(data: CaseData, o: RailRun): ParamsRecord {
  const m = data.manifest;
  return {
    case_id: m.case_id,
    ...m.params,
    target: o.edited && m.params.target.kind === 'traps' ? { kind: 'traps', traps: o.traps } : m.params.target,
    device: o.device === 'ideal' ? null : m.params.device,
    aberration: o.aberrationEdited ? { noll: o.aberration ?? {} } : m.params.aberration,
    budget: { ...m.params.budget, iterations: o.iterations },
  };
}

export function useLiveRun(inp: LiveInputs): LiveState & { cancel: () => void } {
  const [state, setState] = useState<LiveState>(IDLE);
  const { data, methodId, device, iterations, backend, traps, edited, aberration, aberrationEdited, engine, slots } = inp;
  const liveOk = !!engine?.available && engine.client.liveMethods().includes(methodId);
  const cghByModel = methodId === 'M17' && slots.cgh?.answered === 'model' && !!data && cghApplies(data.manifest.params.setup, slots.cgh.card);
  // The slot a method uses, for the label: cgh-net serves M17, the warm start serves M07.
  const slot = methodId === 'M17' ? slots.cgh : methodId === 'M07' ? slots.warm : null;
  const slotLabel = slot ? { slot: slot.slot, answered: slot.answered } : null;

  const sched = useRef<LiveScheduler | null>(null);
  useEffect(() => {
    const s = new LiveScheduler({ cancel: () => engine?.client.cancel() });
    sched.current = s;
    return () => {
      s.dispose();
      sched.current = null;
    };
  }, [engine]);

  const key = useMemo(
    () => JSON.stringify([data?.manifest.case_id, methodId, device, iterations, backend, traps, aberration, liveOk, cghByModel, slot?.answered ?? null]),
    [data, methodId, device, iterations, backend, traps, aberration, liveOk, cghByModel, slot],
  );

  useEffect(() => {
    const s = sched.current;
    if (!s) return;
    if (!data || (!liveOk && !cghByModel)) {
      s.cancel();
      setState({ ...IDLE, slot: slotLabel });
      return;
    }
    // Running from the moment a control changes: what is on screen is the previous result, labelled with its own method, until the new one lands.
    setState((cur) => ({ ...cur, running: true, progress: null, error: null, cancelled: false }));
    s.submit(async (isCurrent) => {
      try {
        const m = data.manifest;
        const base = paramsFor(data, { device, iterations, traps, edited, aberration, aberrationEdited });
        if (cghByModel && slots.cgh?.card) {
          const trace = data.trace;
          const { input } = encodeCghTarget(traps, trace.grid.bin_um, slots.cgh.card.grid ?? 128);
          const phase = await predictCghPhase(input, slots.cgh.card.grid ?? 128);
          if (!isCurrent()) return;
          const wrapped = Float32Array.from(phase, (p) => ((p % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI));
          setState({
            maps: { lane: 'live', method: 'M17', nPix: slots.cgh.card.grid ?? 128, pad: trace.grid.pad, binUm: trace.grid.bin_um, halfFieldUm: trace.grid.half_field_um, phase: wrapped, displayed: null, focal: null, axial: null, shape: null, backend: 'cpu', fallbackReason: null, timeMs: null },
            result: null,
            running: false,
            progress: null,
            error: null,
            cancelled: false,
            slot: { slot: 'cgh-net', answered: 'model' },
          });
          return;
        }
        if (!engine) return;
        // M17's baseline is GS (M04) at 30 iterations; the warm start feeds M07 its trap phases when the released model answers.
        const method = methodId === 'M17' ? 'M04' : methodId;
        const run = methodId === 'M17' ? 30 : iterations;
        let trapPhases: Float64Array | undefined;
        if (methodId === 'M07' && slots.warm?.answered === 'model') {
          trapPhases = await predictWarmstart(traps, data.trace.grid.half_field_um, m.params.setup);
        }
        const res = await engine.client.run(
          { params: base, method, options: { iterations: run, device, backend, traps: edited ? traps : undefined, trapPhases } },
          (p) => isCurrent() && setState((cur) => ({ ...cur, progress: p })),
        );
        if (!isCurrent()) return;
        const { maps, result } = liveMaps(res, traps, LIVE_DB_FLOOR);
        setState({ maps, result: { ...result, method: methodId }, running: false, progress: null, error: null, cancelled: false, slot: slotLabel });
      } catch (e) {
        if (!isCurrent()) return;
        // NotLive: the engine cannot do this one; the replay lane answers and says so. Anything else is shown as the error.
        setState({ ...IDLE, error: e instanceof NotLive ? null : String(e), slot: slotLabel });
      }
    });
    // `key` names every input the run reads
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, engine]);

  const cancel = useCallback(() => {
    sched.current?.cancel();
    setState((cur) => ({ ...IDLE, cancelled: true, slot: cur.slot }));
  }, []);

  return { ...state, cancel };
}

export type GpuProbe = { ok: true; adapter: string } | { ok: false; reason: string };

/** What the browser's WebGPU offers the engine worker, asked once the engine is up; null while the probe is out. */
export function useGpuProbe(engine: Engine | null): GpuProbe | null {
  const [probe, setProbe] = useState<GpuProbe | null>(null);
  useEffect(() => {
    if (!engine) return;
    if (!engine.available) {
      setProbe({ ok: false, reason: 'the live engine is not on this build' });
      return;
    }
    let on = true;
    engine.client.gpu().then(
      (p) => on && setProbe(p),
      (e) => on && setProbe({ ok: false, reason: String(e) }),
    );
    return () => {
      on = false;
    };
  }, [engine]);
  return probe;
}
