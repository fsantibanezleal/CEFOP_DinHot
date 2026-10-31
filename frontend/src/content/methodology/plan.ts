// Which ladder methods each topic of the Methodology page covers, in the order of the page. The page builds its groups from this list and a
// vitest (ladder.test.ts) checks it against the SDD: every ladder row sits in exactly one topic, and a physics topic names none.
export type Group = 'physics' | 'superposition-gs' | 'optimization' | 'shaped-potentials' | 'feedback' | 'proposed';

export interface TopicPlan {
  id: string;
  /** The group of the page: the physics topics, or the family of the methods the topic covers. */
  group: Group;
  /** The ladder ids the topic covers (empty for a physics topic). */
  ids: string[];
}

export const PLAN: TopicPlan[] = [
  { id: 'slm-lens', group: 'physics', ids: [] },
  { id: 'metrics', group: 'physics', ids: [] },
  { id: 'device', group: 'physics', ids: [] },
  { id: 'particle', group: 'physics', ids: [] },
  { id: 'analytic', group: 'superposition-gs', ids: ['M01', 'M02', 'M03'] },
  { id: 'gs', group: 'superposition-gs', ids: ['M04', 'M05', 'M06', 'M19'] },
  { id: 'phase-fixed', group: 'superposition-gs', ids: ['M07'] },
  { id: 'direct', group: 'optimization', ids: ['M09'] },
  { id: 'gradient', group: 'optimization', ids: ['M10', 'M11', 'M13'] },
  { id: 'shaped', group: 'shaped-potentials', ids: ['M08', 'M18'] },
  { id: 'aberration', group: 'shaped-potentials', ids: ['M14', 'M15'] },
  { id: 'loop', group: 'feedback', ids: ['M12', 'M16'] },
  { id: 'cnn', group: 'feedback', ids: ['M17'] },
  { id: 'device-aware-wgs', group: 'proposed', ids: ['B1'] },
  { id: 'flicker-bounded', group: 'proposed', ids: ['B2'] },
  { id: 'learned-warm-start', group: 'proposed', ids: ['B3'] },
  { id: 'robust-hologram', group: 'proposed', ids: ['B4'] },
  { id: 'pareto-front', group: 'proposed', ids: ['B5'] },
];
