// The measured gate on this build (caos-shell-gate, ADR-0078): serves dist/ as GitHub Pages does (or as nginx does on a VPS) and walks every
// route, tab and case at five sizes, both themes and both languages, and requires Focus mode in the App. The expected brand is the product
// name from product.json, so the gate refuses to measure any other subject. Extra arguments are passed through, for example
//   npm run gate -- --sizes 1280x800 --themes light   (a quick pass while working)
//   npm run gate -- --url https://<domain>           (the deployed origin, after a deploy)
//
// The App is what product.json says it is (WB-014, WB-015; shell 0.19.1):
//   "app": "workbench" (the default)  the case workbench: the gate measures it as such.
//   "app": "surface"                  a hub, an explorer or a console (SurfacePage): the gate is told with `--workbench ''` and measures
//                                     the App route's views, G18 walking every view that offers the Focus control.
// --require-focus is always in effect (ADR-0070): an App built from the template must carry Focus mode (G18), and no extra argument
// turns the requirement off. The one exception is a surface App with no simulation, which sets "focus": false with a "focus_reason" in
// product.json and the same reason on the SDD's ADR-0070 row ("not applicable: <reason>"); the runner reads both and refuses to run when
// they do not agree. scripts/check_sdd.py holds the same rules in CI.
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', '..');
const product = JSON.parse(readFileSync(join(root, 'product.json'), 'utf8'));

const KINDS = ['workbench', 'surface'];
const MIN_REASON_WORDS = 8;
const PLACEHOLDER = /^(?:tbd|tba|tbc|todo|fixme|xxx|lorem|ipsum|placeholder|n\/a|na|none|unknown)$/i;
const NOT_APPLICABLE = /^not applicable:\s*(.+)$/i;

const squash = (text) => String(text).replace(/\s+/g, ' ').trim();

/** The findings on the App's kind, from product.json and the SDD text (null when the SDD is absent). Empty: the declaration holds. */
function appKindProblems(doc, sddText) {
  const out = [];
  const app = doc.app === undefined ? 'workbench' : doc.app;
  if (!KINDS.includes(app)) out.push(`product.json "app" is ${JSON.stringify(app)}: it must be "workbench" (the default) or "surface"`);
  if (doc.focus !== undefined && typeof doc.focus !== 'boolean') out.push('product.json "focus" must be true or false');
  const waived = doc.focus === false;
  const reason = typeof doc.focus_reason === 'string' ? squash(doc.focus_reason) : '';
  if (!waived && doc.focus_reason !== undefined) {
    out.push('product.json has a "focus_reason" but "focus" is not false: remove the reason, or record the waiver with "focus": false');
  }
  if (waived) {
    if (app !== 'surface') out.push('product.json "focus": false is valid only with "app": "surface": a workbench App cannot waive Focus mode (ADR-0070, WB-014)');
    const words = reason.split(' ').filter(Boolean);
    if (!reason) out.push('product.json "focus": false needs a non-empty "focus_reason" saying why ADR-0070 does not apply');
    else if (words.length < MIN_REASON_WORDS) out.push(`product.json "focus_reason" has ${words.length} word(s): at least ${MIN_REASON_WORDS} are needed to say why ADR-0070 does not apply`);
    else if (words.some((w) => PLACEHOLDER.test(w.replace(/[^\w/]/g, ''))) || /<[^>]*>|\.\.\./.test(reason)) out.push('product.json "focus_reason" is placeholder text: write the real reason');
  }
  if (sddText === null) {
    if (waived) out.push('docs/design/SDD.md is missing: the waiver is confirmed by its ADR-0070 row');
    return out;
  }
  const row = sddText.split('\n').find((line) => /^\s*\|\s*ADR-0070\s*\|/.test(line));
  const cells = row ? row.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim()) : [];
  const stated = cells.map((c) => NOT_APPLICABLE.exec(c)).find(Boolean);
  if (waived) {
    if (!row) out.push('docs/design/SDD.md has no ADR-0070 row in its ADR fit table: a waiver of Focus mode is recorded there as "not applicable: <reason>"');
    else if (!stated) out.push('docs/design/SDD.md ADR-0070 row does not say "not applicable: <reason>": the waiver in product.json "focus_reason" is not recorded there');
    else if (reason && squash(stated[1]) !== reason) out.push(`docs/design/SDD.md ADR-0070 row gives a reason that differs from product.json "focus_reason" (SDD: "${squash(stated[1])}"; product.json: "${reason}")`);
  } else if (stated) {
    out.push('docs/design/SDD.md ADR-0070 row says "not applicable" but product.json records no waiver ("focus": false with a "focus_reason"): Focus mode applies');
  }
  return out;
}

/**
 * While Focus is required, the pass-through arguments may not redirect what G18 measures: `--require-focus` stays on the command
 * line, but a run that moves the workbench routes (`--workbench`), the surface's App route (`--app-route`, a surface only) or leaves the
 * App route out of `--routes` makes the Focus check measure nothing and pass. Empty: the arguments are fine.
 */
function redirectProblems(doc, extra) {
  const out = [];
  const value = (flag) => { const at = extra.indexOf(flag); return at < 0 ? null : (extra[at + 1] ?? ''); };
  const surface = doc.app === 'surface';
  if (extra.includes('--workbench')) out.push('--workbench: the kind of App comes from product.json (app); a run cannot move the routes G18 measures while --require-focus applies');
  if (extra.includes('--app-route') && !surface) out.push('--app-route is valid only for "app": "surface" (a workbench App is measured at --workbench, /app)');
  const routes = value('--routes');
  if (routes !== null) {
    const appRoute = (surface ? value('--app-route') : null) || '/app';
    const trim = (r) => r.trim().replace(/(.)\/+$/, '$1');
    if (!routes.split(',').map(trim).includes(trim(appRoute))) out.push(`--routes ${routes} leaves out the App route ${appRoute}, so the Focus check would measure nothing`);
  }
  return out.map((p) => `${p} (--require-focus, ADR-0070)`);
}

/** The arguments of the shell gate for this product: the App's kind, Focus, the served build and the pass-through arguments. */
function gateArguments({ doc, deploy, extra, dist, base, out }) {
  const surface = doc.app === 'surface';
  const waived = doc.focus === false;
  const serving = !extra.includes('--url');
  const served = serving ? ['--serve', dist] : [];
  if (base && serving) served.push('--base-path', base);
  // On a VPS the build is served by nginx (try_files $uri $uri/ /index.html): no 404.html, so the gate serves it the same way.
  if (serving && deploy === 'vps') served.push('--spa-fallback');
  return [...served, ...(surface ? ['--workbench', ''] : []), '--expect-brand', doc.name, ...(waived ? [] : ['--require-focus']), '--out', out, ...extra];
}

const sddPath = join(root, 'docs', 'design', 'SDD.md');
const problems = appKindProblems(product, existsSync(sddPath) ? readFileSync(sddPath, 'utf8') : null);
if (problems.length) {
  console.error('gate: the App\'s kind is not declared consistently, so no gate runs:');
  for (const p of problems) console.error(`  - ${p}`);
  process.exit(1);
}
const redirects = product.focus === false ? [] : redirectProblems(product, process.argv.slice(2));
if (redirects.length) {
  console.error('gate: an argument redirects what the Focus check measures, so no gate runs:');
  for (const p of redirects) console.error(`  - ${p}`);
  process.exit(1);
}
const targetPath = join(root, 'deploy', 'TARGET');
const deploy = existsSync(targetPath) ? readFileSync(targetPath, 'utf8').trim() : '';
const require = createRequire(import.meta.url);
const bin = join(dirname(require.resolve('@fasl-work/caos-app-shell/package.json')), 'bin', 'caos-shell-gate.mjs');
const args = gateArguments({
  doc: product, deploy, extra: process.argv.slice(2), dist: join(here, '..', 'dist'), base: process.env.VITE_BASE, out: join(here, '..', 'gate-output'),
});
const run = spawnSync(process.execPath, [bin, ...args], { stdio: 'inherit' });
process.exit(run.status ?? 1);
