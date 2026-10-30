// The two learned models of the product in the browser (onnxruntime-web, single-threaded, self-hosted WASM):
//  - cgh-net (method M17): the amplitudes of three planes (-8, 0, +8 SLM Rayleigh ranges) on a 128 x 128 focal crop in, [1, 3, 128, 128];
//    the SLM phase [1, 1, 128, 128] in radians out.
//  - warmstart-model (method B3): the traps [1, 1024, 4] and their mask [1, 1024] in, one phase per trap [1, 1024] out; the
//    phases start the M07 live run as `trapPhases`.
// Each slot answers with its released model when the card and graph are on the site and pass their schema and sha256, and with
// its baseline otherwise (M19 at 30 iterations for cgh-net, the random trap phases the engine starts from for warmstart-model);
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
  'cgh-net': { en: 'the baseline (multi-plane Gerchberg-Saxton M19, 30 iterations)', es: 'la línea base (Gerchberg-Saxton multiplano M19, 30 iteraciones)' },
  'warmstart-model': { en: 'the baseline (random trap phases)', es: 'la línea base (fases aleatorias de las trampas)' },
};

export function baselineName(slot: SlotId): Text {
  return BASELINE_NAME[slot];
}

const noModel = (slot: SlotId, why: Text): SlotAnswer => ({ slot, answered: 'baseline', card: null, reason: why });

// ---- encoding and decoding (pure) ----

/** The planes the cgh-net graph takes, in SLM-limited Rayleigh ranges, in channel order (model card, `generators.PLANE_INDEX`). */
export const CGH_PLANES = [-1, 0, 1] as const;
export const CGH_PLANE_Z = 8;
/** The graph is trained within this many focal bins of the axis. */
export const CGH_LIMIT_BINS = 60;
/** Tolerance of a trap's depth from its plane, in SLM-limited Rayleigh ranges. */
const PLANE_TOL = 0.05;

type CghSetup = { wavelength_nm: number; focal_mm: number; n_pix: number; pitch_um: number; pad: number };

/** The SLM-limited Rayleigh range z_R = lambda f^2 / (pi R^2), R = N p / 2, in micrometres: the unit of the planes' depths. */
export function slmRayleighUm(s: CghSetup): number {
  const r = (s.n_pix * s.pitch_um) / 2;
  return (s.wavelength_nm * 1e-3 * (s.focal_mm * 1e3) ** 2) / (Math.PI * r * r);
}

/** One focal bin in micrometres, lambda f / (pad N p). */
export function focalBinUm(s: CghSetup): number {
  return (s.wavelength_nm * 1e-3 * s.focal_mm * 1e3) / (s.pad * s.n_pix * s.pitch_um);
}

/**
 * The cgh-net input [1, 3, 128, 128]: for each of the three planes (-8, 0, +8 SLM-limited Rayleigh ranges) the amplitude, the square
 * root of the unit-sum intensity of Gaussian spots of sigma one bin at the rounded trap bins, weighted (generators.render_spots; the
 * Python `planes_from_traps`). Returns the reason in `error` when the traps do not fit what the graph was trained on.
 */
export function encodeCghPlanes(traps: readonly Trap[], setup: CghSetup, grid = CGH_GRID): { input: Float32Array; error: Text | null } {
  const input = new Float32Array(3 * grid * grid);
  const fail = (en: string, es: string) => ({ input, error: { en, es } });
  const b = focalBinUm(setup);
  const zr = slmRayleighUm(setup);
  const c = Math.floor(grid / 2);
  const sets: { x: number; y: number; w: number }[][] = [[], [], []];
  for (const t of traps) {
    if (t.charge !== 0) return fail('cgh-net does not take vortex traps.', 'cgh-net no admite trampas con vórtice.');
    const x = Math.round(t.x_um / b);
    const y = Math.round(t.y_um / b);
    if (Math.abs(x) > CGH_LIMIT_BINS || Math.abs(y) > CGH_LIMIT_BINS) return fail(`cgh-net takes traps within ${CGH_LIMIT_BINS} bins of the axis.`, `cgh-net admite trampas a menos de ${CGH_LIMIT_BINS} bins del eje.`);
    const z = t.z_um / zr;
    const plane = Math.round(z / CGH_PLANE_Z);
    if (Math.abs(plane) > 1 || Math.abs(z - plane * CGH_PLANE_Z) > PLANE_TOL) return fail(`cgh-net takes traps on the planes z = -${CGH_PLANE_Z}, 0 and +${CGH_PLANE_Z} SLM Rayleigh ranges.`, `cgh-net admite trampas en los planos z = -${CGH_PLANE_Z}, 0 y +${CGH_PLANE_Z} rangos de Rayleigh del SLM.`);
    if (t.weight > 0) sets[plane + 1].push({ x, y, w: t.weight });
  }
  sets.forEach((pts, k) => {
    if (!pts.length) return;
    const plane = new Float64Array(grid * grid);
    let sum = 0;
    for (let row = 0; row < grid; row++) {
      for (let col = 0; col < grid; col++) {
        let v = 0;
        for (const p of pts) v += p.w * Math.exp(-((col - c - p.x) ** 2 + (row - c - p.y) ** 2) / 2);
        plane[row * grid + col] = v;
        sum += v;
      }
    }
    for (let i = 0; i < plane.length; i++) input[k * grid * grid + i] = Math.sqrt(plane[i] / sum);
  });
  return { input, error: null };
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

/**
 * Whether cgh-net applies to a case: its graph is fixed at the card's grid with padding 1, and takes point traps on its three planes. The
 * reason is returned when it does not, and the baseline answers.
 */
export function cghApplies(setup: CghSetup, traps: readonly Trap[], card: Pick<ModelCard, 'grid'> | null): { ok: true } | { ok: false; reason: Text } {
  const grid = card?.grid ?? CGH_GRID;
  if (setup.n_pix !== grid || setup.pad !== 1) {
    return { ok: false, reason: { en: `cgh-net is trained for a ${grid} x ${grid} SLM with padding 1; this case has ${setup.n_pix} x ${setup.n_pix} with padding ${setup.pad}.`, es: `cgh-net está entrenada para un SLM de ${grid} x ${grid} con relleno 1; este caso tiene ${setup.n_pix} x ${setup.n_pix} con relleno ${setup.pad}.` } };
  }
  const { error } = encodeCghPlanes(traps, setup, grid);
  return error ? { ok: false, reason: error } : { ok: true };
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

/** The released cgh-net's phase (radians, 128 x 128, row-major) for the three-plane target of `encodeCghPlanes`; the caller has checked `cghApplies`. */
export async function predictCghPhase(target: Float32Array, grid = CGH_GRID): Promise<Float32Array> {
  return run('cgh-net', { target: { data: target, dims: [1, CGH_PLANES.length, grid, grid] } });
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
