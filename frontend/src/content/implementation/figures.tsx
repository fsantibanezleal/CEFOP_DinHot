// Figures of the Implementation page: hand-authored schematics drawn with the Methodology drawing helpers (shell classes and
// tokens only, so they follow the light and dark themes). They hold no measured number; a count in a label is a stable fact of
// the code (the live registry lists 15 methods, `frontend/src/engine/holo/client.ts` `LIVE_METHODS`).
import { useT } from '../bi';
import { Arrow, ArrowDefs, Box, Svg } from '../methodology/svg';

/** The parts of the build and the direction of flow between them. */
export function BuildFigure() {
  const t = useT();
  const id = 'impl-build';
  return (
    <Svg h={300} label={t('The parts of the build: the pipeline, the committed artifacts, the site, the reference and live engines, the workbench and the gate', 'Las partes de la compilación: el pipeline, los artefactos comprometidos, el sitio, los motores de referencia y en vivo, la mesa de trabajo y la compuerta')}>
      <ArrowDefs id={id} />
      <Box x={0} y={14} w={180} h={58} lines={[t('Offline pipeline', 'Pipeline fuera de línea'), 'data-pipeline/run.py']} tone="accent" />
      <Box x={230} y={14} w={180} h={58} lines={[t('Committed artifacts', 'Artefactos versionados'), 'data/derived, models']} tone="good" />
      <Box x={460} y={14} w={180} h={58} lines={[t('Static site', 'Sitio estático'), 'copy-data.mjs, Vite']} />
      <Box x={0} y={118} w={180} h={58} lines={[t('Python engine', 'Motor en Python'), t('the reference', 'la referencia')]} />
      <Box x={230} y={118} w={180} h={58} lines={[t('Live engine', 'Motor en vivo'), 'Web Worker, WebGPU']} tone="accent" />
      <Box x={460} y={118} w={180} h={58} lines={[t('Workbench', 'Mesa de trabajo'), t('replay and live', 'reproducción y en vivo')]} />
      <Box x={0} y={226} w={640} h={52} lines={[t('Measured gate, then GitHub Pages', 'Compuerta medida, luego GitHub Pages'), t('npm run gate walks the built site before any deploy', 'npm run gate recorre el sitio compilado antes de cualquier despliegue')]} tone="good" />
      <Arrow id={id} x1={180} y1={43} x2={230} y2={43} />
      <Arrow id={id} x1={410} y1={43} x2={460} y2={43} />
      <Arrow id={id} x1={90} y1={72} x2={90} y2={118} label={t('runs', 'corre')} lx={118} ly={98} />
      <Arrow id={id} x1={180} y1={147} x2={230} y2={147} label={t('parity', 'paridad')} lx={205} ly={140} dashed />
      <Arrow id={id} x1={410} y1={147} x2={460} y2={147} />
      <Arrow id={id} x1={550} y1={72} x2={550} y2={118} />
      <Arrow id={id} x1={550} y1={176} x2={550} y2={226} />
    </Svg>
  );
}

/** The three lanes and what each holds. */
export function LanesFigure() {
  const t = useT();
  const id = 'impl-lanes';
  return (
    <Svg h={262} label={t('The three lanes: offline, replay and live, with what each holds', 'Los tres carriles: fuera de línea, reproducción y en vivo, con lo que contiene cada uno')}>
      <ArrowDefs id={id} />
      <Box x={0} y={10} w={200} h={52} lines={[t('Offline', 'Fuera de línea'), t('workstation, never CI', 'estación, nunca CI')]} tone="accent" />
      <Box x={220} y={10} w={200} h={52} lines={[t('Replay', 'Reproducción'), t('committed artifacts', 'artefactos versionados')]} tone="good" />
      <Box x={440} y={10} w={200} h={52} lines={[t('Live', 'En vivo'), t('in the browser', 'en el navegador')]} tone="accent" />
      <Box x={0} y={90} w={200} h={52} lines={[t('Bake and benchmark', 'Precálculo y benchmark'), 'run.py all, benchmark']} />
      <Box x={220} y={90} w={200} h={52} lines={[t('Fetched as JSON', 'Pedidos como JSON'), 'data/...json?v=VERSION']} />
      <Box x={440} y={90} w={200} h={52} lines={[t('Web Worker, CPU path', 'Web Worker, vía CPU'), t('15 methods', '15 métodos')]} />
      <Box x={0} y={170} w={200} h={52} lines={[t('Lane gate', 'Compuerta de carril'), '1500 ms, 256 KiB']} />
      <Box x={220} y={170} w={200} h={52} lines={[t('Trace of the case', 'Traza del caso'), t('within the byte gate', 'dentro de la compuerta')]} />
      <Box x={440} y={170} w={200} h={52} lines={[t('WebGPU, optional', 'WebGPU, opcional'), 'M04, M06, M07']} />
      <Arrow id={id} x1={200} y1={36} x2={220} y2={36} />
      <Arrow id={id} x1={420} y1={36} x2={440} y2={36} />
      <Arrow id={id} x1={100} y1={62} x2={100} y2={90} />
      <Arrow id={id} x1={320} y1={62} x2={320} y2={90} />
      <Arrow id={id} x1={540} y1={62} x2={540} y2={90} />
      <Arrow id={id} x1={100} y1={142} x2={100} y2={170} />
      <Arrow id={id} x1={320} y1={142} x2={320} y2={170} />
      <Arrow id={id} x1={540} y1={170} x2={540} y2={142} label={t('falls back', 'recurre a')} lx={592} ly={160} dashed />
      <text x={320} y={250} textAnchor="middle" className="dg-note">
        {t('artifacts flow left to right; parity tests tie the live lane to Python', 'artefactos de izquierda a derecha; la paridad ata el carril en vivo a Python')}
      </text>
    </Svg>
  );
}
