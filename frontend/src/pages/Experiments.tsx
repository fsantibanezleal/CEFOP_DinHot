// The Experiments page of DinHot (ADR-0017 section 2.1): what each case measured against its anchor, read at run time from the committed bake
// (the case index and the manifests, through the workbench's loaders), so the page never restates a number by hand. Eight topics in three
// groups: the matrix and the way answers are judged (areas datasets, metrics and protocol), one tab per family of cases (a section of area
// question per case, then the chart and the table of what every method measured) and the limits. The content is in `content/experiments/`;
// a case added to the index later appears in its family with the generic text, and the matrix lists it.
import { CitationsProvider, DocPage, TabGroups, useShellLang } from '@fasl-work/caos-app-shell';
import { useMemo } from 'react';
import { useT } from '../content/bi';
import { CITATIONS } from '../content/citations';
import { EXPERIMENTS_CITATIONS } from '../content/citations/experiments';
import { METHODOLOGY_CITATIONS } from '../content/citations/methodology';
import { ExperimentsData } from '../content/experiments/context';
import { CasesTopic, FamilyTopic, LimitsTopic, MetricsTopic, ProtocolTopic } from '../content/experiments/topics';

export function Experiments() {
  const lang = useShellLang();
  const t = useT();
  // The page registers its own references, so it renders whether or not the shared list already carries them.
  const items = useMemo(() => {
    const own = [...METHODOLOGY_CITATIONS, ...EXPERIMENTS_CITATIONS];
    return [...CITATIONS, ...own.filter((c) => !CITATIONS.some((x) => x.id === c.id))];
  }, []);
  return (
    <CitationsProvider items={items}>
      <DocPage
        title={{ en: 'Experiments', es: 'Experimentos' }}
        lede={t(
          'The experiments of DinHot ask one question each of the computed holograms: how uniform a trap array can be made, what the shaped and three-dimensional targets cost, what the device and the aberrations cost, and how a camera loop, a trapped particle or a sequence of moving traps behaves. Each answer is read from the committed case index and manifests, set against its published anchor with the conditions of that anchor, and no result of DinHot on the page is typed by hand.',
          'Los experimentos de DinHot hacen una pregunta cada uno a los hologramas calculados: qué tan uniforme puede hacerse una matriz de trampas, qué cuestan los objetivos con forma y tridimensionales, qué cuestan el dispositivo y las aberraciones, y cómo se comporta un lazo de cámara, una partícula atrapada o una secuencia de trampas en movimiento. Cada respuesta se lee del índice de casos y de los manifiestos versionados, se contrasta con su ancla publicada y las condiciones de esa ancla, y ningún resultado de DinHot en la página está escrito a mano.',
        )}
      >
        <ExperimentsData>
          <TabGroups
            ariaLabel={lang === 'es' ? 'Temas de los experimentos' : 'Experiments topics'}
            groups={[
              {
                id: 'judged',
                label: t('What was run, and how is it judged?', '¿Qué se corrió y cómo se juzga?'),
                tabs: [
                  { id: 'cases', label: t('Cases', 'Casos'), content: <CasesTopic /> },
                  { id: 'metrics', label: t('Metrics', 'Métricas'), content: <MetricsTopic /> },
                  { id: 'protocol', label: t('Protocol', 'Protocolo'), content: <ProtocolTopic /> },
                ],
              },
              {
                id: 'measured',
                label: t('What did each family measure?', '¿Qué midió cada familia?'),
                tabs: [
                  { id: 'arrays', label: t('Arrays', 'Matrices'), content: <FamilyTopic family="arrays" /> },
                  { id: 'shaped', label: t('Shaped and 3D', 'Formas y 3D'), content: <FamilyTopic family="shaped" /> },
                  { id: 'device', label: t('Device and optics', 'Dispositivo y óptica'), content: <FamilyTopic family="device" /> },
                  { id: 'dynamics', label: t('Dynamics and controls', 'Dinámica y controles'), content: <FamilyTopic family="dynamics" /> },
                ],
              },
              {
                id: 'limits',
                label: t('Where does it stop?', '¿Dónde se detiene?'),
                tabs: [{ id: 'limits', label: t('Limits', 'Límites'), content: <LimitsTopic /> }],
              },
            ]}
          />
        </ExperimentsData>
      </DocPage>
    </CitationsProvider>
  );
}
