// The Implementation page: a minimal valid page on the shell so the build stands while its content is written by its own unit (the
// documentation pages are filled in order; this one carries no content and no number of its own).
import { DocPage, useShellLang } from '@fasl-work/caos-app-shell';
import { useT } from '../content/bi';

export function Implementation() {
  const lang = useShellLang();
  const t = useT();
  return (
    <DocPage
      title={{ en: 'Implementation', es: 'Implementación' }}
      lede={t(
        'The implementation of DinHot is a Python pipeline that bakes compact artifacts, a TypeScript engine that recomputes the light methods in the browser, and a workbench that reads both, with the contracts between them, the lanes that decide what runs live, and the way a result is reproduced exactly from its seed and version.',
        'La implementación de DinHot es un pipeline en Python que precalcula artefactos compactos, un motor en TypeScript que recalcula los métodos livianos en el navegador y una mesa de trabajo que lee ambos, con los contratos entre ellos, las vías que deciden qué corre en vivo y la forma de reproducir un resultado exactamente a partir de su semilla y versión.',
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
