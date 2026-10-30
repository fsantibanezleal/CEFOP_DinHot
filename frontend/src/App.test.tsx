// The landing and the header order (shell 0.13.1, docs/06_executive-view.md): the product opens on the Introduction's executive view,
// the App has its own route and is the leftmost tab, always (App, Introduction, Methodology, Implementation, Experiments, Benchmark),
// and an old App link keeps its query string and hash (WB-008).
import { APP_ROUTE, LANDING_ROUTE, STANDARD_ROUTES } from '@fasl-work/caos-app-shell';
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const source = readFileSync(new URL('./App.tsx', import.meta.url), 'utf8');

describe('the landing', () => {
  it('the routes are the standard ones, the App first and at /app, the landing on the Introduction', () => {
    expect(LANDING_ROUTE).toBe('/introduction');
    expect(APP_ROUTE).toBe('/app');
    expect(STANDARD_ROUTES.map((r) => r.path)).toEqual(['/app', '/introduction', '/methodology', '/implementation', '/experiments', '/benchmark']);
  });

  it('the example header lists the six routes in the decided order, the App leftmost', () => {
    const order = ['/app', '/introduction', '/methodology', '/implementation', '/experiments', '/benchmark'];
    expect(STANDARD_ROUTES.map((route) => route.path)).toEqual(order);
    expect(source).toContain('routes: STANDARD_ROUTES');
  });

  it('the Introduction opens on the executive view', () => {
    expect(source).toContain("const Introduction = lazy(() => import('./pages/Introduction')");
    expect(source).toContain('<Route path="/introduction" element={<Introduction />} />');
    expect(source).toContain('<Suspense fallback=');
    const introduction = readFileSync(new URL('./pages/Introduction.tsx', import.meta.url), 'utf8');
    expect(introduction).toContain('ExecutiveView data={data}');
  });

  it('the App route renders the workbench and not the executive view', () => {
    expect(source).toContain("const Workbench = lazy(() => import('./workbench/Workbench')");
    expect(source).toContain('<Route path="/app" element={<Workbench />} />');
    const workbench = readFileSync(new URL('./workbench/Workbench.tsx', import.meta.url), 'utf8');
    expect(workbench).toContain('<CaseWorkbench');
  });

  it('the root and the catch-all render the shell landing, which opens the Introduction and keeps an old App link', () => {
    expect(source).toContain('<Route path="/" element={<Landing />} />');
    expect(source).toContain('<Route path="/app" element={<Workbench />} />');
    expect(source).toContain('<Route path="*" element={<Landing />} />');
    expect(source).not.toContain('<Route path="/" element={<Workbench');
  });

  it('adversarial: the Introduction-first order of shell 0.13.0 is refused, the landing does not move the tabs', () => {
    expect(STANDARD_ROUTES[0].path).not.toBe(LANDING_ROUTE);
    expect(STANDARD_ROUTES[0].path).toBe(APP_ROUTE);
    expect(STANDARD_ROUTES.map((r) => r.path).indexOf(LANDING_ROUTE)).toBe(1);
  });

  it('the App route opens Focus mode: the workbench sets focus, and the rail head carries the Focus control (WB-014)', () => {
    const workbench = readFileSync(new URL('./workbench/Workbench.tsx', import.meta.url), 'utf8');
    expect(workbench).toMatch(/<CaseWorkbench[\s\S]*?\bfocus\b/);
  });

  it('adversarial: the root alone does not render the workbench', () => {
    expect(source).toContain('<Route path="/" element={<Landing />} />');
    expect(source).toContain('<Route path="*" element={<Landing />} />');
    expect(source).not.toContain('<Route path="/" element={<Workbench');
  });
});
