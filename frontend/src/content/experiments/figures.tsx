// The protocol figure of the Experiments page: how a result of the bake is judged (above, the path every case follows) and the two
// shortcuts the protocol forbids (below, struck out). Coloured only with the shell's theme tokens and `dg-*` classes, so it follows the
// light and dark themes; a cross is two strokes, never a character. The figure holds no measured number: a count in a label comes from
// the artifacts or the code constants through the caller.
import { useT } from '../bi';
import { Arrow, ArrowDefs, Box, Svg } from '../methodology/svg';

const BAD = 'var(--color-bad)';

function Cross({ x, y }: { x: number; y: number }) {
  return <path d={`M ${x - 7} ${y - 7} L ${x + 7} ${y + 7} M ${x + 7} ${y - 7} L ${x - 7} ${y + 7}`} stroke={BAD} strokeWidth="3" strokeLinecap="round" fill="none" />;
}

function Forbidden({ x, y, w, h, lines }: { x: number; y: number; w: number; h: number; lines: string[] }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={8} fill="none" stroke={BAD} strokeWidth="2" strokeDasharray="6 4" />
      {lines.map((line, i) => (
        <text key={i} x={x + w / 2} y={y + 24 + i * 16} textAnchor="middle" className={i === 0 ? 'dg-box-title' : 'dg-box-sub'}>
          {line}
        </text>
      ))}
      <path d={`M ${x + 8} ${y + h - 8} L ${x + w - 8} ${y + 8}`} stroke={BAD} strokeWidth="2" strokeLinecap="round" opacity="0.7" />
      <Cross x={x + 16} y={y + 16} />
    </g>
  );
}

/** The judging path of a case and the two shortcuts it forbids; `seeds` is the number of seeds a measured range rests on, as text. */
export function ProtocolFigure({ seeds }: { seeds: string }) {
  const t = useT();
  const id = 'exp-protocol';
  return (
    <Svg
      h={286}
      label={t(
        'The path of a case from its record to the page, and the two shortcuts the protocol forbids',
        'El camino de un caso desde su registro hasta la página, y los dos atajos que el protocolo prohíbe',
      )}
    >
      <ArrowDefs id={id} />
      <text x={0} y={16} className="dg-box-title">
        {t('Allowed: every case takes this path', 'Permitido: todo caso sigue este camino')}
      </text>
      <Box x={0} y={30} w={140} h={64} lines={[t('Case record', 'Registro del caso'), t('one seed each', 'una semilla cada uno')]} />
      <Box x={166} y={30} w={140} h={64} lines={[t('Bake', 'Generación'), t('every method, one scoring', 'cada método, una medición')]} tone="accent" />
      <Box x={332} y={30} w={140} h={64} lines={[t('Range check', 'Verificación de rango'), t('outside it, the bake fails', 'fuera de él, falla')]} tone="accent" />
      <Box x={498} y={30} w={142} h={64} lines={[t('Manifest and trace', 'Manifiesto y traza'), t('committed, read here', 'versionados, leídos aquí')]} tone="good" />
      <Arrow id={id} x1={140} y1={62} x2={166} y2={62} />
      <Arrow id={id} x1={306} y1={62} x2={332} y2={62} />
      <Arrow id={id} x1={472} y1={62} x2={498} y2={62} />
      <text x={0} y={134} className="dg-box-title">
        {t('Two kinds of range, kept apart', 'Dos clases de rango, mantenidas aparte')}
      </text>
      <Box x={0} y={146} w={310} h={48} lines={[t('Measured range: a regression envelope', 'Rango medido: una envolvente de regresión'), t(`${seeds} seeds, the canonical seed among them`, `${seeds} semillas, la semilla canónica entre ellas`)]} />
      <Box x={330} y={146} w={310} h={48} lines={[t('Published band: an outside reference', 'Banda publicada: una referencia externa'), t('kept as published, never refitted', 'se conserva como se publicó, nunca se reajusta')]} tone="good" />
      <text x={0} y={224} className="dg-box-title">
        {t('Forbidden', 'Prohibido')}
      </text>
      <Forbidden x={0} y={234} w={310} h={46} lines={[t('Call a measured range a validation', 'Llamar validación a un rango medido'), t('it was fitted on the run it judges', 'se ajustó con la corrida que juzga')]} />
      <Forbidden x={330} y={234} w={310} h={46} lines={[t('Move a published band to fit', 'Mover una banda publicada para ajustarla'), t('a deviation is reported, not hidden', 'una desviación se informa, no se oculta')]} />
    </Svg>
  );
}
