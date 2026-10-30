// The artifact layer refuses what is not JSON: a static host that answers a missing file with its HTML page must
// surface as an error at the fetch, not as a parse failure in a view (T3).
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ArtifactError, getJSON } from './artifacts';

vi.stubGlobal('__APP_VERSION__', 'test-version');

afterEach(() => vi.unstubAllGlobals());

function answer(body: string, status: number, type: string) {
  return vi.fn(async (url: string) => ({ url, ok: status < 400, status, headers: new Headers({ 'content-type': type }), json: async () => JSON.parse(body) }));
}

describe('getJSON', () => {
  it('asks for the artifact under the base with the release version, and returns its JSON', async () => {
    const fetch = answer('{"ok":true}', 200, 'application/json');
    vi.stubGlobal('fetch', fetch);
    vi.stubGlobal('__APP_VERSION__', 'test-version');
    await expect(getJSON('manifests/index.json')).resolves.toEqual({ ok: true });
    expect(fetch.mock.calls[0][0]).toMatch(/\/data\/manifests\/index\.json\?v=test-version$/);
  });
  it('adversarial: refuses an HTML answer (the host fallback for a missing file)', async () => {
    vi.stubGlobal('fetch', answer('<!doctype html>', 200, 'text/html'));
    vi.stubGlobal('__APP_VERSION__', 'test-version');
    await expect(getJSON('manifests/missing.json')).rejects.toThrow(ArtifactError);
  });
  it('refuses an error status, naming the file', async () => {
    vi.stubGlobal('fetch', answer('', 404, 'text/html'));
    vi.stubGlobal('__APP_VERSION__', 'test-version');
    await expect(getJSON('data/x.json')).rejects.toThrow(/data\/x\.json: HTTP 404/);
  });
});
