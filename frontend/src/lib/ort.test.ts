// The two learned slots: the pure encodings (held to the catalog's tensor shapes) and the rule that decides which model answers.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { describe, expect, it, vi } from 'vitest';
import type { ModelCard } from './contract.types';
import { baselineName, cghApplies, decodeWarmstart, encodeCghTarget, encodeWarmstart, loadSlot, rayleighUm, SLOTS, WARMSTART_MAX_TRAPS } from './ort';

vi.stubGlobal('__APP_VERSION__', 'test-version');

const T = (id: number, x: number, y: number, weight = 1, z = 0) => ({ id, x_um: x, y_um: y, z_um: z, weight, charge: 0 });
const catalog = readFileSync(new URL('../../../docs/contracts/catalog.md', import.meta.url), 'utf8');

describe('cgh-net input', () => {
  it('puts sqrt(weight) at each trap pixel of the 128 crop, centred at index 64, with unit energy', () => {
    const { input, dropped } = encodeCghTarget([T(0, 0, 0, 4), T(1, 2, -2, 1)], 1);
    expect(dropped).toBe(0);
    expect(input.length).toBe(128 * 128);
    const energy = input.reduce((a, v) => a + v * v, 0);
    expect(energy).toBeCloseTo(1, 6);
    expect(input[64 * 128 + 64]).toBeCloseTo(Math.sqrt(4 / 5), 6);
    expect(input[62 * 128 + 66]).toBeCloseTo(Math.sqrt(1 / 5), 6);
  });
  it('drops a trap that falls outside the crop and counts it', () => {
    const r = encodeCghTarget([T(0, 0, 0), T(1, 500, 0)], 1);
    expect(r.dropped).toBe(1);
  });
  it('applies to the card grid only', () => {
    expect(cghApplies({ n_pix: 128 }, { grid: 128 })).toBe(true);
    expect(cghApplies({ n_pix: 256 }, { grid: 128 })).toBe(false);
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
    expect(catalog).toMatch(/in: target float32 \[1, 1, 128, 128\].*out: phase float32 \[1, 1, 128, 128\]/);
    expect(catalog).toMatch(/in: traps float32 \[1, 1024, 4\].*and mask float32 \[1, 1024\]; out: trap_phase float32 \[1, 1024\]/);
    expect(catalog).toContain('models/cgh-net.json, models/cgh-net.onnx');
    expect(catalog).toContain('models/warmstart.json, models/warmstart.onnx');
    expect(SLOTS['cgh-net']).toEqual({ card: 'models/cgh-net.json', input: ['target'], output: 'phase' });
    expect(SLOTS['warmstart-model'].input).toEqual(['traps', 'mask']);
    expect(baselineName('cgh-net').en).toMatch(/Gerchberg-Saxton, 30 iterations/);
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
