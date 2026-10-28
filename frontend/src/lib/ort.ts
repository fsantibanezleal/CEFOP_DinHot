// The two learned models of the product in the browser (onnxruntime-web, single-threaded, self-hosted WASM):
//  - cgh-net (method M17): the target amplitude on a 128 x 128 focal crop in, the SLM phase [1, 1, 128, 128] in radians out.
//  - warmstart-model (method B3): the traps [1, 1024, 4] and their mask [1, 1024] in, one phase per trap [1, 1024] out; the
//    phases start the M07 live run as `trapPhases`.
// Each slot answers with its released model when the card and graph are on the site and pass their schema and sha256, and with
// its baseline otherwise (GS at 30 iterations for cgh-net, the random trap phases the engine starts from for warmstart-model);
// the views label the result with the model that answered. The encoding and decoding are pure functions (ort.test.ts); the
// runtime loads on first use. onnxruntime-web forbids concurrent run() on one session, so calls to one graph queue.
//
// Threads: a static host (GitHub Pages) sends no COOP or COEP header, so threaded WASM is unavailable: numThreads = 1, no proxy
// worker. The WASM binary is the one in the pinned npm package (1.31.1), bundled by Vite as an asset of the site: no CDN is asked.
import type { ModelCard, Setup, Text, Trap } from './contract.types';
import { conform, MODEL_CARD, SCHEMAS } from './contract.types';

export type SlotId = 'cgh-net' | 'warmstart-model';

export interface SlotFiles {
  card: string;
  input: string[];
  output: string;
}

/** Where each slot's card sits under data/ and the names of its graph's tensors (catalog rows cgh-net and warmstart-model). */
export const SLOTS: Record<SlotId, SlotFiles> = {
  'cgh-net': { card: 'models/cgh-net.json', input: ['target'], output: 'phase' },
  'warmstart-model': { card: 'models/warmstart.json', input: ['traps', 'mask'], output: 'trap_phase' },
};

export const CGH_GRID = 128;
export const WARMSTART_MAX_TRAPS = 1024;

/** The method ids of the learned slots in the ladder: M17 is cgh-net, B3 the warm start. */
export const SLOT_METHOD: Record<SlotId, string> = { 'cgh-net': 'M17', 'warmstart-model': 'B3' };

export interface SlotAnswer {
  slot: SlotId;
  answered: 'model' | 'baseline';
  card: ModelCard | null;
  /** Why the baseline answers (never empty when it does). */
  reason: Text | null;
}

const BASELINE_NAME: Record<SlotId, Text> = {
  'cgh-net': { en: 'the baseline (Gerchberg-Saxton, 30 iterations)', es: 'la línea base (Gerchberg-Saxton, 30 iteraciones)' },
  'warmstart-model': { en: 'the baseline (random trap phases)', es: 'la línea base (fases aleatorias de las trampas)' },
};

export function baselineName(slot: SlotId): Text {
  return BASELINE_NAME[slot];
}

const noModel = (slot: SlotId, why: Text): SlotAnswer => ({ slot, answered: 'baseline', card: null, reason: why });

// ---- encoding and decoding (pure) ----

/** The focal crop of the cgh-net graph: size 128, x = 0 at index 64. Positions outside it cannot be encoded and are counted. */
export function encodeCghTarget(traps: readonly Trap[], binUm: number, grid = CGH_GRID): { input: Float32Array; dropped: number } {
  const input = new Float32Array(grid * grid);
  const c = Math.floor(grid / 2);
  let dropped = 0;
  for (const t of traps) {
    const col = Math.round(t.x_um / binUm) + c;
    const row = Math.round(t.y_um / binUm) + c;
    if (col < 0 || col >= grid || row < 0 || row >= grid || t.weight <= 0) {
      dropped++;
      continue;
    }
    input[row * grid + col] += Math.sqrt(t.weight);
  }
  let energy = 0;
  for (const v of input) energy += v * v;
  if (energy > 0) {
    const s = 1 / Math.sqrt(energy);
    for (let i = 0; i < input.length; i++) input[i] *= s;
  }
  return { input, dropped };
}

/** The Rayleigh range of the focus in micrometres, n lambda / (pi NA^2) (the paraxial Gaussian focus of a lens of that numerical aperture). */
export function rayleighUm(setup: Pick<Setup, 'wavelength_nm' | 'na' | 'n_imm'>): number {
  return (setup.n_imm * (setup.wavelength_nm * 1e-3)) / (Math.PI * setup.na * setup.na);
}

/** The warm-start input: (x, y) over the half field, z in Rayleigh ranges, weight; padded with zeros to 1024 and the 0/1 mask of the real traps. */
export function encodeWarmstart(
  traps: readonly Trap[],
  halfFieldUm: number,
  setup: Pick<Setup, 'wavelength_nm' | 'na' | 'n_imm'>,
): { traps: Float32Array; mask: Float32Array; used: number } {
  const used = Math.min(traps.length, WARMSTART_MAX_TRAPS);
  const x = new Float32Array(WARMSTART_MAX_TRAPS * 4);
  const mask = new Float32Array(WARMSTART_MAX_TRAPS);
  const zr = rayleighUm(setup);
  for (let i = 0; i < used; i++) {
    const t = traps[i];
    x[i * 4] = t.x_um / halfFieldUm;
    x[i * 4 + 1] = t.y_um / halfFieldUm;
    x[i * 4 + 2] = t.z_um / zr;
    x[i * 4 + 3] = t.weight;
    mask[i] = 1;
  }
  return { traps: x, mask, used };
}

/** The per-trap phases of the warm start, the first `used` of the graph's 1024 outputs, wrapped to [0, 2 pi). */
export function decodeWarmstart(out: ArrayLike<number>, used: number): Float64Array {
  const phases = new Float64Array(used);
  for (let i = 0; i < used; i++) phases[i] = ((out[i] % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
  return phases;
}

/** Whether cgh-net applies to a case: its graph is fixed at the card's grid, so the SLM must have that many pixels per side. */
export function cghApplies(setup: Pick<Setup, 'n_pix'>, card: Pick<ModelCard, 'grid'> | null): boolean {
  return setup.n_pix === (card?.grid ?? CGH_GRID);
}

// ---- the slot answer ----

const base = (): string => import.meta.env.BASE_URL;

async function sha256Hex(bytes: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

const graphs = new Map<SlotId, Promise<ArrayBuffer>>();

/**
 * Which model answers a slot. The released model answers when its card is on the site and conforms to the model-card
 * contract, names the slot, and its graph's sha256 and size are the card's; anything else leaves the baseline answering, with
 * the reason (the catalog's `training` state: no valid released model).
 */
export async function loadSlot(slot: SlotId, fetcher: typeof fetch = fetch): Promise<SlotAnswer> {
  const files = SLOTS[slot];
  let res: Response;
  try {
    res = await fetcher(`${base()}data/${files.card}?v=${encodeURIComponent(__APP_VERSION__)}`);
  } catch (e) {
    return noModel(slot, { en: `The model card could not be fetched (${String(e)}).`, es: `No se pudo obtener la ficha del modelo (${String(e)}).` });
  }
  if (!res.ok || !(res.headers.get('content-type') ?? '').includes('json')) {
    return noModel(slot, { en: 'No released model: the card is not on the site.', es: 'No hay un modelo publicado: la ficha no está en el sitio.' });
  }
  const card = (await res.json()) as ModelCard;
  const problems = conform(card, { object: MODEL_CARD });
  if (problems.length || card.schema !== SCHEMAS.modelCard || card.slot !== slot) {
    return noModel(slot, { en: 'The model card does not conform to the model-card contract.', es: 'La ficha del modelo no cumple el contrato de ficha de modelo.' });
  }
  const g = await fetcher(`${base()}data/${card.onnx}?v=${encodeURIComponent(__APP_VERSION__)}`);
  if (!g.ok) return noModel(slot, { en: 'The card is on the site but its graph is not.', es: 'La ficha está en el sitio pero su grafo no.' });
  const bytes = await g.arrayBuffer();
  if (bytes.byteLength !== card.bytes || (await sha256Hex(bytes)) !== card.sha256) {
    return noModel(slot, { en: 'The graph does not match its card (size or sha256).', es: 'El grafo no coincide con su ficha (tamaño o sha256).' });
  }
  graphs.set(slot, Promise.resolve(bytes));
  return { slot, answered: 'model', card, reason: null };
}

// ---- the runtime: loaded on first use ----

type Ort = typeof import('onnxruntime-web');
type Session = import('onnxruntime-web').InferenceSession;

let runtime: Promise<Ort> | null = null;

function loadRuntime(): Promise<Ort> {
  runtime ??= (async () => {
    // The wasm-only build of the runtime and its binary from the same package version; Vite bundles the binary as an asset of the site.
    const [ort, wasm] = await Promise.all([import('onnxruntime-web/wasm'), import('onnxruntime-web/ort-wasm-simd-threaded.wasm?url')]);
    ort.env.wasm.numThreads = 1;
    ort.env.wasm.proxy = false;
    ort.env.wasm.wasmPaths = { wasm: wasm.default };
    return ort;
  })();
  return runtime;
}

const sessions = new Map<SlotId, Promise<Session>>();
const locks = new Map<SlotId, Promise<unknown>>();

function session(slot: SlotId): Promise<Session> {
  let s = sessions.get(slot);
  if (!s) {
    const bytes = graphs.get(slot);
    if (!bytes) return Promise.reject(new Error(`${slot}: no released model was loaded`));
    s = Promise.all([loadRuntime(), bytes]).then(([ort, b]) => ort.InferenceSession.create(new Uint8Array(b), { executionProviders: ['wasm'] }));
    s.catch(() => sessions.delete(slot)); // a failed load is not kept: the next call tries again
    sessions.set(slot, s);
  }
  return s;
}

async function run(slot: SlotId, feeds: Record<string, { data: Float32Array; dims: number[] }>): Promise<Float32Array> {
  const [ort, s] = await Promise.all([loadRuntime(), session(slot)]);
  const previous = locks.get(slot) ?? Promise.resolve();
  const job = previous.then(async () => {
    const tensors = Object.fromEntries(Object.entries(feeds).map(([name, f]) => [name, new ort.Tensor('float32', f.data, f.dims)]));
    const out = await s.run(tensors);
    return out[SLOTS[slot].output].data as Float32Array;
  });
  locks.set(slot, job.catch(() => undefined));
  return job;
}

/** The released cgh-net's phase (radians, 128 x 128, row-major) for a target; the caller has checked `cghApplies`. */
export async function predictCghPhase(target: Float32Array, grid = CGH_GRID): Promise<Float32Array> {
  return run('cgh-net', { target: { data: target, dims: [1, 1, grid, grid] } });
}

/** The released warm start's phases for the traps of a case, in trap order. */
export async function predictWarmstart(
  traps: readonly Trap[],
  halfFieldUm: number,
  setup: Pick<Setup, 'wavelength_nm' | 'na' | 'n_imm'>,
): Promise<Float64Array> {
  const enc = encodeWarmstart(traps, halfFieldUm, setup);
  const out = await run('warmstart-model', {
    traps: { data: enc.traps, dims: [1, WARMSTART_MAX_TRAPS, 4] },
    mask: { data: enc.mask, dims: [1, WARMSTART_MAX_TRAPS] },
  });
  return decodeWarmstart(out, enc.used);
}
