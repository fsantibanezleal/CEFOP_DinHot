// The files the site serves from data/derived (T3): the index, the readiness document, every manifest it lists, every artifact each
// manifest names (one `artifact`, or a list of `artifacts` for variants baked apart), and the further files the
// index declares in `files` (a product's contract declarations, say). Shared by copy-data.mjs and its test, so the
// rule the build applies is the rule the test checks.
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

export const INDEX_REL = 'manifests/index.json';
/** The readiness document (catalog: Missing-data states): always declared, so a build without it stops. */
export const READINESS_REL = 'readiness.json';

/** The artifact paths a manifest names, in order. */
export function artifactPaths(manifest) {
  if (Array.isArray(manifest.artifacts)) return manifest.artifacts.map((a) => a.path);
  if (manifest.artifact && typeof manifest.artifact.path === 'string') return [manifest.artifact.path];
  return [];
}

/** The paths the readiness document declares absent: the `missing` of every row whose state is `partial` (catalog:
 * Missing-data states). Empty when the document is absent, unreadable or not the readiness shape: nothing is tolerated
 * then, and the build stops on any absent file as before. */
export function declaredAbsent(derived) {
  try {
    const doc = JSON.parse(readFileSync(join(derived, READINESS_REL), 'utf8'));
    const rows = Array.isArray(doc?.contracts) ? doc.contracts : [];
    return rows.filter((r) => r && r.state === 'partial' && Array.isArray(r.missing)).flatMap((r) => r.missing.filter((m) => typeof m === 'string'));
  } catch {
    return [];
  }
}

/** Every declared file under `derived`, the ones missing (`missing`), the part of those the readiness declares absent
 * (`tolerated`: a partial bake builds without them), and the manifests that name no artifact. */
export function declaredFiles(derived) {
  const index = JSON.parse(readFileSync(join(derived, INDEX_REL), 'utf8'));
  const declared = [INDEX_REL, READINESS_REL, ...(Array.isArray(index.files) ? index.files : [])];
  const problems = [];
  for (const entry of index.cases) {
    declared.push(entry.manifest_path);
    const at = join(derived, entry.manifest_path);
    if (!existsSync(at)) continue; // reported among the missing files
    const paths = artifactPaths(JSON.parse(readFileSync(at, 'utf8')));
    if (!paths.length) problems.push(`${entry.manifest_path}: names no artifact (artifact or artifacts)`);
    declared.push(...paths);
  }
  const unique = [...new Set(declared)];
  const absent = unique.filter((rel) => !existsSync(join(derived, rel)));
  const allowed = new Set(declaredAbsent(derived));
  return { index, declared: unique, missing: absent, tolerated: absent.filter((rel) => allowed.has(rel)), problems };
}
