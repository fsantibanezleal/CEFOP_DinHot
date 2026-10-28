// The third group of the Implementation page, "Can it be trusted?": reproducibility (area `reproducibility`), the parity tests, the
// artifacts with their budgets and what is real in a build, and the guards. Sources: the code (core/manifest.py, model/holo/core/rng.py,
// benchmark/protocol.py, stages/engine_reference.py, core/readiness.py, core/trace.py; frontend/src/engine/holo/*.parity.test.ts and
// parity.helpers.ts; frontend/src/readiness/), the contract catalog, the SDD section "Resources", .github/workflows/ci.yml and the
// reports of units E1 and T1 for the measurements, each with its conditions. SDD figures are bounds and are labelled as bounds.
import { Callout, Cite, DocSection, useShellLang } from '@fasl-work/caos-app-shell';
import { P, useT } from '../bi';
import { ReadinessTable } from '../../readiness/ReadinessTable';

const THIS_REPO = { en: 'Describes this repository.', es: 'Describe este repositorio.' };
const WRAP = { overflowWrap: 'anywhere' } as const;

export function ReproducibilityTopic() {
  const t = useT();
  return (
    <DocSection title={{ en: 'Reproducibility', es: 'Reproducibilidad' }} area="reproducibility" refs={['blackman2021', 'splitmix32']}>
      <P
        en={<>A result is reproduced from three things written next to it: the seed, the engine version and the parameters, all in the case manifest, which is a pure function of the parameters and the seed with no clock in it. The generator is the same in both engines: xoshiro128** <Cite id="blackman2021" /> seeded by four outputs of SplitMix32 <Cite id="splitmix32" />, with the draw order fixed as part of the contract, so the TypeScript port reproduces the integer stream and the uniforms bit for bit and the normals to about 1e-15.</>}
        es={<>Un resultado se reproduce con tres cosas escritas junto a él: la semilla, la versión del motor y los parámetros, todo en el manifiesto del caso, que es una función pura de los parámetros y la semilla y no lleva reloj. El generador es el mismo en ambos motores: xoshiro128** <Cite id="blackman2021" /> sembrado con cuatro salidas de SplitMix32 <Cite id="splitmix32" />, con el orden de los sorteos fijado como parte del contrato, de modo que la versión en TypeScript reproduce el flujo de enteros y los uniformes bit a bit y las normales hasta cerca de 1e-15.</>}
      />
      <P
        en="The engine uses no global generator: every method of a case receives a generator built from the case seed, so all of them start from the same random numbers, and a benchmark cell uses the protocol seed as the engine seed. The seeds that tune a method are a different set, offset by 1000, so a tuned row is never fitted on the seeds that score it. A test bakes the same inputs twice into two sandboxes, with a test-only package of planted methods, and compares every JSON file byte by byte."
        es="El motor no usa un generador global: cada método de un caso recibe un generador construido con la semilla del caso, así que todos parten de los mismos números aleatorios, y una celda del benchmark usa la semilla del protocolo como semilla del motor. Las semillas que ajustan un método son un conjunto distinto, desplazado en 1000, de modo que una fila ajustada nunca se calibra con las semillas que la evalúan. Una prueba precalcula dos veces las mismas entradas en dos sandboxes, con un paquete de métodos plantados sólo para pruebas, y compara cada archivo JSON byte a byte."
      />
      <pre>
        <code>{`python data-pipeline/run.py all --only C02_grid_feedback --output <sandbox>
# the manifest of the case records seed, engine_version and params; the same inputs
# and the same version write the same bytes`}</code>
      </pre>
      <Callout variant="note" title={t('One version, one source', 'Una versión, una fuente')}>
        {t(
          'The version is written once, in VERSION. A document baked by an earlier engine version is declared stale by the readiness document and shown with the version that baked it, never as current.',
          'La versión se escribe una sola vez, en VERSION. Un documento generado por una versión anterior del motor lo declara desactualizado el documento de disponibilidad y se muestra con la versión que lo generó, nunca como vigente.',
        )}
      </Callout>
    </DocSection>
  );
}

const TOLERANCES: { group: { en: string; es: string }; phi: string; abs: string; rel: string }[] = [
  { group: { en: 'Methods of the GS family, M01 to M08, M12, M14, M15, M16, M19', es: 'Métodos de la familia GS, M01 a M08, M12, M14, M15, M16, M19' }, phi: '1e-9 rad', abs: '1e-10', rel: '1e-9' },
  { group: { en: 'M10 and M11 (line search and Adam pass last-bit differences through the iterate)', es: 'M10 y M11 (la búsqueda de línea y Adam propagan diferencias del último bit por la iteración)' }, phi: '1e-8 rad', abs: '1e-9', rel: '1e-8' },
  { group: { en: 'Live grid 256 x 256 padded 2, 30 iterations: M04, M06, M07', es: 'Grilla en vivo de 256 x 256 con relleno 2, 30 iteraciones: M04, M06, M07' }, phi: '1e-6 rad', abs: '1e-9', rel: '1e-8' },
];

export function ParityTopic() {
  const t = useT();
  const lang = useShellLang();
  return (
    <DocSection title={{ en: 'Parity tests', es: 'Pruebas de paridad' }} noRefsReason={THIS_REPO}>
      <P
        en="The two engines cannot drift apart unnoticed because the Python engine writes the expected values. The stage engine_reference.py writes 46 reference documents into tests/fixtures/engine/, each of schema dinhot.engine-ref/v1 with its own tolerance, covering the random stream, the geometry, the forward models, the metrics, the device model, the Zernike modes, the camera, the trap physics, the dynamics, every live method and the live grid. The vitest files named *.parity.test.ts read those documents, so no expected value is a constant typed in a test or the output of the engine under test."
        es="Los dos motores no pueden separarse sin que se note porque el motor en Python escribe los valores esperados. La etapa engine_reference.py escribe 46 documentos de referencia en tests/fixtures/engine/, cada uno del esquema dinhot.engine-ref/v1 con su propia tolerancia, que cubren el flujo aleatorio, la geometría, los modelos directos, las métricas, el modelo del dispositivo, los modos de Zernike, la cámara, la física de la trampa, la dinámica, cada método en vivo y la grilla en vivo. Los archivos de vitest llamados *.parity.test.ts leen esos documentos, así que ningún valor esperado es una constante escrita en una prueba ni la salida del motor bajo prueba."
      />
      <P
        en="The tolerances of the method tests are stated in the code with their reason: the observed worst case over the GS family is orders of magnitude below the tolerance, which leaves room for another math library or JavaScript engine without hiding a real difference, and the gradient methods get a wider one. On the Python side a test regenerates every document from the engine and compares it with the committed files, and another fails when a live method has no reference. A phase compares modulo 2π, so a phase of 0 and of 2π minus 1e-12 are the same hologram."
        es="Las tolerancias de las pruebas de métodos están escritas en el código con su razón: el peor caso observado en la familia GS está órdenes de magnitud bajo la tolerancia, lo que deja margen para otra biblioteca matemática u otro motor de JavaScript sin ocultar una diferencia real, y los métodos de gradiente tienen una más amplia. Del lado de Python una prueba regenera cada documento desde el motor y lo compara con los archivos versionados, y otra falla cuando un método en vivo no tiene referencia. Una fase se compara módulo 2π, de modo que una fase de 0 y una de 2π menos 1e-12 son el mismo holograma."
      />
      <table className="caos-table" data-state="ready">
        <thead>
          <tr>
            <th className="caos-col-text">{t('Group of tests', 'Grupo de pruebas')}</th>
            <th>{t('Phase', 'Fase')}</th>
            <th>{t('Absolute', 'Absoluta')}</th>
            <th>{t('Relative', 'Relativa')}</th>
          </tr>
        </thead>
        <tbody>
          {TOLERANCES.map((r) => (
            <tr key={r.phi + r.abs}>
              <td className="caos-col-text" style={WRAP}>{r.group[lang]}</td>
              <td>{r.phi}</td>
              <td>{r.abs}</td>
              <td>{r.rel}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <Callout variant="honest" title={t('What the parity tests prove', 'Qué prueban las pruebas de paridad')}>
        {t(
          'They prove the port equals the Python engine on the references that were written, and the T1 unit showed that five planted defects (a ramp off by one bin, a wrong generator rotation, a floor in place of a round in the quantizer, a phase freeze one iteration late, absent references) each turn the suite red. They do not prove the physics: the oracles of the engine do that, and the worst difference observed of any quantity was 1.8e-11, a sum of 4096 terms. The real Worker and the WebGPU path run only in Chromium, by scripts/engine-browser.mjs, locally and in the gate run, never in Node CI.',
          'Prueban que la versión en TypeScript es igual al motor en Python en las referencias escritas, y la unidad T1 mostró que cinco defectos plantados (una rampa corrida un bin, una rotación errónea del generador, un piso en lugar de un redondeo en el cuantizador, un congelamiento de fase una iteración tarde, referencias ausentes) ponen cada uno en rojo la batería. No prueban la física: eso lo hacen los oráculos del motor, y la mayor diferencia observada en cualquier cantidad fue 1,8e-11, una suma de 4096 términos. El Worker real y la vía WebGPU corren sólo en Chromium, con scripts/engine-browser.mjs, en local y en la corrida de la compuerta, nunca en la CI de Node.',
        )}
      </Callout>
    </DocSection>
  );
}

const BOUNDS: { stage: { en: string; es: string }; bound: { en: string; es: string } }[] = [
  { stage: { en: 'Trace of one case', es: 'Traza de un caso' }, bound: { en: 'at most 256 KiB, enforced by the lane gate (core/gate.py)', es: 'a lo más 256 KiB, impuesto por la compuerta de carril (core/gate.py)' } },
  { stage: { en: 'Bake of the cases', es: 'Precálculo de los casos' }, bound: { en: 'at most 4 GB peak, 3 MB of artifacts, 20 min, on a workstation, never CI', es: 'a lo más 4 GB de pico, 3 MB de artefactos, 20 min, en una estación, nunca CI' } },
  { stage: { en: 'Benchmark', es: 'Benchmark' }, bound: { en: 'at most 4 GB peak, 2 MB of results, 6 h, resumable by cell', es: 'a lo más 4 GB de pico, 2 MB de resultados, 6 h, reanudable por celda' } },
  { stage: { en: 'Training of the two models', es: 'Entrenamiento de los dos modelos' }, bound: { en: 'at most 7 GB of GPU memory, 10 MB of ONNX models, 3 h, never CI', es: 'a lo más 7 GB de memoria de GPU, 10 MB de modelos ONNX, 3 h, nunca CI' } },
  { stage: { en: 'Site build', es: 'Compilación del sitio' }, bound: { en: 'at most 600 MB peak, 30 MB in dist, 60 s', es: 'a lo más 600 MB de pico, 30 MB en dist, 60 s' } },
  { stage: { en: 'Deploy payload', es: 'Carga del despliegue' }, bound: { en: 'at most 30 MB uploaded, one Pages deploy under 3 min', es: 'a lo más 30 MB subidos, un despliegue de Pages en menos de 3 min' } },
];

export function ArtifactsTopic() {
  const t = useT();
  const lang = useShellLang();
  return (
    <DocSection title={{ en: 'Artifacts, budgets and what is real', es: 'Artefactos, presupuestos y qué es real' }} noRefsReason={THIS_REPO}>
      <P
        en="The committed artifacts are the evidence: the index of cases, one manifest and one trace per case, the benchmark results, the model metrics and the readiness document. The site fetches each with the version in the address, so a new release never reads an old cached file, and a reply that is not JSON is an error at the fetch, because a static host that answers a missing file with its HTML page would otherwise fail far from the cause. The budgets in the table are bounds set in the design document from measured transform timings and method costs, not measurements."
        es="Los artefactos versionados son la evidencia: el índice de casos, un manifiesto y una traza por caso, los resultados del benchmark, las métricas de los modelos y el documento de disponibilidad. El sitio pide cada uno con la versión en la dirección, así que una versión nueva nunca lee un archivo antiguo en caché, y una respuesta que no es JSON es un error en la petición, porque un host estático que responde a un archivo ausente con su página HTML fallaría lejos de la causa. Los presupuestos de la tabla son cotas fijadas en el documento de diseño a partir de tiempos medidos de transformadas y costos de métodos, no mediciones."
      />
      <table className="caos-table" data-state="ready">
        <thead>
          <tr>
            <th>{t('Stage', 'Etapa')}</th>
            <th className="caos-col-text">{t('Bound (SDD)', 'Cota (SDD)')}</th>
          </tr>
        </thead>
        <tbody>
          {BOUNDS.map((b) => (
            <tr key={b.stage.en}>
              <td>{b.stage[lang]}</td>
              <td className="caos-col-text" style={WRAP}>{b.bound[lang]}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <P
        en="Memory in the engine is measured where it matters: the separable point-trap evaluation of 1024 traps on a 512 x 512 grid peaked at 16.8 MB in Python (tracemalloc, test under a 1 GB assertion), the live point plan caches at most 2e6 factors, 32 MB, for the length of a run, and the GPU path holds two complex float32 buffers of the FFT size, 4 MB at 512 squared, released when the run ends or is cancelled. A figure that is a bound and not a measurement is labelled so on every page."
        es="La memoria en el motor se mide donde importa: la evaluación separable de trampas puntuales de 1024 trampas sobre una grilla de 512 x 512 tuvo un pico de 16,8 MB en Python (tracemalloc, prueba con aserción bajo 1 GB), el plan puntual en vivo guarda a lo más 2e6 factores, 32 MB, durante una corrida, y la vía GPU mantiene dos búferes complejos float32 del tamaño de la FFT, 4 MB a 512 al cuadrado, liberados cuando la corrida termina o se cancela. Una cifra que es una cota y no una medición se rotula así en cada página."
      />
      <P
        en="Every row of the catalog carries a declared state, computed by the pipeline from the catalog and the repository: available, partial (some manifests or artifacts are absent), stale (baked by an earlier engine version), provider (served by a provider while the real producer is not built), training (a baseline or a released model answers while a newer one trains) or missing. A view shows the result with a note for the states that still hold one, and an explicit not available yet with the reason for the state that does not, never an empty chart. The table reads the readiness document of this build."
        es="Cada fila del catálogo lleva un estado declarado, calculado por el pipeline a partir del catálogo y del repositorio: disponible, parcial (faltan manifiestos o artefactos), desactualizado (generado por una versión anterior del motor), proveedor (lo sirve un proveedor mientras el productor real no está construido), entrenando (responde una línea base o un modelo publicado mientras uno nuevo se entrena) o ausente. Una vista muestra el resultado con una nota para los estados que aún lo permiten, y un aún no disponible explícito con la razón para el estado que no, nunca un gráfico vacío. La tabla lee el documento de disponibilidad de esta versión."
      />
      <ReadinessTable />
    </DocSection>
  );
}

const GUARDS: { script: string; en: string; es: string }[] = [
  { script: 'check_artifacts.py', en: 'Contract 2 on disk: every manifest, trace and size agrees, each lane matches its gate verdict, a trace within 256 KiB, the units gate over the shipped documents.', es: 'El contrato 2 en disco: cada manifiesto, traza y tamaño concuerdan, cada carril coincide con el veredicto de su compuerta, una traza dentro de 256 KiB, la compuerta de unidades sobre los documentos distribuidos.' },
  { script: 'check_contracts.py, check_documents.py', en: 'The catalog has every field and every path, and every committed document validates against its schema file.', es: 'El catálogo tiene cada campo y cada ruta, y cada documento versionado valida contra su archivo de esquema.' },
  { script: 'check_contract_versions.py', en: 'A schema changed under the same version, a version that went down, a missing history row, and against the base commit a breaking change without a major step.', es: 'Un esquema cambiado con la misma versión, una versión que baja, una fila de historial ausente, y contra el commit base un cambio incompatible sin paso mayor.' },
  { script: 'check_readiness.py, check_skeleton.py', en: 'The readiness document is current with the catalog; rows still served by a provider are listed while building and fail on main.', es: 'El documento de disponibilidad está al día con el catálogo; las filas que aún sirve un proveedor se listan mientras se construye y fallan en main.' },
  { script: 'check_version_coherence.py', en: 'VERSION is the single source and the pipeline, the web and the changelog agree with it.', es: 'VERSION es la única fuente y el pipeline, la web y el registro de cambios coinciden con ella.' },
  { script: 'check_sdd.py, check_tech_matrix.py', en: 'Every requirement of the design document names a real gate; the technology table equals the pinned dependencies.', es: 'Cada requisito del documento de diseño nombra una compuerta real; la tabla de tecnología es igual a las dependencias fijadas.' },
  { script: 'check_web_baseline.py', en: 'Tokens, classes, numbers, images and animation loops of the web source.', es: 'Tokens, clases, números, imágenes y bucles de animación del código web.' },
  { script: 'check_content_standards.py', en: 'No em-dash and no emoji in the content of the product.', es: 'Ni raya larga ni emoji en el contenido del producto.' },
  { script: 'check_deploy_place.py, check_ci_budget.py', en: 'One deploy place; CI runs cheap checks only, no training and trunk-only triggers.', es: 'Un solo lugar de despliegue; la CI corre sólo comprobaciones baratas, sin entrenamiento y con disparadores sólo del tronco.' },
  { script: 'tests/adversarial', en: 'Each guard is run against a planted defect and must reject it.', es: 'Cada guarda se ejecuta contra un defecto plantado y debe rechazarlo.' },
];

export function GuardsTopic() {
  const t = useT();
  const lang = useShellLang();
  return (
    <DocSection title={{ en: 'The guards', es: 'Las guardas' }} noRefsReason={THIS_REPO}>
      <P
        en="Three kinds of check stand between a change and a deploy. The gates inside the pipeline judge the data: the lane gate, the expected ranges that make the bake fail when a metric leaves its stated interval, and the units gate that checks each observable is in the domain and the units of the question it answers. The guards in scripts/check_*.py judge the repository and are cheap enough for CI. The measured gate on the built site judges what a reader would meet."
        es="Tres clases de comprobación separan un cambio de un despliegue. Las compuertas dentro del pipeline juzgan los datos: la compuerta de carril, los rangos esperados que hacen fallar el precálculo cuando una métrica sale de su intervalo declarado, y la compuerta de unidades que verifica que cada observable está en el dominio y en las unidades de la pregunta que responde. Las guardas de scripts/check_*.py juzgan el repositorio y son lo bastante baratas para la CI. La compuerta medida sobre el sitio compilado juzga lo que encontraría un lector."
      />
      <P
        en="The units gate recomputes the relative spread and the uniformity of a method from its per-trap intensities and requires the two to agree, which catches a fraction written where a percent belongs or a metric of another quantity under the right name. CI runs on pushes to main and develop and does only cheap work: the guards below, the web build and the vitest suite. The full pytest suite, the bake, the benchmark and the training run locally, by design."
        es="La compuerta de unidades recalcula la dispersión relativa y la uniformidad de un método a partir de sus intensidades por trampa y exige que las dos concuerden, lo que atrapa una fracción escrita donde corresponde un porcentaje o una métrica de otra cantidad bajo el nombre correcto. La CI corre en los push a main y develop y hace sólo trabajo barato: las guardas siguientes, la compilación web y la batería de vitest. La batería completa de pytest, el precálculo, el benchmark y el entrenamiento corren en local, por diseño."
      />
      <table className="caos-table" data-state="ready">
        <thead>
          <tr>
            <th>{t('Guard', 'Guarda')}</th>
            <th className="caos-col-text">{t('What it fails on', 'Ante qué falla')}</th>
          </tr>
        </thead>
        <tbody>
          {GUARDS.map((g) => (
            <tr key={g.script}>
              <td style={WRAP}>{g.script}</td>
              <td className="caos-col-text" style={WRAP}>{lang === 'es' ? g.es : g.en}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </DocSection>
  );
}
