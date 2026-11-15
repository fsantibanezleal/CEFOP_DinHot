// One trap selection across the views (ADR-0082 rule 6). The workbench holds the selected trap as a number (`Rail.trapId`, the actions every
// view calls); the shell's linked-view store holds `selectedId` as a string. They are the same selection: a trap picked in the focal plane,
// in the per-trap bars or on the optical train's focal plane is the same `selectedId` everywhere. The pure reconciliation is here (tested),
// the two effects that run it are `useTrapLink`.
import { useLinkedView } from '@fasl-work/caos-app-shell';
import { useEffect, useRef } from 'react';

export const trapToLinked = (id: number | null): string | null => (id === null ? null : String(id));

/** The trap a linked id names, when it is a trap of this case; null otherwise. */
export function linkedToTrap(linkedId: string | null, traps: readonly { id: number }[]): number | null {
  if (linkedId === null || !/^\d+$/.test(linkedId)) return null;
  const id = Number(linkedId);
  return traps.some((t) => t.id === id) ? id : null;
}

/** The trap to select because the linked store changed, or null when the workbench already shows it. */
export function pullFromLinked(linkedId: string | null, trapId: number | null, traps: readonly { id: number }[]): number | null {
  const id = linkedToTrap(linkedId, traps);
  return id !== null && id !== trapId ? id : null;
}

/** The linked id to write because the workbench trap changed, or null when the store already holds it. */
export function pushToLinked(trapId: number | null, linkedId: string | null): string | null {
  const next = trapToLinked(trapId);
  return next !== null && next !== linkedId ? next : null;
}

/**
 * Keeps the workbench's selected trap and the linked store's `selectedId` equal. Each effect runs only when its own side changed, so a
 * change made elsewhere is never undone by the other side; the case id re-pushes the trap a new case starts with.
 */
export function useTrapLink(caseId: string, trapId: number | null, traps: readonly { id: number }[], selectTrap: (id: number) => void): void {
  const linkedId = useLinkedView((s) => s.selectedId);
  const select = useLinkedView((s) => s.select);
  const latest = useRef({ trapId, traps, linkedId, selectTrap });
  latest.current = { trapId, traps, linkedId, selectTrap };
  useEffect(() => {
    const now = latest.current;
    const pull = pullFromLinked(now.linkedId, now.trapId, now.traps);
    if (pull !== null) now.selectTrap(pull);
  }, [linkedId]);
  useEffect(() => {
    const now = latest.current;
    const push = pushToLinked(now.trapId, now.linkedId);
    if (push !== null) select(push, 'panel');
  }, [caseId, trapId, select]);
}
