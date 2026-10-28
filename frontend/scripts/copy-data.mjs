// Prebuild (T3): copy into public/data/ exactly the files the index declares (see declared.mjs: the index, every
// manifest, every artifact each manifest names, and the index's further `files`), and fail on any that is missing.
// The canonical copies live in ../data/derived (or the tree CAOS_DATA_ROOT names); this overlay is rebuilt from scratch every time, so a file removed
// from the bake never lingers in the site (failure class 9: a filter by extension shipped stale files and missed
// declared ones). A file the readiness document lists as absent in a partial row (a declared-partial bake) is warned
// about and left out; any other absent file stops the build.
import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
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
console.log(`[copy-data] root ${derived}: ${declared.length - tolerated.length} declared files (${index.cases.length} cases, ${tolerated.length} declared absent) -> public/data`);
