// The Benchmark page: a minimal valid page on the shell so the build stands while its content is written by its own unit (the
// documentation pages are filled in order; this one carries no content and no number of its own).
import { DocPage, useShellLang } from '@fasl-work/caos-app-shell';
import { useT } from '../content/bi';

export function Benchmark() {
  const lang = useShellLang();
  const t = useT();
  return (
    <DocPage
      title={{ en: 'Benchmark', es: 'Benchmark' }}
      lede={t(
        'The benchmark of DinHot compares the methods of the ladder on the same geometries, devices and budgets, with the learned models set against their classical baselines on held-out targets, and every number on the page is read from the committed benchmark and model-metric artifacts of the bake.',
        'El benchmark de DinHot compara los métodos de la escalera en las mismas geometrías, dispositivos y presupuestos, con los modelos aprendidos frente a sus líneas base clásicas sobre objetivos reservados, y cada número de la página se lee de los artefactos versionados del benchmark y de las métricas de modelos de la generación.',
      )}
    >
      <p lang={lang}>
        {t(
          'The written content of this page is not published yet. The App holds every case with its live and replayed views, and the Methodology page explains the methods behind them.',
          'El contenido escrito de esta página aún no está publicado. La App contiene cada caso con sus vistas en vivo y reproducidas, y la página de Metodología explica los métodos que hay detrás.',
        )}
      </p>
    </DocPage>
  );
}
