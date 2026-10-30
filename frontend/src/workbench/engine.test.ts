// The live lane's door: until the engine (T1) is on the branch, the adapter answers NotLive and the replay lane carries the views.
import { describe, expect, it } from 'vitest';
import { NotLive, getEngine, laneOf } from './engine';

describe('the engine adapter', () => {
  it('reports no live method and throws NotLive from every call when the engine module is absent', async () => {
    const e = await getEngine();
    if (e.available) return; // T1 merged: the same API answers for real, covered by its own tests
    expect(e.client.liveMethods()).toEqual([]);
    await expect(e.client.run({ params: {} as never, method: 'M04' })).rejects.toBeInstanceOf(NotLive);
    await expect(e.client.particle({} as never)).rejects.toBeInstanceOf(NotLive);
    expect(() => e.client.cancel()).not.toThrow();
  });
  it('labels a result live only when the engine produced it, replay when the bake did', () => {
    expect(laneOf('M04', ['M04', 'M06'])).toBe('live');
    expect(laneOf('M09', ['M04'])).toBe('replay');
    expect(laneOf('M04', [])).toBe('replay');
  });
});
