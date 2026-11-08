// The one trap selection, as the per-trap views draw it (ADR-0082 rule 6). The workbench's trap id is the shell's linked `selectedId`
// (trapLink.ts); a view that draws the traps marks the selected one from it. Pure, so the marking is tested without a DOM.

export interface TrapValue {
  id: number;
  v: number;
}

/** The position of the selected trap among the items as drawn (its rank when sorted), or -1 when none is selected or it is not drawn. */
export function selectedIndex(items: readonly { id: number }[], trapId: number | null): number {
  return trapId === null ? -1 : items.findIndex((i) => i.id === trapId);
}

/** A series with the selected trap's value at its position and a gap everywhere else; null when no trap is selected, so no empty series is drawn. */
export function selectedSeries(items: readonly TrapValue[], trapId: number | null): (number | null)[] | null {
  const k = selectedIndex(items, trapId);
  return k < 0 ? null : items.map((_, i) => (i === k ? items[k].v : null));
}

/** The value of the selected trap, for the histogram's mark and the readouts; null when none is selected. */
export function selectedValue(items: readonly TrapValue[], trapId: number | null): number | null {
  const k = selectedIndex(items, trapId);
  return k < 0 ? null : items[k].v;
}
