// Pieces every group shares: the actions the views call on the workbench's state, the line that says which lane and which model
// produced what a card shows, and the container that gives a drawing the height its note leaves.
import { formatNumber, pick, useShellLang, useWorkbenchState, type BiText, type FormatOptions } from '@fasl-work/caos-app-shell';
import { createContext, useContext, type ReactNode } from 'react';
import { ReadinessNote } from '../readiness/ReadinessNote';
import type { Text } from '../lib/contract.types';
import { methodLabel, UnavailableContext, useSelection, type Selection } from './model';

/** The rows every replay view of the case consumes; the model slots add theirs where a view shows them. */
export const CASE_ROWS = ['case-index', 'case-manifest', 'trace'];

export type EditMode = 'inspect' | 'add' | 'move' | 'delete';

export interface Actions {
  mode: EditMode;
  selectTrap: (id: number | null) => void;
  setRegion: (r: Selection['region']) => void;
  addTrap: (xUm: number, yUm: number) => void;
  moveTrap: (id: number, xUm: number, yUm: number) => void;
  deleteTrap: (id: number) => void;
  /** The last refused edit, in both languages; null when the last edit was accepted. */
  editError: Text | null;
  setIteration: (k: number) => void;
  selectMode: (j: number) => void;
  zmode: number;
  setCorrected: (on: boolean) => void;
  setCoeff: (j: number, value: number) => void;
  setPlane: (plane: 'xz' | 'yz') => void;
  setVolThreshold: (fraction: number) => void;
}
export const ActionsContext = createContext<Actions | null>(null);
export function useActions(): Actions {
  const a = useContext(ActionsContext);
  if (!a) throw new Error('ActionsContext is missing: a view was rendered outside the workbench');
  return a;
}

export function useT() {
  const lang = useShellLang();
  return { lang, t: (en: string, es: string) => (lang === 'es' ? es : en), pick: (b: BiText) => pick(b, lang) };
}

export function useFmt() {
  const lang = useShellLang();
  return (v: number | null | undefined, o: FormatOptions = {}) => formatNumber(v ?? null, lang, o);
}

/**
 * A reason written by the pipeline (the index, the readiness document) reaches the screen as it was written: in Spanish its decimals carry a
 * point. Spanish writes a comma (G11), so a decimal of the text is rewritten here; integers, versions with two dots and words are left alone.
 */
export function localizeDecimals(text: string, lang: 'en' | 'es'): string {
  return lang === 'es' ? text.replace(/(?<![\d.])(\d+)\.(\d+)(?![\d.])/g, '$1,$2') : text;
}

export function Pending({ label }: { label: BiText }) {
  const lang = useShellLang();
  const reason = useContext(UnavailableContext);
  // A case the index lists as refused, or the readiness lists as absent, says so with the reason: never an empty chart, never a spinner.
  if (reason) {
    return (
      <p className="caos-pending" data-state="unavailable">
        {localizeDecimals(reason[lang], lang)}
      </p>
    );
  }
  return (
    <p className="caos-pending" data-state="loading">
      {pick(label, lang)}
    </p>
  );
}

export const LOADING: BiText = { en: 'Loading the case artifacts', es: 'Cargando los artefactos del caso' };

/** A card's body whose content is unavailable for a stated reason (not a spinner, not an empty chart). */
export function Unavailable({ reason }: { reason: BiText }) {
  const lang = useShellLang();
  return (
    <p className="caos-pending" data-state="unavailable">
      {pick(reason, lang)}
    </p>
  );
}

/**
 * The lines above a drawing: the readiness note, then what produced it (lane, method, the model that answered) and anything the
 * reader must know before trusting it (edits held back for want of the engine, a run in progress, an engine error). The drawing
 * takes the height that is left.
 */
/** `quiet` leaves out the readiness note: the first card of a row carries it, the others do not repeat it. */
export function Fill({ children, rows = CASE_ROWS, mapsOnly = false, quiet = false }: { children: ReactNode; rows?: string[]; mapsOnly?: boolean; quiet?: boolean }) {
  const sel = useSelection();
  return (
    <div className="dh-stack">
      {!quiet && <ReadinessNote ids={rows} />}
      {sel && !quiet && <Provenance sel={sel} mapsOnly={mapsOnly} />}
      <div className="dh-fill">{children}</div>
    </div>
  );
}

/** One line: replayed from the bake or computed live; which method's hologram; the learned model that answered; held edits; progress; errors. */
export function Provenance({ sel, mapsOnly }: { sel: Selection; mapsOnly: boolean }) {
  const { lang, t } = useT();
  const fmt = useFmt();
  const lane = sel.maps?.lane ?? 'replay';
  const parts: string[] = [];
  if (sel.maps) {
    parts.push(
      lane === 'live'
        ? t(`Live: ${sel.maps.method} computed in your browser${sel.maps.backend ? ` (${sel.maps.backend === 'gpu' ? 'WebGPU' : 'CPU'}${sel.maps.timeMs !== null ? `, ${fmt(sel.maps.timeMs, { decimals: 0 })} ms` : ''})` : ''}.`, `En vivo: ${sel.maps.method} calculado en su navegador${sel.maps.backend ? ` (${sel.maps.backend === 'gpu' ? 'WebGPU' : 'CPU'}${sel.maps.timeMs !== null ? `, ${fmt(sel.maps.timeMs, { decimals: 0 })} ms` : ''})` : ''}.`)
        : sel.methodId !== sel.maps.method
          ? t(
              `Replayed from the bake: ${sel.methodId} is not run live, so its metrics and per-trap intensities are its own but the maps drawn are those of the reference method ${sel.maps.method}.`,
              `Reproducido de la generación: ${sel.methodId} no corre en vivo, así que sus métricas e intensidades por trampa son las suyas pero los mapas dibujados son los del método de referencia ${sel.maps.method}.`,
            )
          : t(`Replayed from the bake: the maps are those of the reference method ${sel.maps.method}.`, `Reproducido de la generación: los mapas son los del método de referencia ${sel.maps.method}.`),
    );
    // The WebGPU fallback reason is stated once, in the rail's backend line, so a card keeps its height for the drawing.
  }
  if (!mapsOnly && sel.result && sel.result.method !== sel.maps?.method && sel.result.lane === 'replay' && lane === 'live') {
    parts.push(t(`Metrics: ${methodLabel(sel.result.method).en}, replayed.`, `Métricas: ${methodLabel(sel.result.method).es}, reproducidas.`));
  }
  if (sel.edited && !sel.engineAvailable) {
    parts.push(t('Your trap edits are held: the live engine is not on this build, so the result is the baked case.', 'Sus ediciones de trampas quedan guardadas: el motor en vivo no está en esta versión, así que el resultado es el caso precalculado.'));
  } else if (sel.edited && !sel.liveMethods.includes(sel.methodId)) {
    parts.push(t(`Your trap edits are held: ${sel.methodId} is replayed from the bake, not run live.`, `Sus ediciones de trampas quedan guardadas: ${sel.methodId} se reproduce de la generación y no corre en vivo.`));
  }
  if (sel.running) {
    parts.push(
      sel.progress
        ? t(`Running: iteration ${sel.progress.iteration}, uniformity ${fmt(sel.progress.uniformity, { decimals: 3 })}. Change any control to cancel.`, `Calculando: iteración ${sel.progress.iteration}, uniformidad ${fmt(sel.progress.uniformity, { decimals: 3 })}. Cambie cualquier control para cancelar.`)
        : t('Running. Change any control to cancel.', 'Calculando. Cambie cualquier control para cancelar.'),
    );
  }
  if (sel.cancelled) parts.push(t('The live run was cancelled; the replay is shown. Change a control to run again.', 'Se canceló la corrida en vivo; se muestra la reproducción. Cambie un control para correr de nuevo.'));
  if (sel.liveError) parts.push(t(`The live run failed: ${sel.liveError}`, `La corrida en vivo falló: ${sel.liveError}`));
  if (!parts.length) return null;
  return (
    <p className="caos-plot-note dh-lane" role="status" data-lane={lane} data-running={sel.running ? 'true' : 'false'} data-state={sel.running ? 'loading' : undefined} lang={lang}>
      {parts.join(' ')}
    </p>
  );
}

/** The state key the cards are checked against (the shell's). */
export function useStateKey(): string | undefined {
  return useWorkbenchState()?.stateKey;
}
