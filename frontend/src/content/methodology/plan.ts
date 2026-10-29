// Which ladder methods each topic of the Methodology page covers, in the order of the page. The page builds its groups from this list and a
// vitest (ladder.test.ts) checks it against the SDD: every ladder row sits in exactly one topic of its own tier, and a physics topic names none.
import type { Tier } from './ladder';

export interface TopicPlan {
  id: string;
  /** The group of the page: the physics topics, or the tier of the methods the topic covers. */
  group: 'physics' | Tier;
  /** The ladder ids the topic covers (empty for a physics topic). */
  ids: string[];
}

export const PLAN: TopicPlan[] = [
  { id: 'slm-lens', group: 'physics', ids: [] },
  { id: 'metrics', group: 'physics', ids: [] },
  { id: 'device', group: 'physics', ids: [] },
  { id: 'particle', group: 'physics', ids: [] },
  { id: 'analytic', group: 'classical', ids: ['M01', 'M02', 'M03'] },
  { id: 'gs', group: 'classical', ids: ['M04', 'M05', 'M06', 'M19'] },
  { id: 'direct', group: 'classical', ids: ['M09'] },
  { id: 'aberration', group: 'classical', ids: ['M14', 'M15'] },
  { id: 'phase-fixed', group: 'sota', ids: ['M07'] },
  { id: 'shaped', group: 'sota', ids: ['M08', 'M18'] },
  { id: 'gradient', group: 'sota', ids: ['M10', 'M11', 'M13'] },
  { id: 'loop', group: 'sota', ids: ['M12', 'M16'] },
  { id: 'cnn', group: 'sota', ids: ['M17'] },
  { id: 'bs1', group: 'beyond', ids: ['BS-1'] },
  { id: 'bs2', group: 'beyond', ids: ['BS-2'] },
  { id: 'bs3', group: 'beyond', ids: ['BS-3'] },
  { id: 'bs4', group: 'beyond', ids: ['BS-4'] },
  { id: 'bs5', group: 'beyond', ids: ['BS-5'] },
];
