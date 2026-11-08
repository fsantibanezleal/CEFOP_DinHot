// The view switch the optical train uses to open another view of the workbench (ADR-0082 rule 6).
import { describe, expect, it, vi } from 'vitest';
import { GROUP_IDS, initialGroup, initialTab, makeNav, opensView, revealStage } from './nav';

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

  it('a deep link names a sub-view with its group, and only a well-formed one', () => {
    expect(initialTab('?case=C08_device_limited&view=hologram&tab=device')).toEqual({ group: 'hologram', tab: 'device' });
    expect(initialTab('?view=convergence&tab=pareto')).toEqual({ group: 'convergence', tab: 'pareto' });
    expect(initialTab('?view=convergence')).toBeNull();
    expect(initialTab('?tab=%22%3E%3Cscript')).toBeNull();
    expect(initialTab('')).toBeNull();
  });


  it('brings the row of group tabs into view once, when a deep link opened a view', () => {
    expect(opensView('?view=convergence')).toBe(true);
    expect(opensView('?tab=pareto')).toBe(true);
    expect(opensView('?case=C02_grid_feedback')).toBe(false);
    const scrolled = vi.fn();
    revealStage({ querySelector: () => ({ scrollIntoView: scrolled }) } as unknown as ParentNode);
    expect(scrolled).toHaveBeenCalledWith({ block: 'start' });
    let row: unknown = null;
    const frames: (() => void)[] = [];
    revealStage({ querySelector: () => row } as unknown as ParentNode, 3, (f) => frames.push(f));
    row = { scrollIntoView: scrolled };
    frames.shift()!();
    expect(scrolled).toHaveBeenCalledTimes(2);
  });

  it('the first group is the Hologram group, and the URL names a group only when it exists', () => {
    expect(GROUP_IDS[0]).toBe('hologram');
    expect(initialGroup('?case=C08&view=focal')).toBe('focal');
    expect(initialGroup('?view=nonsense')).toBe('hologram');
    expect(initialGroup('')).toBe('hologram');
    expect(initialGroup('?view=context')).toBe('context');
  });
});
