// The Methodology page of DinHot: every method of the 24-rung ladder and the physics it rests on, grouped by the question a reader asks
// (ADR-0071 rule 5: at most six groups). Each topic is one `method` section (ADR-0017 section 2.1) with its dense paragraphs, captioned
// equations, a hand-drawn figure, one honest callout and its references; the content is in `content/methodology/`. The page states no
// measured DinHot number: results belong to the Experiments and Benchmark pages, which read the committed artifacts.
import { CitationsProvider, DocPage, TabGroups, useShellLang } from '@fasl-work/caos-app-shell';
import { useMemo } from 'react';
import { useT } from '../content/bi';
import { CITATIONS } from '../content/citations';
import { METHODOLOGY_CITATIONS } from '../content/citations/methodology';
import { BeyondTopic } from '../content/methodology/beyond';
import { AnalyticTopic, CostTopic, GsTopic, ShapedTopic } from '../content/methodology/design';
import { CnnTopic, WarmTopic } from '../content/methodology/learned';
import { MetricsTopic, OpticsTopic } from '../content/methodology/optics';
import { DeviceTopic, FeedbackTopic } from '../content/methodology/system';

export function Methodology() {
  const lang = useShellLang();
  const t = useT();
  // The page registers its own references, so it renders whether or not the shared list already carries them.
  const items = useMemo(() => [...CITATIONS, ...METHODOLOGY_CITATIONS.filter((c) => !CITATIONS.some((x) => x.id === c.id))], []);
  return (
    <CitationsProvider items={items}>
      <DocPage
        title={{ en: 'Methodology', es: 'Metodología' }}
        lede={t(
          'The methods behind DinHot, in the order a question comes: how light from the spatial light modulator reaches the traps and how a trap array is measured, how a phase hologram is computed from the analytic baselines through the Gerchberg-Saxton family, shaped potentials and cost functions, what the device, the aberrations and the feedback loop change, what learning adds, and what goes beyond the published state of the art.',
          'Los métodos detrás de DinHot, en el orden en que llega una pregunta: cómo la luz del modulador espacial de luz llega a las trampas y cómo se mide un arreglo de trampas, cómo se calcula un holograma de fase desde las líneas base analíticas hasta la familia de Gerchberg-Saxton, los potenciales conformados y las funciones de costo, qué cambian el dispositivo, las aberraciones y el lazo de retroalimentación, qué agrega el aprendizaje y qué va más allá del estado del arte publicado.',
        )}
      >
        <TabGroups
          ariaLabel={lang === 'es' ? 'Métodos' : 'Methods'}
          groups={[
            {
              id: 'optics',
              label: t('How does light reach the traps?', '¿Cómo llega la luz a las trampas?'),
              tabs: [
                { id: 'slm-lens', label: t('SLM, lens and focal plane', 'SLM, lente y plano focal'), content: <OpticsTopic /> },
                { id: 'metrics', label: t('Trap metrics', 'Métricas de trampas'), content: <MetricsTopic /> },
              ],
            },
            {
              id: 'design',
              label: t('How is the hologram computed?', '¿Cómo se calcula el holograma?'),
              tabs: [
                { id: 'analytic', label: t('Analytic holograms', 'Hologramas analíticos'), content: <AnalyticTopic /> },
                { id: 'gs', label: t('Gerchberg-Saxton', 'Gerchberg-Saxton'), content: <GsTopic /> },
                { id: 'shaped', label: t('MRAF and transport', 'MRAF y transporte'), content: <ShapedTopic /> },
                { id: 'cost', label: t('Cost functions', 'Funciones de costo'), content: <CostTopic /> },
              ],
            },
            {
              id: 'system',
              label: t('What do the device and the loop change?', '¿Qué cambian el dispositivo y el lazo?'),
              tabs: [
                { id: 'device', label: t('Device and modes', 'Dispositivo y modos'), content: <DeviceTopic /> },
                { id: 'feedback', label: t('Feedback and dynamics', 'Retroalimentación y dinámica'), content: <FeedbackTopic /> },
              ],
            },
            {
              id: 'learned',
              label: t('What does learning add?', '¿Qué agrega el aprendizaje?'),
              tabs: [
                { id: 'cnn', label: t('CNN hologram (M17)', 'Holograma CNN (M17)'), content: <CnnTopic /> },
                { id: 'warm', label: t('Warm start (B3)', 'Arranque aprendido (B3)'), content: <WarmTopic /> },
              ],
            },
            {
              id: 'beyond',
              label: t('What goes beyond the state of the art?', '¿Qué va más allá del estado del arte?'),
              tabs: [{ id: 'beyond', label: t('B1, B2, B4, B5, BS-6', 'B1, B2, B4, B5, BS-6'), content: <BeyondTopic /> }],
            },
          ]}
        />
      </DocPage>
    </CitationsProvider>
  );
}
