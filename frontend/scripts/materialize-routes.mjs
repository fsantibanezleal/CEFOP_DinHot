// Postbuild (T2): write every standard route as its own page, so a static host answers a deep link with the app
// instead of a 404 (failure classes 2 and 22). Each route gets <route>/index.html (served for /route/ and, through
// the host's redirect, /route); 404.html is the app as well, so an unknown path reaches the router, whose catch-all opens the Introduction.
// The build fails on a partial set.
import { copyFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { STANDARD_ROUTES } from '@fasl-work/caos-app-shell/keys';

const dist = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const index = join(dist, 'index.html');
if (!existsSync(index)) {
  console.error('[materialize-routes] dist/index.html is missing: run vite build first');
  process.exit(1);
}
const routes = STANDARD_ROUTES.map((r) => r.path).filter((p) => p !== '/');
for (const route of routes) {
  const dir = join(dist, route.replace(/^\//, ''));
  mkdirSync(dir, { recursive: true });
  copyFileSync(index, join(dir, 'index.html'));
}
copyFileSync(index, join(dist, '404.html'));

const html = readFileSync(index, 'utf8');
const missing = routes.filter((r) => !existsSync(join(dist, r.replace(/^\//, ''), 'index.html')));
if (missing.length || !existsSync(join(dist, '404.html')) || !existsSync(join(dist, 'build.json'))) {
  console.error(`[materialize-routes] incomplete: missing ${[...missing, ...(existsSync(join(dist, 'build.json')) ? [] : ['build.json'])].join(', ')}`);
  process.exit(1);
}
if (!html.includes('data-theme')) {
  console.error('[materialize-routes] index.html carries no pre-paint theme script');
  process.exit(1);
}
console.log(`[materialize-routes] ${routes.length} routes and 404.html written; build.json present`);
