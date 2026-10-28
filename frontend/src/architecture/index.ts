// The architecture modal (ADR-0058): five tabs, each an inline SVG (imported with ?raw, so it reads the page's
// theme tokens) that carries both languages, and a body in both languages. The shell validates this on mount: at
// least five tabs, inline SVG only, only defined tokens, no hex colours, both languages.
import type { ArchitectureConfig } from '@fasl-work/caos-app-shell';
import app from './01-the-app.svg?raw';
import lanes from './02-lanes.svg?raw';
import flow from './03-web-flow.svg?raw';
import science from './04-the-science.svg?raw';
import contracts from './05-data-contracts.svg?raw';

export const architecture: ArchitectureConfig = {
  tabs: [
    {
      id: 'app',
      en: 'The app',
      es: 'La app',
      svg: app,
      body_en:
        'One workbench: the rail on the left holds the case, its immunisation variant, the two rates of the live engine and the live values; the instrument on the right holds the views of the case, grouped by question, and the open view takes the height the tab row leaves.',
      body_es:
        'Un banco de trabajo: el panel de la izquierda contiene el caso, su variante de inmunización, las dos tasas del motor en vivo y los valores en vivo; el instrumento de la derecha contiene las vistas del caso, agrupadas por pregunta, y la vista abierta toma la altura que deja la fila de pestañas.',
    },
    {
      id: 'lanes',
      en: 'Lanes',
      es: 'Carriles',
      svg: lanes,
      body_en:
        'Offline, the Python pipeline bakes every case and checks it against its expected range. The artifacts are committed and replayed by the web as they are. Live, a TypeScript port of the engine re-runs the case with the reader\'s values, and a parity test holds it to the baked traces.',
      body_es:
        'Fuera de línea, el pipeline en Python precalcula cada caso y lo verifica contra su rango esperado. Los artefactos se comprometen y la web los reproduce tal cual. En vivo, una versión en TypeScript del motor vuelve a correr el caso con los valores del lector, y una prueba de paridad lo sujeta a las trazas precalculadas.',
    },
    {
      id: 'flow',
      en: 'Web flow',
      es: 'Flujo web',
      svg: flow,
      body_en:
        'The index names the cases and the one the App opens on; a case loads its manifest and trace as JSON; the live engine runs with the rail values; every view carries the key of the selection it draws. Before a deploy the gate walks all of it.',
      body_es:
        'El índice nombra los casos y el caso en que abre la App; un caso carga su manifiesto y su traza como JSON; el motor en vivo corre con los valores del panel; cada vista lleva la clave de la selección que dibuja. Antes de desplegar, la compuerta lo recorre todo.',
    },
    {
      id: 'science',
      en: 'The science',
      es: 'La ciencia',
      svg: science,
      body_en:
        'The example model is SIR: infection by homogeneous contact and recovery at a constant rate. Its threshold is R0 = β/γ, and its final size z = 1 - exp(-R0 z) checks any engine independently of the time course. A product replaces this tab with its own science.',
      body_es:
        'El modelo de ejemplo es SIR: contagio por contacto homogéneo y recuperación a tasa constante. Su umbral es R0 = β/γ, y su tamaño final z = 1 - exp(-R0 z) verifica cualquier motor independientemente de la trayectoria. Un producto reemplaza esta pestaña por su propia ciencia.',
    },
    {
      id: 'contracts',
      en: 'Data contracts',
      es: 'Contratos de datos',
      svg: contracts,
      body_en:
        'Contract 1 validates what enters the pipeline; contract 2 is what the pipeline commits for the web. The web declares contract 2 in TypeScript, and a test reads every committed artifact against that declaration in both directions.',
      body_es:
        'El contrato 1 valida lo que entra al pipeline; el contrato 2 es lo que el pipeline compromete para la web. La web declara el contrato 2 en TypeScript, y una prueba lee cada artefacto comprometido contra esa declaración en ambos sentidos.',
    },
  ],
};
