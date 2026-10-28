// The Experiments page: a minimal valid page on the shell so the build stands while its content is written by its own unit (the
// documentation pages are filled in order; this one carries no content and no number of its own).
import { DocPage, useShellLang } from '@fasl-work/caos-app-shell';
import { useT } from '../content/bi';

export function Experiments() {
  const lang = useShellLang();
  const t = useT();
  return (
    <DocPage
      title={{ en: 'Experiments', es: 'Experimentos' }}
      lede={t(
        'The experiments of DinHot ask one question each of the computed holograms: how uniform a trap array can be made, what the device and the aberrations cost, how a camera loop recovers uniformity, and how a trapped particle or an atom array behaves, all read from committed artifacts and never from a hand-typed number.',
        'Los experimentos de DinHot hacen una pregunta cada uno a los hologramas calculados: qué tan uniforme puede hacerse un arreglo de trampas, qué cuestan el dispositivo y las aberraciones, cómo un lazo de cámara recupera la uniformidad y cómo se comporta una partícula atrapada o un arreglo de átomos, todo leído de artefactos versionados y nunca de un número escrito a mano.',
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
