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
//
// The routes it walks (ADR-0082, 0.15.001): the App (/app), the five documentation routes and the guided-story routes the product
// declares in product.json, key "showcase": { "story_routes": ["/story/<step>", ...] }, in the order of the story. No story route is
// written here: a product with its own steps declares them, and the gate walks exactly those. A product that declares none is
// measured on the App and the documentation routes and is told so; the shell's G21 (--require-showcase, never dropped) and
// scripts/check_sdd.py fail the missing story. A `--routes` list may name only declared routes and must name all of them.
// `--plan` prints the routes and the arguments and exits without running the shell gate.
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', '..');
const product = JSON.parse(readFileSync(join(root, 'product.json'), 'utf8'));

const KINDS = ['workbench', 'surface'];
const BASE_ROUTES = ['/app', '/introduction', '/methodology', '/implementation', '/experiments', '/benchmark'];
const STORY_ROUTE = /^\/story\/[A-Za-z0-9][A-Za-z0-9._~-]*$/;
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

/** The story routes product.json declares (`showcase.story_routes`) and the findings on the declaration. Empty routes: no story. */
function storyRoutes(doc) {
  const showcase = doc.showcase;
  if (showcase === undefined) return { routes: [], problems: [] };
  if (showcase === null || typeof showcase !== 'object' || Array.isArray(showcase)) return { routes: [], problems: ['product.json "showcase" must be an object with "story_routes"'] };
  const declared = showcase.story_routes;
  if (declared === undefined) return { routes: [], problems: [] };
  if (!Array.isArray(declared)) return { routes: [], problems: ['product.json showcase.story_routes must be a list of route paths "/story/<step>"'] };
  const problems = [];
  declared.forEach((route, i) => {
    if (typeof route !== 'string' || !STORY_ROUTE.test(route)) problems.push(`product.json showcase.story_routes[${i}] is ${JSON.stringify(route)}: each entry is one story step, "/story/<step>"`);
    else if (declared.indexOf(route) !== i) problems.push(`product.json showcase.story_routes lists ${route} twice`);
  });
  return { routes: problems.length ? [] : declared, problems };
}

/**
 * While Focus is required, the pass-through arguments may not redirect what G18 measures: `--require-focus` stays on the command
 * line, but a run that moves the workbench routes (`--workbench`), the surface's App route (`--app-route`, a surface only) or leaves the
 * App route out of `--routes` makes the Focus check measure nothing and pass. Empty: the arguments are fine.
 */
function redirectProblems(doc, extra, showcaseRoutes) {
  const out = [];
  const value = (flag) => { const at = extra.indexOf(flag); return at < 0 ? null : (extra[at + 1] ?? ''); };
  const surface = doc.app === 'surface';
  if (extra.includes('--workbench')) out.push('--workbench: the kind of App comes from product.json (app); a run cannot move the routes G18 measures while --require-focus applies');
  if (extra.includes('--app-route') && !surface) out.push('--app-route is valid only for "app": "surface" (a workbench App is measured at --workbench, /app)');
  const routes = value('--routes');
  if (routes !== null) {
    const appRoute = (surface ? value('--app-route') : null) || '/app';
    const trim = (r) => r.trim().replace(/(.)\/+$/, '$1');
    const listed = routes.split(',').map(trim);
    if (!listed.includes(trim(appRoute))) out.push(`--routes ${routes} leaves out the App route ${appRoute}, so the Focus check would measure nothing`);
    const missingStory = showcaseRoutes.filter((route) => !listed.includes(trim(route)));
    if (missingStory.length) out.push(`--routes ${routes} leaves out showcase routes ${missingStory.join(', ')}; ADR-0082 requires all declared story steps and product views`);
    const known = new Set([...showcaseRoutes, trim(appRoute)]);
    const undeclared = listed.filter((route) => !known.has(route));
    if (undeclared.length) out.push(`--routes ${routes} names ${undeclared.join(', ')}, which product.json does not declare: a story step is declared in showcase.story_routes, and the gate walks only the App, the documentation routes and the declared steps`);
  }
  return out.map((p) => `${p} (--require-focus, ADR-0070)`);
}

/** The arguments of the shell gate for this product: the App's kind, Focus, the served build and the pass-through arguments. */
function gateArguments({ doc, deploy, extra, dist, base, out, SHOWCASE_ROUTES }) {
  const surface = doc.app === 'surface';
  const waived = doc.focus === false;
  const serving = !extra.includes('--url');
  const served = serving ? ['--serve', dist] : [];
  if (base && serving) served.push('--base-path', base);
  // On a VPS the build is served by nginx (try_files $uri $uri/ /index.html): no 404.html, so the gate serves it the same way.
  if (serving && deploy === 'vps') served.push('--spa-fallback');
  return [...served, ...(surface ? ['--workbench', ''] : []), '--expect-brand', doc.name, ...(waived ? [] : ['--require-focus']), '--require-showcase', '--routes', SHOWCASE_ROUTES, '--out', out, ...extra];
}

const sddPath = join(root, 'docs', 'design', 'SDD.md');
const problems = appKindProblems(product, existsSync(sddPath) ? readFileSync(sddPath, 'utf8') : null);
if (problems.length) {
  console.error('gate: the App\'s kind is not declared consistently, so no gate runs:');
  for (const p of problems) console.error(`  - ${p}`);
  process.exit(1);
}
const story = storyRoutes(product);
if (story.problems.length) {
  console.error('gate: the story routes are not declared correctly, so no gate runs:');
  for (const p of story.problems) console.error(`  - ${p}`);
  process.exit(1);
}
const showcaseRoutes = [...BASE_ROUTES, ...story.routes];
const SHOWCASE_ROUTES = showcaseRoutes.join(',');
const planOnly = process.argv.includes('--plan');
const extra = process.argv.slice(2).filter((a) => a !== '--plan');
const redirects = redirectProblems(product, extra, showcaseRoutes);
if (redirects.length) {
  console.error('gate: an argument redirects what the Focus check measures, so no gate runs:');
  for (const p of redirects) console.error(`  - ${p}`);
  process.exit(1);
}
const targetPath = join(root, 'deploy', 'TARGET');
const deploy = existsSync(targetPath) ? readFileSync(targetPath, 'utf8').trim() : '';
const args = gateArguments({
  doc: product, deploy, extra, dist: join(here, '..', 'dist'), base: process.env.VITE_BASE, out: join(here, '..', 'gate-output'), SHOWCASE_ROUTES,
});
const at = args.lastIndexOf('--routes');
console.log(`gate: routes ${args[at + 1]}`);
if (!story.routes.length) console.log('gate: no story is declared in product.json (showcase.story_routes): the App and the documentation routes are measured, and G21 reports the missing story (ADR-0082)');
if (planOnly) {
  console.log(`gate: arguments ${JSON.stringify(args)}`);
  process.exit(0);
}
const require = createRequire(import.meta.url);
const bin = join(dirname(require.resolve('@fasl-work/caos-app-shell/package.json')), 'bin', 'caos-shell-gate.mjs');
const run = spawnSync(process.execPath, [bin, ...args], { stdio: 'inherit' });
process.exit(run.status ?? 1);
