// The build copies the declared files and then calls the product's optional hook scripts/copy-data.product.mjs.
// A product takes this file verbatim: it tests the base script scripts/copy-data.mjs (0.15.005). A product's own tests of
// copy-data.product.mjs live in a product test file of their own, never here.
import { spawnSync } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterAll, describe, expect, it, vi } from 'vitest';

// Every case spawns node on the build script; the default 5 s can time out under a fully loaded CPU (as gate-script.test.ts).
vi.setConfig({ testTimeout: 60_000 });

const SCRIPTS = dirname(fileURLToPath(new URL('../../scripts/copy-data.mjs', import.meta.url)));
const temp = mkdtempSync(join(process.env.CAOS_TEMP_ROOT?.trim() || tmpdir(), 'copy-data-'));
afterAll(() => rmSync(temp, { recursive: true, force: true }));

let count = 0;
/** A throwaway repository: the two base scripts, a minimal baked tree (index with no case, readiness) and an optional hook. */
function build(hook?: string, opts: { index?: unknown } = {}) {
  const repo = join(temp, `r${count++}`);
  mkdirSync(join(repo, 'frontend', 'scripts'), { recursive: true });
  for (const f of ['copy-data.mjs', 'declared.mjs']) copyFileSync(join(SCRIPTS, f), join(repo, 'frontend', 'scripts', f));
  if (hook !== undefined) writeFileSync(join(repo, 'frontend', 'scripts', 'copy-data.product.mjs'), hook);
  const derived = join(repo, 'data', 'derived');
  mkdirSync(join(derived, 'manifests'), { recursive: true });
  writeFileSync(join(derived, 'manifests', 'index.json'), JSON.stringify(opts.index ?? { cases: [] }));
  writeFileSync(join(derived, 'readiness.json'), JSON.stringify({ contracts: [{ id: 'benchmark-results', state: 'available' }] }));
  mkdirSync(join(derived, 'benchmark'), { recursive: true });
  writeFileSync(join(derived, 'benchmark', 'results.json'), '{"ok":true}');
  return { repo, derived, out: join(repo, 'frontend', 'public', 'data') };
}
function run(repo: string) {
  const env = { ...process.env };
  delete env.CAOS_DATA_ROOT;
  const r = spawnSync(process.execPath, [join(repo, 'frontend', 'scripts', 'copy-data.mjs')], { encoding: 'utf8', env });
  return { code: r.status, stdout: r.stdout, stderr: r.stderr };
}
const HOOK_COPY = `import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
export default function hook({ derived, out }) {
  mkdirSync(dirname(join(out, 'benchmark/results.json')), { recursive: true });
  copyFileSync(join(derived, 'benchmark/results.json'), join(out, 'benchmark/results.json'));
  return { copied: ['benchmark/results.json'], absent: [], problems: [] };
}
`;
const hookReturning = (value: string) => `export default function hook() { return ${value}; }\n`;

describe('copy-data.mjs with the product hook', () => {
  it('without a hook module copies the declared files and prints the base summary only', () => {
    const { repo, derived, out } = build();
    const r = run(repo);
    expect(r.code).toBe(0);
    expect(r.stdout.trim()).toBe(`[copy-data] root ${derived}: 2 declared files (0 cases, 0 declared absent) -> public/data`);
    expect(existsSync(join(out, 'manifests', 'index.json'))).toBe(true);
    expect(existsSync(join(out, 'benchmark', 'results.json'))).toBe(false);
  });

  it('lands the file a hook copies in the overlay and counts it in the summary', () => {
    const { repo, out } = build(HOOK_COPY);
    const r = run(repo);
    expect(r.code, r.stderr).toBe(0);
    expect(readFileSync(join(out, 'benchmark', 'results.json'), 'utf8')).toBe('{"ok":true}');
    expect(r.stdout).toContain('2 declared files');
    expect(r.stdout).toContain('1 from copy-data.product.mjs');
  });

  it('calls the hook once with derived, out, repo and the parsed readiness document', () => {
    const { repo, derived, out } = build(`import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
export default function hook(args) {
  writeFileSync(join(args.out, 'args.json'), JSON.stringify({ keys: Object.keys(args).sort(), ...args }));
  return { copied: ['args.json'], absent: [], problems: [] };
}
`);
    const r = run(repo);
    expect(r.code, r.stderr).toBe(0);
    const seen = JSON.parse(readFileSync(join(out, 'args.json'), 'utf8'));
    expect(seen.keys).toEqual(['derived', 'out', 'readiness', 'repo']);
    expect(seen.derived).toBe(derived);
    expect(seen.out).toBe(out);
    expect(seen.repo).toBe(repo);
    expect(seen.readiness.contracts[0].id).toBe('benchmark-results');
  });

  it('passes null as readiness when the document cannot be read as JSON', () => {
    const { repo, derived, out } = build(`import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
export default function hook({ out, readiness }) {
  writeFileSync(join(out, 'r.json'), JSON.stringify({ readiness }));
  return { copied: ['r.json'], absent: [], problems: [] };
}
`);
    writeFileSync(join(derived, 'readiness.json'), 'not json');
    const r = run(repo);
    expect(r.code, r.stderr).toBe(0);
    expect(JSON.parse(readFileSync(join(out, 'r.json'), 'utf8'))).toEqual({ readiness: null });
  });

  it('prints each absent path the hook declares as a WARN line and builds', () => {
    const { repo } = build(hookReturning(`{ copied: [], absent: ['models/metrics.json'], problems: [] }`));
    const r = run(repo);
    expect(r.code).toBe(0);
    expect(r.stderr + r.stdout).toMatch(/\[copy-data\] WARN models\/metrics\.json is absent/);
  });

  it('stops the build with the hook problems', () => {
    const { repo } = build(hookReturning(`{ copied: [], absent: [], problems: ['models/card.json: sha256 differs'] }`));
    const r = run(repo);
    expect(r.code).toBe(1);
    expect(r.stderr).toContain('models/card.json: sha256 differs');
  });

  it('stops the build when the hook throws, with its message', () => {
    const { repo } = build(`export default function hook() { throw new Error('boom from the hook'); }\n`);
    const r = run(repo);
    expect(r.code).toBe(1);
    expect(r.stderr).toContain('boom from the hook');
  });

  it('stops the build when the module has no default function or returns the wrong shape', () => {
    for (const hook of [`export const x = 1;\n`, hookReturning(`{ copied: 'a', absent: [], problems: [] }`), hookReturning('undefined')]) {
      const { repo } = build(hook);
      expect(run(repo).code).toBe(1);
    }
  });

  it('does not run the hook when a declared file is missing', () => {
    const { repo } = build(
      `import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
export default function hook({ repo }) { writeFileSync(join(repo, 'ran.txt'), 'x'); return { copied: [], absent: [], problems: [] }; }
`,
      { index: { cases: [], files: ['contract/missing.json'] } },
    );
    const r = run(repo);
    expect(r.code).toBe(1);
    expect(r.stderr).toContain('contract/missing.json');
    expect(existsSync(join(repo, 'ran.txt'))).toBe(false);
  });

  it('rebuilds the overlay from scratch: a stale file is gone whether or not a hook exists', () => {
    for (const hook of [undefined, HOOK_COPY]) {
      const { repo, out } = build(hook);
      mkdirSync(out, { recursive: true });
      writeFileSync(join(out, 'stale.json'), '{}');
      expect(run(repo).code).toBe(0);
      expect(existsSync(join(out, 'stale.json'))).toBe(false);
    }
  });

  it('adversarial: refuses a copied or absent path that leaves the overlay, or a copied file that is not there', () => {
    const escapes = [
      `{ copied: ['../escape.txt'], absent: [], problems: [] }`,
      `{ copied: ['a/../../escape.txt'], absent: [], problems: [] }`,
      `{ copied: [process.platform === 'win32' ? 'C:/escape.txt' : '/escape.txt'], absent: [], problems: [] }`,
      `{ copied: [], absent: ['../escape.txt'], problems: [] }`,
      `{ copied: ['never-written.json'], absent: [], problems: [] }`,
    ];
    for (const value of escapes) {
      const { repo } = build(hookReturning(value));
      const r = run(repo);
      expect(r.code, value).toBe(1);
      expect(r.stderr, value).toMatch(/copy-data/);
    }
  });
});
