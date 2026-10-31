// The Methodology page of DinHot: the physics first, then every method of the 24-method ladder by family. Six groups (ADR-0071 rule 5: at most six). The
// Physics group holds the topics that are not methods (optics, metrics, the device model, the trapped particle); four families group the 19 published
// methods and the last group holds the five proposed methods, every topic naming its ladder ids and the link to its design record (docs/design/methods/).
// The ids come from the SDD ladder (content/methodology/plan.ts and ladder.test.ts keep the page in step with it). Each topic is one `method` section
// (ADR-0017 section 2.1) with its dense paragraphs, captioned equations, a hand-drawn figure, one honest callout and its references; the shell's `kind`
// stays `learned` for the learned methods and `classical` otherwise. The page states no measured DinHot number: results belong to the Experiments and
// Benchmark pages, which read the committed artifacts.
import { CitationsProvider, DocPage, TabGroups, useShellLang } from '@fasl-work/caos-app-shell';
import { useMemo } from 'react';
import { useT } from '../content/bi';
import { CITATIONS } from '../content/citations';
import { METHODOLOGY_CITATIONS } from '../content/citations/methodology';
import { Bs1Topic, Bs2Topic, Bs3Topic, Bs4Topic, Bs5Topic } from '../content/methodology/proposed';
import { AberrationTopic, AnalyticTopic, DirectTopic, GsTopic } from '../content/methodology/classical';
import { MetricsTopic, OpticsTopic } from '../content/methodology/optics';
import { DeviceTopic, ParticleTopic } from '../content/methodology/physics';
import { CnnTopic, GradientTopic, LoopTopic, PhaseFixedTopic, ShapedTopic } from '../content/methodology/feedback-optimization';

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
          'The methods behind DinHot: first the physics of the optics, the metrics, the device and the trapped particle, then the 19 published methods in four families (superposition and Gerchberg-Saxton, optimization, shaped potentials with vortices and aberrations, feedback with motion and learning) and the 5 methods DinHot proposes, each naming its ladder id and linking its design record. The defaults are the engine’s, the results of the sources are quoted with their conditions, and the measured DinHot results are on the Experiments and Benchmark pages.',
          'Los métodos detrás de DinHot: primero la física de la óptica, las métricas, el dispositivo y la partícula atrapada, luego los 19 métodos publicados en cuatro familias (superposición y Gerchberg-Saxton, optimización, potenciales con forma con vórtices y aberraciones, realimentación con movimiento y aprendizaje) y los 5 métodos que propone DinHot, cada uno con su id de la escalera y el enlace a su registro de diseño. Los valores por defecto son los del motor, los resultados de las fuentes se citan con sus condiciones, y los resultados medidos de DinHot están en las páginas Experimentos y Benchmark.',
        )}
      >
        <TabGroups
          ariaLabel={lang === 'es' ? 'Métodos' : 'Methods'}
          groups={[
            {
              id: 'physics',
              label: t('Physics', 'Física'),
              tabs: [
                { id: 'slm-lens', label: t('SLM, lens and focal plane', 'SLM, lente y plano focal'), content: <OpticsTopic /> },
                { id: 'metrics', label: t('Trap metrics', 'Métricas de trampas'), content: <MetricsTopic /> },
                { id: 'device', label: t('Device model', 'Modelo del dispositivo'), content: <DeviceTopic /> },
                { id: 'particle', label: t('Trapped particle', 'Partícula atrapada'), content: <ParticleTopic /> },
              ],
            },
            {
              id: 'superposition-gs',
              label: t('Superposition and Gerchberg-Saxton', 'Superposición y Gerchberg-Saxton'),
              tabs: [
                { id: 'analytic', label: t('Analytic (M01 to M03)', 'Analíticos (M01 a M03)'), content: <AnalyticTopic /> },
                { id: 'gs', label: t('GS family and 3D GS (M04 to M06, M19)', 'Familia GS y GS 3D (M04 a M06, M19)'), content: <GsTopic /> },
                { id: 'phase-fixed', label: t('Phase-fixed WGS (M07)', 'WGS de fase fija (M07)'), content: <PhaseFixedTopic /> },
              ],
            },
            {
              id: 'optimization',
              label: t('Optimization', 'Optimización'),
              tabs: [
                { id: 'direct', label: t('Direct search (M09)', 'Búsqueda directa (M09)'), content: <DirectTopic /> },
                { id: 'gradient', label: t('Gradient methods (M10, M11, M13)', 'Métodos de gradiente (M10, M11, M13)'), content: <GradientTopic /> },
              ],
            },
            {
              id: 'shaped-potentials',
              label: t('Shaped potentials, vortices and aberrations', 'Potenciales con forma, vórtices y aberraciones'),
              tabs: [
                { id: 'shaped', label: t('MRAF and transport (M08, M18)', 'MRAF y transporte (M08, M18)'), content: <ShapedTopic /> },
                { id: 'aberration', label: t('Aberrations and vortices (M14, M15)', 'Aberraciones y vórtices (M14, M15)'), content: <AberrationTopic /> },
              ],
            },
            {
              id: 'feedback',
              label: t('Feedback, motion and learning', 'Realimentación, movimiento y aprendizaje'),
              tabs: [
                { id: 'loop', label: t('Feedback and rearrangement (M12, M16)', 'Retroalimentación y reordenamiento (M12, M16)'), content: <LoopTopic /> },
                { id: 'cnn', label: t('CNN hologram (M17)', 'Holograma CNN (M17)'), content: <CnnTopic /> },
              ],
            },
            {
              id: 'proposed',
              label: t('Proposed methods', 'Métodos propuestos'),
              tabs: [
                { id: 'device-aware-wgs', label: t('Device-aware WGS (B1)', 'WGS consciente del dispositivo (B1)'), content: <Bs1Topic /> },
                { id: 'flicker-bounded', label: t('Flicker-bounded sequence (B2)', 'Secuencia acotada en parpadeo (B2)'), content: <Bs2Topic /> },
                { id: 'learned-warm-start', label: t('Learned warm start, refuted (B3)', 'Arranque aprendido, refutado (B3)'), content: <Bs3Topic /> },
                { id: 'robust-hologram', label: t('Aberration-robust hologram (B4)', 'Holograma robusto a aberraciones (B4)'), content: <Bs4Topic /> },
                { id: 'pareto-front', label: t('Efficiency-uniformity front (B5)', 'Frente eficiencia-uniformidad (B5)'), content: <Bs5Topic /> },
              ],
            },
          ]}
        />
      </DocPage>
    </CitationsProvider>
  );
}
