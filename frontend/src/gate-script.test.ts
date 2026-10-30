// The gate this build runs (scripts/gate.mjs) measures the App as what product.json says it is (a workbench by default, or a
// surface) and fails an App without Focus mode: --require-focus is always in effect, whatever extra arguments a run passes, and
// it is dropped only for a surface App that records why ADR-0070 does not apply, in product.json and on the SDD's ADR-0070 row
// (WB-014, WB-015; shell 0.19.1, ADR-0070). The runner is executed here against a stub shell gate that records its arguments.
import { spawnSync } from 'node:child_process';
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterAll, describe, expect, it } from 'vitest';

const frontend = fileURLToPath(new URL('..', import.meta.url));
const gate = readFileSync(new URL('../scripts/gate.mjs', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8')) as { scripts: Record<string, string> };
const realProduct = JSON.parse(readFileSync(new URL('../../product.json', import.meta.url), 'utf8')) as Record<string, unknown>;
const realSdd = readFileSync(new URL('../../docs/design/SDD.md', import.meta.url), 'utf8');

const REASON = 'this hub only links to studies and runs no simulation or dynamic synthetic scenario';
const ROW_PREFIX = '| ADR-0070 |';
const roots: string[] = [];

type Run = { status: number | null; args: string[] | null; stderr: string; stdout: string };

/** A throwaway product tree: this runner, a product.json, an SDD, a deploy target and a stub shell gate that writes its arguments. */
function run(options: { product?: Record<string, unknown>; sdd?: string; target?: string; extra?: string[] } = {}): Run {
  const root = mkdtempSync(join(tmpdir(), 'gate-runner-'));
  roots.push(root);
  mkdirSync(join(root, 'frontend', 'scripts'), { recursive: true });
  mkdirSync(join(root, 'docs', 'design'), { recursive: true });
  mkdirSync(join(root, 'deploy'), { recursive: true });
  cpSync(join(frontend, 'scripts', 'gate.mjs'), join(root, 'frontend', 'scripts', 'gate.mjs'));
  writeFileSync(join(root, 'product.json'), JSON.stringify({ ...realProduct, ...options.product }));
  writeFileSync(join(root, 'docs', 'design', 'SDD.md'), options.sdd ?? realSdd);
  writeFileSync(join(root, 'deploy', 'TARGET'), `${options.target ?? 'pages'}\n`);
  const shell = join(root, 'frontend', 'node_modules', '@fasl-work', 'caos-app-shell');
  mkdirSync(join(shell, 'bin'), { recursive: true });
  writeFileSync(join(shell, 'package.json'), '{"name":"@fasl-work/caos-app-shell","version":"0.0.0"}');
  writeFileSync(join(shell, 'bin', 'caos-shell-gate.mjs'), "import { writeFileSync } from 'node:fs';\nwriteFileSync(process.env.STUB_OUT, JSON.stringify(process.argv.slice(2)));\n");
  const out = join(root, 'stub-args.json');
  const r = spawnSync(process.execPath, [join(root, 'frontend', 'scripts', 'gate.mjs'), ...(options.extra ?? [])], {
    cwd: join(root, 'frontend'), encoding: 'utf8', env: { ...process.env, STUB_OUT: out },
  });
  let args: string[] | null = null;
  try {
    args = (JSON.parse(readFileSync(out, 'utf8')) as string[]).map((a) => (a.startsWith(root) ? `<root>${a.slice(root.length)}` : a));
  } catch {
    args = null;
  }
  return { status: r.status, args, stderr: r.stderr, stdout: r.stdout };
}

/** The SDD with the ADR-0070 row's rule cell replaced. */
function sddWith(rule: string): string {
  return realSdd.split('\n').map((line) => (line.startsWith(ROW_PREFIX) ? `${ROW_PREFIX} ${rule} | the gate runner without \`--require-focus\` |` : line)).join('\n');
}

const waiver = { app: 'surface', focus: false, focus_reason: REASON };
const waivedSdd = sddWith(`not applicable: ${REASON}`);

afterAll(() => {
  for (const root of roots) rmSync(root, { recursive: true, force: true });
});

describe('the gate script', () => {
  it('passes --require-focus to the shell gate, so every App built from the template must carry Focus mode', () => {
    expect(gate).toMatch(/'--require-focus'/);
  });

  it('adversarial: the runner of the previous release, without the flag, or with the flag after the pass-through arguments, is refused (WB-014)', () => {
    const holds = (source: string) => source.includes("'--require-focus'") && source.indexOf("'--require-focus'") < source.indexOf('...extra');
    expect(holds(gate)).toBe(true);
    expect(holds(gate.replace("...(waived ? [] : ['--require-focus']), ", ''))).toBe(false);
    expect(holds(gate.replace("...(waived ? [] : ['--require-focus']), '--out', out, ...extra]", "'--out', out, ...extra, '--require-focus']"))).toBe(false);
  });

  it('puts --require-focus before the pass-through arguments and the npm script does not drop it', () => {
    expect(gate.indexOf("'--require-focus'")).toBeLessThan(gate.indexOf('...extra'));
    expect(pkg.scripts.gate).toBe('node scripts/gate.mjs');
  });
});

describe('the gate runner by the App kind (WB-014, WB-015)', () => {
  it('a workbench, with no app field: --require-focus and no --workbench, as before the App had a kind', () => {
    const r = run();
    expect(r.status).toBe(0);
    expect(r.args).toContain('--require-focus');
    expect(r.args).not.toContain('--workbench');
    expect(r.args).not.toContain('--spa-fallback');
  });

  it('a workbench named "workbench" runs the same arguments as one with no field', () => {
    expect(run({ product: { app: 'workbench' } }).args).toEqual(run().args);
  });

  it('a surface with Focus: --workbench with an empty value, and --require-focus', () => {
    const r = run({ product: { app: 'surface' } });
    expect(r.status).toBe(0);
    const at = r.args!.indexOf('--workbench');
    expect(at).toBeGreaterThanOrEqual(0);
    expect(r.args![at + 1]).toBe('');
    expect(r.args).toContain('--require-focus');
  });

  it('a surface with a confirmed waiver: --workbench with an empty value and no --require-focus', () => {
    const r = run({ product: waiver, sdd: waivedSdd });
    expect(r.status).toBe(0);
    const at = r.args!.indexOf('--workbench');
    expect(r.args![at + 1]).toBe('');
    expect(r.args).not.toContain('--require-focus');
  });

  it('adversarial: no extra argument removes --require-focus when it applies', () => {
    for (const product of [{}, { app: 'surface' }]) {
      for (const extra of [[], ['--url', 'https://example.org'], ['--sizes', '1280x800', '--themes', 'light']]) {
        expect(run({ product, extra }).args, JSON.stringify([product, extra])).toContain('--require-focus');
      }
    }
  });

  it('adversarial: a waiver the SDD does not carry is refused, and the shell gate never runs', () => {
    const r = run({ product: waiver });
    expect(r.status).not.toBe(0);
    expect(r.args).toBeNull();
    expect(r.stderr).toContain('ADR-0070');
    expect(r.stderr).toContain('focus_reason');
  });

  it('adversarial: a waiver whose SDD row gives another reason is refused', () => {
    const r = run({ product: waiver, sdd: sddWith('not applicable: the App is a console with an engine view that simulates a policy') });
    expect(r.status).not.toBe(0);
    expect(r.args).toBeNull();
    expect(r.stderr).toContain('focus_reason');
  });

  it('adversarial: a waiver on a workbench is refused', () => {
    const r = run({ product: { focus: false, focus_reason: REASON }, sdd: waivedSdd });
    expect(r.status).not.toBe(0);
    expect(r.args).toBeNull();
    expect(r.stderr).toContain('"focus"');
  });

  it('adversarial: a waiver with no reason, or a reason under 8 words, is refused', () => {
    expect(run({ product: { app: 'surface', focus: false }, sdd: waivedSdd }).args).toBeNull();
    const short = 'a hub of links';
    expect(run({ product: { app: 'surface', focus: false, focus_reason: short }, sdd: sddWith(`not applicable: ${short}`) }).args).toBeNull();
  });

  it('adversarial: an unknown app value is refused', () => {
    const r = run({ product: { app: 'console' } });
    expect(r.status).not.toBe(0);
    expect(r.args).toBeNull();
    expect(r.stderr).toContain('"app"');
  });

  it('adversarial: an SDD row that says not applicable with no waiver in product.json is refused', () => {
    expect(run({ sdd: waivedSdd }).args).toBeNull();
  });

  it('adversarial: arguments that redirect what G18 measures are refused while Focus is required (the review plant, WB-014)', () => {
    for (const extra of [['--workbench', '/app', '--routes', '/introduction'], ['--routes', '/introduction'], ['--routes', '/,/introduction'], ['--workbench', '/app']]) {
      const r = run({ product: { app: 'surface' }, extra });
      expect(r.status, JSON.stringify(extra)).not.toBe(0);
      expect(r.args, JSON.stringify(extra)).toBeNull();
      expect(r.stderr).toContain('--require-focus');
    }
    const workbench = run({ extra: ['--app-route', '/x'] });
    expect(workbench.args).toBeNull();
  });

  it('accepts a route list that keeps the App route, and a surface that names its own App route', () => {
    expect(run({ extra: ['--routes', '/,/app'] }).args).toContain('--require-focus');
    expect(run({ product: { app: 'surface' }, extra: ['--app-route', '/console', '--routes', '/,/console'] }).args).toContain('--require-focus');
  });

  it('a confirmed waiver may redirect the routes, since nothing requires Focus', () => {
    expect(run({ product: waiver, sdd: waivedSdd, extra: ['--routes', '/introduction'] }).status).toBe(0);
  });

  it('serves as nginx does when the deploy target is a VPS (--spa-fallback), and not on Pages or against a deployed URL', () => {
    expect(run({ target: 'vps' }).args).toContain('--spa-fallback');
    expect(run({ target: 'pages' }).args).not.toContain('--spa-fallback');
    expect(run({ target: 'vps', extra: ['--url', 'https://example.org'] }).args).not.toContain('--spa-fallback');
  });
});
