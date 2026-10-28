// The hand-drawn figures of the Methodology page, one or more per topic. Theme tokens only (the `dg-*` classes and the shell colour tokens),
// labels in both languages through the translator `t`, sized to the container by the viewBox. Schematics carry no measured
// DinHot number: every value written in a figure is a symbol or a published quantity named in the topic's text.
import { Arrow, ArrowDefs, Box, Label, PathArrow, Svg, type Tr } from './svg';

/** Optics: SLM, Fourier lens, focal plane, and the sampling of the focal plane. */
export function OpticsFigure({ t }: { t: Tr }) {
  const id = 'ah-optics';
  return (
    <Svg h={270} label={t('Optical path from the SLM through the lens to the focal plane, with its sampling', 'Camino óptico del SLM a través de la lente hasta el plano focal, con su muestreo')}>
      <ArrowDefs id={id} />
      <rect x={30} y={35} width={14} height={90} rx={3} className="dg-box accent" />
      <Label x={37} y={146}>SLM</Label>
      <Label x={37} y={162} kind="tick">N x N, p</Label>
      <line x1={44} y1={80} x2={236} y2={80} className="dg-edge" markerEnd={`url(#${id})`} />
      <Label x={140} y={72} kind="edge">{t('input beam A(x)', 'haz de entrada A(x)')}</Label>
      <ellipse cx={250} cy={80} rx={10} ry={48} className="dg-fill-accent" />
      <Label x={250} y={26}>{t('lens f', 'lente f')}</Label>
      <line x1={470} y1={30} x2={470} y2={130} className="dg-axis" />
      <Label x={470} y={146}>{t('focal plane', 'plano focal')}</Label>
      {[[50, 62], [80, 80], [110, 98]].map(([y0, y1]) => (
        <line key={y0} x1={260} y1={y0} x2={468} y2={y1} className="dg-edge" />
      ))}
      <Arrow id={id} x1={255} y1={160} x2={468} y2={160} label="f" ly={176} />
      <line x1={60} y1={225} x2={580} y2={225} className="dg-axis" />
      <line x1={120} y1={196} x2={120} y2={240} className="dg-marker" />
      <line x1={520} y1={196} x2={520} y2={240} className="dg-marker" />
      <Label x={120} y={256} kind="tick">-λf/(2p)</Label>
      <Label x={520} y={256} kind="tick">+λf/(2p)</Label>
      <Arrow id={id} x1={320} y1={200} x2={126} y2={200} />
      <Arrow id={id} x1={320} y1={200} x2={514} y2={200} />
      <Label x={320} y={192} kind="edge">{t('replica period λf/p', 'período de réplicas λf/p')}</Label>
      {[200, 260, 380, 440].map((x) => (
        <circle key={x} cx={x} cy={225} r={6} className="dg-node" />
      ))}
      <rect x={314} y={219} width={12} height={12} className="dg-fill-warn" />
      <Label x={320} y={246} kind="tick">{t('zero order', 'orden cero')}</Label>
      <circle cx={560} cy={225} r={6} fill="none" stroke="var(--color-bad)" strokeWidth={1.6} />
      <Label x={560} y={212} kind="tick">{t('refused', 'rechazada')}</Label>
      <line x1={338} y1={218} x2={338} y2={232} className="dg-axis" />
      <Label x={380} y={246} anchor="start" kind="tick">{t('bin λf/(pad N p)', 'bin λf/(pad N p)')}</Label>
    </Svg>
  );
}

/** Metrics: per-trap intensities with max, min and mean, and the power budget. */
export function MetricsFigure({ t }: { t: Tr }) {
  const bars = [44, 62, 51, 70, 38, 58];
  return (
    <Svg h={230} label={t('Trap intensities with their maximum, minimum and mean, and the split of the input power', 'Intensidades de las trampas con su máximo, mínimo y promedio, y el reparto de la potencia de entrada')}>
      <line x1={40} y1={170} x2={300} y2={170} className="dg-axis" />
      {bars.map((h, i) => (
        <rect key={i} x={55 + i * 40} y={170 - h * 1.7} width={26} height={h * 1.7} className="dg-bar" />
      ))}
      <line x1={40} y1={170 - 70 * 1.7} x2={300} y2={170 - 70 * 1.7} className="dg-marker" />
      <line x1={40} y1={170 - 38 * 1.7} x2={300} y2={170 - 38 * 1.7} className="dg-marker" />
      <line x1={40} y1={170 - 54 * 1.7} x2={300} y2={170 - 54 * 1.7} className="dg-curve-faint" />
      <Label x={304} y={170 - 70 * 1.7 + 4} anchor="start" kind="tick">max</Label>
      <Label x={304} y={170 - 54 * 1.7 + 4} anchor="start" kind="tick">{t('mean', 'prom.')}</Label>
      <Label x={304} y={170 - 38 * 1.7 + 4} anchor="start" kind="tick">min</Label>
      <Label x={170} y={192}>{t('trap intensity I_m (schematic)', 'intensidad de trampa I_m (esquema)')}</Label>
      <Label x={170} y={210} kind="note">{t('u = 1 - (max - min)/(max + min)', 'u = 1 - (máx - mín)/(máx + mín)')}</Label>
      <Label x={490} y={40}>{t('where the input power goes (schematic)', 'adónde va la potencia (esquema)')}</Label>
      <rect x={350} y={60} width={140} height={34} className="dg-fill-accent" />
      <rect x={490} y={60} width={50} height={34} className="dg-fill-warn" />
      <rect x={540} y={60} width={70} height={34} className="dg-box" />
      <rect x={610} y={60} width={14} height={34} className="dg-box" />
      <Label x={420} y={115} kind="tick">{t('traps', 'trampas')}</Label>
      <Label x={515} y={115} kind="tick">{t('zero', 'cero')}</Label>
      <Label x={575} y={133} kind="tick">{t('ghosts', 'fantasmas')}</Label>
      <Label x={617} y={151} kind="tick" anchor="middle">{t('rest', 'resto')}</Label>
      <Label x={487} y={186} kind="note">{t('sum of the four = 1 (fractions of N_pix)', 'la suma de las cuatro = 1 (fracciones de N_pix)')}</Label>
    </Svg>
  );
}

const CELL = [
  [2, 0, 3, 1, 0, 2, 3, 1],
  [1, 3, 0, 2, 3, 1, 0, 2],
  [3, 2, 1, 0, 2, 3, 1, 0],
  [0, 1, 2, 3, 1, 0, 2, 3],
  [2, 3, 0, 1, 3, 2, 0, 1],
  [1, 0, 3, 2, 0, 1, 3, 2],
  [3, 1, 2, 0, 2, 3, 1, 0],
  [0, 2, 1, 3, 1, 0, 2, 3],
];
const TRAP_FILL = ['var(--color-accent)', 'var(--color-magenta)', 'var(--color-good)', 'var(--color-warn)'];

/** Analytic holograms: the phasor sum of M01 and M02 and the pixel subdomains of M03. */
export function AnalyticFigure({ t }: { t: Tr }) {
  const id = 'ah-analytic';
  const ph = (cx: number, cy: number, angs: number[]) => {
    let x = cx;
    let y = cy;
    const segs = angs.map((a, i) => {
      const nx = x + 26 * Math.cos(a);
      const ny = y - 26 * Math.sin(a);
      const s = <Arrow key={i} id={id} x1={x} y1={y} x2={nx} y2={ny} />;
      x = nx;
      y = ny;
      return s;
    });
    return { segs, x, y };
  };
  const a = ph(50, 120, [0.2, 0.9, 1.6, 0.5]);
  const b = ph(250, 120, [0.2 + 0.7, 0.9 - 0.5, 1.6 + 1.1, 0.5 - 0.9]);
  return (
    <Svg h={230} label={t('Phasor sum of prisms and lenses, the same with random phases, and the pixel subdomains of the random mask', 'Suma de fasores de prismas y lentes, la misma con fases aleatorias, y los subdominios de píxeles de la máscara aleatoria')}>
      <ArrowDefs id={id} />
      <Label x={110} y={28}>{t('M01: arg of the sum', 'M01: arg de la suma')}</Label>
      {a.segs}
      <Arrow id={id} x1={50} y1={120} x2={a.x} y2={a.y} dashed />
      <Label x={110} y={190} kind="tick">exp(iΔ)</Label>
      <Label x={310} y={28}>{t('M02: random θ_m added', 'M02: se suma θ_m aleatorio')}</Label>
      {b.segs}
      <Arrow id={id} x1={250} y1={120} x2={b.x} y2={b.y} dashed />
      <Label x={310} y={190} kind="tick">exp(i(Δ + θ_m))</Label>
      <Label x={525} y={28}>{t('M03: one trap per pixel', 'M03: una trampa por píxel')}</Label>
      {CELL.map((row, r) =>
        row.map((c, k) => <rect key={`${r}-${k}`} x={465 + k * 15} y={45 + r * 15} width={14} height={14} style={{ fill: TRAP_FILL[c], opacity: 0.8 }} />),
      )}
      <Label x={525} y={190} kind="tick">{t('disjoint subdomains I_k', 'subdominios disjuntos I_k')}</Label>
    </Svg>
  );
}

/** The Gerchberg-Saxton loop between the SLM plane and the focal plane, with the weights and the fixed phase. */
export function GsFigure({ t }: { t: Tr }) {
  const id = 'ah-gs';
  return (
    <Svg h={250} label={t('Gerchberg-Saxton loop between the SLM plane and the focal plane, with trap weights and the phase fixing', 'Lazo de Gerchberg-Saxton entre el plano del SLM y el plano focal, con pesos de trampa y fijación de fase')}>
      <ArrowDefs id={id} />
      <Box x={20} y={70} w={190} h={80} lines={[t('SLM plane', 'plano del SLM'), t('amplitude set to A(x)', 'amplitud fijada en A(x)'), t('phase φ kept', 'fase φ se conserva')]} tone="accent" />
      <Box x={430} y={70} w={190} h={80} lines={[t('focal plane', 'plano focal'), t('amplitude set to target', 'amplitud fijada al objetivo'), t('phase ψ kept (or fixed)', 'fase ψ se conserva (o se fija)')]} tone="accent" />
      <PathArrow id={id} d="M 210 90 C 280 60 360 60 430 90" label={t('forward: F or Σ exp(-iΔ)', 'directa: F o Σ exp(-iΔ)')} lx={320} ly={50} />
      <PathArrow id={id} d="M 430 130 C 360 160 280 160 210 130" label={t('inverse: F⁻¹ or Σ exp(+iΔ)', 'inversa: F⁻¹ o Σ exp(+iΔ)')} lx={320} ly={172} />
      <Box x={240} y={190} w={160} h={44} lines={[t('weights w_m or g_i', 'pesos w_m o g_i'), t('rescale the target', 'reescalan el objetivo')]} tone="good" />
      <PathArrow id={id} d="M 400 212 C 460 212 520 190 525 154" dashed />
      <Label x={320} y={20} kind="note">{t('repeat; after N iterations phase-fixed WGS keeps ψ_i = ψ_N', 'repetir; tras N iteraciones el WGS con fase fija mantiene ψ_i = ψ_N')}</Label>
    </Svg>
  );
}

/** MRAF regions and the optimal-transport map that seeds it. */
export function ShapedFigure({ t }: { t: Tr }) {
  const id = 'ah-shaped';
  return (
    <Svg h={250} label={t('MRAF signal and noise regions, and the optimal-transport map from the input beam to the target', 'Regiones de señal y de ruido de MRAF, y el mapa de transporte óptimo del haz de entrada al objetivo')}>
      <ArrowDefs id={id} />
      <rect x={30} y={40} width={230} height={170} rx={6} className="dg-fill-warn" />
      <ellipse cx={145} cy={125} rx={70} ry={55} className="dg-fill-accent" />
      <ellipse cx={145} cy={125} rx={34} ry={26} className="dg-box" style={{ fill: 'var(--color-surface)' }} />
      <Label x={145} y={32}>{t('focal plane', 'plano focal')}</Label>
      <Label x={145} y={120} kind="tick">{t('signal SR', 'señal SR')}</Label>
      <Label x={145} y={134} kind="tick">{t('amplitude √(m I0)', 'amplitud √(m I0)')}</Label>
      <Label x={55} y={198} anchor="start" kind="tick">{t('noise NR: free, weight (1 - m)', 'ruido NR: libre, peso (1 - m)')}</Label>
      <rect x={340} y={70} width={90} height={90} rx={45} className="dg-fill-accent" />
      <Label x={385} y={60}>{t('input g²', 'entrada g²')}</Label>
      <ellipse cx={560} cy={115} rx={52} ry={52} className="dg-fill-warn" />
      <ellipse cx={560} cy={115} rx={26} ry={26} className="dg-box" style={{ fill: 'var(--color-surface)' }} />
      <Label x={560} y={60}>{t('target G²', 'objetivo G²')}</Label>
      <Arrow id={id} x1={430} y1={100} x2={508} y2={90} />
      <Arrow id={id} x1={430} y1={130} x2={508} y2={140} />
      <Label x={470} y={190} kind="tick">{t('φ(x) = ∫ γ · ds', 'φ(x) = ∫ γ · ds')}</Label>
      <Label x={470} y={206} kind="note">{t('transport map seeds GS or MRAF', 'el mapa de transporte siembra GS o MRAF')}</Label>
    </Svg>
  );
}

/** The three families of cost-function methods. */
export function CostFigure({ t }: { t: Tr }) {
  const id = 'ah-cost';
  return (
    <Svg h={250} label={t('Direct search, conjugate gradient and Wirtinger descent as three loops', 'Búsqueda directa, gradiente conjugado y descenso de Wirtinger como tres lazos')}>
      <ArrowDefs id={id} />
      <Label x={110} y={22}>M09</Label>
      <Box x={20} y={34} w={180} h={40} lines={[t('change one pixel', 'cambiar un píxel')]} />
      <Box x={20} y={102} w={180} h={40} lines={[t('cost C decreases?', '¿baja el costo C?')]} />
      <Box x={20} y={170} w={180} h={40} lines={[t('keep or undo', 'conservar o deshacer')]} tone="good" />
      <Arrow id={id} x1={110} y1={74} x2={110} y2={102} />
      <Arrow id={id} x1={110} y1={142} x2={110} y2={170} />
      <Label x={320} y={22}>M10</Label>
      <Box x={230} y={34} w={180} h={40} lines={[t('two FFTs: C and ∂C/∂φ', 'dos FFT: C y ∂C/∂φ')]} />
      <Box x={230} y={102} w={180} h={40} lines={['d = g + γ d_prev']} />
      <Box x={230} y={170} w={180} h={40} lines={[t('line step along d', 'paso en línea a lo largo de d')]} tone="good" />
      <Arrow id={id} x1={320} y1={74} x2={320} y2={102} />
      <Arrow id={id} x1={320} y1={142} x2={320} y2={170} />
      <Label x={530} y={22}>M11</Label>
      <Box x={440} y={34} w={180} h={40} lines={[t('forward model P(φ)', 'modelo directo P(φ)')]} />
      <Box x={440} y={102} w={180} h={40} lines={[t('Wirtinger gradient', 'gradiente de Wirtinger')]} />
      <Box x={440} y={170} w={180} h={40} lines={[t('Adam step on φ', 'paso de Adam sobre φ')]} tone="good" />
      <Arrow id={id} x1={530} y1={74} x2={530} y2={102} />
      <Arrow id={id} x1={530} y1={142} x2={530} y2={170} />
      <Label x={320} y={236} kind="note">{t('each loop returns to its first box until the stop rule', 'cada lazo vuelve a su primera caja hasta la regla de parada')}</Label>
    </Svg>
  );
}

/** The device chain and the total displayed phase. */
export function DeviceFigure({ t }: { t: Tr }) {
  const id = 'ah-device';
  const row1 = [t('wrap 0..2π', 'envolver 0..2π'), t('quantize 2^b', 'cuantizar 2^b'), t('LUT γ', 'LUT γ'), t('flicker', 'parpadeo')];
  return (
    <Svg h={290} label={t('The device chain from the ideal phase to the focal field, and the sum of phase terms', 'La cadena del dispositivo de la fase ideal al campo focal, y la suma de términos de fase')}>
      <ArrowDefs id={id} />
      {row1.map((l, i) => (
        <g key={l}>
          <Box x={14 + i * 112} y={30} w={96} h={40} lines={[l]} />
          {i < 3 && <Arrow id={id} x1={110 + i * 112} y1={50} x2={126 + i * 112} y2={50} />}
        </g>
      ))}
      <Arrow id={id} x1={446} y1={50} x2={472} y2={50} />
      <Box x={472} y={22} w={154} h={56} lines={[t('upsample 3 x 3', 'sobremuestreo 3 x 3'), t('blur with kernel K', 'difuminar con el núcleo K')]} tone="accent" />
      <PathArrow id={id} d="M 549 78 L 549 112 L 330 112 L 330 128" />
      <Box x={200} y={128} w={260} h={40} lines={[t('pixel aperture sinc², FFT', 'apertura del píxel sinc², FFT')]} />
      <Arrow id={id} x1={330} y1={168} x2={330} y2={192} />
      <Box x={200} y={192} w={260} h={40} lines={[t('focal field E(u)', 'campo focal E(u)')]} tone="good" />
      <Label x={90} y={118} kind="note">{t('total displayed phase', 'fase total mostrada')}</Label>
      <Label x={90} y={140} kind="tick">φ + blaze + lens</Label>
      <Label x={90} y={156} kind="tick">+ l·arg(x + iy)</Label>
      <Label x={90} y={172} kind="tick">+ Σ c_j Z_j + φ_factory</Label>
      <Label x={90} y={188} kind="tick">(mod 2π)</Label>
      <Label x={630} y={246} anchor="end" kind="note">{t('K = F⁻¹{exp[-(|kx|^q + |ky|^q)/σ^q]}', 'K = F⁻¹{exp[-(|kx|^q + |ky|^q)/σ^q]}')}</Label>
      <Label x={630} y={262} anchor="end" kind="tick">{t('σ = 1.24, q = 1.80 (Schroff)', 'σ = 1,24, q = 1,80 (Schroff)')}</Label>
      <Label x={330} y={282} kind="note">{t('a missing device means the ideal one', 'un dispositivo ausente significa el ideal')}</Label>
    </Svg>
  );
}

/** The closed loop with an emulated camera. */
export function LoopFigure({ t }: { t: Tr }) {
  const id = 'ah-loop';
  return (
    <Svg h={250} label={t('Closed loop: weighted GS, SLM and optics, emulated camera, target update', 'Lazo cerrado: GS ponderado, SLM y óptica, cámara emulada, actualización del objetivo')}>
      <ArrowDefs id={id} />
      <Box x={14} y={50} w={130} h={64} lines={[t('weighted GS', 'GS ponderado'), t('warm start', 'arranque en caliente')]} tone="accent" />
      <Box x={176} y={50} w={130} h={64} lines={[t('SLM and optics', 'SLM y óptica'), t('forward model', 'modelo directo')]} />
      <Box x={338} y={50} w={150} h={64} lines={[t('emulated camera', 'cámara emulada'), t('gain, noise, blur', 'ganancia, ruido, desenfoque')]} tone="warn" />
      <Box x={520} y={50} w={106} h={64} lines={[t('measured I_i', 'I_i medida')]} />
      <Arrow id={id} x1={144} y1={82} x2={176} y2={82} />
      <Arrow id={id} x1={306} y1={82} x2={338} y2={82} />
      <Arrow id={id} x1={488} y1={82} x2={520} y2={82} />
      <PathArrow id={id} d="M 573 114 L 573 176 L 79 176 L 79 114" label={t("target update: I'_i = Ī / (1 - G (1 - I_i/Ī))", "actualización del objetivo: I'_i = Ī / (1 - G (1 - I_i/Ī))")} lx={326} ly={196} />
      <Label x={326} y={228} kind="note">{t('repeat for the steps of the case; gain G about 0.7 in the source', 'repetir por los pasos del caso; ganancia G cercana a 0,7 en la fuente')}</Label>
      <Label x={326} y={26} kind="note">{t('emulation: the errors are stated parameters, not a sensor', 'emulación: los errores son parámetros declarados, no un sensor')}</Label>
    </Svg>
  );
}

/** A rearrangement: loaded atoms, targets, the matching and the interpolation steps. */
export function RearrangeFigure({ t }: { t: Tr }) {
  const id = 'ah-rearr';
  const atoms: [number, number][] = [[60, 50], [150, 70], [90, 120], [200, 130], [40, 170]];
  const targets: [number, number][] = [[360, 80], [450, 80], [405, 140], [495, 140], [405, 200]];
  return (
    <Svg h={250} label={t('Atoms matched to targets by the Hungarian assignment and moved in interpolation steps', 'Átomos asignados a objetivos con la asignación húngara y movidos en pasos de interpolación')}>
      <ArrowDefs id={id} />
      <Label x={120} y={26}>{t('loaded atoms', 'átomos cargados')}</Label>
      <Label x={430} y={26}>{t('target sites', 'sitios objetivo')}</Label>
      {atoms.map(([x, y]) => (
        <circle key={`a${x}${y}`} cx={x} cy={y} r={8} style={{ fill: 'var(--color-accent)' }} />
      ))}
      {targets.map(([x, y]) => (
        <circle key={`t${x}${y}`} cx={x} cy={y} r={8} fill="none" stroke="var(--color-fg-faint)" strokeWidth={1.6} strokeDasharray="3 3" />
      ))}
      {atoms.map(([x, y], i) => (
        <Arrow key={`m${i}`} id={id} x1={x + 9} y1={y} x2={targets[i][0] - 10} y2={targets[i][1]} dashed />
      ))}
      <Label x={280} y={236} kind="note">{t('x(s) = x_init + (s/N)(x_final - x_init), φ(s) likewise', 'x(s) = x_inic + (s/N)(x_final - x_inic), φ(s) igual')}</Label>
    </Svg>
  );
}

/** M17: the unsupervised network, the differentiable propagation and the loss. */
export function CnnFigure({ t }: { t: Tr }) {
  const id = 'ah-cnn';
  return (
    <Svg h={260} label={t('Unsupervised training of a hologram network through a differentiable propagation, beside the Gerchberg-Saxton baseline', 'Entrenamiento no supervisado de una red de hologramas a través de una propagación diferenciable, junto a la línea base de Gerchberg-Saxton')}>
      <ArrowDefs id={id} />
      <Box x={10} y={40} w={100} h={56} lines={[t('target T', 'objetivo T'), t('traps or field', 'trampas o campo')]} />
      <Box x={140} y={40} w={110} h={56} lines={[t('network N_θ', 'red N_θ'), t('CNN, ONNX', 'CNN, ONNX')]} tone="accent" />
      <Box x={280} y={40} w={100} h={56} lines={[t('phase φ', 'fase φ'), t('2π range', 'rango 2π')]} />
      <Box x={410} y={40} w={110} h={56} lines={[t('propagation P', 'propagación P'), t('differentiable', 'diferenciable')]} />
      <Box x={550} y={40} w={80} h={56} lines={['|E|²', t('loss vs T', 'pérdida vs T')]} tone="warn" />
      <Arrow id={id} x1={110} y1={68} x2={140} y2={68} />
      <Arrow id={id} x1={250} y1={68} x2={280} y2={68} />
      <Arrow id={id} x1={380} y1={68} x2={410} y2={68} />
      <Arrow id={id} x1={520} y1={68} x2={550} y2={68} />
      <PathArrow id={id} d="M 590 96 L 590 140 L 195 140 L 195 96" label={t('gradient to θ (training, offline)', 'gradiente hacia θ (entrenamiento, fuera de línea)')} lx={392} ly={158} dashed />
      <Box x={140} y={186} w={250} h={44} lines={[t('baseline: GS to the same wall-clock', 'línea base: GS al mismo tiempo de reloj')]} />
      <Label x={500} y={212} kind="note">{t('compared on held-out targets', 'comparado en objetivos reservados')}</Label>
    </Svg>
  );
}

/** B3: the permutation-equivariant warm start in front of phase-fixed WGS. */
export function WarmFigure({ t }: { t: Tr }) {
  const id = 'ah-warm';
  return (
    <Svg h={250} label={t('A learned warm start for phase-fixed WGS beside the random start', 'Un arranque aprendido para el WGS de fase fija junto al arranque aleatorio')}>
      <ArrowDefs id={id} />
      <Box x={10} y={30} w={110} h={56} lines={[t('trap coordinates', 'coordenadas'), '(x_m, y_m, z_m)']} />
      <Box x={150} y={30} w={130} h={56} lines={[t('set network', 'red de conjuntos'), t('permutation equivariant', 'equivariante a permutaciones')]} tone="accent" />
      <Box x={310} y={30} w={90} h={56} lines={[t('phases θ_m', 'fases θ_m')]} />
      <Box x={430} y={30} w={200} h={56} lines={['φ_j = arg Σ exp(i(Δ + θ_m))']} />
      <Arrow id={id} x1={120} y1={58} x2={150} y2={58} />
      <Arrow id={id} x1={280} y1={58} x2={310} y2={58} />
      <Arrow id={id} x1={400} y1={58} x2={430} y2={58} />
      <Box x={430} y={120} w={200} h={50} lines={[t('phase-fixed WGS', 'WGS de fase fija'), t('iterations counted to σ ≤ 1 %', 'iteraciones contadas hasta σ ≤ 1 %')]} tone="good" />
      <Arrow id={id} x1={530} y1={86} x2={530} y2={120} />
      <Box x={150} y={120} w={130} h={50} lines={[t('baseline start', 'arranque base'), t('random θ_m', 'θ_m aleatorio')]} />
      <PathArrow id={id} d="M 280 145 L 430 145" dashed label={t('same WGS', 'mismo WGS')} lx={355} ly={138} />
      <Label x={320} y={218} kind="note">{t('claim: median iterations at least 2x lower, final e and u equal within 1 %', 'afirmación: iteraciones medianas al menos 2 veces menores, e y u finales iguales dentro de 1 %')}</Label>
    </Svg>
  );
}

/** B5: the published efficiency and uniformity points and the front the continuation will trace. */
export function ParetoFigure({ t }: { t: Tr }) {
  const X0 = 70;
  const Y0 = 190;
  const sx = (e: number) => X0 + e * 480;
  const sy = (u: number) => Y0 - u * 160;
  const pts: [string, number, number][] = [
    ['GS', 0.94, 0.6],
    ['GAA', 0.93, 0.79],
    ['GSW', 0.93, 0.99],
    ['DS', 0.68, 1.0],
    ['SR', 0.69, 0.01],
  ];
  return (
    <Svg h={250} label={t('Published efficiency and uniformity points of the 10 by 10 task and the schematic front a continuation traces', 'Puntos publicados de eficiencia y uniformidad de la tarea 10 por 10 y el frente esquemático que traza una continuación')}>
      <line x1={X0} y1={Y0} x2={X0 + 500} y2={Y0} className="dg-axis" />
      <line x1={X0} y1={Y0} x2={X0} y2={20} className="dg-axis" />
      <Label x={X0 + 250} y={Y0 + 34}>{t('efficiency e', 'eficiencia e')}</Label>
      <Label x={24} y={100} anchor="middle">u</Label>
      {[0, 0.5, 1].map((v) => (
        <g key={v}>
          <Label x={sx(v)} y={Y0 + 14} kind="tick">{t(String(v), String(v).replace('.', ','))}</Label>
          <Label x={X0 - 8} y={sy(v) + 4} anchor="end" kind="tick">{t(String(v), String(v).replace('.', ','))}</Label>
        </g>
      ))}
      <path d={`M ${sx(0.68)} ${sy(1.0)} C ${sx(0.85)} ${sy(1.0)} ${sx(0.93)} ${sy(0.99)} ${sx(0.96)} ${sy(0.9)}`} className="dg-curve-faint" />
      <Label x={sx(0.68) - 4} y={sy(1.0) - 12} anchor="start" kind="note">{t('schematic front, not a result', 'frente esquemático, no un resultado')}</Label>
      {pts.map(([n, e, u]) => (
        <g key={n}>
          <circle cx={sx(e)} cy={sy(u)} r={5} className="dg-node" />
          <Label x={sx(e) + 8} y={sy(u) + 4} anchor="start" kind="tick">{n}</Label>
        </g>
      ))}
      <Label x={X0 + 255} y={Y0 + 50} kind="note">{t('Di Leonardo et al. 2007, 10 x 10, 768 x 768, simulation', 'Di Leonardo et al. 2007, 10 x 10, 768 x 768, simulación')}</Label>
    </Svg>
  );
}

/** B1: one device-aware step of the weighted GS. */
export function DeviceWgsFigure({ t }: { t: Tr }) {
  const id = 'ah-b1';
  return (
    <Svg h={230} label={t('One step of device-aware weighted GS through the crosstalk operator', 'Un paso de GS ponderado consciente del dispositivo a través del operador de diafonía')}>
      <ArrowDefs id={id} />
      <Box x={10} y={30} w={90} h={50} lines={[t('phase φ', 'fase φ')]} />
      <Box x={125} y={30} w={110} h={50} lines={[t('upsample U', 'sobremuestreo U'), t('blur K', 'difuminado K')]} tone="accent" />
      <Box x={260} y={30} w={110} h={50} lines={[t('traps V_m', 'trampas V_m'), t('sum over pixels', 'suma sobre píxeles')]} />
      <Box x={395} y={30} w={110} h={50} lines={[t('loss L', 'pérdida L'), t('weights w_m', 'pesos w_m')]} tone="warn" />
      <Arrow id={id} x1={100} y1={55} x2={125} y2={55} />
      <Arrow id={id} x1={235} y1={55} x2={260} y2={55} />
      <Arrow id={id} x1={370} y1={55} x2={395} y2={55} />
      <PathArrow id={id} d="M 450 80 L 450 130 L 180 130 L 180 80" dashed label={t('gradient: chain rule, adjoint of K = K reversed', 'gradiente: regla de la cadena, adjunto de K = K invertido')} lx={315} ly={150} />
      <Box x={520} y={30} w={110} h={50} lines={[t('step on φ', 'paso sobre φ')]} tone="good" />
      <Arrow id={id} x1={505} y1={55} x2={520} y2={55} />
      <Label x={320} y={200} kind="note">{t('the weights follow the GSW rule; only the phase update changes', 'los pesos siguen la regla del GSW; sólo cambia la actualización de fase')}</Label>
    </Svg>
  );
}
