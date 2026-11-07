// The view switch of the workbench (ADR-0082 rule 6, linked views): an element of the optical train opens the view it stands for (the SLM
// opens Device effects, the focal plane opens the Focal plane group). The workbench holds the open group and the open sub-view of the groups
// that offer a switch; the shell's CaseWorkbench takes the group as a controlled value, so the URL (`?view=`) is written here.
import { createContext, useContext } from 'react';

/** The groups of the instrument, in the order of the tab row (the Context write-up is the shell's last peer). */
export const GROUP_IDS = ['hologram', 'focal', 'traps', 'convergence', 'dynamics', 'context'] as const;
export type GroupId = (typeof GROUP_IDS)[number];

export interface ViewTarget {
  group: GroupId;
  /** The sub-view of the group; absent leaves the group's own. */
  tab?: string;
}

export interface Nav {
  open: (target: ViewTarget) => void;
  /** The sub-view each group was told to show; a group never told keeps its first. */
  tabs: Readonly<Record<string, string | undefined>>;
  setTab: (group: string, tab: string) => void;
}

export function makeNav(setGroup: (group: GroupId) => void, setTab: (group: string, tab: string) => void, tabs: Readonly<Record<string, string | undefined>>): Nav {
  return {
    open: (target) => {
      setGroup(target.group);
      if (target.tab) setTab(target.group, target.tab);
    },
    tabs,
    setTab,
  };
}

/** The open group at load: the `view` parameter when it names a group of the instrument, else the first. */
export function initialGroup(search: string): GroupId {
  const v = new URLSearchParams(search).get('view');
  return (GROUP_IDS as readonly string[]).includes(v ?? '') ? (v as GroupId) : GROUP_IDS[0];
}

export const NavContext = createContext<Nav | null>(null);
/** The switch of the enclosing workbench; null in a view rendered on its own (a test, a doc), where a view then changes nothing. */
export function useNav(): Nav | null {
  return useContext(NavContext);
}
