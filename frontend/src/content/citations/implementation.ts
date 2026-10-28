// The references of the Implementation page that the other pages do not already carry. The page also cites entries of `./methodology`
// (Di Leonardo 2007, Kim 2019, Schroff 2023, Nogrette 2014). Every entry here carries the URL the code itself names or that the package
// metadata names: the generator and its seeding mixer in `data-pipeline/pipeline/model/holo/core/rng.py` (read on 2026-10-28), and the
// repositories of the two runtime libraries as `frontend/node_modules/fft.js/package.json` and `onnxruntime-web/package.json` declare them.
// The page registers both lists itself (it wraps its content in a `CitationsProvider`), so it renders whether or not the shared list
// carries them.
//
// Fragment for the main session: to list these in the shared `content/citations.ts` as well, add this import and spread the array into
// `CITATIONS`:
//
//   import { IMPLEMENTATION_CITATIONS } from './citations/implementation';
//   export const CITATIONS: Citation[] = [ ...existing entries, ...IMPLEMENTATION_CITATIONS ];
import type { Citation } from '@fasl-work/caos-app-shell';

export const IMPLEMENTATION_CITATIONS: Citation[] = [
  {
    id: 'blackman2021',
    label: { en: 'Blackman and Vigna 2021', es: 'Blackman y Vigna 2021' },
    citation:
      'Blackman, D., Vigna, S. (2021). Scrambled linear pseudorandom number generators. ACM Transactions on Mathematical Software (arXiv 1805.01407); the reference implementation of xoshiro128** is at prng.di.unimi.it/xoshiro128starstar.c.',
    url: 'https://prng.di.unimi.it/xoshiro128starstar.c',
  },
  {
    id: 'splitmix32',
    label: { en: 'SplitMix32 (public domain)', es: 'SplitMix32 (dominio público)' },
    citation: 'bryc (n.d.). JavaScript PRNGs and hashes, the SplitMix32 mixer with the improved constants (public domain), used to seed the four state words.',
    url: 'https://github.com/bryc/code/blob/master/jshash/PRNGs.md',
  },
  {
    id: 'fftjs',
    label: 'fft.js 4.0.4',
    citation: 'Indutny, F. fft.js, a fast Fourier transform for JavaScript with radix-4 power-of-two sizes (version 4.0.4, pinned in frontend/package.json).',
    url: 'https://github.com/indutny/fft.js',
  },
  {
    id: 'onnxruntime',
    label: 'ONNX Runtime',
    citation: 'Microsoft. ONNX Runtime, the cross-platform inference engine; the web build onnxruntime-web 1.31.1 is pinned in frontend/package.json.',
    url: 'https://github.com/microsoft/onnxruntime',
  },
];
