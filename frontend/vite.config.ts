// The product build (T1, T4 of the 2026-10-04 base requirements).
// - base from VITE_BASE or '/', never './': a relative base breaks every deep link below the root (failure class 1).
// - one React and one router in the bundle (resolve.dedupe): a second copy leaves the shell outside the router.
// - VERSION is the single source of the version: injected as __APP_VERSION__, written to dist/build.json with the
//   commit, so the deployed site says which build it is and the deploy check can compare it with the pushed SHA.
// - the shell's pre-paint script and the product name are written into index.html at build time.
import react from '@vitejs/plugin-react';
import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { defineConfig } from 'vitest/config';
import { THEME_BOOT_SCRIPT } from '@fasl-work/caos-app-shell/keys';

const root = new URL('..', import.meta.url);
const VERSION = readFileSync(new URL('VERSION', root), 'utf8').trim();
const product = JSON.parse(readFileSync(new URL('product.json', root), 'utf8')) as { name: string; tagline: { en: string } };

function commit(): string {
  if (process.env.GITHUB_SHA) return process.env.GITHUB_SHA;
  try {
    return execSync('git rev-parse HEAD', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
  } catch {
    return 'unknown';
  }
}
const SHA = commit();

export default defineConfig({
  base: process.env.VITE_BASE || '/',
  plugins: [
    react(),
    {
      name: 'caos-product-html',
      transformIndexHtml: (html) =>
        html
          .replaceAll('%PRODUCT_NAME%', product.name)
          .replaceAll('%PRODUCT_TAGLINE%', product.tagline.en)
          .replace('<!--caos-boot-->', `<script>${THEME_BOOT_SCRIPT}</script>`),
    },
    {
      name: 'caos-build-json',
      apply: 'build',
      // writeBundle, not closeBundle: closeBundle also runs when the build fails, and writing into a dist that was never
      // created replaced the build's own error with an ENOENT on build.json
      writeBundle() {
        writeFileSync(new URL('frontend/dist/build.json', root), `${JSON.stringify({ version: VERSION, sha: SHA, built: new Date().toISOString() }, null, 2)}\n`);
      },
    },
  ],
  define: {
    __APP_VERSION__: JSON.stringify(VERSION),
    __BUILD_ID__: JSON.stringify(SHA.slice(0, 7)),
  },
  resolve: { dedupe: ['react', 'react-dom', 'react-router'] },
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: 'react-vendor', test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/, priority: 20, includeDependenciesRecursively: false },
            { name: 'math-vendor', test: /node_modules[\\/]katex[\\/]/, priority: 10, includeDependenciesRecursively: false },
          ],
        },
      },
    },
  },
  test: { environment: 'node', include: ['src/**/*.test.ts', 'src/**/*.test.tsx'] },
});
