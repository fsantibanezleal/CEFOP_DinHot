// The references of the Introduction's technical view that the other pages do not already carry. The view also cites entries of
// `./methodology` (Di Leonardo 2007, Polin 2005, Kim 2019, Schroff 2023, Nogrette 2014, Grimm 2000, Tolic-Norrelykke 2006, Manetsch 2025,
// Pasienski 2008, the linear phase interpolation preprint), whose DOIs and URLs a research dossier of the coordination records lists as
// opened. The page registers both lists itself (it wraps its content in a `CitationsProvider`), so it renders whether or not the shared
// list carries them.
//
// Fragment for the main session: to list these in the shared `content/citations.ts` as well, add this import and spread the array into
// `CITATIONS`:
//
//   import { INTRODUCTION_CITATIONS } from './citations/introduction';
//   export const CITATIONS: Citation[] = [ ...existing entries, ...INTRODUCTION_CITATIONS ];
import type { Citation } from '@fasl-work/caos-app-shell';

export const INTRODUCTION_CITATIONS: Citation[] = [
  {
    id: 'dinhot-legacy',
    label: { en: 'DinHotSys and the Python port, commit f032a9b', es: 'DinHotSys y el port a Python, commit f032a9b' },
    citation:
      'CEFOP_DinHot repository at commit f032a9b (2026-07-03): the C++ desktop tool DinHotSys (legacy/, Copyright (c) UdeC 2010) and the Python and FastAPI port (app/) that this release replaces.',
    url: 'https://github.com/fsantibanezleal/CEFOP_DinHot/tree/f032a9b',
  },
];
