import { CitationsProvider, DocPage, ExecutiveView, Tabs } from '@fasl-work/caos-app-shell';
import { useMemo } from 'react';
import executive from '../../../content/executive.json';
import { useT } from '../content/bi';
import { CITATIONS } from '../content/citations';
import { INTRODUCTION_CITATIONS } from '../content/citations/introduction';
import { METHODOLOGY_CITATIONS } from '../content/citations/methodology';
import { TechnicalView } from '../content/introduction/technical';

/** The Introduction has two views (problem-context-first): the executive view, first and the default, rendered by the shell
 *  from content/executive.json, and the technical view of DinHot (content/introduction/). The product writes the data file; it never
 *  designs the executive view. The technical view states no measured DinHot number: the Experiments and Benchmark pages read the artifacts. */
export function Introduction() {
  return <IntroductionPage data={executive} />;
}

export function IntroductionPage({ data }: { data: unknown }) {
  const t = useT();
  // The page registers its own references, so it renders whether or not the shared list already carries them.
  const items = useMemo(() => {
    const own = [...METHODOLOGY_CITATIONS, ...INTRODUCTION_CITATIONS];
    return [...CITATIONS, ...own.filter((c, i) => !CITATIONS.some((x) => x.id === c.id) && own.findIndex((y) => y.id === c.id) === i)];
  }, []);
  return (
    <CitationsProvider items={items}>
      <DocPage
        title={{ en: 'Introduction', es: 'Introducción' }}
        lede={t(
          'DinHot is a holography studio for optical trap arrays and shaped light fields that runs in the browser. The executive view frames the problem of programmable light fields for a decision maker; the technical view gives the problem and the product, the physics, the mathematics, the pipeline, the limits of what is claimed, how to read the App and where the product comes from.',
          'DinHot es un estudio de holografía para arreglos de trampas ópticas y campos de luz conformados que se ejecuta en el navegador. La vista ejecutiva enmarca el problema de los campos de luz programables para quien decide; la vista técnica da el problema y el producto, la física, la matemática, el pipeline, los límites de lo que se afirma, cómo leer la App y de dónde viene el producto.',
        )}
      >
        <Tabs
          ariaLabel={t('Introduction views', 'Vistas de la introducción')}
          tabs={[
            { id: 'executive', label: t('Executive', 'Ejecutiva'), content: <ExecutiveView data={data} base={import.meta.env.BASE_URL} /> },
            { id: 'technical', label: t('Technical', 'Técnica'), content: <TechnicalView /> },
          ]}
        />
      </DocPage>
    </CitationsProvider>
  );
}
