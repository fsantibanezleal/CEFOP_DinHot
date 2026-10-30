// Small inline figures of the documentation pages: a row of labelled stages joined by arrows, coloured only with the
// shell's theme tokens, so it follows the light and dark themes. Each figure is placed in a `Figure` that carries its
// caption; the labels are written in the displayed language by the caller (`useT`).

/** Splits a label into at most two lines of about `width` characters, at a space. */
function wrap(label: string, width: number): string[] {
  if (label.length <= width) return [label];
  const words = label.split(' ');
  const lines: string[] = [''];
  for (const w of words) {
    const cur = lines[lines.length - 1];
    if (cur && (cur + ' ' + w).length > width && lines.length < 2) lines.push(w);
    else lines[lines.length - 1] = cur ? `${cur} ${w}` : w;
  }
  return lines;
}

export function FlowFigure({ stages, edges, label, tone }: { stages: string[]; edges?: string[]; label: string; tone?: 'accent' | 'good' | 'warn' }) {
  const n = stages.length;
  const gap = edges ? 64 : 36;
  const w = (620 - (n - 1) * gap) / n;
  const chars = Math.max(9, Math.floor(w / 8.6));
  const fill = tone === 'good' ? 'var(--color-good)' : tone === 'warn' ? 'var(--color-warn)' : 'var(--color-accent)';
  return (
    <svg className="fig-svg wide" viewBox="0 0 640 130" role="img" aria-label={label}>
      {stages.map((s, i) => {
        const x = 10 + i * (w + gap);
        const lines = wrap(s, chars);
        return (
          <g key={i}>
            <rect x={x} y="36" width={w} height="64" rx="8" fill="var(--color-surface-2)" stroke="var(--color-border)" strokeWidth="1.5" />
            <rect x={x} y="36" width="6" height="64" rx="3" fill={fill} />
            {lines.map((line, k) => (
              <text key={k} x={x + w / 2 + 3} y={lines.length === 1 ? 73 : 62 + k * 18} textAnchor="middle" fontSize="13" fontWeight="600" fill="var(--color-fg)">
                {line}
              </text>
            ))}
            {i < n - 1 && (
              <g>
                <path d={`M ${x + w + 6} 68 L ${x + w + gap - 6} 68 M ${x + w + gap - 13} 62 L ${x + w + gap - 6} 68 L ${x + w + gap - 13} 74`} fill="none" stroke="var(--color-fg-faint)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                {edges?.[i] && (
                  <text x={x + w + gap / 2} y="56" textAnchor="middle" fontSize="12" fill="var(--color-fg-subtle)">
                    {edges[i]}
                  </text>
                )}
              </g>
            )}
          </g>
        );
      })}
    </svg>
  );
}
