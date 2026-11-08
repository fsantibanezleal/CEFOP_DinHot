// Prebuild (T3): copy into public/data/ exactly the files the index declares (see declared.mjs: the index, every
// manifest, every artifact each manifest names, and the index's further `files`), and fail on any that is missing.
// The canonical copies live in ../data/derived (or the tree CAOS_DATA_ROOT names); this overlay is rebuilt from scratch every time, so a file removed
// from the bake never lingers in the site (failure class 9: a filter by extension shipped stale files and missed
// declared ones). A file the readiness document lists as absent in a partial row (a declared-partial bake) is warned
// about and left out; any other absent file stops the build.
// Product hook (0.15.005): a product that serves further files beyond its index (a benchmark document, model metrics, released
// model cards) puts that in its own module `copy-data.product.mjs` next to this script and takes this file verbatim. Its default
// export is called once, after the declared files are copied into the rebuilt overlay, with `{ derived, out, repo, readiness }`
// (the data tree, the overlay folder, the repository root, the parsed readiness document or null) and returns
// `{ copied, absent, problems }`, arrays of strings: the paths (relative to `out`) it copied, the paths it leaves out as declared
// absent (each printed as a WARN line), and the problems that stop the build. A hook that throws, returns another shape, or
// reports a path outside `out` or a copied file that is not there stops the build. No module: the output is that of 0.15.004.
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { declaredFiles, INDEX_REL } from './declared.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const repo = join(here, '..', '..');
// CAOS_DATA_ROOT selects the provider tree (absolute, or relative to the repository root); the default is the bake.
const root = process.env.CAOS_DATA_ROOT?.trim() || 'data/derived';
const derived = isAbsolute(root) ? root : resolve(repo, root);
const out = join(here, '..', 'public', 'data');

if (!existsSync(join(derived, INDEX_REL))) {
  console.error(`[copy-data] ${INDEX_REL} is missing under ${derived}: run the pipeline first (scripts/precompute)`);
  process.exit(1);
}
const { index, declared, missing, tolerated, problems } = declaredFiles(derived);
const stopping = missing.filter((rel) => !tolerated.includes(rel));
for (const rel of tolerated) console.warn(`[copy-data] WARN ${rel} is absent, as readiness.json declares (partial): the site says not available yet`);
if (stopping.length || problems.length) {
  if (stopping.length) console.error(`[copy-data] declared but missing under ${derived}:\n  ${stopping.join('\n  ')}`);
  if (problems.length) console.error(`[copy-data] ${problems.join('\n  ')}`);
  process.exit(1);
}
rmSync(out, { recursive: true, force: true });
for (const rel of declared.filter((r) => !tolerated.includes(r))) {
  mkdirSync(dirname(join(out, rel)), { recursive: true });
  cpSync(join(derived, rel), join(out, rel));
}
let summary = `[copy-data] root ${derived}: ${declared.length - tolerated.length} declared files (${index.cases.length} cases, ${tolerated.length} declared absent) -> public/data`;

const HOOK = 'copy-data.product.mjs';
if (existsSync(join(here, HOOK))) {
  const fail = (lines) => {
    console.error(`[copy-data] ${HOOK}:\n  ${lines.join('\n  ')}`);
    process.exit(1);
  };
  /** A path the hook reports is relative and stays inside the overlay. */
  const inside = (rel) => typeof rel === 'string' && rel !== '' && !isAbsolute(rel) && !/^[a-zA-Z]:/.test(rel) &&
    !relative(out, resolve(out, rel)).split(/[\\/]/).includes('..') && relative(out, resolve(out, rel)) !== '';
  let readiness = null;
  try {
    readiness = JSON.parse(readFileSync(join(derived, 'readiness.json'), 'utf8'));
  } catch {
    readiness = null;
  }
  let result;
  try {
    const hook = (await import(pathToFileURL(join(here, HOOK)).href)).default;
    if (typeof hook !== 'function') fail(['the default export is not a function']);
    result = await hook({ derived, out, repo, readiness });
  } catch (error) {
    fail([`threw: ${error?.stack ?? error}`]);
  }
  const lists = ['copied', 'absent', 'problems'];
  if (!result || lists.some((k) => !Array.isArray(result[k]) || result[k].some((s) => typeof s !== 'string'))) {
    fail(['must return { copied, absent, problems }, each an array of strings']);
  }
  const { copied, absent, problems: hookProblems } = result;
  const outside = [...copied, ...absent].filter((rel) => !inside(rel));
  const notThere = copied.filter((rel) => inside(rel) && !existsSync(join(out, rel)));
  if (hookProblems.length || outside.length || notThere.length) {
    fail([
      ...hookProblems,
      ...outside.map((rel) => `reports ${JSON.stringify(rel)}, which is not a path inside public/data`),
      ...notThere.map((rel) => `reports ${rel} as copied, but it is not in public/data`),
    ]);
  }
  for (const rel of absent) console.warn(`[copy-data] WARN ${rel} is absent, as ${HOOK} declares: the site says not available yet`);
  summary += `; ${copied.length} from ${HOOK} (${absent.length} declared absent)`;
}
console.log(summary);
