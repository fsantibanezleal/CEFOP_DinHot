// The first group of the Implementation page, "How is it built?": the repository and its areas (area `architecture`), the offline
// pipeline, and the contracts (area `contract`). Sources: the code (data-pipeline/pipeline/pipeline.py, bake.py, io/contract.py,
// benchmark/protocol.py; frontend/scripts/gen-contract-types.mjs), the contract catalog (docs/contracts/catalog.md), the SDD sections
// "Sizing and contracts" and "Lanes", and the README's table of areas. The page states no measured DinHot number: the Benchmark page
// reads the committed artifacts.
import { Callout, DocSection, Equation, Figure, useShellLang } from '@fasl-work/caos-app-shell';
import { L, P, useT } from '../bi';
import { CONTRACT_ROWS } from './contract-rows';
import { BuildFigure } from './figures';

const THIS_REPO = { en: 'Describes this repository.', es: 'Describe este repositorio.' };
const WRAP = { overflowWrap: 'anywhere' } as const;

const AREAS: { area: { en: string; es: string }; folder: string; en: string; es: string }[] = [
  { area: { en: 'Web', es: 'Web' }, folder: 'frontend/', en: 'The workbench and the five documentation routes on the shared shell, the TypeScript engine, the artifact layer.', es: 'La mesa de trabajo y las cinco rutas de documentación sobre el shell compartido, el motor en TypeScript, la capa de artefactos.' },
  { area: { en: 'API', es: 'API' }, folder: 'app/', en: 'A read-only FastAPI layer over the committed documents. Dormant: the site reads the files directly.', es: 'Una capa FastAPI de sólo lectura sobre los documentos versionados. Inactiva: el sitio lee los archivos directamente.' },
  { area: { en: 'Core pipelines', es: 'Pipelines centrales' }, folder: 'data-pipeline/', en: 'The named stages, the Python engine and its methods, the bake and the benchmark.', es: 'Las etapas con nombre, el motor en Python y sus métodos, el precálculo y el benchmark.' },
  { area: { en: 'Packages', es: 'Paquetes' }, folder: '(PyPI)', en: 'The product declares no package of its own; it consumes numpy.', es: 'El producto no declara paquete propio; consume numpy.' },
  { area: { en: 'Notebooks', es: 'Cuadernos' }, folder: 'notebooks/', en: 'The didactic notebooks, English and Spanish.', es: 'Los cuadernos didácticos, en inglés y en español.' },
  { area: { en: 'Data', es: 'Datos' }, folder: 'data/, models/', en: 'The committed derived artifacts and the model files of the learned slots.', es: 'Los artefactos derivados versionados y los archivos de modelo de los espacios aprendidos.' },
  { area: { en: 'Contracts', es: 'Contratos' }, folder: 'docs/contracts/', en: 'The catalog, the schemas, the examples and the provider tree.', es: 'El catálogo, los esquemas, los ejemplos y el árbol de proveedor.' },
  { area: { en: 'Documentation', es: 'Documentación' }, folder: 'docs/', en: 'The software design document, the guides, the framework cards and the case cards.', es: 'El documento de diseño del software, las guías, las fichas de marcos y las fichas de casos.' },
  { area: { en: 'Tests and gates', es: 'Pruebas y compuertas' }, folder: 'tests/, scripts/', en: 'pytest, vitest and the guards in scripts/check_*.py.', es: 'pytest, vitest y las guardas de scripts/check_*.py.' },
  { area: { en: 'Deploy', es: 'Despliegue' }, folder: 'deploy/, .github/', en: 'The deploy place, the CI and the Pages workflow.', es: 'El lugar de despliegue, la CI y el flujo de Pages.' },
];

export function RepositoryTopic() {
  const t = useT();
  const lang = useShellLang();
  return (
    <DocSection title={{ en: 'The repository and its parts', es: 'El repositorio y sus partes' }} area="architecture" noRefsReason={THIS_REPO}>
      <P
        en="DinHot has one direction of flow. A Python pipeline runs the engine and every method on a workstation, checks each result against numeric expectations and writes small documents. The repository commits those documents, and a static site copies and replays them with no server. A TypeScript port of the engine, running in a Web Worker, recomputes the light methods in the browser with the reader's values. A measured gate walks the built site before any deploy."
        es="DinHot tiene un solo sentido de flujo. Un pipeline en Python ejecuta el motor y cada método en una estación de trabajo, verifica cada resultado contra expectativas numéricas y escribe documentos pequeños. El repositorio versiona esos documentos y un sitio estático los copia y los reproduce sin servidor. Una versión del motor en TypeScript, ejecutada en un Web Worker, recalcula en el navegador los métodos livianos con los valores del lector. Una compuerta medida recorre el sitio compilado antes de cualquier despliegue."
      />
      <Figure caption={t('The parts of the build and the direction of flow between them. The dashed arrow is the parity test that holds the live engine to the Python one.', 'Las partes de la compilación y el sentido del flujo entre ellas. La flecha punteada es la prueba de paridad que sujeta el motor en vivo al de Python.')}>
        <BuildFigure />
      </Figure>
      <P
        en="The product declares no package of its own: the engine and the methods live in data-pipeline/pipeline/model/holo/, scanned by a registry at start, and the only runtime dependency of the pipeline for the methods is numpy. The browser side adds fft.js for the transforms and onnxruntime-web for the two learned models. Anything that must be shared with another product would be a separate repository and a published package, never a folder of this one."
        es="El producto no declara un paquete propio: el motor y los métodos viven en data-pipeline/pipeline/model/holo/, que un registro recorre al iniciar, y la única dependencia de ejecución del pipeline para los métodos es numpy. El lado del navegador suma fft.js para las transformadas y onnxruntime-web para los dos modelos aprendidos. Lo que deba compartirse con otro producto sería un repositorio aparte y un paquete publicado, nunca una carpeta de éste."
      />
      <table className="caos-table" data-state="ready">
        <thead>
          <tr>
            <th>{t('Area', 'Área')}</th>
            <th>{t('Folder', 'Carpeta')}</th>
            <th className="caos-col-text">{t('What it holds', 'Qué contiene')}</th>
          </tr>
        </thead>
        <tbody>
          {AREAS.map((a) => (
            <tr key={a.folder}>
              <td>{a.area[lang]}</td>
              <td style={WRAP}>{a.folder}</td>
              <td className="caos-col-text" style={WRAP}>{lang === 'es' ? a.es : a.en}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </DocSection>
  );
}

export function PipelineTopic() {
  const t = useT();
  return (
    <DocSection title={{ en: 'The offline pipeline', es: 'El pipeline fuera de línea' }} noRefsReason={THIS_REPO}>
      <P
        en="The pipeline is run by path, python data-pipeline/run.py, and never installed. Its commands are all, to bake the cases, readiness, benchmark, cases and units. Bake options select cases with --only, skip cases whose manifest already carries the same inputs and version with --resume, and write to a sandbox with --output; omitting --output is an intentional canonical release bake, so tests and trials always name a sandbox."
        es="El pipeline se ejecuta por ruta, python data-pipeline/run.py, y nunca se instala. Sus comandos son all, para precalcular los casos, readiness, benchmark, cases y units. Las opciones del precálculo eligen casos con --only, omiten los casos cuyo manifiesto ya tiene las mismas entradas y versión con --resume, y escriben en un sandbox con --output; omitir --output es un precálculo canónico de publicación, a propósito, así que las pruebas y los ensayos siempre nombran un sandbox."
      />
      <P
        en="One case is baked in a fixed order: the contract 1 record, every valid method through the registry, the expected ranges, the lane measurement, the maps and the three drivers (camera feedback, the particle, the rearrangement), the trace within its byte gate, the units gate and last the manifest. A failure never stops the other cases: the bake collects them all and raises one error that names the case, the method or the driver, and the metric."
        es="Un caso se precalcula en un orden fijo: el registro del contrato 1, cada método válido a través del registro, los rangos esperados, la medición del carril, los mapas y los tres simuladores (realimentación de cámara, la partícula, el reordenamiento), la traza dentro de su compuerta de bytes, la compuerta de unidades y al final el manifiesto. Una falla no detiene a los otros casos: el precálculo las reúne todas y levanta un solo error que nombra el caso, el método o el simulador, y la métrica."
      />
      <ol>
        <li>{t('preprocess: read the source document of cases and apply contract 1.', 'preprocess: leer el documento de casos de origen y aplicar el contrato 1.')}</li>
        <li>{t('feature_extraction: the derived geometry of a record, such as the trap count and the smallest spacing in focal bins.', 'feature_extraction: la geometría derivada de un registro, como el número de trampas y el menor espaciado en bins focales.')}</li>
        <li>{t('train: the offline fit of the two learned models, run locally and never in CI. The stage belongs to the models unit and is in progress: the file in this tree is still the example of the template and the bake does not call it (see Models and slots).', 'train: el ajuste fuera de línea de los dos modelos aprendidos, ejecutado en local y nunca en CI. La etapa pertenece a la unidad de modelos y está en curso: el archivo de este árbol sigue siendo el ejemplo de la plantilla y el precálculo no lo llama (véase Modelos y espacios).')}</li>
        <li>{t('infer: every method valid for the case, scored independently from its returned phase.', 'infer: cada método válido para el caso, evaluado de forma independiente a partir de la fase que devuelve.')}</li>
        <li>{t('evaluate: the held-out comparison of each learned model against its baseline, in progress with the same unit.', 'evaluate: la comparación con datos reservados de cada modelo aprendido contra su línea base, en curso con la misma unidad.')}</li>
        <li>{t('export: the compact trace and the manifest, the contract 2 documents.', 'export: la traza compacta y el manifiesto, los documentos del contrato 2.')}</li>
      </ol>
      <P
        en="Every method of a case receives the same seed and the same budget, so all of them start from the same random numbers, and the figures of a method are recomputed from the phase it returns rather than taken from the history it reports. The benchmark protocol runs the same registry over seven geometries, G1 to G7, with iteration budgets of 10, 30 and 100, wall-clock budgets of 50 ms and 1 s and a converged run, scoring every run from its final phase through the device when there is one."
        es="Todos los métodos de un caso reciben la misma semilla y el mismo presupuesto, así que todos parten de los mismos números aleatorios, y las cifras de un método se recalculan a partir de la fase que devuelve y no del historial que informa. El protocolo del benchmark ejecuta el mismo registro sobre siete geometrías, G1 a G7, con presupuestos de 10, 30 y 100 iteraciones, de 50 ms y 1 s de reloj y una corrida convergida, evaluando cada corrida desde su fase final a través del dispositivo cuando lo hay."
      />
    </DocSection>
  );
}

export function ContractsTopic() {
  const t = useT();
  const lang = useShellLang();
  return (
    <DocSection title={{ en: 'The two contracts and the catalog', es: 'Los dos contratos y el catálogo' }} area="contract" noRefsReason={THIS_REPO}>
      <P
        en="Two contracts bound the pipeline. Contract 1 validates what enters it, a params record, and contract 2 is what it commits for the web. Every boundary is a row of the catalog in docs/contracts/catalog.md with one schema file as its single source, an example, a producer test, a consumer test, its missing-data behavior and a provider. Twelve rows exist today. The catalog, the schemas and the TypeScript types are changed together in one pull request."
        es="Dos contratos acotan el pipeline. El contrato 1 valida lo que entra, un registro de parámetros, y el contrato 2 es lo que compromete para la web. Cada frontera es una fila del catálogo en docs/contracts/catalog.md con un archivo de esquema como única fuente, un ejemplo, una prueba del productor, una prueba del consumidor, su comportamiento ante datos ausentes y un proveedor. Hoy existen doce filas. El catálogo, los esquemas y los tipos de TypeScript se cambian juntos en un mismo pull request."
      />
      <table className="caos-table" data-state="ready">
        <thead>
          <tr>
            <th>{t('Contract', 'Contrato')}</th>
            <th>{t('Version', 'Versión')}</th>
            <th className="caos-col-text">{t('Producer', 'Productor')}</th>
            <th className="caos-col-text">{t('What it is', 'Qué es')}</th>
            <th className="caos-col-text">{t('Who reads it', 'Quién lo lee')}</th>
          </tr>
        </thead>
        <tbody>
          {CONTRACT_ROWS.map((r) => (
            <tr key={r.id}>
              <td style={WRAP}>{r.id}</td>
              <td>{r.version}</td>
              <td className="caos-col-text" style={WRAP}>{r.owner}</td>
              <td className="caos-col-text" style={WRAP}>{r.what[lang]}</td>
              <td className="caos-col-text" style={WRAP}>{r.reader[lang]}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <P
        en={<>Contract 1 is checked by a standard-library validator of the schema file, so the readiness computation runs in CI with nothing installed, plus the rules a schema cannot state: unique trap ids, a reference method among the methods, a numerical aperture that does not exceed the immersion index, and a device model that excludes traps off the focal plane. The rule that matters most is the field of view. A trap lies strictly inside the unaliased window, and a trap at or beyond the bound is refused with the bound in its reason, never silently clipped.</>}
        es={<>El contrato 1 lo revisa un validador de biblioteca estándar del archivo de esquema, de modo que el cálculo de disponibilidad corre en CI sin instalar nada, más las reglas que un esquema no puede expresar: identificadores de trampa únicos, un método de referencia entre los métodos, una apertura numérica que no excede el índice de inmersión y un modelo de dispositivo que excluye trampas fuera del plano focal. La regla que más importa es el campo de visión. Una trampa queda estrictamente dentro de la ventana sin aliasing, y una trampa en la cota o más allá se rechaza con la cota en su razón, nunca se recorta en silencio.</>}
      />
      <Equation
        tex="|x_m| < \frac{\lambda f}{2p},\qquad |y_m| < \frac{\lambda f}{2p},\qquad \Delta_{\mathrm{bin}} = \frac{\lambda f}{n_{\mathrm{pad}}\, n_{\mathrm{pix}}\, p}"
        caption={t('The admission rule of contract 1 for a trap at (x_m, y_m): λ is the wavelength, f the focal length, p the SLM pixel pitch, n_pix the pixels per side and n_pad the zero-padding factor; Δ_bin is one bin of the focal FFT grid. A trap at the bound lies outside the centred grid.', 'La regla de admisión del contrato 1 para una trampa en (x_m, y_m): λ es la longitud de onda, f la distancia focal, p el paso de píxel del SLM, n_pix los píxeles por lado y n_pad el factor de relleno de ceros; Δ_bin es un bin de la grilla de la FFT focal. Una trampa en la cota queda fuera de la grilla centrada.')}
      />
      <P
        en="The web declares contract 2 in TypeScript, generated from docs/contracts/api.openapi.json by frontend/scripts/gen-contract-types.mjs, and the build fails if the generated file is out of date. A test reads every committed document against that declaration in both directions, once on the baked tree and once on the provider tree, a small hand-made tree in the layout of data/derived that lets the site build before any bake and is labelled as a provider on every surface by the readiness document."
        es="La web declara el contrato 2 en TypeScript, generado a partir de docs/contracts/api.openapi.json por frontend/scripts/gen-contract-types.mjs, y la compilación falla si el archivo generado está desactualizado. Una prueba lee cada documento versionado contra esa declaración en ambos sentidos, una vez sobre el árbol precalculado y otra sobre el árbol de proveedor, un árbol pequeño hecho a mano con la disposición de data/derived que permite compilar el sitio antes de cualquier precálculo y que el documento de disponibilidad rotula como proveedor en cada superficie."
      />
      <L
        items={[
          {
            en: 'Versions move with their schema by semver, and every version has a row in the catalog history; scripts/check_contract_versions.py fails when a schema changed under the same version, and in CI against the base commit it also fails on a breaking change that did not take a major step.',
            es: 'Las versiones se mueven con su esquema según semver, y cada versión tiene una fila en el historial del catálogo; scripts/check_contract_versions.py falla cuando un esquema cambió con la misma versión, y en CI contra el commit base falla además ante un cambio incompatible que no tomó un paso mayor.',
          },
          {
            en: 'Swapping a provider for the real producer is a test, not a hope: the swap tests run the same assertions on the provider tree and on the bake.',
            es: 'Cambiar un proveedor por el productor real es una prueba, no una esperanza: las pruebas de intercambio corren las mismas aserciones sobre el árbol de proveedor y sobre el precálculo.',
          },
        ]}
      />
      <Callout variant="note" title={t('What a provider is', 'Qué es un proveedor')}>
        {t('A provider is scaffolding: it lets the web build and the tests run before the real producer exists, and it is never counted as done. The readiness document says so on every surface until the row is real.', 'Un proveedor es andamiaje: deja compilar la web y correr las pruebas antes de que exista el productor real, y nunca se cuenta como terminado. El documento de disponibilidad lo dice en cada superficie hasta que la fila es real.')}
      </Callout>
    </DocSection>
  );
}
