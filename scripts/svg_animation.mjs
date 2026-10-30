// The analysis half of scripts/check_svg_animation.py: reads the SVG files named on the command line and prints, as JSON, what the
// shell's own gate analysis (gate/areas.mjs of @fasl-work/caos-app-shell, shell 0.14.0) finds in each one. It reuses
// `analyseSvgAnimation` and `animationFailures` and holds no rule of its own, so the guard and the gate (G17) can never disagree.
// Usage: node scripts/svg_animation.mjs <frontend dir> <svg file>...
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const [frontend, ...files] = process.argv.slice(2);
const module = join(resolve(frontend), 'node_modules', '@fasl-work', 'caos-app-shell', 'gate', 'areas.mjs');
const { analyseSvgAnimation, animationFailures } = await import(pathToFileURL(module).href);
const report = files.map((file) => {
  const analysis = analyseSvgAnimation(readFileSync(file, 'utf8'));
  return { file, animated: analysis.animated, seconds: analysis.seconds, failures: animationFailures(analysis, file) };
});
process.stdout.write(JSON.stringify(report));
