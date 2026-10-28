// Prebuild (T3): copy into public/data/ exactly the files the index declares (see declared.mjs: the index, every
// manifest, every artifact each manifest names, and the index's further `files`), and fail on any that is missing.
// The canonical copies live in ../data/derived (or the tree CAOS_DATA_ROOT names); this overlay is rebuilt from scratch every time, so a file removed
// from the bake never lingers in the site (failure class 9: a filter by extension shipped stale files and missed
// declared ones). A file the readiness document lists as absent in a partial row (a declared-partial bake) is warned
// about and left out; any other absent file stops the build.
import { createHash } from 'node:crypto';
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { declaredFiles, INDEX_REL } from './declared.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const repo = join(here, '..', '..');
// CAOS_DATA_ROOT selects the provider tree (absolute, or relative to the repository root); the default is the bake.
const root = process.env.CAOS_DATA_ROOT?.trim() || 'data/derived';
const derived = isAbsolute(root) ? root : resolve(repo, root);
// CAOS_PUBLIC_DIR and CAOS_MODELS_DIR exist for the test of this script (declared.test.ts); a build never sets them.
const out = process.env.CAOS_PUBLIC_DIR?.trim() || join(here, '..', 'public', 'data');
const modelsDir = process.env.CAOS_MODELS_DIR?.trim() || join(repo, 'models');

if (!existsSync(join(derived, INDEX_REL))) {
  console.error(`[copy-data] ${INDEX_REL} is missing under ${derived}: run the pipeline first (scripts/precompute)`);
  process.exit(1);
}
const { index, declared, missing, tolerated, problems } = declaredFiles(derived);

// DinHot's further declared files (catalog rows benchmark-results and model-metrics): documents of the bake that the Benchmark views and the
// workbench's Pareto view read. They are required, unless the readiness document says the row is `missing` (the views then say not available
// yet, with the reason, which is the catalog's behaviour for an unbaked benchmark).
const PRODUCT_FILES = [
  { rel: 'benchmark/results.json', row: 'benchmark-results' },
  { rel: 'models/metrics.json', row: 'model-metrics' },
];
let readinessDoc = null;
try {
  readinessDoc = JSON.parse(readFileSync(join(derived, 'readiness.json'), 'utf8'));
} catch {
  readinessDoc = null;
}
const rowState = (id) => readinessDoc?.contracts?.find((c) => c.id === id)?.state;
for (const f of PRODUCT_FILES) {
  declared.push(f.rel);
  if (!existsSync(join(derived, f.rel))) {
    missing.push(f.rel);
    if (rowState(f.row) === 'missing') tolerated.push(f.rel);
  }
}

// The learned models (catalog rows cgh-net and warmstart-model): the card and the graph of a released model sit in the repository's models/
// directory, not in the bake, and are copied beside the bake's documents (the site reads them from data/models/). No card means no released
// model (the baseline answers). A card whose graph is absent, or whose sha256 or size is not the graph's, stops the build: the browser would
// refuse it at run time, and a site must not ship a model it will refuse.
const MODEL_CARDS = ['cgh-net.json', 'warmstart.json'];
const models = [];
const modelProblems = [];
for (const name of MODEL_CARDS) {
  const cardAt = join(modelsDir, name);
  if (!existsSync(cardAt)) continue;
  let card;
  try {
    card = JSON.parse(readFileSync(cardAt, 'utf8'));
  } catch (e) {
    modelProblems.push(`models/${name}: not JSON (${e.message})`);
    continue;
  }
  const graphAt = join(modelsDir, String(card.onnx ?? '').replace(/^models\//, ''));
  if (!card.onnx || !existsSync(graphAt)) {
    modelProblems.push(`models/${name}: names the graph ${card.onnx}, which is absent`);
    continue;
  }
  const bytes = readFileSync(graphAt);
  if (bytes.length !== card.bytes || createHash('sha256').update(bytes).digest('hex') !== card.sha256) {
    modelProblems.push(`models/${name}: the graph ${card.onnx} is not the one its card describes (size or sha256)`);
    continue;
  }
  models.push({ from: cardAt, rel: `models/${name}` }, { from: graphAt, rel: String(card.onnx) });
}
if (modelProblems.length) problems.push(...modelProblems);

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
for (const m of models) {
  mkdirSync(dirname(join(out, m.rel)), { recursive: true });
  cpSync(m.from, join(out, m.rel));
}
console.log(`[copy-data] root ${derived}: ${declared.length - tolerated.length} declared files (${index.cases.length} cases, ${tolerated.length} declared absent), ${models.length / 2} released model(s) -> public/data`);
