// The door of the live lane. The engine is the TypeScript port of the Python holography core, built by unit T1 at
// frontend/src/engine/holo/client.ts with the fixed client API below. This adapter loads that module when it is on the branch
// (a glob import: it matches nothing now and the module after the merge, with no code change) and otherwise answers with
// `NotLive`, so every view runs on the replay lane (the committed trace) and says so. The types are the contract of T1's
// client, copied here so the workbench compiles before and after the merge.
import type { ParamsRecord } from '../lib/contract.types';

export interface RunRequest {
  params: ParamsRecord;
  method: string;
  options?: {
    iterations?: number;
    device?: 'ideal' | 'case';
    backend?: 'auto' | 'cpu' | 'gpu';
    trapPhases?: Float64Array;
    traps?: { id: number; x_um: number; y_um: number; z_um: number; weight: number; charge: number }[];
  };
}
export interface Progress {
  iteration: number;
  efficiency: number;
  uniformity: number;
  relStdPct: number;
}
export interface RunResult {
  method: string;
  backend: 'cpu' | 'gpu';
  fallbackReason: string | null;
  nPix: number;
  pad: number;
  binUm: number;
  halfFieldUm: number;
  phase: Float64Array;
  displayedPhase: Float64Array | null;
  focal: Float32Array;
  focalSize: number;
  trapIntensity: Float64Array;
  history: Progress[];
  metrics: { efficiency: number; uniformity: number; relStdPct: number; zeroOrder: number; ghost: number };
  timeMs: number;
}
export interface ParticleRequest {
  focal: Float32Array;
  focalSize: number;
  binUm: number;
  dynamics: NonNullable<ParamsRecord['dynamics']>;
  seed: number;
}
export interface ParticleResult {
  xUm: Float64Array;
  yUm: Float64Array;
  dtS: number;
  psd: { fHz: Float64Array; p: Float64Array };
  fcHz: number;
  stiffness: { value: number; unit: string };
}
export interface EngineClient {
  liveMethods(): string[];
  run(req: RunRequest, onProgress?: (p: Progress) => void): Promise<RunResult>;
  particle(req: ParticleRequest): Promise<ParticleResult>;
  axialCut(req: { phase: Float64Array; params: ParamsRecord; trapId: number; nz: number }): Promise<{ xz: Float32Array; nx: number; nz: number; zUm: [number, number] }>;
  cancel(): void;
  dispose(): void;
}

/** Thrown by a client that cannot compute the request live: the replay lane answers instead. */
export class NotLive extends Error {
  constructor(message = 'the live engine is not available in this build') {
    super(message);
    this.name = 'NotLive';
  }
}

const notLive: EngineClient = {
  liveMethods: () => [],
  run: () => Promise.reject(new NotLive()),
  particle: () => Promise.reject(new NotLive()),
  axialCut: () => Promise.reject(new NotLive()),
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
