// The references of the example model. Every entry carries a DOI that resolves (checked against doi.org and the
// Crossref record on 2026-10-04); the shell reports an entry without a DOI or URL. A product replaces this list with
// the references of its own dossiers.
import type { Citation } from '@fasl-work/caos-app-shell';

export const CITATIONS: Citation[] = [
  {
    id: 'km1927',
    label: { en: 'Kermack and McKendrick 1927', es: 'Kermack y McKendrick 1927' },
    citation:
      'Kermack, W. O., McKendrick, A. G. (1927). A contribution to the mathematical theory of epidemics. Proceedings of the Royal Society of London, Series A, 115(772), 700-721.',
    doi: '10.1098/rspa.1927.0118',
  },
  {
    id: 'hethcote2000',
    label: 'Hethcote 2000',
    citation: 'Hethcote, H. W. (2000). The mathematics of infectious diseases. SIAM Review, 42(4), 599-653.',
    doi: '10.1137/S0036144500371907',
  },
  {
    id: 'diekmann1990',
    label: { en: 'Diekmann, Heesterbeek and Metz 1990', es: 'Diekmann, Heesterbeek y Metz 1990' },
    citation:
      'Diekmann, O., Heesterbeek, J. A. P., Metz, J. A. J. (1990). On the definition and the computation of the basic reproduction ratio R0 in models for infectious diseases in heterogeneous populations. Journal of Mathematical Biology, 28(4).',
    doi: '10.1007/BF00178324',
  },
  {
    id: 'vdd2002',
    label: { en: 'van den Driessche and Watmough 2002', es: 'van den Driessche y Watmough 2002' },
    citation:
      'van den Driessche, P., Watmough, J. (2002). Reproduction numbers and sub-threshold endemic equilibria for compartmental models of disease transmission. Mathematical Biosciences, 180(1-2), 29-48.',
    doi: '10.1016/S0025-5564(02)00108-6',
  },
  {
    id: 'miller2012',
    label: 'Miller 2012',
    citation: 'Miller, J. C. (2012). A note on the derivation of epidemic final sizes. Bulletin of Mathematical Biology, 74(9), 2125-2141.',
    doi: '10.1007/s11538-012-9749-6',
  },
  {
    id: 'hairer1993',
    label: { en: 'Hairer, Norsett and Wanner 1993', es: 'Hairer, Norsett y Wanner 1993' },
    citation:
      'Hairer, E., Norsett, S. P., Wanner, G. (1993). Solving Ordinary Differential Equations I: Nonstiff Problems (2nd ed.). Springer Series in Computational Mathematics 8. Springer.',
    doi: '10.1007/978-3-540-78862-1',
  },
];
