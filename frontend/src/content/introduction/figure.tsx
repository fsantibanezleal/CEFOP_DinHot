// The Introduction's overview figure: the App's six groups, each drawn as the question it answers, under the one case they all read.
// A hand-authored schematic in the shell's theme classes and tokens only, so it follows the light and dark themes; it holds no measured
// number. Sources: the App's groups in the coordination records (u0 section 6) and the SDD (the views the groups hold).
import { useT } from '../bi';
import { Arrow, ArrowDefs, Box, Svg } from '../methodology/svg';

export function GroupsFigure() {
  const t = useT();
  const id = 'intro-groups';
  const groups: { title: string; question: string; tone?: 'accent' | 'good' | 'warn' }[] = [
    { title: t('Hologram', 'Holograma'), question: t('What does the SLM display?', '¿Qué muestra el SLM?'), tone: 'accent' },
    { title: t('Focal plane', 'Plano focal'), question: t('Where does the light go?', '¿A dónde va la luz?'), tone: 'accent' },
    { title: t('Traps', 'Trampas'), question: t('How equal, how efficient?', '¿Qué tan iguales y eficientes?'), tone: 'good' },
    { title: t('Convergence', 'Convergencia'), question: t('How does a method settle?', '¿Cómo se asienta un método?'), tone: 'good' },
    { title: t('Dynamics', 'Dinámica'), question: t('What does a trapped bead do?', '¿Qué hace una partícula atrapada?'), tone: 'warn' },
    { title: t('Aberrations', 'Aberraciones'), question: t('What do optical errors cost?', '¿Cuánto cuestan los errores ópticos?'), tone: 'warn' },
  ];
  const w = 190;
  const gap = 15;
  return (
    <Svg h={250} label={t('The six groups of the App, each drawn as the question it answers, under one case', 'Los seis grupos de la App, cada uno dibujado como la pregunta que responde, bajo un mismo caso')}>
      <ArrowDefs id={id} />
      <Box x={170} y={14} w={300} h={56} lines={[t('One case', 'Un caso'), t('setup, device, target, method', 'montaje, dispositivo, objetivo, método')]} tone="accent" />
      {groups.map((g, i) => {
        const col = i % 3;
        const row = Math.floor(i / 3);
        const x = 10 + col * (w + gap);
        const y = 104 + row * 74;
        return (
          <g key={g.title}>
            {row === 0 && <Arrow id={id} x1={320} y1={70} x2={x + w / 2} y2={y} />}
            <Box x={x} y={y} w={w} h={60} lines={[g.title, g.question]} tone={g.tone} />
          </g>
        );
      })}
    </Svg>
  );
}
