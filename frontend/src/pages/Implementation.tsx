import { Callout, DocPage, DocSection, Equation, Figure, TabGroups } from '@fasl-work/caos-app-shell';
import { P, L, useT } from '../content/bi';
import { FlowFigure } from '../content/figures';
import { ReadinessTable } from '../readiness/ReadinessTable';

const THIS_REPO = { en: 'Describes this repository.', es: 'Describe este repositorio.' };

export function Implementation() {
  const t = useT();
  return (
    <DocPage
      title={{ en: 'Implementation', es: 'Implementación' }}
      lede={t(
        'How the product is built, in four questions: how the offline pipeline, the contracts and the site fit together, what runs where, whether a result can be trusted and reproduced, and how the web and the deploy are made and checked.',
        'Cómo está construido el producto, en cuatro preguntas: cómo encajan el pipeline fuera de línea, los contratos y el sitio, qué corre dónde, si un resultado puede confiarse y reproducirse, y cómo se hacen y se verifican la web y el despliegue.',
      )}
    >
      <TabGroups
        ariaLabel={t('Implementation topics', 'Temas de implementación')}
        groups={[
          {
            id: 'built',
            label: t('How is it built?', '¿Cómo está construido?'),
            tabs: [
              { id: 'architecture', label: t('Architecture', 'Arquitectura'), content: <>
      <DocSection title={{ en: 'The architecture', es: 'La arquitectura' }} area="architecture" noRefsReason={THIS_REPO}>
        <P
          en="The product has one direction of flow. An offline pipeline bakes every case into small committed artifacts; the site copies them and replays them with no server; a live engine in the browser re-runs a case with the reader's values; and a measured gate walks the build before it is deployed. Nothing the reader sees is computed on a machine the reader does not hold."
          es="El producto tiene un solo sentido de flujo. Un pipeline fuera de línea precalcula cada caso en artefactos pequeños y comprometidos; el sitio los copia y los reproduce sin servidor; un motor en vivo en el navegador vuelve a correr un caso con los valores del lector; y una compuerta medida recorre la compilación antes de desplegarla. Nada de lo que ve el lector se calcula en una máquina que el lector no tenga."
        />
        <Figure caption={t('The five parts of the build and the direction of flow between them.', 'Las cinco partes de la compilación y el sentido del flujo entre ellas.')}>
          <FlowFigure stages={[t('Offline pipeline', 'Pipeline fuera de línea'), t('Committed artifacts', 'Artefactos comprometidos'), t('Static site', 'Sitio estático'), t('Live engine', 'Motor en vivo'), t('Measured gate', 'Compuerta medida')]} label={t('The architecture of the build', 'La arquitectura de la compilación')} />
        </Figure>
      </DocSection>
              </> },
              { id: 'pipeline', label: t('Pipeline', 'Pipeline'), content: <>
              <DocSection title={{ en: 'The pipeline', es: 'El pipeline' }} noRefsReason={THIS_REPO}>
                <P
                  en="The offline pipeline (data-pipeline/) runs every case of the registry through named stages: preprocess, feature extraction, train, infer, evaluate and export. The ingestion contract validates each case's inputs before anything runs: a bad value is rejected with its reason, never coerced, and an unusual one is flagged and carried into the manifest. Every random generator is seeded, so a second bake writes the same bytes."
                  es="El pipeline fuera de línea (data-pipeline/) pasa cada caso del registro por etapas con nombre: preprocesamiento, extracción de atributos, entrenamiento, inferencia, evaluación y exportación. El contrato de ingesta valida las entradas de cada caso antes de que algo corra: un valor inválido se rechaza con su razón, nunca se fuerza, y uno inusual se marca y se lleva al manifiesto. Cada generador aleatorio tiene semilla, así que un segundo precálculo escribe los mismos bytes."
                />
              </DocSection>
              </> },
              { id: 'contract', label: t('Artifacts and contract', 'Artefactos y contrato'), content: <>
              <DocSection title={{ en: 'The artifacts', es: 'Los artefactos' }} area="contract" noRefsReason={THIS_REPO}>
                <P
                  en="The pipeline writes the artifact contract into data/derived/, and the repository commits it: an index of the cases (with the case the App opens on), one manifest per case (parameters, seed, engine and version, the artifact, the lane verdict and the evaluation metrics), and one trace per case (200 points of the trajectory and its summary). Every reader-facing string in them is bilingual."
                  es="El pipeline escribe el contrato de artefactos en data/derived/, y el repositorio lo compromete: un índice de los casos (con el caso en que abre la App), un manifiesto por caso (parámetros, semilla, motor y versión, el artefacto, el veredicto de carril y las métricas de evaluación) y una traza por caso (200 puntos de la trayectoria y su resumen). Cada texto para el lector es bilingüe."
                />
                <table className="caos-table" data-state="ready">
                  <thead>
                    <tr>
                      <th>{t('Document', 'Documento')}</th>
                      <th className="caos-col-text">{t('Where it is', 'Dónde está')}</th>
                      <th className="caos-col-text">{t('What it holds', 'Qué contiene')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{t('Case index', 'Índice de casos')}</td>
                      <td className="caos-col-text">data/derived/manifests/index.json</td>
                      <td className="caos-col-text">{t('The cases with bilingual titles and categories, the default case and the files to copy.', 'Los casos con títulos y categorías bilingües, el caso por defecto y los archivos a copiar.')}</td>
                    </tr>
                    <tr>
                      <td>{t('Case manifest', 'Manifiesto de caso')}</td>
                      <td className="caos-col-text">data/derived/manifests/&lt;case&gt;.json</td>
                      <td className="caos-col-text">{t('Parameters, seed, engine and version, the artifact, the lane verdict, the metrics and the expected ranges.', 'Parámetros, semilla, motor y versión, el artefacto, el veredicto de carril, las métricas y los rangos esperados.')}</td>
                    </tr>
                    <tr>
                      <td>{t('Trace', 'Traza')}</td>
                      <td className="caos-col-text">data/derived/&lt;case&gt;/trace.json</td>
                      <td className="caos-col-text">{t('At most 200 points of S, I and R, and the summary: peak, day of the peak, attack rate.', 'Hasta 200 puntos de S, I y R, y el resumen: pico, día del pico, tasa de ataque.')}</td>
                    </tr>
                    <tr>
                      <td>{t('Surrogate bundle', 'Paquete del sustituto')}</td>
                      <td className="caos-col-text">models/surrogate.json</td>
                      <td className="caos-col-text">{t('The kind, the four basis functions and the four coefficients of the learned model.', 'El tipo, las cuatro funciones base y los cuatro coeficientes del modelo aprendido.')}</td>
                    </tr>
                    <tr>
                      <td>{t('Readiness', 'Disponibilidad')}</td>
                      <td className="caos-col-text">data/derived/readiness.json</td>
                      <td className="caos-col-text">{t('The declared state of every row of the contract catalog.', 'El estado declarado de cada fila del catálogo de contratos.')}</td>
                    </tr>
                  </tbody>
                </table>
                <P
                  en="The web declares the same contract in TypeScript, and a test reads every committed artifact against that declaration in both directions: a key the pipeline writes and the web does not read fails, a key the web reads and the pipeline does not write fails, and a boolean where a number is expected fails."
                  es="La web declara el mismo contrato en TypeScript, y una prueba lee cada artefacto comprometido contra esa declaración en ambas direcciones: falla una clave que el pipeline escribe y la web no lee, falla una clave que la web lee y el pipeline no escribe, y falla un booleano donde se espera un número."
                />
              </DocSection>
              </> },
            ],
          },
          {
            id: 'runs',
            label: t('What runs where?', '¿Qué corre dónde?'),
            tabs: [
              { id: 'lanes', label: t('Lanes', 'Carriles'), content: <>
              <DocSection title={{ en: 'The lanes', es: 'Los carriles' }} area="lanes" noRefsReason={THIS_REPO}>
                <P
                  en="The lane of a case is decided by a gate in the pipeline, not by hand. A case is eligible for the live lane when its engine is pure Python with only a small set of allowed packages, its committed trace is under 256 KiB and one run takes under 1500 ms; the verdict and the reasons are written into the manifest, and a case that fails any of them is labelled precompute and replayed only."
                  es="El carril de un caso lo decide una compuerta del pipeline, no una persona. Un caso es elegible para el carril en vivo cuando su motor es Python puro con sólo un conjunto pequeño de paquetes permitidos, su traza comprometida pesa menos de 256 KiB y una corrida toma menos de 1500 ms; el veredicto y las razones se escriben en el manifiesto, y un caso que falla alguno se rotula precálculo y sólo se reproduce."
                />
                <P
                  en="The budget is judged on a measured cost: the median of several runs after a warm-up, not the time of the whole bake, which once made the verdict depend on which case was baked first. The Benchmark page repeats the measurement in the reader's browser, so the claim that a case may run live is checked on the device that runs it."
                  es="El presupuesto se juzga sobre un costo medido: la mediana de varias corridas tras un calentamiento, no el tiempo de todo el precálculo, que una vez hizo depender el veredicto de qué caso se calculaba primero. La página Benchmark repite la medición en el navegador del lector, de modo que la afirmación de que un caso puede correr en vivo se verifica en el dispositivo que lo corre."
                />
                <L
                  items={[
                    { en: 'Offline: the Python pipeline, run on a workstation; its results are committed.', es: 'Fuera de línea: el pipeline en Python, corrido en una estación de trabajo; sus resultados se comprometen.' },
                    { en: 'Replay: the web reads the committed artifacts; nothing is recomputed.', es: 'Reproducción: la web lee los artefactos comprometidos; nada se recalcula.' },
                    { en: 'Live: the TypeScript engine re-runs a case in the browser with the reader\'s values. A parity test holds it to the baked traces, so the two engines cannot drift apart unnoticed.', es: 'En vivo: el motor en TypeScript vuelve a correr un caso en el navegador con los valores del lector. Una prueba de paridad lo sujeta a las trazas precalculadas, así que los dos motores no pueden separarse sin que se note.' },
                  ]}
                />
              </DocSection>
              </> },
              { id: 'engine', label: t('Engine', 'Motor'), content: <>
      <DocSection title={{ en: 'The engine', es: 'El motor' }} area="engine" noRefsReason={THIS_REPO}>
        <P
          en="The live engine is a step-for-step port of the Python one. It starts from S equal to N minus the initial infected and I equal to the initial infected, moves a share v of the susceptible to R when an immunisation is asked for, and then repeats a quarter-day step until the horizon: new infections are the contact rate times S times I over N times the step, new recoveries are the recovery rate times I times the step."
          es="El motor en vivo es un port paso a paso del de Python. Parte de S igual a N menos los contagiados iniciales e I igual a los contagiados iniciales, pasa una fracción v de los susceptibles a R cuando se pide una inmunización, y luego repite un paso de un cuarto de día hasta el horizonte: los nuevos contagios son la tasa de contacto por S por I sobre N por el paso, y las nuevas recuperaciones son la tasa de recuperación por I por el paso."
        />
        <Equation
          tex="\Delta_{\mathrm{inf}} = \frac{\beta}{N} S_k I_k \, \Delta t, \qquad \Delta_{\mathrm{rec}} = \gamma I_k \, \Delta t, \qquad \Delta t = \tfrac{1}{4} \text{ day}"
          caption={t('The two quantities of one step; S and I are then updated and clamped at zero, R only grows.', 'Las dos cantidades de un paso; luego S e I se actualizan y se limitan en cero, y R sólo crece.')}
        />
        <P
          en="The peak is the first sample with the largest infected count, so a tie resolves to the earlier day. The trace keeps at most 200 points of the trajectory, taken at evenly spaced steps of the run, and rounds each value to two decimals; the parity test holds the live engine to that rounding on every baked case."
          es="El pico es la primera muestra con el mayor número de contagiados, de modo que un empate se resuelve hacia el día anterior. La traza guarda a lo más 200 puntos de la trayectoria, tomados en pasos igualmente espaciados de la corrida, y redondea cada valor a dos decimales; la prueba de paridad exige al motor en vivo ese redondeo en cada caso precalculado."
        />
        <Callout variant="note" title={t('Where it works and where it fails', 'Dónde funciona y dónde falla')}>
          {t('It works for a closed population and a horizon long enough to see the epidemic end. It fails to reach the final size when the horizon cuts the run, or when R0 is so near one that the epidemic is still burning, and a step far larger than a quarter day would make the clamp act.', 'Funciona para una población cerrada y un horizonte lo bastante largo para ver el fin de la epidemia. No llega al tamaño final cuando el horizonte corta la corrida, o cuando R0 está tan cerca de uno que la epidemia sigue activa, y un paso mucho mayor que un cuarto de día haría actuar el límite en cero.')}
        </Callout>
      </DocSection>
              </> },
            ],
          },
          {
            id: 'trust',
            label: t('Can it be trusted?', '¿Se puede confiar?'),
            tabs: [
              { id: 'reproducibility', label: t('Reproducibility', 'Reproducibilidad'), content: <>
      <DocSection title={{ en: 'Reproducibility', es: 'Reproducibilidad' }} area="reproducibility" noRefsReason={THIS_REPO}>
        <P
          en="A result is reproduced from three things written next to it: the seed, the engine version and the case parameters, all in the manifest. Every random generator in the pipeline is built from the bake seed, 42 by default, and the held-out evaluation uses that seed plus a fixed offset, so a second bake on the same code writes the same artifacts byte for byte and a test fails if it does not."
          es="Un resultado se reproduce con tres cosas escritas junto a él: la semilla, la versión del motor y los parámetros del caso, todo en el manifiesto. Todo generador aleatorio del pipeline se construye con la semilla del precálculo, 42 por defecto, y la evaluación con datos reservados usa esa semilla más un desplazamiento fijo, de modo que un segundo precálculo con el mismo código escribe los mismos artefactos byte a byte y una prueba falla si no es así."
        />
        <Callout variant="note" title={t('One version, one source', 'Una versión, una fuente')}>
          {t('The version is written once, in VERSION. A manifest baked by an earlier engine version is shown as stale, never as current.', 'La versión se escribe una sola vez, en VERSION. Un manifiesto generado por una versión anterior del motor se muestra como desactualizado, nunca como vigente.')}
        </Callout>
      </DocSection>
              </> },
              { id: 'real', label: t('What is real', 'Qué es real'), content: <>
              <DocSection title={{ en: 'What is real in this build', es: 'Qué es real en esta versión' }} noRefsReason={THIS_REPO}>
                <P
                  en="Every row of the contract catalog carries a declared state, computed by the pipeline from the catalog and the repository and committed as readiness.json: available, partial (some manifests or artifacts are absent), stale (baked by an earlier version of the engine), provider (served by a provider while the real producer is not built), training (a baseline or a released model answers while a newer one trains) or missing. A view shows the result with a note for the states that still hold one, and an explicit not available yet with the reason for the state that does not, never an empty chart."
                  es="Cada fila del catálogo de contratos lleva un estado declarado, calculado por el pipeline a partir del catálogo y del repositorio y versionado como readiness.json: disponible, parcial (faltan manifiestos o artefactos), desactualizado (generado por una versión anterior del motor), proveedor (lo sirve un proveedor mientras el productor real no está construido), entrenando (responde una línea base o un modelo publicado mientras uno nuevo se entrena) o ausente. Una vista muestra el resultado con una nota para los estados que aún lo permiten, y un aún no disponible explícito con la razón para el estado que no, nunca un gráfico vacío."
                />
                <ReadinessTable />
              </DocSection>
              </> },
            ],
          },
          {
            id: 'ships',
            label: t('How does it ship?', '¿Cómo se entrega?'),
            tabs: [
              { id: 'web', label: t('The web', 'La web'), content: <>
              <DocSection title={{ en: 'The web', es: 'La web' }} noRefsReason={THIS_REPO}>
                <P
                  en="The frontend is built on the shared CAOS app shell: the header, the theme and language toggles, the workbench with its rail and instrument, the documentation page, the chart, and the measured gate. A build copies exactly the artifacts the index declares into the site (and fails on a missing one), fetches them with the version in the address so a release never reads an old cached file, writes every route as its own page so a deep link answers directly, and writes build.json with the version and the commit."
                  es="El frontend está construido sobre el shell compartido de las apps CAOS: el encabezado, los selectores de tema e idioma, el banco de trabajo con su panel e instrumento, la página de documentación, el gráfico y la compuerta medida. Una compilación copia al sitio exactamente los artefactos que declara el índice (y falla si falta uno), los pide con la versión en la dirección para que una versión nueva nunca lea un archivo antiguo en caché, escribe cada ruta como su propia página para que un enlace directo responda, y escribe build.json con la versión y el commit."
                />
                <P
                  en="Before a deploy, the gate serves the build as GitHub Pages would and walks every route, tab and case at five screen sizes, in both themes and both languages, and fails on what a reader would meet: an error, a broken link, something that cannot be scrolled to or clicked, a blank or undersized drawing, a view that never settles, a loop at rest, or a control that changes nothing."
                  es="Antes de un despliegue, la compuerta sirve la compilación como lo haría GitHub Pages y recorre cada ruta, pestaña y caso en cinco tamaños de pantalla, con ambos temas y ambos idiomas, y falla ante lo que encontraría un lector: un error, un enlace roto, algo a lo que no se puede llegar ni hacer clic, un dibujo en blanco o demasiado pequeño, una vista que nunca se estabiliza, un ciclo en reposo o un control que no cambia nada."
                />
              </DocSection>
              </> },
              { id: 'deploy', label: t('Versions and deploy', 'Versiones y despliegue'), content: <>
              <DocSection title={{ en: 'Versions and deploy', es: 'Versiones y despliegue' }} area="deployment" noRefsReason={THIS_REPO}>
                <P
                  en="VERSION is the only place the version is written; the pipeline, the web and the changelog read it, and a guard fails when any of them disagrees or falls behind the latest tag. Each product has one deploy place, decided at instantiation and written in deploy/TARGET; this template deploys to GitHub Pages, and the deploy job checks the live site afterwards: every route answers, a missing file answers 404, and build.json names the commit that was pushed."
                  es="VERSION es el único lugar donde se escribe la versión; el pipeline, la web y el registro de cambios la leen, y una guarda falla cuando alguno discrepa o queda detrás de la última etiqueta. Cada producto tiene un único lugar de despliegue, decidido al instanciar y escrito en deploy/TARGET; esta plantilla despliega en GitHub Pages, y el trabajo de despliegue verifica después el sitio en vivo: cada ruta responde, un archivo faltante responde 404, y build.json nombra el commit que se empujó."
                />
              </DocSection>
              </> },
            ],
          },
        ]}
      />
    </DocPage>
  );
}
