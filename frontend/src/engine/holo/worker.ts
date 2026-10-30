/**
 * The Web Worker entry of the live engine: every method, the scoring, the particle simulation and the axial cut run here, so the
 * page's main thread never blocks. All logic is in `runner.ts`; this file only wires the worker's message port to it.
 * The optional WebGPU backend (`gpu/`) is attached when the worker can see `navigator.gpu`.
 */
import { createGpuBackend } from './gpu';
import { EngineRunner, type InMsg, type OutMsg } from './runner';

const scope = self as unknown as {
  postMessage(msg: OutMsg, transfer?: Transferable[]): void;
  onmessage: ((e: MessageEvent<InMsg>) => void) | null;
};

const runner = new EngineRunner((msg, transfer) => scope.postMessage(msg, transfer ?? []), undefined, createGpuBackend());
scope.onmessage = (e): void => runner.handle(e.data);
