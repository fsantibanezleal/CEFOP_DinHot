// The Benchmark page of DinHot (ADR-0017 section 2.1, guide 07): the protocol, the comparison of every method on every geometry at the budget and
// device the reader chooses, the three tiers against each other, the Pareto fronts, the beyond-the-state-of-the-art claims each with its
// measurement or its measured negative, the learned models against their baselines, the degradation curves, the in-browser timing of the live
// engine, the provenance of every row and the limits. Every number is read at run time from the committed documents (the benchmark results and the
// model metrics, through the artifact loaders); the acceptance measurements the matrix cannot reproduce are recorded in `content/benchmark/recorded.ts`
// and kept equal to the SDD by a test. The sections are in `content/benchmark/`; the documents are loaded once, here.
import { CitationsProvider, DocPage, TabGroups, useShellLang } from '@fasl-work/caos-app-shell';
import { useMemo } from 'react';
import { useT } from '../content/bi';
import { CaveatTopic } from '../content/benchmark/caveat';
import { ClaimsTopic } from '../content/benchmark/claims';
import { GeometryTopic } from '../content/benchmark/geometry';
import { LearnedTopic } from '../content/benchmark/learned';
import { LiveTopic } from '../content/benchmark/live';
import { ParetoTopic } from '../content/benchmark/pareto';
import { ProtocolTopic } from '../content/benchmark/protocol';
import { ProvenanceTopic } from '../content/benchmark/provenance';
import { BudgetTopic, DeviceTopic } from '../content/benchmark/robustness';
import { BenchProvider } from '../content/benchmark/shared';
import { PublishedProposedTopic } from '../content/benchmark/published-proposed';
import { CITATIONS } from '../content/citations';
import { BENCHMARK_CITATIONS } from '../content/citations/benchmark';
import { EXPERIMENTS_CITATIONS } from '../content/citations/experiments';
import { METHODOLOGY_CITATIONS } from '../content/citations/methodology';

export function Benchmark() {
  const lang = useShellLang();
  const t = useT();
  // The page registers its own references, so it renders whether or not the shared list already carries them.
  const items = useMemo(() => {
    const own = [...METHODOLOGY_CITATIONS, ...EXPERIMENTS_CITATIONS, ...BENCHMARK_CITATIONS];
    return [...CITATIONS, ...own.filter((c) => !CITATIONS.some((x) => x.id === c.id))];
  }, []);
  const geo = (id: string) => ({ id: id.toLowerCase(), label: id, content: <GeometryTopic id={id} /> });
  return (
    <CitationsProvider items={items}>
      <DocPage
        title={{ en: 'Benchmark', es: 'Benchmark' }}
        lede={t(
          'The benchmark of DinHot puts every method of the ladder, the 19 published and the 5 proposed, on the same geometries with the same seeds, devices and budgets, each at the default parameters of its paper and with a shared tuning grid, and the learned models against their published baselines on held-out targets. Choose a device, a parameter set and a budget and every table and chart follows. Every number is read from the committed benchmark and model-metric documents when the page loads, and each claim about a proposed method is shown with the measurement that supports it or the measured negative.',
          'El benchmark de DinHot pone cada método de la escalera, los 19 publicados y los 5 propuestos, sobre las mismas geometrías con las mismas semillas, dispositivos y presupuestos, cada uno con los parámetros por defecto de su artículo y con una rejilla de ajuste común, y los modelos aprendidos frente a sus líneas base publicadas sobre objetivos reservados. Elija un dispositivo, un conjunto de parámetros y un presupuesto y cada tabla y cada gráfico lo siguen. Cada número se lee de los documentos versionados del benchmark y de las métricas de modelos cuando la página carga, y cada afirmación sobre un método propuesto se muestra con la medición que la sustenta o con el negativo medido.',
        )}
      >
        <BenchProvider>
          <TabGroups
            ariaLabel={lang === 'es' ? 'Temas del benchmark' : 'Benchmark topics'}
            groups={[
              {
                id: 'measured',
                label: t('How was it measured?', '¿Cómo se midió?'),
                tabs: [
                  { id: 'protocol', label: t('Protocol', 'Protocolo'), content: <ProtocolTopic /> },
                  { id: 'provenance', label: t('Provenance', 'Procedencia'), content: <ProvenanceTopic /> },
                ],
              },
              {
                id: 'arrays',
                label: t('Arrays, G1 to G4', 'Matrices, G1 a G4'),
                tabs: ['G1', 'G2', 'G3', 'G4'].map(geo),
              },
              {
                id: 'others',
                label: t('Volume, large and shaped, G5 to G7', 'Volumen, grandes y con forma, G5 a G7'),
                tabs: ['G5', 'G6', 'G7'].map(geo),
              },
              {
                id: 'comparison',
                label: t('Do the proposed methods improve on the published ones?', '¿Mejoran los métodos propuestos a los publicados?'),
                tabs: [
                  { id: 'published-proposed', label: t('Published and proposed', 'Publicados y propuestos'), content: <PublishedProposedTopic /> },
                  { id: 'pareto', label: t('Pareto fronts', 'Frentes de Pareto'), content: <ParetoTopic /> },
                  { id: 'claims', label: t('Proposed-method claims', 'Afirmaciones de los métodos propuestos'), content: <ClaimsTopic /> },
                  { id: 'learned', label: t('Learned models', 'Modelos aprendidos'), content: <LearnedTopic /> },
                ],
              },
              {
                id: 'robust',
                label: t('How robust and how fast?', '¿Qué tan robusto y qué tan rápido?'),
                tabs: [
                  { id: 'device', label: t('Device degradation', 'Degradación por dispositivo'), content: <DeviceTopic /> },
                  { id: 'budget', label: t('Budget curves', 'Curvas de presupuesto'), content: <BudgetTopic /> },
                  { id: 'live', label: t('In-browser timing', 'Tiempo en el navegador'), content: <LiveTopic /> },
                ],
              },
              {
                id: 'limits',
                label: t('Where does it stop?', '¿Dónde se detiene?'),
                tabs: [{ id: 'limits', label: t('Limits', 'Límites'), content: <CaveatTopic /> }],
              },
            ]}
          />
        </BenchProvider>
      </DocPage>
    </CitationsProvider>
  );
}
