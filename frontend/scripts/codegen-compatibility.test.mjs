import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { linkSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, statSync, symlinkSync, unlinkSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { test } from 'node:test';
import { prepareCodegenCompatibility } from './codegen-compatibility.mjs';

const local = createRequire(new URL('../package.json', import.meta.url));
const producer = createRequire(local.resolve('openapi-typescript'));
const installed = readFileSync(producer.resolve('@redocly/openapi-core/lib/utils.js'), 'utf8');
const original = installed.replace('const { minimatch } = require("minimatch");', 'const minimatch = require("minimatch");');
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
assert.equal(digest(original), '896a9acce92e3e5905aa267e895985d57888a87f500d58c29da9c8f9d488ff1c');

function fixture(t) {
  const temp = process.env.CAOS_TEMP_ROOT || tmpdir();
  mkdirSync(temp, { recursive: true });
  const base = mkdtempSync(join(resolve(temp), 'codegen-fixture-'));
  const frontend = join(base, 'frontend');
  const modules = join(frontend, 'node_modules');
  const api = join(modules, 'openapi-typescript');
  const redoc = join(api, 'node_modules', '@redocly', 'openapi-core');
  const minimatch = join(modules, 'minimatch');
  const utils = join(redoc, 'lib', 'utils.js');
  const links = [];
  t.after(() => {
    for (const link of links) {
      assert.ok(lstatSync(link).isSymbolicLink());
      unlinkSync(link);
    }
    rmSync(base, { recursive: true });
  });
  const put = (file, contents) => { mkdirSync(resolve(file, '..'), { recursive: true }); writeFileSync(file, contents); };
  const manifest = (dir, name, version) => put(join(dir, 'package.json'), JSON.stringify({ name, version, main: 'index.cjs' }));
  put(join(frontend, 'package.json'), '{}');
  manifest(api, 'openapi-typescript', '7.13.0');
  put(join(api, 'index.cjs'), 'throw new Error("producer imported before preparation");');
  manifest(redoc, '@redocly/openapi-core', '1.34.22');
  put(utils, original);
  manifest(minimatch, 'minimatch', '11.0.1');
  put(join(minimatch, 'index.cjs'), 'exports.minimatch = () => true;');
  return { base, frontend, modules, api, redoc, minimatch, utils, put, manifest, links };
}

test('adversarial: exact original bytes adapt once and preserve every other byte', (t) => {
  const f = fixture(t);
  const first = prepareCodegenCompatibility(f.frontend);
  assert.equal(first.changed, true);
  assert.equal(first.utilsPath, f.utils);
  const adapted = readFileSync(f.utils);
  assert.equal(digest(adapted), '825736f13fb67dc4a1e2157bb51396209c7343cfd00376ed5d923e3e9ff82a18');
  assert.equal(adapted.toString().replace('const { minimatch } = require("minimatch");', 'const minimatch = require("minimatch");'), original);
  const before = statSync(f.utils).mtimeNs ?? statSync(f.utils).mtimeMs;
  assert.equal(prepareCodegenCompatibility(f.frontend).changed, false);
  assert.equal(statSync(f.utils).mtimeNs ?? statSync(f.utils).mtimeMs, before);
  assert.deepEqual(readFileSync(f.utils), adapted);
});

test('adversarial: already adapted bytes are accepted without a write', (t) => {
  const f = fixture(t);
  f.put(f.utils, original.replace('const minimatch = require("minimatch");', 'const { minimatch } = require("minimatch");'));
  const before = statSync(f.utils).mtimeMs;
  assert.equal(prepareCodegenCompatibility(f.frontend).changed, false);
  assert.equal(statSync(f.utils).mtimeMs, before);
});

for (const [key, name, version] of [['api', 'openapi-typescript', '7.13.1'], ['redoc', '@redocly/openapi-core', '2.7.0'], ['minimatch', 'minimatch', '11.0.0']]) {
  test(`adversarial: unsupported ${name} version fails before vendor mutation`, (t) => {
    const f = fixture(t);
    f.manifest(f[key], name, version);
    assert.throws(() => prepareCodegenCompatibility(f.frontend), /Unsupported .* version/);
    assert.equal(readFileSync(f.utils, 'utf8'), original);
  });
}

for (const [name, transform] of [
  ['unknown bytes', (s) => `${s}\n// changed vendor bytes\n`],
  ['absent binding', (s) => s.replace('const minimatch = require("minimatch");', '')],
  ['duplicate binding', (s) => `${s}\nconst minimatch = require("minimatch");\n`],
  ['mixed bindings', (s) => `${s}\nconst { minimatch } = require("minimatch");\n`],
  ['tampered adapted bytes', (s) => `${s.replace('const minimatch = require("minimatch");', 'const { minimatch } = require("minimatch");')}\n// changed\n`],
]) {
  test(`adversarial: ${name} fails closed`, (t) => {
    const f = fixture(t);
    const changed = transform(original);
    f.put(f.utils, changed);
    assert.throws(() => prepareCodegenCompatibility(f.frontend), /Unsupported Redocly utils bytes/);
    assert.equal(readFileSync(f.utils, 'utf8'), changed);
  });
}

test('adversarial: wrong named export fails before vendor mutation', (t) => {
  const f = fixture(t);
  f.put(join(f.minimatch, 'index.cjs'), 'module.exports = () => true;');
  assert.throws(() => prepareCodegenCompatibility(f.frontend), /Unsupported minimatch export shape/);
  assert.equal(readFileSync(f.utils, 'utf8'), original);
});

test('adversarial: missing dependency reports local install requirement', (t) => {
  const f = fixture(t);
  unlinkSync(join(f.minimatch, 'index.cjs'));
  assert.throws(() => prepareCodegenCompatibility(f.frontend), /codegen compatibility:.*local.*npm ci/);
  assert.equal(readFileSync(f.utils, 'utf8'), original);
});

for (const target of ['redoc', 'minimatch', 'modules']) {
  test(`adversarial: external ${target} junction or symlink is refused`, (t) => {
    const f = fixture(t);
    const destination = join(f.base, 'outside');
    // Move only this disposable fixture directory; no real installed dependency is modified.
    renameSync(f[target], destination);
    symlinkSync(destination, f[target], process.platform === 'win32' ? 'junction' : 'dir');
    f.links.push(f[target]);
    const externalUtils = target === 'redoc' ? join(destination, 'lib', 'utils.js')
      : target === 'modules' ? join(destination, 'openapi-typescript', 'node_modules', '@redocly', 'openapi-core', 'lib', 'utils.js') : f.utils;
    assert.throws(() => prepareCodegenCompatibility(f.frontend), /outside local node_modules|linked dependency/);
    assert.equal(readFileSync(externalUtils, 'utf8'), original);
  });
}

test('adversarial: a shared hard-linked vendor file is refused', (t) => {
  const f = fixture(t);
  const shared = join(f.base, 'shared-utils.js');
  linkSync(f.utils, shared);
  assert.throws(() => prepareCodegenCompatibility(f.frontend), /shared hard links/);
  assert.equal(readFileSync(shared, 'utf8'), original);
});

test('adversarial: a previously loaded unadapted consumer is refused', (t) => {
  const f = fixture(t);
  const fixtureRequire = createRequire(join(f.frontend, 'package.json'));
  fixtureRequire.cache[f.utils] = { exports: {} };
  try {
    assert.throws(() => prepareCodegenCompatibility(f.frontend), /already loaded/);
    assert.equal(readFileSync(f.utils, 'utf8'), original);
  } finally {
    delete fixtureRequire.cache[f.utils];
  }
});
