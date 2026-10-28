// A map drawn into the shell's Stage: the values go through a colormap into a canvas texture (an ImageData at the data's own
// resolution, scaled to the stage with nearest-neighbour sampling, so a 1024 x 1024 map is one drawImage per frame), and the
// marks, the crosshair and the selection are drawn over it from the theme's tokens (read from the page at draw time and redrawn on a
// theme change, so no colour is written here).
//
// Tier A of the interactive-visualization rubric on every map: a crosshair that follows the pointer and the arrow keys with a
// readout in the page language, wheel zoom around the pointer (while the map holds the focus, or with Ctrl or Meta), Shift-drag pan,
// brush-to-select, a Reset zoom control, double-click and the keys 0 and Escape to reset, a described-by summary and a hidden table
// of the values (thinned to a block grid, as the shell's charts thin to 1000 rows), and a keyboard path for every pointer action.
// The trap editor is a mode of this component (add, move, delete), so the editor stays a control of the case on the map it edits.
import { Stage, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { useCallback, useEffect, useId, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type PointerEvent as ReactPointerEvent } from 'react';

export type MarkTone = 'good' | 'bad' | 'warn' | 'accent' | 'fg';
export interface HeatMark {
  id?: number;
  /** Cell coordinates; a cell centre is at + 0.5. */
  col: number;
  row: number;
  kind: 'ring' | 'cross' | 'diamond';
  tone: MarkTone;
  selected?: boolean;
  /** Drawn beside the mark; leave empty on a dense set. */
  label?: string;
  radius?: number;
}
export interface HeatRect {
  c0: number;
  r0: number;
  c1: number;
  r1: number;
  tone: MarkTone;
  dashed?: boolean;
  label?: string;
}
export type EditMode = 'inspect' | 'add' | 'move' | 'delete';

export interface HeatmapProps {
  label: BiText;
  data: ArrayLike<number>;
  cols: number;
  rows: number;
  lut: Uint8Array;
  range: [number, number];
  /** The text of the readout for a cell (the value, in the caller's units). */
  describe: (col: number, row: number, value: number) => string;
  /** One line for the screen reader: what the map is and its extremes, in the page language. */
  summary: string;
  marks?: HeatMark[];
  rects?: HeatRect[];
  /** The selected region (cells), drawn solid. */
  region?: { c0: number; r0: number; c1: number; r1: number } | null;
  mode?: EditMode;
  onPick?: (col: number, row: number) => void;
  onBrush?: (c0: number, r0: number, c1: number, r1: number) => void;
  onAdd?: (col: number, row: number) => void;
  onMove?: (id: number, col: number, row: number) => void;
  onDelete?: (id: number) => void;
  /** Called with the cell under the crosshair (or null): a linked view follows it. */
  onCursor?: (cell: { col: number; row: number } | null) => void;
  /** A trajectory drawn over the map (cell coordinates), up to index `upto`; the head is marked. */
  trail?: { col: ArrayLike<number>; row: ArrayLike<number>; upto: number } | null;
  /** A cell is a square when rows and cols are equal in micrometres; false stretches to the stage (an xz cut). */
  square?: boolean;
  /** Reset zoom label in both languages is the shell's wording for charts; the same words here. */
  tableLabel?: BiText;
}

const RESET: BiText = { en: 'Reset zoom', es: 'Restablecer zoom' };
const HIT = 9;

interface View {
  scale: number;
  tx: number;
  ty: number;
}

const token = (name: string): string => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#888';
const TONE: Record<MarkTone, string> = {
  good: '--color-good',
  bad: '--color-bad',
  warn: '--color-warn',
  accent: '--color-accent',
  fg: '--color-fg',
};

/** The block grid the hidden table reads: at most `cap` x `cap` cells, each the mean of its block. */
export function thinned(data: ArrayLike<number>, cols: number, rows: number, cap = 16): { values: number[][]; bc: number; br: number } {
  const bc = Math.max(1, Math.ceil(cols / cap));
  const br = Math.max(1, Math.ceil(rows / cap));
  const values: number[][] = [];
  for (let r0 = 0; r0 < rows; r0 += br) {
    const line: number[] = [];
    for (let c0 = 0; c0 < cols; c0 += bc) {
      let s = 0;
      let n = 0;
      for (let r = r0; r < Math.min(rows, r0 + br); r++) {
        for (let c = c0; c < Math.min(cols, c0 + bc); c++) {
          const v = data[r * cols + c];
          if (!Number.isNaN(v)) {
            s += v;
            n++;
          }
        }
      }
      line.push(n ? s / n : NaN);
    }
    values.push(line);
  }
  return { values, bc, br };
}

function HeatCanvas(props: HeatmapProps & { width: number; height: number }) {
  const { data, cols, rows, lut, range, describe, marks = [], rects = [], region = null, mode = 'inspect', width, height, square = true } = props;
  const lang = useShellLang();
  const canvas = useRef<HTMLCanvasElement | null>(null);
  const texture = useRef<HTMLCanvasElement | null>(null);
  const [view, setView] = useState<View>({ scale: 1, tx: 0, ty: 0 });
  const [cursor, setCursor] = useState<{ col: number; row: number } | null>(null);
  const [drag, setDrag] = useState<null | { kind: 'brush' | 'pan' | 'trap'; x0: number; y0: number; x1: number; y1: number; id?: number; view0?: View }>(null);
  const [focused, setFocused] = useState(false);
  // Bumped when the texture is rebuilt or the theme changes, so the overlay redraws against the new image and tokens.
  const [theme, setTheme] = useState(0);
  const summaryId = useId();
  const tableId = useId();

  // The fit: the whole map inside the stage, square cells (or stretched for a cut), centred.
  const fit = useMemo(() => {
    if (!square) return { sx: width / cols, sy: height / rows, ox: 0, oy: 0 };
    const s = Math.min(width / cols, height / rows);
    return { sx: s, sy: s, ox: (width - s * cols) / 2, oy: (height - s * rows) / 2 };
  }, [width, height, cols, rows, square]);
  const zoomed = view.scale !== 1 || view.tx !== 0 || view.ty !== 0;
  const toCell = useCallback(
    (px: number, py: number) => ({ col: (px - fit.ox - view.tx) / (fit.sx * view.scale), row: (py - fit.oy - view.ty) / (fit.sy * view.scale) }),
    [fit, view],
  );
  const toPx = useCallback(
    (col: number, row: number) => ({ x: fit.ox + view.tx + col * fit.sx * view.scale, y: fit.oy + view.ty + row * fit.sy * view.scale }),
    [fit, view],
  );

  // The texture: rebuilt only when the data, the colormap or the range changes.
  useEffect(() => {
    const t = texture.current ?? document.createElement('canvas');
    texture.current = t;
    t.width = cols;
    t.height = rows;
    const ctx = t.getContext('2d');
    if (!ctx) return;
    const img = ctx.createImageData(cols, rows);
    const [lo, hi] = range;
    const span = hi - lo || 1;
    for (let i = 0; i < cols * rows; i++) {
      const v = data[i];
      const o = i * 4;
      if (Number.isNaN(v)) {
        img.data[o + 3] = 0;
        continue;
      }
      const u = Math.max(0, Math.min(1, (v - lo) / span));
      const k = Math.round(u * 255) * 3;
      img.data[o] = lut[k];
      img.data[o + 1] = lut[k + 1];
      img.data[o + 2] = lut[k + 2];
      img.data[o + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    setTheme((n) => n + 1);
    // the range is read by its two ends: a parent that builds `[lo, hi]` anew each render must not rebuild the texture each render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, cols, rows, lut, range[0], range[1]]);

  // A theme change redraws the overlay with the new tokens.
  useEffect(() => {
    const obs = new MutationObserver(() => setTheme((n) => n + 1));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'class'] });
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    const c = canvas.current;
    const t = texture.current;
    if (!c || !t) return;
    const dpr = window.devicePixelRatio || 1;
    c.width = Math.round(width * dpr);
    c.height = Math.round(height * dpr);
    const ctx = c.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.imageSmoothingEnabled = false;
    const o = toPx(0, 0);
    ctx.save();
    ctx.beginPath();
    ctx.rect(fit.ox, fit.oy, fit.sx * cols, fit.sy * rows);
    ctx.clip();
    ctx.drawImage(t, o.x, o.y, cols * fit.sx * view.scale, rows * fit.sy * view.scale);
    for (const r of rects) {
      const a = toPx(r.c0, r.r0);
      const b = toPx(r.c1, r.r1);
      ctx.strokeStyle = token(TONE[r.tone]);
      ctx.lineWidth = 1.5;
      ctx.setLineDash(r.dashed ? [6, 4] : []);
      ctx.strokeRect(a.x, a.y, b.x - a.x, b.y - a.y);
      if (r.label) {
        ctx.setLineDash([]);
        ctx.font = '11px sans-serif';
        ctx.fillStyle = token(TONE[r.tone]);
        ctx.fillText(r.label, Math.max(a.x, fit.ox) + 4, Math.max(a.y, fit.oy) + 13);
      }
    }
    ctx.setLineDash([]);
    if (region) {
      const a = toPx(region.c0, region.r0);
      const b = toPx(region.c1 + 1, region.r1 + 1);
      ctx.strokeStyle = token('--color-accent');
      ctx.lineWidth = 2;
      ctx.strokeRect(a.x, a.y, b.x - a.x, b.y - a.y);
    }
    const dense = marks.length > 200;
    for (const m of marks) {
      const p = toPx(m.col + 0.5, m.row + 0.5);
      if (p.x < fit.ox - 10 || p.y < fit.oy - 10 || p.x > fit.ox + fit.sx * cols + 10 || p.y > fit.oy + fit.sy * rows + 10) continue;
      const radius = m.radius ?? (m.selected ? 9 : dense ? 3 : 7);
      ctx.strokeStyle = token(TONE[m.tone]);
      ctx.lineWidth = m.selected ? 2.5 : 1.5;
      ctx.beginPath();
      if (m.kind === 'ring') ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
      else if (m.kind === 'cross') {
        ctx.moveTo(p.x - radius, p.y);
        ctx.lineTo(p.x + radius, p.y);
        ctx.moveTo(p.x, p.y - radius);
        ctx.lineTo(p.x, p.y + radius);
      } else {
        ctx.moveTo(p.x, p.y - radius);
        ctx.lineTo(p.x + radius, p.y);
        ctx.lineTo(p.x, p.y + radius);
        ctx.lineTo(p.x - radius, p.y);
        ctx.closePath();
      }
      ctx.stroke();
      if (m.label && (m.selected || !dense)) {
        ctx.font = '11px sans-serif';
        ctx.fillStyle = token('--color-fg');
        ctx.strokeStyle = token('--color-bg');
        ctx.lineWidth = 3;
        ctx.strokeText(m.label, p.x + radius + 3, p.y - radius);
        ctx.fillText(m.label, p.x + radius + 3, p.y - radius);
      }
    }
    const trail = props.trail;
    if (trail && trail.upto > 0) {
      const from = Math.max(0, trail.upto - 400);
      ctx.strokeStyle = token('--color-warn');
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.8;
      ctx.beginPath();
      for (let i = from; i <= trail.upto && i < trail.col.length; i++) {
        const p = toPx(trail.col[i] + 0.5, trail.row[i] + 0.5);
        if (i === from) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      }
      ctx.stroke();
      ctx.globalAlpha = 1;
      const h = toPx(trail.col[Math.min(trail.upto, trail.col.length - 1)] + 0.5, trail.row[Math.min(trail.upto, trail.row.length - 1)] + 0.5);
      ctx.fillStyle = token('--color-warn');
      ctx.beginPath();
      ctx.arc(h.x, h.y, 4, 0, Math.PI * 2);
      ctx.fill();
    }
    if (cursor) {
      const p = toPx(cursor.col + 0.5, cursor.row + 0.5);
      ctx.strokeStyle = token('--color-fg');
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(p.x, fit.oy);
      ctx.lineTo(p.x, fit.oy + fit.sy * rows);
      ctx.moveTo(fit.ox, p.y);
      ctx.lineTo(fit.ox + fit.sx * cols, p.y);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    if (drag?.kind === 'brush') {
      ctx.strokeStyle = token('--color-accent');
      ctx.fillStyle = token('--color-accent');
      ctx.globalAlpha = 0.18;
      ctx.fillRect(Math.min(drag.x0, drag.x1), Math.min(drag.y0, drag.y1), Math.abs(drag.x1 - drag.x0), Math.abs(drag.y1 - drag.y0));
      ctx.globalAlpha = 1;
      ctx.strokeRect(Math.min(drag.x0, drag.x1), Math.min(drag.y0, drag.y1), Math.abs(drag.x1 - drag.x0), Math.abs(drag.y1 - drag.y0));
    }
    ctx.restore();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [width, height, view, cursor, marks, rects, region, drag, theme, fit, toPx, cols, rows, props.trail]);

  const cellAt = (e: { clientX: number; clientY: number }) => {
    const box = canvas.current!.getBoundingClientRect();
    const px = e.clientX - box.left;
    const py = e.clientY - box.top;
    const c = toCell(px, py);
    return { px, py, col: Math.floor(c.col), row: Math.floor(c.row), inside: c.col >= 0 && c.col < cols && c.row >= 0 && c.row < rows };
  };
  const hitMark = (px: number, py: number): HeatMark | undefined => {
    let best: HeatMark | undefined;
    let bestD = HIT * HIT;
    for (const m of marks) {
      if (m.id === undefined) continue;
      const p = toPx(m.col + 0.5, m.row + 0.5);
      const d = (p.x - px) ** 2 + (p.y - py) ** 2;
      if (d <= bestD) {
        best = m;
        bestD = d;
      }
    }
    return best;
  };

  const zoomAt = useCallback(
    (factor: number, px: number, py: number) => {
      setView((v) => {
        const scale = Math.max(1, Math.min(64, v.scale * factor));
        if (scale === 1) return { scale: 1, tx: 0, ty: 0 };
        const k = scale / v.scale;
        // keep the point under (px, py) fixed
        const cx = px - fit.ox;
        const cy = py - fit.oy;
        const w = fit.sx * cols * scale;
        const h = fit.sy * rows * scale;
        const tx = Math.min(0, Math.max(width - fit.ox * 2 - w, cx - (cx - v.tx) * k));
        const ty = Math.min(0, Math.max(height - fit.oy * 2 - h, cy - (cy - v.ty) * k));
        return { scale, tx, ty };
      });
    },
    [fit, cols, rows, width, height],
  );

  // The wheel needs a non-passive listener to keep the page from scrolling while the map zooms.
  useEffect(() => {
    const c = canvas.current;
    if (!c) return;
    const onWheel = (e: WheelEvent) => {
      if (!(focused || e.ctrlKey || e.metaKey)) return;
      e.preventDefault();
      const box = c.getBoundingClientRect();
      zoomAt(e.deltaY < 0 ? 1.25 : 0.8, e.clientX - box.left, e.clientY - box.top);
    };
    c.addEventListener('wheel', onWheel, { passive: false });
    return () => c.removeEventListener('wheel', onWheel);
  }, [focused, zoomAt]);

  useEffect(() => {
    setView({ scale: 1, tx: 0, ty: 0 });
  }, [cols, rows]);

  const publish = useCallback(
    (cell: { col: number; row: number } | null) => {
      setCursor(cell);
      props.onCursor?.(cell);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [props.onCursor],
  );

  const onDown = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    const { px, py, col, row, inside } = cellAt(e);
    e.currentTarget.focus();
    e.currentTarget.setPointerCapture(e.pointerId);
    if (!inside) return;
    if (e.shiftKey) {
      setDrag({ kind: 'pan', x0: px, y0: py, x1: px, y1: py, view0: view });
      return;
    }
    if (mode === 'add') {
      props.onAdd?.(col, row);
      return;
    }
    const hit = hitMark(px, py);
    if (mode === 'delete') {
      if (hit?.id !== undefined) props.onDelete?.(hit.id);
      return;
    }
    if (mode === 'move' && hit?.id !== undefined) {
      setDrag({ kind: 'trap', x0: px, y0: py, x1: px, y1: py, id: hit.id });
      return;
    }
    setDrag({ kind: 'brush', x0: px, y0: py, x1: px, y1: py });
  };
  const onMovePointer = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    const { px, py, col, row, inside } = cellAt(e);
    if (inside) publish({ col, row });
    if (!drag) return;
    if (drag.kind === 'pan' && drag.view0) {
      const w = fit.sx * cols * drag.view0.scale;
      const h = fit.sy * rows * drag.view0.scale;
      setView({
        scale: drag.view0.scale,
        tx: Math.min(0, Math.max(width - fit.ox * 2 - w, drag.view0.tx + px - drag.x0)),
        ty: Math.min(0, Math.max(height - fit.oy * 2 - h, drag.view0.ty + py - drag.y0)),
      });
      return;
    }
    if (drag.kind === 'trap' && drag.id !== undefined && inside) props.onMove?.(drag.id, col, row);
    setDrag({ ...drag, x1: px, y1: py });
  };
  const onUp = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    if (!drag) return;
    const { col, row, inside } = cellAt(e);
    if (drag.kind === 'brush') {
      const moved = Math.hypot(drag.x1 - drag.x0, drag.y1 - drag.y0) >= 5;
      const a = toCell(drag.x0, drag.y0);
      const b = toCell(drag.x1, drag.y1);
      const clamp = (v: number, n: number) => Math.max(0, Math.min(n - 1, Math.floor(v)));
      if (moved) props.onBrush?.(clamp(Math.min(a.col, b.col), cols), clamp(Math.min(a.row, b.row), rows), clamp(Math.max(a.col, b.col), cols), clamp(Math.max(a.row, b.row), rows));
      else if (inside) props.onPick?.(col, row);
    }
    setDrag(null);
  };

  const onKey = (e: ReactKeyboardEvent<HTMLCanvasElement>) => {
    const step = e.shiftKey ? 10 : 1;
    const at = cursor ?? { col: Math.floor(cols / 2), row: Math.floor(rows / 2) };
    const move = (dc: number, dr: number) => {
      e.preventDefault();
      publish({ col: Math.max(0, Math.min(cols - 1, at.col + dc * step)), row: Math.max(0, Math.min(rows - 1, at.row + dr * step)) });
    };
    if (e.key === 'ArrowLeft') move(-1, 0);
    else if (e.key === 'ArrowRight') move(1, 0);
    else if (e.key === 'ArrowUp') move(0, -1);
    else if (e.key === 'ArrowDown') move(0, 1);
    else if (e.key === 'Home') {
      e.preventDefault();
      publish({ col: 0, row: at.row });
    } else if (e.key === 'End') {
      e.preventDefault();
      publish({ col: cols - 1, row: at.row });
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (mode === 'add') props.onAdd?.(at.col, at.row);
      else props.onPick?.(at.col, at.row);
    } else if (e.key === '+' || e.key === '=') {
      e.preventDefault();
      zoomAt(1.25, width / 2, height / 2);
    } else if (e.key === '-') {
      e.preventDefault();
      zoomAt(0.8, width / 2, height / 2);
    } else if (e.key === '0' || (e.key === 'Escape' && zoomed)) {
      e.preventDefault();
      setView({ scale: 1, tx: 0, ty: 0 });
    }
  };

  const value = cursor ? data[cursor.row * cols + cursor.col] : null;
  const reading = cursor && value !== null && !Number.isNaN(value) ? describe(cursor.col, cursor.row, value) : null;
  const table = useMemo(() => thinned(data, cols, rows), [data, cols, rows]);
  return (
    <div style={{ position: 'relative', width, height }}>
      <canvas
        ref={canvas}
        tabIndex={0}
        role="img"
        aria-label={pick(props.label, lang)}
        aria-describedby={`${summaryId} ${tableId}`}
        data-heatmap=""
        data-mode={mode}
        data-zoomed={zoomed ? 'true' : 'false'}
        style={{ width, height, display: 'block', cursor: mode === 'add' ? 'copy' : mode === 'delete' ? 'not-allowed' : drag?.kind === 'pan' ? 'grabbing' : 'crosshair', touchAction: 'pan-y' }}
        onPointerDown={onDown}
        onPointerMove={onMovePointer}
        onPointerUp={onUp}
        onPointerLeave={() => !drag && publish(null)}
        onDoubleClick={() => setView({ scale: 1, tx: 0, ty: 0 })}
        onKeyDown={onKey}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
      />
      <p className="dh-readout" role="status" aria-live="polite" data-heatmap-readout="">
        {reading ?? (lang === 'es' ? 'Pase el puntero o use las flechas para leer valores.' : 'Hover or use the arrow keys to read values.')}
      </p>
      {zoomed && (
        <button type="button" className="btn dh-reset" onClick={() => setView({ scale: 1, tx: 0, ty: 0 })}>
          {pick(RESET, lang)}
        </button>
      )}
      <p id={summaryId} className="sr-only">
        {props.summary}
      </p>
      <table id={tableId} className="sr-only">
        <caption>{pick(props.tableLabel ?? props.label, lang)}</caption>
        <tbody>
          {table.values.map((line, i) => (
            <tr key={i}>
              <th scope="row">{i * table.br}</th>
              {line.map((v, j) => (
                <td key={j}>{Number.isNaN(v) ? '' : Number(v.toPrecision(4))}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** The map in a Stage: the stage gives it a real size, and nothing is drawn before it has one. */
export function Heatmap(props: HeatmapProps) {
  return <Stage label={props.label}>{(size) => <HeatCanvas {...props} width={size.width} height={size.height} />}</Stage>;
}
