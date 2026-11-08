// The header callouts (ADR-0082) declare themselves loading until the shell's layer has laid its cards out: the layer starts from a
// size of 0, so for a frame or two (seconds on a loaded machine) its cards are 20 px wide and stacked on top of one another, and a
// reader of the page, or the gate, that looked then would see three callouts overlapping.
import { LinkedViewProvider } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { CalloutHeader, calloutsLaidOut, type CardBox } from './CalloutHeader';

const card = (id: string, left: number, top: number, width = 184, height = 70, styleWidth = width): CardBox => ({ id, left, top, width, height, styleWidth });

describe('calloutsLaidOut', () => {
  it('is false before the layer has a width or any card', () => {
    expect(calloutsLaidOut([], 800)).toBe(false);
    expect(calloutsLaidOut([card('a', 8, 8)], 0)).toBe(false);
  });

  it('is false for the first frame, when the layer was laid out at width 0 (cards 20 px wide, stacked)', () => {
    const first = [card('laser', 0, 8, 20, 129, 0), card('slm', 0, 68, 20, 135, 0), card('focal', 0, 128, 20, 263, 0)];
    expect(calloutsLaidOut(first, 1072)).toBe(false);
  });

  it('is false while the cards overlap, as when they sit on heights measured before their text wrapped', () => {
    expect(calloutsLaidOut([card('a', 8, 8, 184, 100), card('b', 8, 60, 184, 100)], 400)).toBe(false);
  });

  it('is false while a card is not yet as wide as the layout made it', () => {
    expect(calloutsLaidOut([card('a', 8, 8, 120, 70, 184)], 800)).toBe(false);
  });

  it('is true for three cards in a row, in two columns, or in one column, none of them touching', () => {
    expect(calloutsLaidOut([card('a', 89, 8), card('b', 444, 8), card('c', 799, 8)], 1072)).toBe(true);
    expect(calloutsLaidOut([card('a', 20, 8, 164, 76), card('b', 206, 8, 164, 92), card('c', 113, 108, 164, 92)], 390)).toBe(true);
    expect(calloutsLaidOut([card('a', 8, 8, 164, 76), card('b', 8, 90, 164, 76), card('c', 8, 172, 164, 76)], 180)).toBe(true);
  });
});

describe('CalloutHeader', () => {
  it('renders the shell layer and, until it is laid out, a loading marker the gate and a screen reader can see', () => {
    const html = renderToStaticMarkup(
      <LinkedViewProvider>
        <CalloutHeader items={[{ id: 'a', eyebrow: { en: 'A', es: 'A' }, value: '1', unit: { en: 'u', es: 'u' }, state: 'normal', anchor: { x: 0.2, y: 0.5 }, source: { en: 's', es: 's' } }]} />
      </LinkedViewProvider>,
    );
    expect(html).toContain('data-caos-callout-layer');
    expect(html).toContain('data-placement="header"');
    expect(html).toContain('data-state="loading"');
    expect(html).toContain('sr-only');
  });
});

describe('the band the cards measure', () => {
  it('maps an anchor written on the drawing into the stage under the band: y prime = (band + y (H - band)) / H', async () => {
    const { anchorInDrawing } = await import('./CalloutHeader');
    const a = anchorInDrawing({ x: 0.5, y: 0.5 }, 200, 800);
    expect(a.x).toBe(0.5);
    expect(a.y).toBeCloseTo((200 + 0.5 * 600) / 800, 10);
    // the top of the drawing sits at the band, never above it
    expect(anchorInDrawing({ x: 0.1, y: 0 }, 200, 800).y).toBeCloseTo(0.25, 10);
    // a stage no taller than its band has no drawing to map into: the anchor is left alone
    expect(anchorInDrawing({ x: 0.3, y: 0.4 }, 900, 800)).toEqual({ x: 0.3, y: 0.4 });
  });
});
