// Preview the build the way GitHub Pages serves it (no SPA fallback): a deep link that was not materialised, or an
// artifact missing from the build, fails here as it would after the deploy. `vite preview` answers both with the app.
// Usage: npm run preview [-- --port 4173]
import { servePages } from '@fasl-work/caos-app-shell/serve';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const dist = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const portArg = process.argv.indexOf('--port');
const port = portArg > 0 ? Number(process.argv[portArg + 1]) : 4173;
const server = await servePages(dist, process.env.VITE_BASE || '/', port);
console.log(`[preview] ${server.url} (Ctrl+C to stop)`);
