// The fourth group of the Implementation page, "How does it ship?": the models and their slots, the web, and the versions, CI and deploy
// (area `deployment`). Sources: the contract catalog (rows cgh-net, warmstart-model, model-metrics and their missing-data states),
// frontend/src/lib/ort.ts, frontend/scripts/copy-data.mjs, data-pipeline/pipeline/model/baseline.py,
// the SDD ("Deploy driver", "Technology and versions", "ADR fit"), frontend/src/App.tsx, frontend/vite.config.ts, frontend/scripts/
// {materialize-routes,gate}.mjs, .github/workflows/{ci,deploy-pages}.yml and scripts/check_live.py. The learned models are in progress
// (unit M1): this page describes their slots from the catalog and the code; their measurements are on the Benchmark page.
import { Callout, Cite, DocSection } from '@fasl-work/caos-app-shell';
import { L, P, useT } from '../bi';

const THIS_REPO = { en: 'Describes this repository.', es: 'Describe este repositorio.' };

export function ModelsTopic() {
  const t = useT();
  return (
    <DocSection title={{ en: 'Models and their slots', es: 'Modelos y sus espacios' }} refs={['onnxruntime']}>
      <P
        en={<>Two learned models are slots in the catalog, each behind the same contract as its baseline. The slot cgh-net (method M17) maps the target amplitude on a 128 x 128 focal crop, normalised to unit energy, to a phase mask of the same size; its baseline is Gerchberg-Saxton, M04, for 30 iterations. The slot warmstart-model (method B3) maps a list of up to 1024 traps, with x and y in focal bins, z in Rayleigh ranges and the weight, to one starting phase per trap, which starts the live M07 run; its baseline is the random trap phases of the portable generator. Both run in the browser with onnxruntime-web <Cite id="onnxruntime" />.</>}
        es={<>Dos modelos aprendidos son espacios del catálogo, cada uno detrás del mismo contrato que su línea base. El espacio cgh-net (método M17) lleva la amplitud objetivo sobre un recorte focal de 128 x 128, normalizada a energía unitaria, a una máscara de fase del mismo tamaño; su línea base es Gerchberg-Saxton, M04, durante 30 iteraciones. El espacio warmstart-model (método B3) lleva una lista de hasta 1024 trampas, con x e y en bins focales, z en rangos de Rayleigh y el peso, a una fase inicial por trampa, que inicia la corrida en vivo de M07; su línea base son las fases aleatorias de las trampas del generador portable. Ambos corren en el navegador con onnxruntime-web <Cite id="onnxruntime" />.</>}
      />
      <P
        en="A slot answers with its released model only when the card is on the site, conforms to the model-card contract, names the slot, and the graph has the size and the sha256 the card states; anything else leaves the baseline answering, with the reason, and the readiness document decides first so a slot declared as training does not even fetch a file that is not there. The site build applies the same test: a card whose graph is absent or differs from it stops the build, because the browser would refuse the model at run time. The views always label the result with the model that answered."
        es="Un espacio responde con su modelo publicado sólo cuando la ficha está en el sitio, cumple el contrato de ficha de modelo, nombra el espacio, y el grafo tiene el tamaño y el sha256 que declara la ficha; cualquier otra cosa deja respondiendo a la línea base, con la razón, y el documento de disponibilidad decide primero, de modo que un espacio declarado como en entrenamiento ni siquiera pide un archivo que no está. La compilación del sitio aplica la misma prueba: una ficha cuyo grafo está ausente o difiere de ella detiene la compilación, porque el navegador rechazaría el modelo en tiempo de ejecución. Las vistas rotulan siempre el resultado con el modelo que respondió."
      />
      <L
        items={[
          {
            en: 'The runtime is onnxruntime-web 1.31.1 with its WebAssembly binary bundled from the package, so the site asks no CDN; it runs with one thread and no proxy worker because GitHub Pages sends no COOP or COEP headers. Calls to one graph queue, as the runtime forbids concurrent runs on one session.',
            es: 'El runtime es onnxruntime-web 1.31.1 con su binario WebAssembly empaquetado desde el paquete, así que el sitio no consulta ninguna CDN; corre con un hilo y sin worker proxy porque GitHub Pages no envía las cabeceras COOP ni COEP. Las llamadas a un grafo se encolan, porque el runtime prohíbe corridas concurrentes sobre una sesión.',
          },
          {
            en: 'M17 answers in the browser only on 128 x 128 cases with a released model; its phase is shown and its focal plane needs the live engine. Without a model, GS at 30 iterations answers.',
            es: 'M17 responde en el navegador sólo en casos de 128 x 128 con un modelo publicado; se muestra su fase y su plano focal necesita el motor en vivo. Sin modelo responde GS a 30 iteraciones.',
          },
          {
            en: 'Training is offline, in PyTorch on the workstation GPU, and never in CI; held-out geometries are written apart before training, so a model is not judged by its own training data.',
            es: 'El entrenamiento es fuera de línea, en PyTorch sobre la GPU de la estación, y nunca en CI; las geometrías reservadas se escriben aparte antes de entrenar, de modo que un modelo no se juzga con sus propios datos de entrenamiento.',
          },
        ]}
      />
      <Callout variant="honest" title={t('State of the models in this build', 'Estado de los modelos en esta versión')}>
        {t(
          'The models unit is in progress. The repository holds no released model card or graph yet, so both slots are answered by their baselines, the training stage and the evaluation stage of the pipeline are not built (the files in the tree are still the template\'s example and the bake does not call them), and the encodings of the two graphs are written from the catalog rows, so the cards of the first released models must fix them. Their measurements are on the Benchmark page; this page states none.',
          'La unidad de modelos está en curso. El repositorio aún no contiene ninguna ficha ni grafo de modelo publicado, así que ambos espacios los responden sus líneas base, las etapas de entrenamiento y de evaluación del pipeline no están construidas (los archivos del árbol siguen siendo el ejemplo de la plantilla y el precálculo no los llama), y las codificaciones de los dos grafos están escritas a partir de las filas del catálogo, de modo que las fichas de los primeros modelos publicados deben fijarlas. Sus mediciones están en la página Benchmark; esta página no afirma ninguna.',
        )}
      </Callout>
    </DocSection>
  );
}

export function WebTopic() {
  return (
    <DocSection title={{ en: 'The web', es: 'La web' }} noRefsReason={THIS_REPO}>
      <P
        en="The frontend is built on the shared CAOS app shell, pinned exactly: the header with its six routes (App, Introduction, Methodology, Implementation, Experiments, Benchmark), the theme and language toggles, the workbench layout with its rail and instrument, the documentation page, the charts and the measured gate. The pages and the workbench are loaded on demand, the three-dimensional lobes and the model runtime only when first used, and the build copies exactly the artifacts the index declares into the site and fails on a missing one, so a file removed from the bake never lingers."
        es="El frontend está construido sobre el shell compartido de las apps CAOS, fijado exactamente: el encabezado con sus seis rutas (App, Introducción, Metodología, Implementación, Experimentos, Benchmark), los selectores de tema e idioma, la disposición de la mesa de trabajo con su panel e instrumento, la página de documentación, los gráficos y la compuerta medida. Las páginas y la mesa de trabajo se cargan bajo demanda, los lóbulos tridimensionales y el runtime de modelos sólo en su primer uso, y la compilación copia al sitio exactamente los artefactos que declara el índice y falla si falta uno, de modo que un archivo retirado del precálculo nunca queda en el sitio."
      />
      <P
        en="The App is one workbench. The rail holds the case and the method, then four sections: Run (the device, the iteration count, the backend, the trap power and the seed), View, Edit (the trap editor, which adds, moves and deletes traps and re-runs the live methods) and the live Values. The instrument holds five groups, Hologram, Focal plane, Traps, Convergence and Dynamics, plus the Context write-up. Focus mode opens the open group in the full viewport and returns to the same case, group and view with Escape. Each group carries a lane badge, live or replay, and the provenance of what it draws."
        es="La App es una sola mesa de trabajo. El panel contiene el caso y el método, y luego cuatro secciones: Corrida (el dispositivo, el número de iteraciones, el motor de cálculo, la potencia de la trampa y la semilla), Vista, Edición (el editor de trampas, que agrega, mueve y borra trampas y vuelve a ejecutar los métodos en vivo) y los Valores en vivo. El instrumento contiene cinco grupos, Holograma, Plano focal, Trampas, Convergencia y Dinámica, más el texto de Contexto. El modo Foco abre el grupo abierto en toda la ventana y vuelve al mismo caso, grupo y vista con Escape. Cada grupo lleva una insignia de carril, en vivo o reproducción, y la procedencia de lo que dibuja."
      />
      <P
        en="Every route is written as its own page after the build, and 404.html is the app as well, so a deep link on a static host answers with the application and an unknown path reaches the router. The build writes build.json with the version, the commit and the build time. Before a deploy, the gate serves the built site as GitHub Pages would and walks every route, tab and case at five screen sizes, in both themes and both languages, and requires Focus mode. A person then reads its captures: the gate measures, it does not judge content."
        es="Cada ruta se escribe como su propia página tras la compilación, y 404.html es también la aplicación, de modo que un enlace directo en un host estático responde con la aplicación y una ruta desconocida llega al enrutador. La compilación escribe build.json con la versión, el commit y la hora de la compilación. Antes de un despliegue, la compuerta sirve el sitio compilado como lo haría GitHub Pages y recorre cada ruta, pestaña y caso en cinco tamaños de pantalla, con ambos temas y ambos idiomas, y exige el modo Foco. Luego una persona lee sus capturas: la compuerta mide, no juzga el contenido."
      />
    </DocSection>
  );
}

export function DeployTopic() {
  const t = useT();
  return (
    <DocSection title={{ en: 'Versions, CI and deploy', es: 'Versiones, CI y despliegue' }} area="deployment" noRefsReason={THIS_REPO}>
      <P
        en="DinHot deploys to GitHub Pages at dinhot.fasl-work.com: a public repository, a static site, every artifact committed, no secret and no server. The compute is an FFT loop the browser runs within the lane budget, so no server trigger applies. The deploy place is written once in deploy/TARGET and checked by a guard. VERSION is the only place the version is written, and the pipeline, the web and the changelog read it. The workflow never rebakes, retrains or recomputes: it publishes the committed artifacts."
        es="DinHot se despliega en GitHub Pages en dinhot.fasl-work.com: un repositorio público, un sitio estático, cada artefacto versionado, sin secretos y sin servidor. El cómputo es un bucle de FFT que el navegador ejecuta dentro del presupuesto de carril, así que no se aplica ningún disparador de servidor. El lugar de despliegue se escribe una vez en deploy/TARGET y lo verifica una guarda. VERSION es el único lugar donde se escribe la versión, y la leen el pipeline, la web y el registro de cambios. El flujo nunca vuelve a precalcular, ni a entrenar, ni a recomputar: publica los artefactos versionados."
      />
      <P
        en="CI runs on pushes to main and develop in three jobs, checks, web and guards, and does only cheap work. The deploy workflow starts only after CI succeeded on the same commit of main, checks out exactly that commit, verifies the artifacts and the deploy place, builds the site with the base path of the domain and uploads the build. After the deploy it checks the live site: build.json names the commit that was pushed, every route answers 200 with HTML with and without its trailing slash, a file that does not exist answers 404, and the artifact index answers JSON."
        es="La CI corre en los push a main y develop en tres trabajos, checks, web y guards, y hace sólo trabajo barato. El flujo de despliegue empieza sólo después de que la CI tuvo éxito sobre el mismo commit de main, descarga exactamente ese commit, verifica los artefactos y el lugar de despliegue, compila el sitio con la ruta base del dominio y sube la compilación. Tras el despliegue verifica el sitio en vivo: build.json nombra el commit que se empujó, cada ruta responde 200 con HTML con y sin barra final, un archivo que no existe responde 404, y el índice de artefactos responde JSON."
      />
      <Callout variant="note" title={t('What Pages cannot do', 'Qué no puede hacer Pages')}>
        {t(
          'GitHub Pages sends no COOP or COEP headers, so the workers are single-threaded and SharedArrayBuffer is not used. The previous service of this product on a VPS is retired after the Pages site passes its live checks.',
          'GitHub Pages no envía las cabeceras COOP ni COEP, así que los workers son de un solo hilo y no se usa SharedArrayBuffer. El servicio anterior de este producto en un VPS se retira después de que el sitio de Pages pase sus comprobaciones en vivo.',
        )}
      </Callout>
    </DocSection>
  );
}
