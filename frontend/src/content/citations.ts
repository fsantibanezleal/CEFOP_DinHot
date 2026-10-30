// The references of DinHot: the union of the lists of the documentation routes (`./citations/*.ts`), each id once, in the order
// of the routes. The App's provider carries all of them, so the workbench and its Context write-up can cite any of them; a route
// adds its own list again and the duplicates are dropped by id. The shell lists only the ids a page or panel cites.
import type { Citation } from '@fasl-work/caos-app-shell';
import { BENCHMARK_CITATIONS } from './citations/benchmark';
import { EXPERIMENTS_CITATIONS } from './citations/experiments';
import { IMPLEMENTATION_CITATIONS } from './citations/implementation';
import { INTRODUCTION_CITATIONS } from './citations/introduction';
import { METHODOLOGY_CITATIONS } from './citations/methodology';

const ROUTES: Citation[][] = [
  INTRODUCTION_CITATIONS,
  METHODOLOGY_CITATIONS,
  IMPLEMENTATION_CITATIONS,
  EXPERIMENTS_CITATIONS,
  BENCHMARK_CITATIONS,
];

export const CITATIONS: Citation[] = ROUTES.flat().filter((c, i, all) => all.findIndex((x) => x.id === c.id) === i);
