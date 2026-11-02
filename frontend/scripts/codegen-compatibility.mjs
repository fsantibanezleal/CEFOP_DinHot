// MIT Redocly 1.34.22 expects the old callable CommonJS minimatch export.
// Adapt just that binding to patched minimatch 11.0.1, before loading OpenAPI TS.
// Exact hashes deliberately refuse dependency updates until reviewed. No loader hook.
import { createHash } from 'node:crypto';
import { lstatSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const ORIGINAL = 'const minimatch = require("minimatch");';
const ADAPTED = 'const { minimatch } = require("minimatch");';
const ORIGINAL_SHA = '896a9acce92e3e5905aa267e895985d57888a87f500d58c29da9c8f9d488ff1c';
const ADAPTED_SHA = '825736f13fb67dc4a1e2157bb51396209c7343cfd00376ed5d923e3e9ff82a18';
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');

export function prepareCodegenCompatibility(frontend = fileURLToPath(new URL('..', import.meta.url))) {
  try {
    const modules = resolve(frontend, 'node_modules');
    // Even a valid vendor file is not ours to modify in a junction/shared store.
    if (lstatSync(modules).isSymbolicLink() || realpathSync(modules) !== modules) {
      throw new Error('linked dependency directory: node_modules must be local');
    }
    function owned(path) {
      const rel = relative(modules, resolve(path));
      if (!rel || isAbsolute(rel) || rel === '..' || rel.startsWith(`..${sep}`)) {
        throw new Error(`Dependency outside local node_modules: ${path}`);
      }
      let current = modules;
      for (const part of rel.split(sep)) {
        current = join(current, part);
        if (lstatSync(current).isSymbolicLink()) throw new Error(`linked dependency: ${current}`);
      }
      if (realpathSync(path) !== resolve(path)) throw new Error(`linked dependency: ${path}`);
      return path;
    }
    function version(path, name, expected) {
      const value = JSON.parse(readFileSync(owned(path), 'utf8'));
      if (value.name !== name || value.version !== expected) {
        throw new Error(`Unsupported ${name} version: expected ${expected}, got ${value.name}@${value.version}`);
      }
    }
    const local = createRequire(join(resolve(frontend), 'package.json'));
    const api = owned(local.resolve('openapi-typescript'));
    // Resolve through the producer rather than assuming Redocly is hoisted.
    const apiManifest = owned(local.resolve('openapi-typescript/package.json'));
    version(apiManifest, 'openapi-typescript', '7.13.0');
    const producer = createRequire(api);
    const utilsPath = owned(producer.resolve('@redocly/openapi-core/lib/utils.js'));
    version(join(dirname(utilsPath), '..', 'package.json'), '@redocly/openapi-core', '1.34.22');
    const redocly = createRequire(utilsPath);
    owned(redocly.resolve('minimatch'));
    version(redocly.resolve('minimatch/package.json'), 'minimatch', '11.0.1');

    const bytes = readFileSync(utilsPath);
    const source = bytes.toString('utf8');
    const hash = sha(bytes);
    const occurrences = (text) => source.split(text).length - 1;
    const original = hash === ORIGINAL_SHA && occurrences(ORIGINAL) === 1 && occurrences(ADAPTED) === 0;
    const adapted = hash === ADAPTED_SHA && occurrences(ORIGINAL) === 0 && occurrences(ADAPTED) === 1;
    if (!original && !adapted) throw new Error(`Unsupported Redocly utils bytes: SHA256 ${hash}`);
    if (lstatSync(utilsPath).nlink !== 1) throw new Error('linked dependency: vendor file has shared hard links');
    const minimatch = redocly('minimatch');
    if (!minimatch || typeof minimatch !== 'object' || typeof minimatch.minimatch !== 'function') {
      throw new Error('Unsupported minimatch export shape: expected named minimatch function');
    }
    if (original) {
      if (redocly.cache[utilsPath]) throw new Error('Redocly utils already loaded: prepare compatibility before importing the consumer');
      const patched = Buffer.from(source.replace(ORIGINAL, ADAPTED), 'utf8');
      if (sha(patched) !== ADAPTED_SHA) throw new Error('Unsupported adapted Redocly utils bytes');
      writeFileSync(utilsPath, patched);
      if (sha(readFileSync(utilsPath)) !== ADAPTED_SHA) throw new Error('Redocly adaptation verification failed');
    }
    return { changed: original, utilsPath };
  } catch (error) {
    const missing = error.code === 'MODULE_NOT_FOUND' || error.code === 'ENOENT';
    throw new Error(`codegen compatibility: ${missing ? 'Missing local dependency; run npm ci in frontend. ' : ''}${error.message}`, { cause: error });
  }
}
