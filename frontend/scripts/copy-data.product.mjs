// DinHot's further site files. The base frontend/scripts/copy-data.mjs (template 0.15.005) copies what the index declares into
// public/data and then calls this product module once, with { derived, out, repo, readiness }; it prints each `absent` as a warning,
// stops the build on any `problems`, and counts `copied` in its summary.
//
// (1) Further documents of the bake (catalog rows benchmark-results and model-metrics), which the Benchmark views and the workbench's
//     Pareto view read. They are required, unless the readiness document says the row is `missing` or `provider`: the views then say
//     not available yet, with the reason, which is the catalog's behaviour for an unbaked benchmark.
// (2) The learned models (catalog rows cgh-net and warmstart-model): the card and the graph of a released model sit in the repository's
//     models/ directory, not in the bake, and are copied beside the bake's documents (the site reads them from data/models/). No card
//     means no released model (the baseline answers). A card whose graph is absent, or whose size or sha256 is not the graph's, stops the
//     build: the browser would refuse it at run time, and a site must not ship a model it will refuse.
import { createHash } from 'node:crypto';
import { cpSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

export const PRODUCT_FILES = [
  { rel: 'benchmark/results.json', row: 'benchmark-results' },
  { rel: 'models/metrics.json', row: 'model-metrics' },
];
export const MODEL_CARDS = ['cgh-net.json', 'warmstart.json'];
const ABSENT_STATES = ['missing', 'provider'];

/** Copy DinHot's further files into `out`; `modelsDir` defaults to the repository's models/ (tests point it elsewhere). */
export default function productFiles({ derived, out, repo, readiness, modelsDir = join(repo, 'models') }) {
  const copied = [];
  const absent = [];
  const problems = [];
  const rowState = (id) => readiness?.contracts?.find((c) => c.id === id)?.state;
  const copy = (from, rel) => {
    mkdirSync(dirname(join(out, rel)), { recursive: true });
    cpSync(from, join(out, rel));
    copied.push(rel);
  };
  for (const f of PRODUCT_FILES) {
    const at = join(derived, f.rel);
    if (existsSync(at)) copy(at, f.rel);
    else if (ABSENT_STATES.includes(rowState(f.row))) absent.push(f.rel);
    else problems.push(`declared but missing under ${derived}: ${f.rel} (readiness row ${f.row} is ${rowState(f.row) ?? 'absent'})`);
  }
  const ready = [];
  for (const name of MODEL_CARDS) {
    const cardAt = join(modelsDir, name);
    if (!existsSync(cardAt)) continue;
    let card;
    try {
      card = JSON.parse(readFileSync(cardAt, 'utf8'));
    } catch (e) {
      problems.push(`models/${name}: not JSON (${e.message})`);
      continue;
    }
    const graphAt = join(modelsDir, String(card.onnx ?? '').replace(/^models\//, ''));
    if (!card.onnx || !existsSync(graphAt)) {
      problems.push(`models/${name}: names the graph ${card.onnx}, which is absent`);
      continue;
    }
    const bytes = readFileSync(graphAt);
    if (bytes.length !== card.bytes || createHash('sha256').update(bytes).digest('hex') !== card.sha256) {
      problems.push(`models/${name}: the graph ${card.onnx} is not the one its card describes (size or sha256)`);
      continue;
    }
    ready.push([cardAt, `models/${name}`], [graphAt, String(card.onnx)]);
  }
  if (!problems.length) for (const [from, rel] of ready) copy(from, rel);
  return { copied, absent, problems };
}
