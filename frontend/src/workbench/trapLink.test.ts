// Linked trap selection (ADR-0082 rule 6): the shell's linked store holds a string id, the workbench holds the selected trap as a number;
// the two are one selection. The pure reconciliation is tested here, then driven through the shell's own store the way the two effects do.
import { createLinkedViewStore } from '@fasl-work/caos-app-shell';
import { describe, expect, it } from 'vitest';
import { linkedToTrap, pullFromLinked, pushToLinked, trapToLinked } from './trapLink';

const traps = [{ id: 0 }, { id: 3 }, { id: 7 }, { id: 12 }];

describe('the ids', () => {
  it('a trap id is its decimal string and back', () => {
    expect(trapToLinked(7)).toBe('7');
    expect(trapToLinked(0)).toBe('0');
    expect(trapToLinked(null)).toBeNull();
    expect(linkedToTrap('12', traps)).toBe(12);
    expect(linkedToTrap('0', traps)).toBe(0);
  });
  it('a linked id that names no trap of the case selects nothing', () => {
    expect(linkedToTrap('5', traps)).toBeNull();
    expect(linkedToTrap('abc', traps)).toBeNull();
    expect(linkedToTrap('', traps)).toBeNull();
    expect(linkedToTrap(null, traps)).toBeNull();
    expect(linkedToTrap('7.5', traps)).toBeNull();
  });
});

describe('reconciliation', () => {
  it('a linked selection that differs from the workbench trap selects that trap', () => {
    expect(pullFromLinked('7', 3, traps)).toBe(7);
  });
  it('a linked selection equal to the workbench trap changes nothing', () => {
    expect(pullFromLinked('7', 7, traps)).toBeNull();
  });
  it('a workbench trap that differs from the linked id is pushed; an equal one is not', () => {
    expect(pushToLinked(7, '3')).toBe('7');
    expect(pushToLinked(7, '7')).toBeNull();
    expect(pushToLinked(7, null)).toBe('7');
    expect(pushToLinked(null, '3')).toBeNull();
  });
});

describe('one selection across the views, through the shell store', () => {
  /** What the workbench does: the store pushes into the trap state, the trap state pushes into the store. */
  function wire() {
    const store = createLinkedViewStore();
    const state = { trapId: 0 as number | null };
    const selectTrap = (id: number | null) => {
      state.trapId = id; // the actions every view calls (focal plane, bars, the optical train through the store)
      const push = pushToLinked(id, store.getState().selectedId);
      if (push !== null) store.getState().select(push, 'panel');
    };
    store.subscribe((s) => {
      const pull = pullFromLinked(s.selectedId, state.trapId, traps);
      if (pull !== null) state.trapId = pull;
    });
    return { store, state, selectTrap };
  }

  it('a trap picked in the optical train (the scene) is the trap of the focal plane and the bars', () => {
    const { store, state } = wire();
    store.getState().select('12', 'scene');
    expect(state.trapId).toBe(12);
  });

  it('a trap picked in the bars or the focal plane (the actions) is the linked selectedId the optical train marks', () => {
    const { store, state, selectTrap } = wire();
    selectTrap(7);
    expect(state.trapId).toBe(7);
    expect(store.getState().selectedId).toBe('7');
    expect(store.getState().origin).toBe('panel');
  });

  it('selecting in one view and then another leaves one selection', () => {
    const { store, state, selectTrap } = wire();
    store.getState().select('3', 'scene');
    selectTrap(12);
    store.getState().select('0', 'scene');
    expect(state.trapId).toBe(0);
    expect(store.getState().selectedId).toBe('0');
  });
});
