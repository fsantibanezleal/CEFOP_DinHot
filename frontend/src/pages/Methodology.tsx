// The Methodology page of DinHot: the physics first, then every method of the 24-method ladder by tier (the method tiers rule, adopted with template
// 0.13.000): classical, state of the art, and beyond the state of the art. Four groups (ADR-0071 rule 5: at most six). The Physics group holds the topics
// that are not methods (optics, metrics, the device model, the trapped particle); each tier group holds the topics of its methods, every topic naming its
// ladder ids, its tier and the link to its design record (docs/design/methods/). The ids and tiers come from the SDD ladder (content/methodology/plan.ts and
// ladder.test.ts keep the page in step with it). Each topic is one `method` section (ADR-0017 section 2.1) with its dense paragraphs, captioned equations,
// a hand-drawn figure, one honest callout and its references; the shell's `kind` stays `learned` for the learned methods and `classical` otherwise. The page
// states no measured DinHot number: results belong to the Experiments and Benchmark pages, which read the committed artifacts.
import { CitationsProvider, DocPage, TabGroups, useShellLang } from '@fasl-work/caos-app-shell';
import { useMemo, type ReactNode } from 'react';
import { useT } from '../content/bi';
import { CITATIONS } from '../content/citations';
import { METHODOLOGY_CITATIONS } from '../content/citations/methodology';
import { Bs1Topic, Bs2Topic, Bs3Topic, Bs4Topic, Bs5Topic } from '../content/methodology/beyond';
import { AberrationTopic, AnalyticTopic, DirectTopic, GsTopic } from '../content/methodology/classical';
import { MethodTable, type Tier } from '../content/methodology/ladder';
import { MetricsTopic, OpticsTopic } from '../content/methodology/optics';
import { DeviceTopic, ParticleTopic } from '../content/methodology/physics';
import { CnnTopic, GradientTopic, LoopTopic, PhaseFixedTopic, ShapedTopic } from '../content/methodology/sota';

/** The overview of a tier, shown above the first topic of its group: every ladder method of the tier with its design record. */
function TierOverview({ tier, children }: { tier: Tier; children: ReactNode }) {
  return (
    <div data-tier-overview={tier}>
      <div style={{ margin: '0 0 var(--space-4, 1rem)' }}>
        {children}
        <MethodTable tier={tier} />
      </div>
    </div>
  );
}

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
          'The methods behind DinHot, presented by tier as the method tiers rule asks: first the physics of the optics, the metrics, the device and the trapped particle, then the 10 classical methods, the 9 state-of-the-art methods and the 5 methods beyond the state of the art, each naming its ladder id and linking its design record. The defaults are the engine’s, the results of the sources are quoted with their conditions, and the measured DinHot results are on the Experiments and Benchmark pages.',
          'Los métodos detrás de DinHot, presentados por nivel como pide la regla de niveles de métodos: primero la física de la óptica, las métricas, el dispositivo y la partícula atrapada, luego los 10 métodos clásicos, los 9 métodos del estado del arte y los 5 métodos más allá del estado del arte, cada uno con su id de la escalera y el enlace a su registro de diseño. Los valores por defecto son los del motor, los resultados de las fuentes se citan con sus condiciones, y los resultados medidos de DinHot están en las páginas Experimentos y Benchmark.',
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
              id: 'classical',
              label: t('Classical methods', 'Métodos clásicos'),
              tabs: [
                {
                  id: 'analytic',
                  label: t('Analytic (M01 to M03)', 'Analíticos (M01 a M03)'),
                  content: (
                    <>
                      <TierOverview tier="classical">
                        <p>
                          {t(
                            'Classical tier: the established methods of the problem, ten in all. Each topic below groups the methods of one family.',
                            'Nivel clásico: los métodos establecidos del problema, diez en total. Cada tema siguiente agrupa los métodos de una familia.',
                          )}
                        </p>
                      </TierOverview>
                      <AnalyticTopic />
                    </>
                  ),
                },
                { id: 'gs', label: t('GS family and 3D GS (M04 to M06, M19)', 'Familia GS y GS 3D (M04 a M06, M19)'), content: <GsTopic /> },
                { id: 'direct', label: t('Direct search (M09)', 'Búsqueda directa (M09)'), content: <DirectTopic /> },
                { id: 'aberration', label: t('Aberrations and vortices (M14, M15)', 'Aberraciones y vórtices (M14, M15)'), content: <AberrationTopic /> },
              ],
            },
            {
              id: 'sota',
              label: t('State of the art', 'Estado del arte'),
              tabs: [
                {
                  id: 'phase-fixed',
                  label: t('Phase-fixed WGS (M07)', 'WGS de fase fija (M07)'),
                  content: (
                    <>
                      <TierOverview tier="sota">
                        <p>
                          {t(
                            'State-of-the-art tier: the current solutions, nine in all, each replicated in the engine or implemented as part of the tool.',
                            'Nivel del estado del arte: las soluciones actuales, nueve en total, cada una replicada en el motor o implementada como parte de la herramienta.',
                          )}
                        </p>
                      </TierOverview>
                      <PhaseFixedTopic />
                    </>
                  ),
                },
                { id: 'shaped', label: t('MRAF and transport (M08, M18)', 'MRAF y transporte (M08, M18)'), content: <ShapedTopic /> },
                { id: 'gradient', label: t('Gradient methods (M10, M11, M13)', 'Métodos de gradiente (M10, M11, M13)'), content: <GradientTopic /> },
                { id: 'loop', label: t('Feedback and rearrangement (M12, M16)', 'Retroalimentación y reordenamiento (M12, M16)'), content: <LoopTopic /> },
                { id: 'cnn', label: t('CNN hologram (M17)', 'Holograma CNN (M17)'), content: <CnnTopic /> },
              ],
            },
            {
              id: 'beyond',
              label: t('Beyond the state of the art', 'Más allá del estado del arte'),
              tabs: [
                {
                  id: 'bs1',
                  label: t('Device-aware WGS (BS-1)', 'WGS con dispositivo (BS-1)'),
                  content: (
                    <>
                      <TierOverview tier="beyond">
                        <p>
                          {t(
                            'Beyond-the-state-of-the-art tier: five proposals of the product, each with its hypothesis, its criterion and its outcome, including the negative ones.',
                            'Nivel más allá del estado del arte: cinco propuestas del producto, cada una con su hipótesis, su criterio y su resultado, incluidos los negativos.',
                          )}
                        </p>
                      </TierOverview>
                      <Bs1Topic />
                    </>
                  ),
                },
                { id: 'bs2', label: t('Flicker-bounded sequence (BS-2)', 'Secuencia acotada (BS-2)'), content: <Bs2Topic /> },
                { id: 'bs3', label: t('Learned warm start, refuted (BS-3)', 'Arranque aprendido, refutado (BS-3)'), content: <Bs3Topic /> },
                { id: 'bs4', label: t('Robust hologram (BS-4)', 'Holograma robusto (BS-4)'), content: <Bs4Topic /> },
                { id: 'bs5', label: t('Pareto front (BS-5)', 'Frente de Pareto (BS-5)'), content: <Bs5Topic /> },
              ],
            },
          ]}
        />
      </DocPage>
    </CitationsProvider>
  );
}
