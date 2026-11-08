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
  /** Loads another case of the release into the workbench, keeping the open view (a view that has nothing to show on this case offers the one that has). */
  openCase?: (caseId: string) => void;
}

export function makeNav(setGroup: (group: GroupId) => void, setTab: (group: string, tab: string) => void, tabs: Readonly<Record<string, string | undefined>>, openCase?: (caseId: string) => void): Nav {
  return {
    open: (target) => {
      setGroup(target.group);
      if (target.tab) setTab(target.group, target.tab);
    },
    tabs,
    setTab,
    openCase,
  };
}

/** The open group at load: the `view` parameter when it names a group of the instrument, else the first. */
export function initialGroup(search: string): GroupId {
  const v = new URLSearchParams(search).get('view');
  return (GROUP_IDS as readonly string[]).includes(v ?? '') ? (v as GroupId) : GROUP_IDS[0];
}

/** The sub-view the URL names (`?tab=`), with the group it belongs to: the group of `?view=`. A link such as `/app?view=convergence&tab=pareto` opens that sub-view. */
export function initialTab(search: string): { group: GroupId; tab: string } | null {
  const tab = new URLSearchParams(search).get('tab');
  return tab && /^[a-z][a-z0-9-]{0,31}$/.test(tab) ? { group: initialGroup(search), tab } : null;
}

/** Whether the URL asks for a view (`?view=` or `?tab=`): the reader arrived by a deep link to a view, not to the workbench as a whole. */
export function opensView(search: string): boolean {
  const q = new URLSearchParams(search);
  return q.has('view') || q.has('tab');
}

/**
 * On a phone the rail stacks above the stage, so a deep link to a view opens on the rail with the stage below the fold: bring the row of
 * group tabs to the top of the screen, once. The workbench calls it from an effect that runs once the case has loaded, when the row is in
 * the document; it returns whether it found the row.
 */
export function revealStage(root: ParentNode = document): boolean {
  const row = root.querySelector<HTMLElement>('.caos-cw > .tabs');
  if (row) row.scrollIntoView({ block: 'start' });
  return row !== null;
}

export const NavContext = createContext<Nav | null>(null);
/** The switch of the enclosing workbench; null in a view rendered on its own (a test, a doc), where a view then changes nothing. */
export function useNav(): Nav | null {
  return useContext(NavContext);
}
