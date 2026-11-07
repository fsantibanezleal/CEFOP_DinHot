// The view switch the optical train uses to open another view of the workbench (ADR-0082 rule 6).
import { describe, expect, it, vi } from 'vitest';
import { GROUP_IDS, initialGroup, makeNav } from './nav';

describe('the workbench view switch', () => {
  it('opening a view sets its group and, when given, its sub-view', () => {
    const setGroup = vi.fn();
    const setTab = vi.fn();
    const nav = makeNav(setGroup, setTab, { hologram: 'mask' });
    nav.open({ group: 'hologram', tab: 'device' });
    expect(setGroup).toHaveBeenCalledWith('hologram');
    expect(setTab).toHaveBeenCalledWith('hologram', 'device');
    expect(nav.tabs.hologram).toBe('mask');
  });

  it('opening a group without a sub-view leaves its sub-view alone', () => {
    const setGroup = vi.fn();
    const setTab = vi.fn();
    makeNav(setGroup, setTab, {}).open({ group: 'traps' });
    expect(setGroup).toHaveBeenCalledWith('traps');
    expect(setTab).not.toHaveBeenCalled();
  });

  it('the first group is the Hologram group, and the URL names a group only when it exists', () => {
    expect(GROUP_IDS[0]).toBe('hologram');
    expect(initialGroup('?case=C08&view=focal')).toBe('focal');
    expect(initialGroup('?view=nonsense')).toBe('hologram');
    expect(initialGroup('')).toBe('hologram');
    expect(initialGroup('?view=context')).toBe('context');
  });
});
