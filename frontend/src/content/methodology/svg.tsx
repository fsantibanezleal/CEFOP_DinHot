// Drawing helpers of the Methodology figures: boxes, arrows and labels coloured only with the shell's theme classes and tokens
// (`dg-*` classes and `var(--color-*)`), so every figure follows the light and dark themes. The labels are written in the displayed
// language by the caller (`useT`). A figure is placed in a `Figure` that carries its caption.
import type { ReactNode } from 'react';

export type Tr = (en: string, es: string) => string;
export type Tone = 'accent' | 'good' | 'warn' | undefined;

/** The arrowhead marker of one figure; `id` must be unique on the page. */
export function ArrowDefs({ id }: { id: string }) {
  return (
    <defs>
      <marker id={id} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" className="dg-arrowhead" />
      </marker>
    </defs>
  );
}

/** A straight arrow from (x1, y1) to (x2, y2) with an optional label at (lx, ly). */
export function Arrow({ id, x1, y1, x2, y2, label, lx, ly, dashed }: { id: string; x1: number; y1: number; x2: number; y2: number; label?: string; lx?: number; ly?: number; dashed?: boolean }) {
  return (
    <g>
      <line x1={x1} y1={y1} x2={x2} y2={y2} className="dg-edge" strokeDasharray={dashed ? '5 4' : undefined} markerEnd={`url(#${id})`} />
      {label && (
        <text x={lx ?? (x1 + x2) / 2} y={ly ?? (y1 + y2) / 2 - 6} textAnchor="middle" className="dg-edge-label">
          {label}
        </text>
      )}
    </g>
  );
}

/** A path arrow (curves and elbows). */
export function PathArrow({ id, d, label, lx, ly, dashed }: { id: string; d: string; label?: string; lx?: number; ly?: number; dashed?: boolean }) {
  return (
    <g>
      <path d={d} className="dg-edge" strokeDasharray={dashed ? '5 4' : undefined} markerEnd={`url(#${id})`} />
      {label && (
        <text x={lx ?? 0} y={ly ?? 0} textAnchor="middle" className="dg-edge-label">
          {label}
        </text>
      )}
    </g>
  );
}

/** A rounded box with one to three centred lines; the first line is the title, the others the sub-lines. */
export function Box({ x, y, w, h, lines, tone }: { x: number; y: number; w: number; h: number; lines: string[]; tone?: Tone }) {
  const n = lines.length;
  const lh = 15;
  const y0 = y + h / 2 - ((n - 1) * lh) / 2 + 4;
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={8} className={`dg-box${tone === 'accent' || tone === 'good' ? ' ' + tone : ''}`} style={tone === 'warn' ? { stroke: 'var(--color-warn)' } : undefined} />
      {lines.map((line, i) => (
        <text key={i} x={x + w / 2} y={y0 + i * lh} textAnchor="middle" className={i === 0 ? `dg-box-title${tone === 'accent' ? ' accent' : ''}` : 'dg-box-sub'}>
          {line}
        </text>
      ))}
    </g>
  );
}

/** A free text label. */
export function Label({ x, y, children, anchor = 'middle', kind = 'axis' }: { x: number; y: number; children: ReactNode; anchor?: 'start' | 'middle' | 'end'; kind?: 'axis' | 'note' | 'tick' | 'edge' }) {
  const cls = kind === 'axis' ? 'dg-axis-label' : kind === 'note' ? 'dg-note' : kind === 'tick' ? 'dg-tick' : 'dg-edge-label';
  return (
    <text x={x} y={y} textAnchor={anchor} className={cls}>
      {children}
    </text>
  );
}

/** The root of a figure: wide, responsive, with a role and a label. */
export function Svg({ h, label, children }: { h: number; label: string; children: ReactNode }) {
  return (
    <svg className="fig-svg wide" viewBox={`0 0 640 ${h}`} role="img" aria-label={label}>
      {children}
    </svg>
  );
}
