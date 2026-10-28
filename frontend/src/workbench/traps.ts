// The trap editor (a control of the case, never a separate surface): click adds, drag moves, delete removes. The edited list is
// the target of the next live run. The field-of-view rule is the engine's (core.traps.check_in_field and contract 1): a trap lies
// strictly inside the unaliased window, |x| and |y| below lambda f / (2 p), because the bin at the bound is outside the centred
// FFT grid; a refused edit leaves the list unchanged and answers the engine's message in both languages.
import type { Text, Trap } from '../lib/contract.types';

/** The most traps a target may hold (the params record schema). */
export const MAX_TRAPS = 4096;

const g = (v: number): string => String(Number(v.toPrecision(6)));
const gEs = (v: number): string => g(v).replace('.', ',');

/** null when the trap lies inside the unaliased field of view, else the engine's reason (the wording of io/contract.py). */
export function outsideField(t: Trap, halfFieldUm: number): Text | null {
  for (const axis of ['x_um', 'y_um'] as const) {
    if (Math.abs(t[axis]) >= halfFieldUm) {
      const bound = halfFieldUm.toFixed(1);
      return {
        en: `trap ${t.id} has ${axis}=${g(t[axis])} um, outside the unaliased field of view (abs must be below ${bound} um = lambda f / (2 p))`,
        es: `la trampa ${t.id} tiene ${axis}=${gEs(t[axis])} um, fuera del campo de visión sin solapamiento (abs debe ser menor que ${bound.replace('.', ',')} um = lambda f / (2 p))`,
      };
    }
  }
  return null;
}

export type Edit = { traps: Trap[] } | { error: Text };

export const nextTrapId = (traps: readonly Trap[]): number => traps.reduce((m, t) => Math.max(m, t.id), -1) + 1;

export function addTrap(traps: readonly Trap[], xUm: number, yUm: number, halfFieldUm: number): Edit {
  if (traps.length >= MAX_TRAPS) {
    return { error: { en: `A target holds at most ${MAX_TRAPS} traps.`, es: `Un objetivo admite como máximo ${MAX_TRAPS} trampas.` } };
  }
  const t: Trap = { id: nextTrapId(traps), x_um: xUm, y_um: yUm, z_um: 0, weight: 1, charge: 0 };
  const bad = outsideField(t, halfFieldUm);
  return bad ? { error: bad } : { traps: [...traps, t] };
}

export function moveTrap(traps: readonly Trap[], id: number, xUm: number, yUm: number, halfFieldUm: number): Edit {
  const at = traps.findIndex((t) => t.id === id);
  if (at < 0) return { error: { en: `No trap ${id}.`, es: `No existe la trampa ${id}.` } };
  const moved: Trap = { ...traps[at], x_um: xUm, y_um: yUm };
  const bad = outsideField(moved, halfFieldUm);
  if (bad) return { error: bad };
  const next = traps.slice();
  next[at] = moved;
  return { traps: next };
}

export function deleteTrap(traps: readonly Trap[], id: number): Edit {
  if (traps.length <= 1) {
    return { error: { en: 'A target needs at least one trap.', es: 'Un objetivo necesita al menos una trampa.' } };
  }
  return { traps: traps.filter((t) => t.id !== id) };
}

/** The focal crop is size x size bins of `binUm`, with x = 0 at index floor(size / 2) (the centred FFT grid). Pixel column and row of a position. */
export function umToPixel(xUm: number, yUm: number, size: number, binUm: number): [number, number] {
  const c = Math.floor(size / 2);
  return [Math.round(xUm / binUm) + c, Math.round(yUm / binUm) + c];
}

export function pixelToUm(col: number, row: number, size: number, binUm: number): [number, number] {
  const c = Math.floor(size / 2);
  return [(col - c) * binUm, (row - c) * binUm];
}
