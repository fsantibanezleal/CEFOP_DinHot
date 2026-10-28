// The door of the live lane. The engine is the TypeScript port of the Python holography core (unit T1,
// frontend/src/engine/holo/client.ts). The client module is loaded lazily, by a glob import, the first time a view asks for it, so the
// main bundle does not carry the engine; where it cannot be loaded the adapter answers `NotLive` and every view runs on the replay
// lane (the committed trace) and says so. The types are the client's own, imported as types only.
import type { EngineClient, Progress, RunRequest, RunResult, ParticleRequest, ParticleResult } from '../engine/holo/client';
import { AbortError, NotLive } from '../engine/holo/types';

export type { EngineClient, Progress, RunRequest, RunResult, ParticleRequest, ParticleResult };
export { AbortError, NotLive };

const notLive: EngineClient = {
  liveMethods: () => [],
  run: (req) => Promise.reject(new NotLive(req.method)),
  particle: () => Promise.reject(new NotLive('particle')),
  axialCut: () => Promise.reject(new NotLive('axial cut')),
  gpu: () => Promise.resolve({ ok: false, reason: 'the live engine is not on this build' }),
  cancel: () => undefined,
  dispose: () => undefined,
};

export interface Engine {
  /** True when T1's client is on this build; false carries the NotLive adapter. */
  available: boolean;
  client: EngineClient;
}

// The glob matches nothing until T1's module is merged; Vite resolves it at build time.
const modules = import.meta.glob<{ createEngineClient: () => EngineClient }>('../engine/holo/client.ts');

let engine: Promise<Engine> | null = null;

/** The engine client of this build, created once. */
export function getEngine(): Promise<Engine> {
  engine ??= (async (): Promise<Engine> => {
    const load = Object.values(modules)[0];
    if (!load) return { available: false, client: notLive };
    try {
      const mod = await load();
      return { available: true, client: mod.createEngineClient() };
    } catch (e) {
      console.error(`[engine] the live engine failed to load (${String(e)}); the replay lane answers`);
      return { available: false, client: notLive };
    }
  })();
  return engine;
}

/** The lane a method's result comes from: live when the engine can run it, replay when the bake carries it. */
export const laneOf = (method: string, liveMethods: readonly string[]): 'live' | 'replay' => (liveMethods.includes(method) ? 'live' : 'replay');
