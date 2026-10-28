// Fragment for the main session: the references of the Methodology page are in `./methodology.ts`. The page registers them itself
// (it wraps its content in a `CitationsProvider` that adds them to the shared list), so the shared file needs no change to render.
// To list them in the shared `content/citations.ts` as well, add this import and spread the array into `CITATIONS`:
//
//   import { METHODOLOGY_CITATIONS } from './citations/methodology';
//   export const CITATIONS: Citation[] = [ ...existing entries, ...METHODOLOGY_CITATIONS ];
export {};
