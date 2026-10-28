// The references of the Experiments page that the other pages do not already carry. The page also cites entries of `./methodology`
// (Di Leonardo 2007, Bianchi 2010, Pasienski 2008, Polin 2005, Kim 2019, Nogrette 2014, Schroff 2023, Leutenegger 2006, Noll 1976, Grimm 2000,
// Tolic-Norrelykke 2006, Ebadi 2021, Barredo 2016, Endres 2016, Lee 2017). The one entry here is the work the particle driver of the product
// names for the bias of the linearised Lorentzian fit: `docs/frameworks/P05_particle-dynamics.md` (Limits) and the docstring of
// `data-pipeline/pipeline/model/holo/core/dynamics.py` give the authors, the year and the arXiv number, and say that only the abstract was
// read (UNVERIFIED which correction applies), so the entry carries nothing beyond those three facts. The page registers both lists itself
// (it wraps its content in a `CitationsProvider`), so it renders whether or not the shared list carries them.
//
// Fragment for the main session: to list these in the shared `content/citations.ts` as well, add this import and spread the array into
// `CITATIONS`:
//
//   import { EXPERIMENTS_CITATIONS } from './citations/experiments';
//   export const CITATIONS: Citation[] = [ ...existing entries, ...EXPERIMENTS_CITATIONS ];
import type { Citation } from '@fasl-work/caos-app-shell';

export const EXPERIMENTS_CITATIONS: Citation[] = [
  {
    id: 'norrelykke2010',
    label: { en: 'Norrelykke and Flyvbjerg 2010', es: 'Norrelykke y Flyvbjerg 2010' },
    citation: 'Norrelykke, S. F., Flyvbjerg, H. (2010). arXiv:0906.1708; cited by the product for the bias of the linearised Lorentzian fit at low segment counts (abstract only read).',
    url: 'https://arxiv.org/abs/0906.1708',
  },
];
