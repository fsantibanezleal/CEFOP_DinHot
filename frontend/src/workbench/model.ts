// The selection the views share, and the variants every case offers.
import type { CaseData } from '../api/artifacts';
import type { SirRun } from '../engine/sir';

/** The variants of every case: the share of the population immunised before the outbreak. */
export const COVERAGE = [
  { id: 'v0', share: 0, label: { en: 'No immunisation', es: 'Sin inmunización' }, note: { en: 'The case as baked.', es: 'El caso tal como se precalculó.' } },
  { id: 'v30', share: 0.3, label: { en: '30% immunised', es: '30% inmunizado' }, note: { en: 'A third of the susceptible are immune at the start.', es: 'Un tercio de los susceptibles es inmune al inicio.' } },
  { id: 'v60', share: 0.6, label: { en: '60% immunised', es: '60% inmunizado' }, note: { en: 'Above the herd threshold of most cases.', es: 'Sobre el umbral de rebaño de la mayoría de los casos.' } },
] as const;

export interface Selection {
  data: CaseData;
  beta: number;
  gamma: number;
  coverage: number;
  run: SirRun;
}
