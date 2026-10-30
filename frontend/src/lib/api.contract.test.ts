// Catalog row api: the types generated from docs/contracts/api.openapi.json carry exactly the document types the
// rest of the app names (contract.types.ts), and the 503 example conforms to the descriptor. The type assertions are
// checked by `tsc --noEmit` (npm run build); the run-time assertion by vitest.
import { readFileSync } from 'node:fs';
import { describe, expect, it, expectTypeOf } from 'vitest';
import type { paths } from './contract.gen';
import { conform, UNAVAILABLE, type CaseIndex, type CaseManifest, type NotFoundBody, type Readiness, type Trace, type UnavailableBody } from './contract.types';

type Body<R, S extends number> = R extends { responses: Record<S, { content: { 'application/json': infer B } }> } ? B : never;
type Get<P extends keyof paths> = paths[P]['get'];
type Responses<P extends keyof paths> = Get<P> extends { responses: infer R } ? R : never;
type Json<R, S extends number> = R extends Record<S, { content: { 'application/json': infer B } }> ? B : never;

describe('api: the generated response bodies are the document types', () => {
  it('200 bodies', () => {
    expectTypeOf<Json<Responses<'/api/cases'>, 200>>().toEqualTypeOf<CaseIndex>();
    expectTypeOf<Json<Responses<'/api/cases/{case_id}/manifest'>, 200>>().toEqualTypeOf<CaseManifest>();
    expectTypeOf<Json<Responses<'/api/artifacts/{rel_path}'>, 200>>().toEqualTypeOf<Trace>();
    expectTypeOf<Json<Responses<'/api/readiness'>, 200>>().toEqualTypeOf<Readiness>();
    expectTypeOf<Body<Get<'/api/cases'>, 200>>().toEqualTypeOf<CaseIndex>();
  });
  it('adversarial: every 503 is UnavailableBody and every 404 is NotFoundBody', () => {
    type R503 = { content: { 'application/json': UnavailableBody } };
    type R404 = { content: { 'application/json': NotFoundBody } };
    expectTypeOf<Responses<'/api/cases'>[503 & keyof Responses<'/api/cases'>]>().toMatchTypeOf<R503>();
    expectTypeOf<Responses<'/api/cases/{case_id}/manifest'>[503 & keyof Responses<'/api/cases/{case_id}/manifest'>]>().toMatchTypeOf<R503>();
    expectTypeOf<Responses<'/api/readiness'>[503 & keyof Responses<'/api/readiness'>]>().toMatchTypeOf<R503>();
    expectTypeOf<Responses<'/api/cases/{case_id}/manifest'>[404 & keyof Responses<'/api/cases/{case_id}/manifest'>]>().toMatchTypeOf<R404>();
    expectTypeOf<Responses<'/api/artifacts/{rel_path}'>[404 & keyof Responses<'/api/artifacts/{rel_path}'>]>().toMatchTypeOf<R404>();
  });
  it('the committed 503 example conforms to UNAVAILABLE', () => {
    const url = new URL('../../../docs/contracts/examples/api-unavailable.json', import.meta.url);
    const example = JSON.parse(readFileSync(url, 'utf8')) as unknown;
    expect(conform(example, { object: UNAVAILABLE })).toEqual([]);
  });
});
