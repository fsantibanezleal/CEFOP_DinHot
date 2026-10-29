// The two learned slots: the pure encodings (held to the catalog's tensor shapes) and the rule that decides which model answers.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { describe, expect, it, vi } from 'vitest';
import type { ModelCard } from './contract.types';
import { baselineName, cghApplies, decodeWarmstart, encodeCghPlanes, encodeWarmstart, focalBinUm, slmRayleighUm, loadSlot, rayleighUm, SLOTS, WARMSTART_MAX_TRAPS } from './ort';

vi.stubGlobal('__APP_VERSION__', 'test-version');

const T = (id: number, x: number, y: number, weight = 1, z = 0) => ({ id, x_um: x, y_um: y, z_um: z, weight, charge: 0 });
const catalog = readFileSync(new URL('../../../docs/contracts/catalog.md', import.meta.url), 'utf8');

describe('cgh-net input', () => {
  // SLM 128 x 128, pad 1, 12.5 um pitch, 0.85 um, f 250 mm: bin = lambda f / (N p) = 132.8 um, z_R = lambda f^2 / (pi R^2) = 6.5 mm
  const setup = { wavelength_nm: 850, focal_mm: 250, n_pix: 128, pitch_um: 12.5, pad: 1 };
  const bin = focalBinUm(setup);
  const zr = slmRayleighUm(setup);
  it('is three planes of unit-sum Gaussian spots, as amplitudes, centred at index 64, in the order -8, 0, +8', () => {
    const { input, error } = encodeCghPlanes([T(0, 0, 0, 1, 0), T(1, 2 * bin, -2 * bin, 3, 8 * zr), T(2, 0, 0, 1, -8 * zr)], setup);
    expect(error).toBeNull();
    expect(input.length).toBe(3 * 128 * 128);
    const plane = (k: number) => input.subarray(k * 16384, (k + 1) * 16384);
    for (const k of [0, 1, 2]) expect(plane(k).reduce((a, v) => a + v * v, 0)).toBeCloseTo(1, 5); // unit-sum intensity per plane
    const peak = (k: number) => plane(k).indexOf(Math.max(...plane(k)));
    expect(peak(0)).toBe(64 * 128 + 64); // plane -8
    expect(peak(1)).toBe(64 * 128 + 64); // plane 0
    expect(peak(2)).toBe(62 * 128 + 66); // plane +8, x = +2, y = -2
  });
  it('an empty plane stays zero', () => {
    const { input } = encodeCghPlanes([T(0, 0, 0)], setup);
    expect(input.subarray(0, 16384).every((v) => v === 0)).toBe(true);
    expect(input.subarray(32768).every((v) => v === 0)).toBe(true);
  });
  it('refuses, with the reason, a vortex, a depth off the planes and a trap beyond 60 bins', () => {
    expect(encodeCghPlanes([{ ...T(0, 0, 0), charge: 1 }], setup).error?.en).toMatch(/vortex/);
    expect(encodeCghPlanes([T(0, 0, 0, 1, 3 * zr)], setup).error?.en).toMatch(/planes/);
    expect(encodeCghPlanes([T(0, 61 * bin, 0)], setup).error?.en).toMatch(/60 bins/);
  });
  it('applies to the card grid with padding 1 and traps on the planes, and says why not otherwise', () => {
    expect(cghApplies(setup, [T(0, 0, 0)], { grid: 128 }).ok).toBe(true);
    const big = cghApplies({ ...setup, n_pix: 256, pad: 2 }, [T(0, 0, 0)], { grid: 128 });
    expect(big.ok).toBe(false);
    expect(!big.ok && big.reason.en).toMatch(/128 x 128 SLM with padding 1/);
    expect(cghApplies(setup, [T(0, 0, 0, 1, 5 * zr)], { grid: 128 }).ok).toBe(false);
  });
});

describe('cgh-net input against the released card', () => {
  it('has the length of the card input shape, and the planes of the card are the encoder planes', () => {
    const card = JSON.parse(readFileSync(new URL('../../../models/cgh-net.json', import.meta.url), 'utf8')) as ModelCard;
    const shape = card.inputs[0].shape;
    expect(shape).toEqual([1, 3, 128, 128]);
    const setup = { wavelength_nm: 850, focal_mm: 250, n_pix: 128, pitch_um: 12.5, pad: 1 };
    const { input } = encodeCghPlanes([T(0, 0, 0)], setup, card.grid ?? 128);
    expect(input.length).toBe(shape.reduce((a, v) => a * v, 1));
    expect(card.trained_on.en).toMatch(/planes at -8, 0, \+8/);
  });
});

describe('warmstart input', () => {
  const setup = { wavelength_nm: 1064, na: 1.2, n_imm: 1.33 };
  it('is [1024, 4] and [1024], padded with zeros, x and y over the half field, z in Rayleigh ranges', () => {
    const zr = rayleighUm(setup);
    expect(zr).toBeCloseTo((1.33 * 1.064) / (Math.PI * 1.44), 9);
    const e = encodeWarmstart([T(0, 100, -50, 2, zr)], 200, setup);
    expect(e.traps.length).toBe(WARMSTART_MAX_TRAPS * 4);
    expect(e.mask.length).toBe(WARMSTART_MAX_TRAPS);
    expect([...e.traps.slice(0, 4)]).toEqual([0.5, -0.25, 1, 2]);
    expect(e.mask[0]).toBe(1);
    expect(e.mask[1]).toBe(0);
    expect(e.traps[4]).toBe(0);
    expect(e.used).toBe(1);
  });
  it('truncates beyond 1024 traps and decodes the phases wrapped to [0, 2 pi)', () => {
    const many = Array.from({ length: 1030 }, (_, i) => T(i, 0, 0));
    expect(encodeWarmstart(many, 1, setup).used).toBe(WARMSTART_MAX_TRAPS);
    const p = decodeWarmstart([-0.5, 7, 3], 3);
    expect(p[0]).toBeCloseTo(2 * Math.PI - 0.5, 9);
    expect(p[1]).toBeCloseTo(7 - 2 * Math.PI, 9);
    expect(p[2]).toBe(3);
  });
});

describe('the slots agree with the catalog', () => {
  it('names the tensors the catalog row gives and the cards at their documented paths', () => {
    expect(catalog).toMatch(/in: target float32 \[1, 3, 128, 128\].*out: phase float32 \[1, 1, 128, 128\].*baseline: the volumetric GS \(M19\)/);
    expect(catalog).toMatch(/in: traps float32 \[1, 1024, 4\].*and mask float32 \[1, 1024\]; out: trap_phase float32 \[1, 1024\]/);
    expect(catalog).toContain('models/cgh-net.json, models/cgh-net.onnx');
    expect(catalog).toContain('models/warmstart.json, models/warmstart.onnx');
    expect(SLOTS['cgh-net']).toEqual({ card: 'models/cgh-net.json', input: ['target'], output: 'phase' });
    expect(SLOTS['warmstart-model'].input).toEqual(['traps', 'mask']);
    expect(baselineName('cgh-net').en).toMatch(/Gerchberg-Saxton M19, 30 iterations/);
  });
});

describe('which model answers a slot', () => {
  const graph = new Uint8Array([1, 2, 3, 4, 5]);
  const card = (over: Partial<ModelCard> = {}): ModelCard => ({
    schema: 'dinhot.model-card/v1',
    slot: 'cgh-net',
    onnx: 'models/cgh-net.onnx',
    sha256: createHash('sha256').update(graph).digest('hex'),
    bytes: graph.length,
    opset: 17,
    inputs: [{ name: 'target', shape: [1, 1, 128, 128], dtype: 'float32' }],
    outputs: [{ name: 'phase', shape: [1, 1, 128, 128], dtype: 'float32' }],
    grid: 128,
    trained_on: { en: 'x', es: 'x' },
    held_out: { en: 'x', es: 'x' },
    metrics_path: 'data/derived/models/metrics.json',
    ...over,
  });
  const serve = (files: Record<string, unknown>): typeof fetch =>
    (async (url: string) => {
      const path = String(url).replace(/^.*\/data\//, '').replace(/\?.*$/, '');
      const body = files[path];
      if (body === undefined) return new Response('not found', { status: 404, headers: { 'content-type': 'text/html' } });
      if (body instanceof Uint8Array) return new Response(body as BodyInit, { status: 200, headers: { 'content-type': 'application/octet-stream' } });
      return new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } });
    }) as typeof fetch;

  it('the baseline answers, with its reason, when no card is on the site', async () => {
    const a = await loadSlot('cgh-net', serve({}));
    expect(a.answered).toBe('baseline');
    expect(a.card).toBeNull();
    expect(a.reason?.en).toMatch(/No released model/);
    expect(a.reason?.es).toMatch(/No hay un modelo publicado/);
  });
  it('the released model answers when the card conforms and the graph matches its sha256 and size', async () => {
    const a = await loadSlot('cgh-net', serve({ 'models/cgh-net.json': card(), 'models/cgh-net.onnx': graph }));
    expect(a.answered).toBe('model');
    expect(a.reason).toBeNull();
    expect(a.card?.grid).toBe(128);
  });
  it('adversarial: a graph that differs by one byte, a card of another slot and a card that drifts from the contract all leave the baseline', async () => {
    const bad = new Uint8Array([1, 2, 3, 4, 6]);
    expect((await loadSlot('cgh-net', serve({ 'models/cgh-net.json': card(), 'models/cgh-net.onnx': bad }))).answered).toBe('baseline');
    expect((await loadSlot('cgh-net', serve({ 'models/cgh-net.json': card({ slot: 'warmstart-model' }), 'models/cgh-net.onnx': graph }))).answered).toBe('baseline');
    const drift = { ...card(), extra: 1 };
    expect((await loadSlot('cgh-net', serve({ 'models/cgh-net.json': drift, 'models/cgh-net.onnx': graph }))).answered).toBe('baseline');
    expect((await loadSlot('cgh-net', serve({ 'models/cgh-net.json': card() }))).reason?.en).toMatch(/graph is not/);
  });
});
