// A drawing under the shell's header callouts, with each leader anchored on a mark of the drawing (ADR-0082 rule 5). The scene measures
// itself, so an anchor is placed from the map's own geometry (where a trap, the zero order or the worst trap stands in the picture),
// never a fixed fraction of the card. The callouts are the shell's; this only gives them a box and the anchors.
import { useStageSize, type SceneCalloutDef } from '@fasl-work/caos-app-shell';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { CalloutHeader } from './CalloutHeader';
import './viz-app.css';

/** The band the header callouts take above the drawing (CSS px); the narrow layout stacks them in a taller band (viz-app.css). */
export const CALLOUT_BAND = 86;
export const CALLOUT_BAND_NARROW = 175;
const NARROW = 900;

/**
 * The anchor, as a fraction of the whole scene (band included), of a cell of a `cols` by `rows` map drawn square into the box that is
 * `width` wide and `height` tall below the band. Pure, so the geometry is tested.
 */
export function mapAnchor(col: number, row: number, cols: number, rows: number, width: number, height: number, band: number): { x: number; y: number } {
  const s = Math.min(width / cols, (height - band) / rows);
  const ox = (width - s * cols) / 2;
  const oy = band + (height - band - s * rows) / 2;
  const clamp = (v: number) => Math.max(0.02, Math.min(0.98, v));
  return { x: clamp((ox + (col + 0.5) * s) / width), y: clamp((oy + (row + 0.5) * s) / height) };
}

/** The box is a direct child of a `dh-stack`: a flexible share of the card on a desktop, a fixed scene height on a phone (`tall`: the dynamics view, with its charts). */
/** `items` null draws the scene with no band: the page around it (the story) already carries the callouts. */
export function CalloutScene({ items, tall, children }: { items: ((geometry: { width: number; height: number; band: number }) => SceneCalloutDef[]) | null; tall?: boolean; children: ReactNode }) {
  const [ref, size] = useStageSize();
  const scene = useRef<HTMLDivElement | null>(null);
  const [measured, setMeasured] = useState<number | null>(null);
  // The shell's layer sets `--caos-callout-band` to the height its cards need once it has laid them out: the drawing starts below it.
  useEffect(() => {
    const layer = scene.current?.querySelector<HTMLElement>('[data-caos-callout-layer]');
    if (!layer) {
      setMeasured(null);
      return;
    }
    const read = () => {
      const v = Number.parseFloat(layer.style.getPropertyValue('--caos-callout-band') || getComputedStyle(layer).getPropertyValue('--caos-callout-band'));
      setMeasured(Number.isFinite(v) && v > 0 ? Math.ceil(v) + 8 : null);
    };
    read();
    const obs = new MutationObserver(read);
    obs.observe(layer, { attributes: true, attributeFilter: ['style'] });
    return () => obs.disconnect();
  });
  const nominal = size.width > 0 && typeof window !== 'undefined' && window.innerWidth <= NARROW ? CALLOUT_BAND_NARROW : CALLOUT_BAND;
  const band = items ? (measured ?? nominal) : 0;
  const list = items && size.width > 0 && size.height > 0 ? items({ width: size.width, height: size.height, band }) : [];
  return (
    <div ref={ref} className={`dh-va-box${tall ? ' dh-va-tall' : ''}`} data-caos-flow="">
      <div ref={scene} className={`dh-scene dh-va-scene${items ? '' : ' dh-va-bare'}`} style={items ? { paddingTop: band } : undefined}>
        {list.length > 0 && <CalloutHeader items={list} />}
        <div className="dh-va-map">{children}</div>
      </div>
    </div>
  );
}
