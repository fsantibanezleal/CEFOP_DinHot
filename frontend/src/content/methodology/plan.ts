import { ID } from '../../lib/methodIds';
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
  { id: 'analytic', group: 'superposition-gs', ids: [ID.M01, ID.M02, ID.M03] },
  { id: 'gs', group: 'superposition-gs', ids: [ID.M04, ID.M05, ID.M06, ID.M19] },
  { id: 'phase-fixed', group: 'superposition-gs', ids: [ID.M07] },
  { id: 'direct', group: 'optimization', ids: [ID.M09] },
  { id: 'gradient', group: 'optimization', ids: [ID.M10, ID.M11, ID.M13] },
  { id: 'shaped', group: 'shaped-potentials', ids: [ID.M08, ID.M18] },
  { id: 'aberration', group: 'shaped-potentials', ids: [ID.M14, ID.M15] },
  { id: 'loop', group: 'feedback', ids: [ID.M12, ID.M16] },
  { id: 'cnn', group: 'feedback', ids: [ID.M17] },
  { id: 'device-aware-wgs', group: 'proposed', ids: [ID.B1] },
  { id: 'flicker-bounded', group: 'proposed', ids: [ID.B2] },
  { id: 'learned-warm-start', group: 'proposed', ids: [ID.B3] },
  { id: 'robust-hologram', group: 'proposed', ids: [ID.B4] },
  { id: 'pareto-front', group: 'proposed', ids: [ID.B5] },
];
