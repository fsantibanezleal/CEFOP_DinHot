// The Methodology page names every method of the SDD ladder once, in its tier (ADR-0017 section 2.1, method tiers rule): this test reads the
// ladder table of docs/design/SDD.md and compares it with the page's data, so a method added to or moved in the SDD fails here until the page follows.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { LADDER } from './ladder';
import { PLAN } from './plan';

const sdd = readFileSync(new URL('../../../../docs/design/SDD.md', import.meta.url), 'utf8');

function sddRows() {
  const start = sdd.indexOf('## Method ladder');
  const end = sdd.indexOf('\n## ', start + 5);
  const rows: { id: string; tier: string; method: string }[] = [];
  for (const line of sdd.slice(start, end).split('\n')) {
    const m = /^\| ((?:M|BS-)\d+) \| (classical|sota|beyond) \| (.+?) \| /.exec(line);
    if (m) rows.push({ id: m[1], tier: m[2], method: m[3] });
  }
  return rows;
}

describe('the ladder on the Methodology page', () => {
  const rows = sddRows();

  it('reads the 24 rows of the SDD ladder', () => {
    expect(rows).toHaveLength(24);
    expect(rows.filter((r) => r.tier === 'classical')).toHaveLength(10);
    expect(rows.filter((r) => r.tier === 'sota')).toHaveLength(9);
    expect(rows.filter((r) => r.tier === 'beyond')).toHaveLength(5);
  });

  it('has the same ids, tiers and names as the SDD', () => {
    expect(LADDER.map((r) => r.id).sort()).toEqual(rows.map((r) => r.id).sort());
    for (const row of rows) {
      const mine = LADDER.find((r) => r.id === row.id);
      expect(mine?.tier, row.id).toBe(row.tier);
      const name = row.method.replace(/ \(engine id (B\d)\)$/, '');
      expect(mine?.name.en, row.id).toBe(name);
      const engine = /\(engine id (B\d)\)$/.exec(row.method)?.[1] ?? row.id;
      expect(mine?.engine, row.id).toBe(engine);
    }
  });

  it('places every ladder method in exactly one topic, of its own tier', () => {
    const seen = new Map<string, string>();
    for (const topic of PLAN) {
      for (const id of topic.ids) {
        expect(seen.has(id), `${id} appears in ${seen.get(id)} and ${topic.id}`).toBe(false);
        seen.set(id, topic.id);
        expect(topic.group, `${id} is in the ${topic.group} group`).toBe(LADDER.find((r) => r.id === id)?.tier);
      }
      if (topic.group === 'physics') expect(topic.ids).toEqual([]);
    }
    expect([...seen.keys()].sort()).toEqual(LADDER.map((r) => r.id).sort());
  });

  it('shows, in the topic files, exactly the methods of the plan, by tier file', () => {
    const files: Record<string, string> = { classical: 'classical.tsx', sota: 'sota.tsx', beyond: 'beyond.tsx' };
    for (const [tier, file] of Object.entries(files)) {
      const source = readFileSync(new URL(file, import.meta.url), 'utf8');
      const shown = [...source.matchAll(/<MethodTable ids=\{\[([^\]]*)\]\} \/>/g)].flatMap((m) => [...m[1].matchAll(/'([^']+)'/g)].map((x) => x[1]));
      const planned = PLAN.filter((topic) => topic.group === tier).flatMap((topic) => topic.ids);
      expect(shown.sort(), file).toEqual(planned.sort());
    }
    const physics = readFileSync(new URL('physics.tsx', import.meta.url), 'utf8');
    expect(physics).not.toContain('<MethodTable');
  });

  it('keeps the page within six groups and names a design record file for every row', () => {
    expect(new Set(PLAN.map((t) => t.group)).size).toBeLessThanOrEqual(6);
    for (const row of LADDER) expect(row.record, row.id).toMatch(/^(M|BS-)\d+-.+\.md$/);
  });
});
