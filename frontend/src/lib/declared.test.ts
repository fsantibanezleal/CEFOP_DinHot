// The build copies what the index declares: one artifact or several per manifest, and the index's further files.
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
// @ts-expect-error: a plain ES module shared with the build script
import { artifactPaths, declaredFiles, READINESS_REL } from '../../scripts/declared.mjs';

const root = mkdtempSync(join(tmpdir(), 'declared-'));
afterAll(() => rmSync(root, { recursive: true, force: true }));
const put = (rel: string, doc: unknown) => {
  mkdirSync(dirname(join(root, rel)), { recursive: true });
  writeFileSync(join(root, rel), JSON.stringify(doc));
};

describe('the declared files of the site', () => {
  it('reads one artifact or a list of artifacts', () => {
    expect(artifactPaths({ artifact: { path: 'A/trace.json' } })).toEqual(['A/trace.json']);
    expect(artifactPaths({ artifacts: [{ path: 'B/v1.json' }, { path: 'B/v2.json' }] })).toEqual(['B/v1.json', 'B/v2.json']);
    expect(artifactPaths({})).toEqual([]);
  });
  it('names every missing declared file, and a manifest that names no artifact', () => {
    put('manifests/index.json', {
      files: ['contract/index.json'],
      cases: [
        { case_id: 'A', manifest_path: 'manifests/A.json' },
        { case_id: 'B', manifest_path: 'manifests/B.json' },
        { case_id: 'C', manifest_path: 'manifests/C.json' },
      ],
    });
    put('manifests/A.json', { artifact: { path: 'A/trace.json' } });
    put('A/trace.json', {});
    put('manifests/B.json', { artifacts: [{ path: 'B/v1.json' }, { path: 'B/v2.json' }] });
    put('B/v1.json', {});
    put('manifests/C.json', { title: 'no artifact' });
    put('readiness.json', {});
    const { declared, missing, problems } = declaredFiles(root);
    expect(declared).toEqual([
      'manifests/index.json', 'readiness.json', 'contract/index.json', 'manifests/A.json', 'A/trace.json', 'manifests/B.json',
      'B/v1.json', 'B/v2.json', 'manifests/C.json',
    ]);
    expect(missing).toEqual(['contract/index.json', 'B/v2.json']);
    expect(problems).toEqual(['manifests/C.json: names no artifact (artifact or artifacts)']);
  });
  it('declares the readiness document right after the index, and reports it missing when absent', () => {
    expect(READINESS_REL).toBe('readiness.json');
    const bare = join(root, 'bare');
    mkdirSync(join(bare, 'manifests'), { recursive: true });
    writeFileSync(join(bare, 'manifests/index.json'), JSON.stringify({ cases: [] }));
    const { declared, missing } = declaredFiles(bare);
    expect(declared).toEqual(['manifests/index.json', 'readiness.json']);
    expect(missing).toEqual(['readiness.json']);
  });
});

describe('a declared-partial bake builds', () => {
  const partial = join(root, 'partial');
  const putPartial = (rel: string, doc: unknown) => {
    mkdirSync(dirname(join(partial, rel)), { recursive: true });
    writeFileSync(join(partial, rel), JSON.stringify(doc));
  };
  const readiness = (missing: string[], state = 'partial') => ({
    contracts: [{ id: 'trace', state, missing }, { id: 'params-record', state: 'partial', missing: ['some_case_id'] }],
  });
  const setup = (doc: unknown) => {
    putPartial('manifests/index.json', { cases: [{ case_id: 'A', manifest_path: 'manifests/A.json' }, { case_id: 'B', manifest_path: 'manifests/B.json' }] });
    putPartial('manifests/A.json', { artifact: { path: 'A/trace.json' } });
    putPartial('manifests/B.json', { artifact: { path: 'B/trace.json' } });
    putPartial('A/trace.json', {});
    if (doc !== null) putPartial('readiness.json', doc);
  };
  it('tolerates an absent file that the readiness lists in a partial row, and only that one', () => {
    setup(readiness(['B/trace.json']));
    const { missing, tolerated } = declaredFiles(partial);
    expect(missing).toEqual(['B/trace.json']);
    expect(tolerated).toEqual(['B/trace.json']);
  });
  it('does not tolerate an absent file that the readiness does not list', () => {
    setup(readiness(['A/other.json']));
    const { missing, tolerated } = declaredFiles(partial);
    expect(missing).toEqual(['B/trace.json']);
    expect(tolerated).toEqual([]);
  });
  it('lists nothing as declared-absent for a row whose state is not partial', () => {
    setup(readiness(['B/trace.json'], 'available'));
    expect(declaredFiles(partial).tolerated).toEqual([]);
  });
  it('tolerates nothing when the readiness is absent or unreadable', () => {
    setup(null);
    expect(declaredFiles(partial).tolerated).toEqual([]);
    putPartial('readiness.json', 'not an object');
    expect(declaredFiles(partial).tolerated).toEqual([]);
  });
});
