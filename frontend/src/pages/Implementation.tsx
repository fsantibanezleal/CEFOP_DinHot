// The Implementation page of DinHot (ADR-0017 section 2.1): how the product is built, in four questions. Each topic is a leaf of the tab
// groups (ADR-0071 rule 5: at most six groups) and the sections declare the areas the shell's gate counts: architecture, contract, lanes,
// engine (three topics), reproducibility and deployment. The content is in `content/implementation/`; every claim is transcribed from the
// code, the contract catalog, the SDD or a unit report (each file names its sources). The page states no measured DinHot result: the
// Benchmark page reads the committed artifacts.
import { CitationsProvider, DocPage, TabGroups, useShellLang } from '@fasl-work/caos-app-shell';
import { useMemo } from 'react';
import { useT } from '../content/bi';
import { CITATIONS } from '../content/citations';
import { IMPLEMENTATION_CITATIONS } from '../content/citations/implementation';
import { METHODOLOGY_CITATIONS } from '../content/citations/methodology';
import { ContractsTopic, PipelineTopic, RepositoryTopic } from '../content/implementation/build';
import { GpuTopic, LanesTopic, LiveEngineTopic, PythonEngineTopic } from '../content/implementation/runs';
import { DeployTopic, ModelsTopic, WebTopic } from '../content/implementation/ships';
import { ArtifactsTopic, GuardsTopic, ParityTopic, ReproducibilityTopic } from '../content/implementation/trust';

export function Implementation() {
  const lang = useShellLang();
  const t = useT();
  // The page registers its own references, so it renders whether or not the shared list already carries them.
  const items = useMemo(() => {
    const own = [...METHODOLOGY_CITATIONS, ...IMPLEMENTATION_CITATIONS];
    return [...CITATIONS, ...own.filter((c) => !CITATIONS.some((x) => x.id === c.id))];
  }, []);
  return (
    <CitationsProvider items={items}>
      <DocPage
        title={{ en: 'Implementation', es: 'Implementación' }}
        lede={t(
          'How DinHot is built, in four questions: how the Python pipeline, the two contracts and the site fit together, what runs offline, replayed or live in the browser and what admits a method to the live lane, whether a result can be trusted and reproduced, and how the models, the web and the deploy are made and checked.',
          'Cómo está construido DinHot, en cuatro preguntas: cómo encajan el pipeline en Python, los dos contratos y el sitio, qué corre fuera de línea, reproducido o en vivo en el navegador y qué admite un método en el carril en vivo, si un resultado puede confiarse y reproducirse, y cómo se hacen y se verifican los modelos, la web y el despliegue.',
        )}
      >
        <TabGroups
          ariaLabel={lang === 'es' ? 'Temas de implementación' : 'Implementation topics'}
          groups={[
            {
              id: 'built',
              label: t('How is it built?', '¿Cómo está construido?'),
              tabs: [
                { id: 'repository', label: t('Repository', 'Repositorio'), content: <RepositoryTopic /> },
                { id: 'pipeline', label: t('Pipeline', 'Pipeline'), content: <PipelineTopic /> },
                { id: 'contracts', label: t('Contracts', 'Contratos'), content: <ContractsTopic /> },
              ],
            },
            {
              id: 'runs',
              label: t('What runs where?', '¿Qué corre dónde?'),
              tabs: [
                { id: 'lanes', label: t('Lanes', 'Carriles'), content: <LanesTopic /> },
                { id: 'python-engine', label: t('Python engine', 'Motor en Python'), content: <PythonEngineTopic /> },
                { id: 'live-engine', label: t('Live engine', 'Motor en vivo'), content: <LiveEngineTopic /> },
                { id: 'webgpu', label: t('WebGPU', 'WebGPU'), content: <GpuTopic /> },
              ],
            },
            {
              id: 'trust',
              label: t('Can it be trusted?', '¿Se puede confiar?'),
              tabs: [
                { id: 'reproducibility', label: t('Reproducibility', 'Reproducibilidad'), content: <ReproducibilityTopic /> },
                { id: 'parity', label: t('Parity', 'Paridad'), content: <ParityTopic /> },
                { id: 'artifacts', label: t('Artifacts', 'Artefactos'), content: <ArtifactsTopic /> },
                { id: 'guards', label: t('Guards', 'Guardas'), content: <GuardsTopic /> },
              ],
            },
            {
              id: 'ships',
              label: t('How does it ship?', '¿Cómo se entrega?'),
              tabs: [
                { id: 'models', label: t('Models', 'Modelos'), content: <ModelsTopic /> },
                { id: 'web', label: t('The web', 'La web'), content: <WebTopic /> },
                { id: 'deploy', label: t('Deploy', 'Despliegue'), content: <DeployTopic /> },
              ],
            },
          ]}
        />
      </DocPage>
    </CitationsProvider>
  );
}
