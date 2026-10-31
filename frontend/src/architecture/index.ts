// The architecture modal of DinHot (ADR-0058): five tabs, each an inline SVG (imported with ?raw, so it reads the page's theme tokens)
// that carries both languages, and a body in both languages. The shell validates this on mount: at least five tabs, inline SVG only,
// only defined tokens, no hex colours, both languages. The diagrams are transcribed from the code and the contract catalog (see the
// Implementation page); a body states what the diagram shows and why it matters, and a number in it is a stable fact of the design.
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
        'The product has six routes, and the App is the workbench. The rail on the left holds the case and the method, the run controls, the view controls, the trap editor and the live values; the instrument on the right holds five groups of views of the computed hologram and its physics, plus the write-up of the case. Each group says which lane produced what it draws, and Focus mode opens the open group in the full viewport.',
      body_es:
        'El producto tiene seis rutas, y la App es la mesa de trabajo. El panel de la izquierda contiene el caso y el método, los controles de corrida, los controles de vista, el editor de trampas y los valores en vivo; el instrumento de la derecha contiene cinco grupos de vistas del holograma calculado y su física, más el texto del caso. Cada grupo dice qué carril produjo lo que dibuja, y el modo Foco abre el grupo abierto en toda la ventana.',
    },
    {
      id: 'lanes',
      en: 'Lanes',
      es: 'Carriles',
      svg: lanes,
      body_en:
        'Offline, the Python pipeline bakes every case with every valid method and checks each against its expected ranges and its lane gate. The committed artifacts are replayed by the site as they are. Live, a TypeScript port of the engine re-runs the light methods in a Web Worker, with an optional WebGPU path that falls back to the CPU, and parity tests hold it to the Python engine.',
      body_es:
        'Fuera de línea, el pipeline en Python precalcula cada caso con cada método válido y verifica cada uno contra sus rangos esperados y su compuerta de carril. El sitio reproduce tal cual los artefactos versionados. En vivo, una versión del motor en TypeScript vuelve a ejecutar los métodos livianos en un Web Worker, con una vía opcional WebGPU que recurre a la CPU, y las pruebas de paridad la sujetan al motor en Python.',
    },
    {
      id: 'flow',
      en: 'Web flow',
      es: 'Flujo web',
      svg: flow,
      body_en:
        'The readiness document is read first and says what is real in the build. The index names the cases, a case loads its manifest and its trace as JSON, and the live engine and the two model slots add to what the views draw. Before a deploy the gate walks the built site, and a person reads its captures.',
      body_es:
        'El documento de disponibilidad se lee primero y dice qué es real en la versión. El índice nombra los casos, un caso carga su manifiesto y su traza como JSON, y el motor en vivo y los dos espacios de modelo suman a lo que dibujan las vistas. Antes de desplegar, la compuerta recorre el sitio compilado y una persona lee sus capturas.',
    },
    {
      id: 'science',
      en: 'The science',
      es: 'La ciencia',
      svg: science,
      body_en:
        'A method returns a phase mask for the SLM. The chain carries it through the device, the lens and the focal field to the trap metrics and to the trapped particle, and the ladder of methods runs from the analytic baselines to five methods that DinHot proposes. The oracles that check the chain are physical laws, never a model judging a model.',
      body_es:
        'Un método devuelve una máscara de fase para el SLM. La cadena la lleva por el dispositivo, la lente y el campo focal hasta las métricas de las trampas y la partícula atrapada, y la escalera de métodos va de las líneas base analíticas a cinco métodos que propone DinHot. Los oráculos que verifican la cadena son leyes físicas, nunca un modelo juzgando a un modelo.',
    },
    {
      id: 'contracts',
      en: 'Data contracts',
      es: 'Contratos de datos',
      svg: contracts,
      body_en:
        'Contract 1 validates what enters the pipeline; contract 2 is what the pipeline commits for the web, with the two model slots, the engine reference and the readiness document. Every row of the catalog has one schema file as its single source, a test on each side and a stated behavior when its document is missing.',
      body_es:
        'El contrato 1 valida lo que entra al pipeline; el contrato 2 es lo que el pipeline versiona para la web, con los dos espacios de modelo, la referencia del motor y el documento de disponibilidad. Cada fila del catálogo tiene un archivo de esquema como única fuente, una prueba en cada lado y un comportamiento declarado cuando falta su documento.',
    },
  ],
};
