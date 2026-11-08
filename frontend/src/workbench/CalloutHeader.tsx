// The header placement of the shell's SceneCallouts, declared loading until the layer has laid its cards out (ADR-0082, ADR-0078).
// The shell's layer starts from a size of 0 and measures itself in a ResizeObserver, so for a frame (seconds on a loaded machine) its
// cards are 20 px wide and stacked on top of each other, whatever the stage is. The page says so with a `data-state="loading"` marker
// until the cards stand where the layout put them and none touches another; the shell's class and layout are composed, never restyled.
import { SceneCallouts, useShellLang, type SceneCalloutDef } from '@fasl-work/caos-app-shell';
import { useCallback, useEffect, useRef, useState } from 'react';

/** A card as the page measures it: its offset box in the layer (transform-free) and the width the layout gave it. */
export interface CardBox {
  id: string;
  left: number;
  top: number;
  width: number;
  height: number;
  /** The width the shell's layout set on the card, in px (0 when it laid the layer out at width 0). */
  styleWidth: number;
}

/** The narrowest card the shell lays out is 140 px; below that the layer still holds its first frame at width 0. */
const MIN_CARD = 100;

/** Whether the layer has laid its cards out: each as wide as its layout made it, and no two of them touching. Pure. */
export function calloutsLaidOut(cards: readonly CardBox[], layerWidth: number): boolean {
  if (!(layerWidth > 0) || cards.length === 0) return false;
  for (const c of cards) if (!(c.styleWidth >= MIN_CARD) || Math.abs(c.width - c.styleWidth) > 1) return false;
  for (let i = 0; i < cards.length; i += 1) {
    for (let j = i + 1; j < cards.length; j += 1) {
      const a = cards[i];
      const b = cards[j];
      if (a.left < b.left + b.width && a.left + a.width > b.left && a.top < b.top + b.height && a.top + a.height > b.top) return false;
    }
  }
  return true;
}

function measure(layer: HTMLElement): CardBox[] {
  return [...layer.querySelectorAll<HTMLElement>('[data-caos-callout]')].map((el) => ({
    id: el.getAttribute('data-caos-callout') ?? '',
    left: el.offsetLeft,
    top: el.offsetTop,
    width: el.offsetWidth,
    height: el.offsetHeight,
    styleWidth: Number.parseFloat(el.style.width) || 0,
  }));
}

/** The band the cards occupy above the drawing, as the shell measures it (`SceneCallouts` `onLayout`), and the callback that feeds it. `fallback` is the
 * band used until the cards are measured. A change under a pixel is not a change, so a drawing laid out on the band never chases a rounding. */
export function useCalloutBand(fallback: number): { band: number; onLayout: (info: { bandHeight: number }) => void } {
  const [band, setBand] = useState(fallback);
  const onLayout = useCallback(({ bandHeight }: { bandHeight: number }) => setBand((cur) => (Math.abs(cur - bandHeight) < 1 ? cur : Math.ceil(bandHeight))), []);
  return { band, onLayout };
}

/** The space between the last card and the drawing under it, in px. */
export const BAND_GAP = 8;

/**
 * A value once it has held for `ms`: null until then, and again while it changes. The shell's header layer can report a band laid out
 * before it has its width (CEFOP_DinHot, story hold at 2560 x 1440: 182, then 357, then 87 px, about 400 ms apart, shell known defect 65);
 * a view sized by the band mounts on the settled one, so it is built once, at its final size.
 */
export function useSettledValue<T>(value: T | null, ms: number): T | null {
  const [settled, setSettled] = useState<T | null>(null);
  useEffect(() => {
    setSettled(null);
    if (value === null) return undefined;
    const timer = setTimeout(() => setSettled(value), ms);
    return () => clearTimeout(timer);
  }, [value, ms]);
  return settled !== null && settled === value ? settled : null;
}

/** An anchor written as fractions of the drawing (the part of the stage under the band), as fractions of the whole stage: y' = (band + y (H - band)) / H. */
export function anchorInDrawing(anchor: { x: number; y: number }, band: number, height: number): { x: number; y: number } {
  if (!(height > band)) return anchor;
  return { x: anchor.x, y: (band + anchor.y * (height - band)) / height };
}

export interface CalloutHeaderProps {
  items: SceneCalloutDef[];
  className?: string;
  /** Receives the band height once the shell has measured its cards. */
  onLayout?: (info: { bandHeight: number }) => void;
}

/** The shell's header callouts for a scene; the wrapper has no box of its own (`display: contents`), so the layer sits where it always did. */
export function CalloutHeader({ items, className, onLayout }: CalloutHeaderProps) {
  const lang = useShellLang();
  const host = useRef<HTMLDivElement | null>(null);
  const [laidOut, setLaidOut] = useState(false);
  const ids = items.map((item) => item.id).join('\u0000');
  useEffect(() => {
    const layer = host.current?.querySelector<HTMLElement>('[data-caos-callout-layer]');
    if (!layer) return;
    const check = () => setLaidOut(calloutsLaidOut(measure(layer), layer.offsetWidth));
    const sizes = new ResizeObserver(check);
    const watch = () => {
      sizes.disconnect();
      sizes.observe(layer);
      layer.querySelectorAll('[data-caos-callout]').forEach((card) => sizes.observe(card));
    };
    // the layer re-writes the left, top and width of its cards whenever its size or a card's height changes
    const edits = new MutationObserver(() => {
      watch();
      check();
    });
    edits.observe(layer, { subtree: true, childList: true, attributes: true, attributeFilter: ['style'] });
    watch();
    check();
    return () => {
      sizes.disconnect();
      edits.disconnect();
    };
  }, [ids]);
  return (
    <div ref={host} className="dh-callouts" style={{ display: 'contents' }}>
      <SceneCallouts items={items} placement="header" className={className} onLayout={onLayout} />
      {!laidOut && (
        <span className="sr-only" data-state="loading">
          {lang === 'es' ? 'Colocando los valores sobre el dibujo' : 'Placing the values on the drawing'}
        </span>
      )}
    </div>
  );
}
