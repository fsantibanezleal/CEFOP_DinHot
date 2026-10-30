// The trap editor's rules (click to add, drag to move, delete) and the focal-crop coordinates the views share.
import { describe, expect, it } from 'vitest';
import { addTrap, deleteTrap, moveTrap, nextTrapId, outsideField, pixelToUm, umToPixel, MAX_TRAPS } from './traps';

const T = (id: number, x: number, y = 0) => ({ id, x_um: x, y_um: y, z_um: 0, weight: 1, charge: 0 });
const HALF = 665;

describe('the field-of-view bound', () => {
  it('accepts a trap strictly inside and names the bound for one at or beyond it, in both languages', () => {
    expect(outsideField(T(0, 664.9), HALF)).toBeNull();
    const at = outsideField(T(3, 665), HALF);
    expect(at?.en).toBe('trap 3 has x_um=665 um, outside the unaliased field of view (abs must be below 665.0 um = lambda f / (2 p))');
    expect(at?.es).toMatch(/la trampa 3 tiene x_um=665 um, fuera del campo de visión sin solapamiento \(abs debe ser menor que 665,0 um/);
    expect(outsideField(T(1, 0, -700), HALF)?.en).toMatch(/y_um=-700/);
  });
});

describe('the editor', () => {
  const base = [T(0, -10), T(1, 0), T(2, 10)];
  it('adds a trap on the focal plane with the next free id and weight 1', () => {
    const r = addTrap(base, 5, 7, HALF);
    expect('traps' in r && r.traps.map((t) => t.id)).toEqual([0, 1, 2, 3]);
    expect('traps' in r && r.traps[3]).toEqual({ id: 3, x_um: 5, y_um: 7, z_um: 0, weight: 1, charge: 0 });
    expect(nextTrapId([T(0, 0), T(5, 1)])).toBe(6);
  });
  it('refuses an added or moved trap outside the field with the engine message, and leaves the list unchanged', () => {
    const add = addTrap(base, 700, 0, HALF);
    expect('error' in add && add.error.en).toMatch(/outside the unaliased field of view/);
    const mv = moveTrap(base, 1, 0, 9999, HALF);
    expect('error' in mv && mv.error.en).toMatch(/trap 1 has y_um=9999/);
    expect(base.map((t) => t.x_um)).toEqual([-10, 0, 10]);
  });
  it('moves a trap by id and keeps its other fields', () => {
    const r = moveTrap([{ ...T(0, 0), weight: 2, charge: 1 }, T(1, 4)], 0, 3, -3, HALF);
    expect('traps' in r && r.traps[0]).toEqual({ id: 0, x_um: 3, y_um: -3, z_um: 0, weight: 2, charge: 1 });
  });
  it('deletes a trap but never the last one (a target needs at least one trap)', () => {
    const r = deleteTrap(base, 1);
    expect('traps' in r && r.traps.map((t) => t.id)).toEqual([0, 2]);
    const last = deleteTrap([T(0, 0)], 0);
    expect('error' in last && last.error.en).toMatch(/at least one trap/);
  });
  it('refuses a list longer than the contract allows', () => {
    const many = Array.from({ length: MAX_TRAPS }, (_, i) => T(i, 0, 0));
    const r = addTrap(many, 1, 1, HALF);
    expect('error' in r && r.error.en).toMatch(/at most 4096/);
  });
});

describe('focal-crop coordinates', () => {
  it('maps a trap to its pixel and back through the crop centre (index floor(size / 2) is x = 0)', () => {
    expect(umToPixel(0, 0, 3, 10.3906)).toEqual([1, 1]);
    expect(umToPixel(-10.3906, 0, 3, 10.3906)).toEqual([0, 1]);
    const [c, r] = umToPixel(20.7812, -10.3906, 64, 10.3906);
    expect([c, r]).toEqual([34, 31]);
    const back = pixelToUm(c, r, 64, 10.3906);
    expect(back[0]).toBeCloseTo(20.7812, 6);
    expect(back[1]).toBeCloseTo(-10.3906, 6);
  });
});
