// The contract table of the Implementation page against the catalog it transcribes (docs/contracts/catalog.md): the same rows in the
// same order, each with its version and producer. A row added to or changed in the catalog without this page failing is the drift
// this test exists to catch.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { CONTRACT_ROWS } from './contract-rows';

const catalog = readFileSync(new URL('../../../../docs/contracts/catalog.md', import.meta.url), 'utf8');

/** The cells of the "Contracts" table of the catalog: id, version, owner. */
function catalogRows(): { id: string; version: string; owner: string }[] {
  const start = catalog.indexOf('## Contracts');
  const end = catalog.indexOf('## Missing-data states');
  expect(start).toBeGreaterThan(0);
  expect(end).toBeGreaterThan(start);
  return catalog
    .slice(start, end)
    .split('\n')
    .filter((l) => l.startsWith('| ') && !l.startsWith('| id ') && !l.startsWith('|---'))
    .map((l) => l.split('|').map((c) => c.trim()))
    .map((c) => ({ id: c[1], version: c[2], owner: c[3] }));
}

describe('the contract table of the Implementation page', () => {
  it('lists the rows of the catalog, in order, with their version and producer', () => {
    expect(CONTRACT_ROWS.map(({ id, version, owner }) => ({ id, version, owner }))).toEqual(catalogRows());
  });
  it('has eleven rows, each described in both languages', () => {
    expect(CONTRACT_ROWS).toHaveLength(11);
    for (const r of CONTRACT_ROWS) {
      for (const text of [r.what, r.reader]) {
        expect(text.en.trim().length, r.id).toBeGreaterThan(10);
        expect(text.es.trim().length, r.id).toBeGreaterThan(10);
      }
    }
  });
});
