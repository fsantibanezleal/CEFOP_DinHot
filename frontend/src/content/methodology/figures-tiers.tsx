// The figures that the tier restructure of the Methodology page added: M07, M09, M14 and M15, the trapped particle, B2 and B4. Same rules as figures.tsx:
// theme tokens only (the `dg-*` classes and the shell colour tokens), bilingual labels through the translator, no measured DinHot number written in a figure.
// The curves of the B2 and B4 figures are schematic and say so on the figure.
import { Arrow, ArrowDefs, Box, Label, PathArrow, Svg, type Tr } from './svg';

/** M07: the focal phase follows the field up to iteration N and is frozen afterwards, while the weights keep updating. */
export function PhaseFixedFigure({ t }: { t: Tr }) {
  const id = 'ah-pf';
  return (
    <Svg h={236} label={t('Iterations of phase-fixed weighted GS: the focal phase follows the field up to N and is then frozen', 'Iteraciones del GS ponderado de fase fija: la fase focal sigue al campo hasta N y luego se congela')}>
      <ArrowDefs id={id} />
      <Label x={320} y={20} kind="note">{t('iterations i, from the first to the last', 'iteraciones i, de la primera a la última')}</Label>
      <Box x={40} y={34} w={210} h={58} lines={[t('i below N', 'i menor que N'), t('focal phase ψ follows the field', 'la fase focal ψ sigue al campo')]} tone="accent" />
      <Box x={250} y={34} w={350} h={58} lines={[t('i from N on', 'i desde N'), t('focal phase frozen: ψ_i = ψ_N', 'fase focal congelada: ψ_i = ψ_N')]} tone="good" />
      <Arrow id={id} x1={40} y1={130} x2={600} y2={130} label={t('weights g_i keep updating at every iteration', 'los pesos g_i se siguen actualizando en cada iteración')} lx={320} ly={120} />
      <line x1={250} y1={146} x2={250} y2={162} className="dg-axis" />
      <line x1={420} y1={146} x2={420} y2={162} className="dg-axis" />
      <Label x={244} y={180} anchor="end" kind="tick">N = 12</Label>
      <Label x={244} y={196} anchor="end" kind="note">{t('published, default', 'publicado, por defecto')}</Label>
      <Label x={426} y={180} anchor="start" kind="tick">N = 60</Label>
      <Label x={426} y={196} anchor="start" kind="note">{t('acceptance run', 'corrida de aceptación')}</Label>
      <Label x={320} y={226} kind="note">{t('the freeze removes the focal phase change that the laser amplitude introduces', 'la fijación elimina el cambio de fase focal que introduce la amplitud del láser')}</Label>
    </Svg>
  );
}

/** M09: direct search, one pixel at a time. */
export function DirectFigure({ t }: { t: Tr }) {
  const id = 'ah-direct';
  return (
    <Svg h={226} label={t('Direct search: visit a pixel, try every phase level, keep the best, and go to the next pixel', 'Búsqueda directa: visitar un píxel, probar cada nivel de fase, conservar el mejor y pasar al siguiente píxel')}>
      <ArrowDefs id={id} />
      <Box x={20} y={40} w={180} h={64} lines={[t('visit pixel j', 'visitar el píxel j'), t('random order', 'orden aleatorio')]} />
      <Box x={230} y={40} w={180} h={64} lines={[t('try P levels', 'probar P niveles'), t('cost C of each', 'costo C de cada uno')]} tone="accent" />
      <Box x={440} y={40} w={180} h={64} lines={[t('keep the lowest C', 'conservar el menor C'), t('the cost never rises', 'el costo nunca sube')]} tone="good" />
      <Arrow id={id} x1={200} y1={72} x2={230} y2={72} />
      <Arrow id={id} x1={410} y1={72} x2={440} y2={72} />
      <PathArrow id={id} d="M 530 104 L 530 150 L 110 150 L 110 104" label={t('next pixel, until the sweeps of the budget end', 'siguiente píxel, hasta que terminen los barridos del presupuesto')} lx={320} ly={170} dashed />
      <Label x={320} y={206} kind="note">{t('C = -⟨I⟩ + f σ, with P = 8 levels and f = 0.5 by default', 'C = -⟨I⟩ + f σ, con P = 8 niveles y f = 0,5 por defecto')}</Label>
    </Svg>
  );
}

/** M14 and M15: the parabola of the modal search and the phase of a vortex trap. */
export function AberrationFigure({ t }: { t: Tr }) {
  const dots: [number, number][] = [
    [110, 135.6],
    [140, 118.6],
    [170, 108.4],
  ];
  return (
    <Svg h={250} label={t('Sensorless modal search: a parabola through three trial values of one coefficient; and the phase of a vortex trap', 'Búsqueda modal sin sensor: una parábola por tres valores de prueba de un coeficiente; y la fase de una trampa de vórtice')}>
      <line x1={50} y1={200} x2={350} y2={200} className="dg-axis" />
      <line x1={50} y1={200} x2={50} y2={40} className="dg-axis" />
      <path d="M 50 190 Q 200 20 350 190" className="dg-curve" />
      {dots.map(([x, y]) => (
        <circle key={x} cx={x} cy={y} r={5} className="dg-node" />
      ))}
      <line x1={200} y1={105} x2={200} y2={200} className="dg-curve-faint" />
      <Label x={110} y={218} kind="tick">c - δ</Label>
      <Label x={140} y={234} kind="tick">c</Label>
      <Label x={170} y={218} kind="tick">c + δ</Label>
      <Label x={215} y={234} kind="tick">{t('vertex', 'vértice')}</Label>
      <Label x={200} y={30}>{t('ln M against one Zernike coefficient', 'ln M frente a un coeficiente de Zernike')}</Label>
      <circle cx={500} cy={125} r={55} fill="none" stroke="var(--color-fg-faint)" strokeWidth={1.6} />
      <circle cx={500} cy={125} r={5} className="dg-node" />
      <Label x={578} y={129} kind="tick">0</Label>
      <Label x={500} y={58} kind="tick">π/2</Label>
      <Label x={422} y={129} kind="tick">π</Label>
      <Label x={500} y={198} kind="tick">3π/2</Label>
      <Label x={500} y={30}>{t('vortex trap, l = 1', 'trampa de vórtice, l = 1')}</Label>
      <Label x={500} y={226} kind="note">{t('phase l·atan2(y, x): 2π l around the centre', 'fase l·atan2(y, x): 2π l alrededor del centro')}</Label>
    </Svg>
  );
}

/** The physics of a trapped bead: the harmonic well, and the Lorentzian spectrum of its overdamped motion. */
export function ParticleFigure({ t }: { t: Tr }) {
  return (
    <Svg h={250} label={t('A bead in a harmonic well and the Lorentzian spectrum of its overdamped motion', 'Una esfera en un pozo armónico y el espectro lorentziano de su movimiento sobreamortiguado')}>
      <Label x={150} y={26}>{t('potential well, stiffness κ', 'pozo de potencial, rigidez κ')}</Label>
      <path d="M 40 60 Q 150 200 260 60" className="dg-curve" />
      <circle cx={150} cy={128} r={9} className="dg-node" />
      <line x1={100} y1={172} x2={200} y2={172} className="dg-edge" />
      <Label x={150} y={192} kind="tick">{t('thermal motion, overdamped', 'movimiento térmico, sobreamortiguado')}</Label>
      <Label x={150} y={226} kind="note">{t('U = -U0 I / Imax from the computed focal map', 'U = -U0 I / Imax del mapa focal calculado')}</Label>
      <line x1={350} y1={200} x2={610} y2={200} className="dg-axis" />
      <line x1={350} y1={200} x2={350} y2={50} className="dg-axis" />
      <path d="M 355 70 C 420 72 450 82 480 120 S 560 186 608 196" className="dg-curve-2" />
      <line x1={470} y1={112} x2={470} y2={200} className="dg-curve-faint" />
      <Label x={470} y={218} kind="tick">f_c = κ / (2πγ)</Label>
      <Label x={480} y={26}>{t('position spectrum, Lorentzian', 'espectro de posición, lorentziana')}</Label>
      <Label x={610} y={240} anchor="end" kind="note">{t('frequency f, log scale', 'frecuencia f, escala logarítmica')}</Label>
    </Svg>
  );
}

/** B2: the transient intensity of a moving trap between frames, schematic. */
export function TransientFigure({ t }: { t: Tr }) {
  const X0 = 70;
  const Y0 = 200;
  return (
    <Svg h={272} label={t('Schematic transient intensity of a moving trap between frames, with and without locked phases', 'Intensidad transitoria esquemática de una trampa móvil entre cuadros, con y sin fases ligadas')}>
      <line x1={X0} y1={Y0} x2={X0 + 520} y2={Y0} className="dg-axis" />
      <line x1={X0} y1={Y0} x2={X0} y2={30} className="dg-axis" />
      <line x1={X0} y1={65} x2={X0 + 520} y2={65} className="dg-curve-faint" />
      <Label x={X0 + 520} y={82} anchor="end" kind="tick">{t('0.9 of the mean', '0,9 de la media')}</Label>
      <path d="M 70 70 C 150 70 180 165 260 150 S 380 60 430 75 S 520 135 590 80" className="dg-curve-2" />
      <path d="M 70 62 C 200 58 300 68 400 62 S 520 66 590 60" className="dg-curve" />
      <Label x={X0 + 260} y={Y0 + 30}>{t('frames of the trajectory, in time', 'cuadros de la trayectoria, en el tiempo')}</Label>
      <Label x={36} y={110} kind="tick">I / mean</Label>
      <Label x={250} y={176} kind="tick">{t('frames not optimized (LPI)', 'cuadros sin optimizar (LPI)')}</Label>
      <Label x={330} y={46} kind="tick">{t('optimized frames, locked phases (B2)', 'cuadros optimizados, fases ligadas (B2)')}</Label>
      <Label x={X0 + 260} y={Y0 + 50} kind="note">{t('schematic of the mechanism, not a result', 'esquema del mecanismo, no un resultado')}</Label>
    </Svg>
  );
}

/** B4: the spread against a residual aberration for a nominal and a robust hologram, schematic. */
export function RobustFigure({ t }: { t: Tr }) {
  const X0 = 70;
  const Y0 = 190;
  return (
    <Svg h={250} label={t('Schematic trap spread against residual aberration for a nominal and a robust hologram', 'Dispersión esquemática de las trampas frente a la aberración residual para un holograma nominal y uno robusto')}>
      <line x1={X0} y1={Y0} x2={X0 + 520} y2={Y0} className="dg-axis" />
      <line x1={X0} y1={Y0} x2={X0} y2={20} className="dg-axis" />
      <path d="M 70 170 C 250 160 380 90 590 30" className="dg-curve-2" />
      <path d="M 70 150 C 250 148 380 120 590 80" className="dg-curve" />
      <Label x={X0 + 260} y={Y0 + 32}>{t('residual aberration, drawn from the prior', 'aberración residual, sorteada del a priori')}</Label>
      <Label x={40} y={100} kind="tick">σ</Label>
      <Label x={520} y={22} anchor="end" kind="tick">{t('nominal phase-fixed WGS (M07)', 'WGS de fase fija nominal (M07)')}</Label>
      <Label x={560} y={104} anchor="end" kind="tick">{t('robust hologram (B4)', 'holograma robusto (B4)')}</Label>
      <Label x={X0 + 260} y={Y0 + 54} kind="note">{t('sigma points: ± s_a √8 on one mode at a time; schematic, not a result', 'puntos sigma: ± s_a √8 en un modo a la vez; esquema, no un resultado')}</Label>
    </Svg>
  );
}
