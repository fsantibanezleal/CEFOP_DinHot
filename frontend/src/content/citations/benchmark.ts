// The references of the Benchmark page that the other pages do not already carry. The page also cites entries of `./methodology`
// (Di Leonardo 2007, Pasienski 2008, Kim 2019, Schroff 2023, Eybposh 2020, Whyte and Courtial 2005, the linear phase interpolation of
// 2025, Machu et al. 2025). The one entry here is the open implementation the benchmark protocol names as the cross-check oracle of its
// phase-fixed weighted GS: its licence, version and repository are the facts of the algorithms dossier, D4.1 (repository metadata read
// through the GitHub API and the PyPI JSON API on 2026-10-28). The page registers both lists itself (it wraps its content in a
// `CitationsProvider`), so it renders whether or not the shared list carries them.
//
// Fragment for the main session: to list these in the shared `content/citations.ts` as well, add this import and spread the array into
// `CITATIONS`:
//
//   import { BENCHMARK_CITATIONS } from './citations/benchmark';
//   export const CITATIONS: Citation[] = [ ...existing entries, ...BENCHMARK_CITATIONS ];
import type { Citation } from '@fasl-work/caos-app-shell';

export const BENCHMARK_CITATIONS: Citation[] = [
  {
    id: 'slmsuite',
    label: { en: 'slmsuite 0.5.0', es: 'slmsuite 0.5.0' },
    citation:
      'slmsuite: a Python package for holography with spatial light modulators (MIT licence; release 0.5.0 of 2026-10-05, PyPI project slmsuite). Its weighted GS is the phase-fixed form of Kim et al. 2019; the benchmark of DinHot uses it as a cross-check of M07, not as a method of the matrix.',
    url: 'https://github.com/slmsuite/slmsuite',
  },
];
