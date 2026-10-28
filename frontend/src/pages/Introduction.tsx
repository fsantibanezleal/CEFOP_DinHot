import { Callout, Cite, DocPage, DocSection, Equation, ExecutiveView, Figure, Glossary, Tabs } from '@fasl-work/caos-app-shell';
import executive from '../../../content/executive.json';
import product from '../../../product.json';
import { L, P, useT } from '../content/bi';

/** The Introduction has two views (problem-context-first): the executive view, first and the default, rendered by the shell
 *  from content/executive.json, and the technical view. The product writes the data file; it never designs the executive view. */
export function Introduction() {
  return <IntroductionPage data={executive} />;
}

export function IntroductionPage({ data }: { data: unknown }) {
  const t = useT();
  return (
    <DocPage
      title={{ en: 'Introduction', es: 'Introducción' }}
      lede={t(
        `${product.tagline.en} The executive view frames the problem space for a decision maker; the technical view gives the model, the pipeline and the limits of what the example proves.`,
        `${product.tagline.es} La vista ejecutiva enmarca el espacio del problema para quien decide; la vista técnica da el modelo, el pipeline y los límites de lo que el ejemplo demuestra.`,
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
  );
}

/** The four stages of the build as a drawing: boxes and arrows are right here, it is a technical figure of the pipeline. */
function PipelineFigure() {
  const t = useT();
  const stages = [
    t('Bake offline', 'Precalcular'),
    t('Check and store', 'Verificar y guardar'),
    t('Replay in the site', 'Reproducir en el sitio'),
    t('Re-run live', 'Recalcular en vivo'),
  ];
  return (
    <svg className="fig-svg wide" viewBox="0 0 640 120" role="img" aria-label={t('The four stages of the build', 'Las cuatro etapas de la compilación')}>
      {stages.map((label, i) => (
        <g key={i} transform={`translate(${10 + i * 160} 30)`}>
          <rect width="128" height="60" rx="8" fill="var(--color-surface-2)" stroke="var(--color-border)" strokeWidth="1.5" />
          <text x="64" y="36" textAnchor="middle" fontSize="14" fontWeight="600" fill="var(--color-fg)">
            {label}
          </text>
          {i < stages.length - 1 && <path d="M 132 30 L 154 30 M 148 24 L 154 30 L 148 36" fill="none" stroke="var(--color-fg-faint)" strokeWidth="2" strokeLinecap="round" />}
        </g>
      ))}
    </svg>
  );
}

function TechnicalView() {
  const t = useT();
  return (
    <>
      <DocSection title={{ en: 'The problem', es: 'El problema' }} area="problem" refs={['hethcote2000']}>
        <P
          en={<>A health service has to decide, week by week during a rising outbreak, how many beds and how much staff to commit, while the number of infected people changes faster than a monthly report can follow. The example reduces that to a closed population of 100000 people, a small group infected at the start, and a model that says how the infection spreads and how it ends <Cite id="hethcote2000" />.</>}
          es={<>Un servicio de salud debe decidir, semana a semana durante un brote en aumento, cuántas camas y cuánto personal comprometer, mientras el número de personas contagiadas cambia más rápido de lo que un informe mensual puede seguir. El ejemplo lo reduce a una población cerrada de 100000 personas, un grupo pequeño contagiado al inicio y un modelo que dice cómo se propaga la infección y cómo termina <Cite id="hethcote2000" />.</>}
        />
        <P
          en="The decision is about timing as much as size. In the epidemic case the number of infected people peaks on day 24 and in the fast-burn case on day 9, so a plan agreed after three weeks arrives after the peak in one case and long after it in the other. The product shows the whole course before the meeting and recomputes it while the room waits."
          es="La decisión trata tanto de la oportunidad como del tamaño. En el caso de epidemia el número de personas contagiadas llega a su máximo el día 24 y en el de combustión rápida el día 9, de modo que un plan acordado tras tres semanas llega después del pico en un caso y mucho después en el otro. El producto muestra el curso completo antes de la reunión y lo recalcula mientras la sala espera."
        />
      </DocSection>
      <DocSection title={{ en: 'The principles it rests on', es: 'Los principios en que se apoya' }} area="principles" refs={['km1927', 'diekmann1990']}>
        <P
          en={<>The population is split into the susceptible, the infected and the recovered, and people move only in that order <Cite id="km1927" />. Contacts are homogeneous, so the rate of new infections is proportional to the product of susceptible and infected people, and an infected person recovers at a constant rate. Nothing else enters: no births, no deaths, no structure by age or place.</>}
          es={<>La población se divide en susceptibles, contagiados y recuperados, y las personas se mueven sólo en ese orden <Cite id="km1927" />. Los contactos son homogéneos, de modo que la tasa de nuevas infecciones es proporcional al producto de susceptibles y contagiados, y una persona contagiada se recupera a una tasa constante. Nada más interviene: ni nacimientos, ni muertes, ni estructura por edad o lugar.</>}
        />
        <P
          en={<>Two consequences carry the whole product. The basic reproduction number, the average number of people one infected person infects in a fully susceptible population, decides whether an outbreak grows at all <Cite id="diekmann1990" />. And the share of the population that is ever infected follows from that number alone, whatever the course in time, which gives an exact check on every run.</>}
          es={<>Dos consecuencias sostienen todo el producto. El número reproductivo básico, el promedio de personas que una persona contagiada contagia en una población totalmente susceptible, decide si un brote crece siquiera <Cite id="diekmann1990" />. Y la fracción de la población que llega a contagiarse se deduce sólo de ese número, sea cual sea el curso en el tiempo, lo que da una verificación exacta de cada corrida.</>}
        />
      </DocSection>
      <DocSection title={{ en: 'The mathematics', es: 'La matemática' }} area="math" refs={['km1927', 'diekmann1990', 'miller2012']}>
        <Equation
          tex="\frac{dS}{dt} = -\beta \frac{S I}{N}, \qquad \frac{dI}{dt} = \beta \frac{S I}{N} - \gamma I, \qquad \frac{dR}{dt} = \gamma I"
          caption={t('The closed system of the susceptible S, the infected I and the recovered R, with S + I + R = N at every time.', 'El sistema cerrado de susceptibles S, contagiados I y recuperados R, con S + I + R = N en todo instante.')}
        />
        <Equation
          tex="R_0 = \frac{\beta}{\gamma}, \qquad p_c = 1 - \frac{1}{R_0}"
          caption={t('The basic reproduction number R0 and the share p_c of the population that must be immune to prevent an outbreak.', 'El número reproductivo básico R0 y la fracción p_c de la población que debe ser inmune para impedir un brote.')}
        />
        <Equation
          tex="z = 1 - e^{-R_0 z}"
          caption={t('The final size z, the share of the population ever infected, which depends on R0 alone.', 'El tamaño final z, la fracción de la población que llega a contagiarse, que depende sólo de R0.')}
        />
        <Glossary
          entries={[
            { term: 'S(t)', definition: { en: 'people who can still be infected at time t', es: 'personas que aún pueden contagiarse en el tiempo t' } },
            { term: 'I(t)', definition: { en: 'people who are infected and infectious at time t', es: 'personas contagiadas y contagiosas en el tiempo t' } },
            { term: 'R(t)', definition: { en: 'people who have recovered and cannot be infected again', es: 'personas recuperadas que no pueden volver a contagiarse' } },
            { term: 'N', definition: { en: 'the size of the closed population, constant', es: 'el tamaño de la población cerrada, constante' } },
            { term: 'β', definition: { en: 'the contact rate: new infections per infected person per day', es: 'la tasa de contacto: nuevos contagios por persona contagiada por día' } },
            { term: 'γ', definition: { en: 'the recovery rate: the share of the infected who recover per day', es: 'la tasa de recuperación: la fracción de contagiados que se recupera por día' } },
            { term: 'R0', definition: { en: 'the basic reproduction number, β divided by γ', es: 'el número reproductivo básico, β dividido por γ' } },
            { term: 'p_c', definition: { en: 'the immune share that prevents an outbreak', es: 'la fracción inmune que impide un brote' } },
            { term: 'z', definition: { en: 'the final size: the share of the population ever infected', es: 'el tamaño final: la fracción de la población que llega a contagiarse' } },
            { term: 'v', definition: { en: 'the share made immune at the start in the immunisation variants', es: 'la fracción hecha inmune al inicio en las variantes de inmunización' } },
          ]}
        />
      </DocSection>
      <DocSection title={{ en: 'From the data to the screen', es: 'De los datos a la pantalla' }} area="pipeline" noRefsReason={{ en: 'Describes this build.', es: 'Describe esta compilación.' }}>
        <ol>
          <li>{t('The pipeline validates the parameters of each case and bakes its course offline.', 'El pipeline valida los parámetros de cada caso y precalcula su curso fuera de línea.')}</li>
          <li>{t('The gates check each baked case against its expected ranges and write its artifact and its manifest.', 'Las compuertas verifican cada caso precalculado contra sus rangos esperados y escriben su artefacto y su manifiesto.')}</li>
          <li>{t('The build copies the declared artifacts into the site, which replays them with no server.', 'La compilación copia los artefactos declarados al sitio, que los reproduce sin servidor.')}</li>
          <li>{t('The live engine re-runs a case in the browser, and the workbench shows both courses side by side.', 'El motor en vivo vuelve a correr un caso en el navegador, y el banco de trabajo muestra ambos cursos lado a lado.')}</li>
        </ol>
        <Figure caption={t('The four stages, from the offline bake to the workbench in the browser.', 'Las cuatro etapas, desde el precálculo fuera de línea hasta el banco de trabajo en el navegador.')}>
          <PipelineFigure />
        </Figure>
      </DocSection>
      <DocSection title={{ en: 'What is exact and what is not', es: 'Qué es exacto y qué no' }} area="honesty" noRefsReason={{ en: 'States the limits of this example.', es: 'Declara los límites de este ejemplo.' }}>
        <P
          en="The live engine reproduces every baked course to the rounding of the stored trace, and the final size of each run that ends inside its horizon matches the closed relation. That is the exact part. The population, the starting group and the rates are illustrative: no real outbreak, region or hospital was used, so no number here is a forecast."
          es="El motor en vivo reproduce cada curso precalculado hasta el redondeo de la traza guardada, y el tamaño final de cada corrida que termina dentro de su horizonte coincide con la relación cerrada. Esa es la parte exacta. La población, el grupo inicial y las tasas son ilustrativos: no se usó ningún brote, región ni hospital reales, de modo que ninguna cifra aquí es un pronóstico."
        />
        <Callout variant="honest" title={t('Not a forecast', 'No es un pronóstico')}>
          {t('The model is closed, homogeneous and deterministic. A product replaces it with a model fitted to its own data and states its own limits.', 'El modelo es cerrado, homogéneo y determinista. Un producto lo reemplaza por un modelo ajustado a sus propios datos y declara sus propios límites.')}
        </Callout>
      </DocSection>
      <DocSection title={{ en: 'What this product is', es: 'Qué es este producto' }} refs={['km1927', 'hethcote2000']}>
        <P
          en={<>This is the CAOS product archetype, built so that every part of a product is present and working on the first day: an offline pipeline that bakes cases, committed artifacts that the web replays, a live engine that re-runs a case in the browser, a workbench on the shared shell, five documentation pages, and a build that is measured before it is deployed. The domain is a placeholder: the classical SIR epidemic model <Cite id="km1927" />, small enough to read in one sitting and rich enough to exercise every lane.</>}
          es={<>Este es el arquetipo de producto CAOS, construido para que cada parte de un producto esté presente y funcionando desde el primer día: un pipeline fuera de línea que precalcula casos, artefactos comprometidos que la web reproduce, un motor en vivo que vuelve a correr un caso en el navegador, un banco de trabajo sobre el shell compartido, cinco páginas de documentación y una compilación que se mide antes de desplegarse. El dominio es un marcador: el modelo epidémico SIR clásico <Cite id="km1927" />, lo bastante pequeño para leerse de una vez y lo bastante rico para ejercitar cada carril.</>}
        />
        <P
          en={<>A product instantiated from this repository replaces the model, the cases and the content with its own, and keeps the structure: the contracts, the lanes, the workbench, the pages and the gates. The model itself is standard; Hethcote&apos;s review <Cite id="hethcote2000" /> covers it and its extensions.</>}
          es={<>Un producto instanciado desde este repositorio reemplaza el modelo, los casos y el contenido por los suyos, y conserva la estructura: los contratos, los carriles, el banco de trabajo, las páginas y las compuertas. El modelo en sí es estándar; la revisión de Hethcote <Cite id="hethcote2000" /> lo cubre junto con sus extensiones.</>}
        />
      </DocSection>
      <DocSection title={{ en: 'How to read the App', es: 'Cómo leer la App' }} noRefsReason={{ en: 'Describes this interface.', es: 'Describe esta interfaz.' }}>
        <P
          en="The App is one workbench. The rail on the left holds what you choose and what you read: the case, its variant, the parameters of the live engine, and the live values. The instrument on the right holds the views of the case, grouped by the question they answer."
          es="La App es un banco de trabajo. El panel de la izquierda contiene lo que se elige y lo que se lee: el caso, su variante, los parámetros del motor en vivo y los valores en vivo. El instrumento de la derecha contiene las vistas del caso, agrupadas por la pregunta que responden."
        />
        <L
          items={[
            { en: 'Dynamics: the three compartments over time, the live run solid and the committed replay dashed.', es: 'Dinámica: los tres compartimentos en el tiempo, la corrida en vivo continua y la reproducción comprometida segmentada.' },
            { en: 'Validation: the two engines compared on the baked case, and the run compared with the final-size relation.', es: 'Validación: los dos motores comparados en el caso precalculado, y la corrida comparada con la relación de tamaño final.' },
            { en: 'Compare immunisation: the case re-run with a share of the population immune from the start.', es: 'Comparar inmunización: el caso vuelto a correr con una fracción de la población inmune desde el inicio.' },
            { en: 'Context: the case, its parameters, the model and how to read each view.', es: 'Contexto: el caso, sus parámetros, el modelo y cómo leer cada vista.' },
          ]}
        />
        <P
          en="Every view carries two badges: its lane (live, computed in your browser; replay, read from a committed artifact; offline, computed by the pipeline and shown as is) and its data (synthetic, real or published). A view still showing an earlier selection says so while it recomputes. A case can be linked directly with ?case= followed by its identifier."
          es="Cada vista lleva dos insignias: su carril (en vivo, calculado en el navegador; reproducción, leído de un artefacto comprometido; fuera de línea, calculado por el pipeline y mostrado tal cual) y sus datos (sintéticos, reales o publicados). Una vista que todavía muestra una selección anterior lo indica mientras recalcula. Un caso se puede enlazar directamente con ?case= seguido de su identificador."
        />
      </DocSection>
      <DocSection title={{ en: 'The six pages', es: 'Las seis páginas' }} noRefsReason={{ en: 'Describes this site.', es: 'Describe este sitio.' }}>
        <L
          items={[
            { en: 'App: the workbench, the leftmost tab; the product opens on the Introduction.', es: 'App: el banco de trabajo, la primera pestaña; el producto abre en la Introducción.' },
            { en: 'Introduction: what the product is and how to read it (this page).', es: 'Introducción: qué es el producto y cómo leerlo (esta página).' },
            { en: 'Methodology: the model, its threshold, its final size and the numerical scheme, with their sources.', es: 'Metodología: el modelo, su umbral, su tamaño final y el esquema numérico, con sus fuentes.' },
            { en: 'Implementation: the pipeline, the contracts, the lanes, the web and the deploy.', es: 'Implementación: el pipeline, los contratos, los carriles, la web y el despliegue.' },
            { en: 'Experiments: every case, read from its artifacts, against the theory.', es: 'Experimentos: cada caso, leído desde sus artefactos, contra la teoría.' },
            { en: 'Benchmark: what each case costs, baked and live, against its budgets.', es: 'Benchmark: lo que cuesta cada caso, precalculado y en vivo, contra sus presupuestos.' },
          ]}
        />
      </DocSection>
      <DocSection title={{ en: 'Making a product from it', es: 'Hacer un producto a partir de él' }} noRefsReason={{ en: 'Describes this repository.', es: 'Describe este repositorio.' }}>
        <P
          en="A new product starts from this repository as a GitHub template. scripts/instantiate.py names it, picks its single deploy place (GitHub Pages or the VPS), sets its licence and visibility, removes the template sentinel and runs the pipeline, the tests and the build once. From then on the residue guard fails the build while any part of the example remains."
          es="Un producto nuevo parte de este repositorio como plantilla de GitHub. scripts/instantiate.py le da nombre, elige su único lugar de despliegue (GitHub Pages o el VPS), fija su licencia y su visibilidad, elimina el centinela de la plantilla y corre una vez el pipeline, las pruebas y la compilación. Desde entonces, la guarda de residuos hace fallar la compilación mientras quede alguna parte del ejemplo."
        />
      </DocSection>
    </>
  );
}
