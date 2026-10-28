// The methods of the example, one topic each (ADR-0017 section 2.1): the classical model and its relations, then the
// learned surrogate and how it is judged. Every topic is one `method` section with its paragraphs, two captioned
// equations, a figure, one honest callout and its references. A product replaces the methods and keeps the structure.
import { Callout, Cite, DocPage, DocSection, Equation, Figure, Tabs, useShellLang } from '@fasl-work/caos-app-shell';
import { P, useT } from '../content/bi';
import { FlowFigure } from '../content/figures';

function Model() {
  const t = useT();
  return (
    <DocSection title={{ en: 'The model and its threshold', es: 'El modelo y su umbral' }} area="method" kind="classical" refs={['km1927', 'hethcote2000', 'diekmann1990', 'vdd2002']}>
      <P
        en={<>A closed population of N people is split into the susceptible S, the infected I and the recovered R <Cite id="km1927" />. Contacts are homogeneous: each infected person infects susceptible people at a rate proportional to their share of the population, with contact rate β, and recovers at rate γ, so the infectious period is exponential with mean 1/γ <Cite id="hethcote2000" />.</>}
        es={<>Una población cerrada de N personas se divide en susceptibles S, contagiados I y recuperados R <Cite id="km1927" />. Los contactos son homogéneos: cada persona contagiada contagia a los susceptibles a una tasa proporcional a su fracción de la población, con tasa de contacto β, y se recupera a tasa γ, de modo que el período infeccioso es exponencial con media 1/γ <Cite id="hethcote2000" />.</>}
      />
      <Equation
        tex="\frac{dS}{dt} = -\beta \frac{S I}{N}, \qquad \frac{dI}{dt} = \beta \frac{S I}{N} - \gamma I, \qquad \frac{dR}{dt} = \gamma I"
        caption={t('The SIR system; S + I + R = N at every time.', 'El sistema SIR; S + I + R = N en todo instante.')}
      />
      <Figure caption={t('The three compartments and the two flows between them.', 'Los tres compartimentos y los dos flujos entre ellos.')}>
        <FlowFigure stages={[t('Susceptible S', 'Susceptibles S'), t('Infected I', 'Contagiados I'), t('Recovered R', 'Recuperados R')]} edges={['β', 'γ']} label={t('The SIR compartments', 'Los compartimentos SIR')} />
      </Figure>
      <P
        en="The assumptions are the limits of the example: no births or deaths, no waning immunity, no structure by age or place, and a deterministic population large enough for fractions to be meaningful. A product replaces this model with the one its research chose; the structure of the page stays."
        es="Los supuestos son los límites del ejemplo: sin nacimientos ni muertes, sin pérdida de inmunidad, sin estructura por edad o lugar, y una población determinista lo bastante grande para que las fracciones tengan sentido. Un producto reemplaza este modelo por el que eligió su investigación; la estructura de la página se mantiene."
      />
      <P
        en={<>The basic reproduction number R0 is the expected number of infections caused by one infected person in a fully susceptible population <Cite id="diekmann1990" />. For this model it is the contact rate times the mean infectious period. While the effective number R0 S/N stays above one, infections grow; the epidemic peaks when it crosses one <Cite id="vdd2002" />.</>}
        es={<>El número reproductivo básico R0 es el número esperado de contagios que causa una persona contagiada en una población totalmente susceptible <Cite id="diekmann1990" />. En este modelo es la tasa de contacto por el período infeccioso medio. Mientras el número efectivo R0 S/N se mantiene sobre uno, los contagios crecen; la epidemia alcanza su pico cuando cruza uno <Cite id="vdd2002" />.</>}
      />
      <Equation tex="R_0 = \frac{\beta}{\gamma}, \qquad R_t = R_0 \frac{S(t)}{N}, \qquad p_c = 1 - \frac{1}{R_0}" caption={t('The basic and effective reproduction numbers, and the share p_c that must be immune to prevent an outbreak.', 'Los números reproductivos básico y efectivo, y la fracción p_c que debe ser inmune para impedir un brote.')} />
      <P
        en="The immunisation variants of the App move a share v of the susceptible to R at the start. The outbreak is prevented when v exceeds p_c, which is why the 60% variant suppresses the fast-burn case only partly and the slow-spread case entirely."
        es="Las variantes de inmunización de la App mueven una fracción v de los susceptibles a R al inicio. El brote se impide cuando v supera p_c; por eso la variante de 60% suprime sólo en parte el caso de combustión rápida y por completo el de propagación lenta."
      />
      <Callout variant="honest" title={t('What this model is not', 'Lo que este modelo no es')}>
        {t('It is a textbook model with homogeneous mixing. It does not describe a real outbreak, a region or a hospital, and it is not a forecast.', 'Es un modelo de texto con mezcla homogénea. No describe un brote real, una región ni un hospital, y no es un pronóstico.')}
      </Callout>
    </DocSection>
  );
}

function FinalSize() {
  const t = useT();
  return (
    <DocSection title={{ en: 'The final size', es: 'El tamaño final' }} area="method" kind="classical" refs={['km1927', 'miller2012']}>
      <P
        en={<>Dividing the first equation by the third gives dS/dR = -R0 S/N, so S falls exponentially in R. When the epidemic ends, I is zero and R is N minus S, which closes the relation that fixes how many are ever infected <Cite id="km1927" />. Miller derives it, and its extensions, directly from this argument <Cite id="miller2012" />.</>}
        es={<>Al dividir la primera ecuación por la tercera se obtiene dS/dR = -R0 S/N, de modo que S decae exponencialmente en R. Cuando la epidemia termina, I es cero y R es N menos S, lo que cierra la relación que fija cuántos se contagian alguna vez <Cite id="km1927" />. Miller la deriva, junto con sus extensiones, directamente desde este argumento <Cite id="miller2012" />.</>}
      />
      <Equation tex="S_\infty = S_0 \, e^{-R_0 (N - S_\infty)/N} \quad \Longrightarrow \quad z = 1 - e^{-R_0 z} \;\; (S_0 \to N)" caption={t('The final-size relation; z is the share of the population ever infected.', 'La relación de tamaño final; z es la fracción de la población alguna vez contagiada.')} />
      <P
        en="It does not depend on the time course, only on R0, so it is an independent check of any engine: run long enough, the simulated attack rate must reach z. The Validation group of the App plots both. Where they part, either the horizon ended the run before the epidemic did, or R0 is so close to one that the epidemic is still burning."
        es="No depende de la trayectoria temporal, sólo de R0, así que es una verificación independiente de cualquier motor: con una corrida lo bastante larga, la tasa de ataque simulada debe llegar a z. El grupo Validación de la App grafica ambas. Donde se separan, o el horizonte terminó la corrida antes que la epidemia, o R0 está tan cerca de uno que la epidemia sigue activa."
      />
      <P
        en="The relation has no closed form, so the engine solves it numerically. It starts from z equal to one and applies Newton's method to the function z minus one plus e to the minus R0 z, stopping when a step changes z by less than a hundred-trillionth. For R0 at or below one the only solution is zero, and the function returns it directly."
        es="La relación no tiene forma cerrada, así que el motor la resuelve numéricamente. Parte de z igual a uno y aplica el método de Newton a la función z menos uno más e elevado a menos R0 z, y se detiene cuando un paso cambia z en menos de una cienbillonésima. Para R0 igual o menor que uno la única solución es cero, y la función la devuelve directamente."
      />
      <Equation tex="z_{k+1} = z_k - \frac{z_k - 1 + e^{-R_0 z_k}}{1 - R_0 e^{-R_0 z_k}}, \qquad z_0 = 1" caption={t('Newton iteration for the final size; it converges in a handful of steps for R0 above one.', 'Iteración de Newton para el tamaño final; converge en pocos pasos para R0 sobre uno.')} />
      <P
        en="The final size is also the quickest sanity check of a new case. Before reading any curve, compute z from the reproduction number and ask whether the case should end near it: the epidemic case should, the slow-spread case should not within its horizon, and the sub-critical case should stay at zero. A case that disagrees with all three has a wrong parameter, not a subtle effect."
        es="El tamaño final es también la verificación más rápida de un caso nuevo. Antes de mirar cualquier curva, calcule z a partir del número reproductivo y pregunte si el caso debería terminar cerca de él: el caso de epidemia debería, el de propagación lenta no dentro de su horizonte, y el subcrítico debería quedar en cero. Un caso que discrepa en los tres tiene un parámetro equivocado, no un efecto sutil."
      />
      <Figure caption={t('How the final size is checked against a run.', 'Cómo se verifica el tamaño final contra una corrida.')}>
        <FlowFigure stages={[t('R0 from the case', 'R0 del caso'), t('Solve for z', 'Resolver z'), t('Compare with the run', 'Comparar con la corrida')]} edges={['', '']} label={t('The final-size check', 'La verificación del tamaño final')} tone="good" />
      </Figure>
      <Callout variant="honest" title={t('Where the check stops', 'Dónde termina la verificación')}>
        {t('The relation holds for a closed, homogeneous population seeded by a vanishing infection. A run cut off by its horizon is expected to fall short of z, and the page says so.', 'La relación vale para una población cerrada y homogénea sembrada con una infección que tiende a cero. Una corrida cortada por su horizonte debe quedar bajo z, y la página lo dice.')}
      </Callout>
    </DocSection>
  );
}

function Numerics() {
  const t = useT();
  return (
    <DocSection title={{ en: 'The numerical scheme', es: 'El esquema numérico' }} area="method" kind="classical" refs={['hairer1993']}>
      <P
        en={<>Both engines integrate the system with the explicit Euler method at a step of a quarter of a day. It is first order: the global error shrinks in proportion to the step <Cite id="hairer1993" />. Each compartment is clamped at zero, which only acts when a large step would otherwise drive it negative.</>}
        es={<>Ambos motores integran el sistema con el método de Euler explícito a un paso de un cuarto de día. Es de primer orden: el error global disminuye en proporción al paso <Cite id="hairer1993" />. Cada compartimento se limita a cero, lo que sólo actúa cuando un paso grande lo llevaría a valores negativos.</>}
      />
      <Equation
        tex="\begin{aligned} S_{k+1} &= \max\!\left(0,\; S_k - \beta \tfrac{S_k I_k}{N} \Delta t\right) \\ I_{k+1} &= \max\!\left(0,\; I_k + \beta \tfrac{S_k I_k}{N} \Delta t - \gamma I_k \Delta t\right) \\ R_{k+1} &= R_k + \gamma I_k \Delta t \end{aligned}"
        caption={t('One step of the scheme, with Δt = 0.25 days; the Python and TypeScript engines perform the same operations in the same order.', 'Un paso del esquema, con Δt = 0,25 días; los motores en Python y en TypeScript hacen las mismas operaciones en el mismo orden.')}
      />
      <P
        en="Both engines perform the same floating-point operations in the same order. The committed trace rounds values to two decimals, and the parity test holds the live engine to that rounding on every baked case. A first-order scheme is enough for an example; a product picks its integrator from its own error budget."
        es="Ambos motores hacen las mismas operaciones de punto flotante en el mismo orden. La traza comprometida redondea a dos decimales, y la prueba de paridad exige al motor en vivo ese redondeo en cada caso precalculado. Un esquema de primer orden basta para un ejemplo; un producto elige su integrador según su propio presupuesto de error."
      />
      <P
        en="A first-order method is checked by halving the step: the error should halve with it. The convergence test runs a long epidemic at steps of a quarter, an eighth and a sixteenth of a day, and requires the gap between the simulated attack rate and the final size to fall by about half at each halving. It would fail if a step size were hard-coded or the clamp acted where it should not."
        es="Un método de primer orden se verifica reduciendo el paso a la mitad: el error debe reducirse también a la mitad. La prueba de convergencia corre una epidemia larga con pasos de un cuarto, un octavo y un dieciseisavo de día, y exige que la brecha entre la tasa de ataque simulada y el tamaño final caiga cerca de la mitad en cada reducción. Fallaría si un tamaño de paso estuviera fijo en el código o el límite en cero actuara donde no debe."
      />
      <Equation tex="\left| a_{\Delta t} - z \right| \le C \, \Delta t" caption={t('First-order global error: the gap between the simulated attack rate and the final size z is proportional to the step; the constant C depends on the case.', 'Error global de primer orden: la brecha entre la tasa de ataque simulada y el tamaño final z es proporcional al paso; la constante C depende del caso.')} />
      <P
        en="The step of a quarter of a day is a constant shared by both engines and by the trace, not a setting the reader can change. With that step the fastest case, whose peak comes in under ten days, has dozens of steps on its rise, while a whole run of 160 days takes 640 steps and, measured on the development workstation, runs in about ten microseconds."
        es="El paso de un cuarto de día es una constante compartida por ambos motores y por la traza, no un ajuste que el lector pueda cambiar. Con ese paso el caso más rápido, cuyo pico llega en menos de diez días, tiene decenas de pasos en su subida, mientras que una corrida completa de 160 días toma 640 pasos y, medida en la estación de desarrollo, corre en unos diez microsegundos."
      />
      <Figure caption={t('One step of the scheme, repeated until the horizon.', 'Un paso del esquema, repetido hasta el horizonte.')}>
        <FlowFigure stages={[t('Read S, I, R', 'Leer S, I, R'), t('New infections and recoveries', 'Nuevos contagios y recuperaciones'), t('Clamp at zero', 'Limitar en cero'), t('Store the step', 'Guardar el paso')]} label={t('One Euler step', 'Un paso de Euler')} />
      </Figure>
      <Callout variant="honest" title={t('Exact and approximate', 'Exacto y aproximado')}>
        {t('The two engines agree to the rounding of the trace; both approximate the true solution with a first-order error that the convergence test measures.', 'Los dos motores coinciden hasta el redondeo de la traza; ambos aproximan la solución verdadera con un error de primer orden que la prueba de convergencia mide.')}
      </Callout>
    </DocSection>
  );
}

function Baseline() {
  const t = useT();
  return (
    <DocSection title={{ en: 'The analytic peak', es: 'El pico analítico' }} area="method" kind="classical" refs={['km1927', 'hethcote2000']}>
      <P
        en={<>The classical baseline of the surrogate needs no training. The model has a first integral: the sum of S and I minus the logarithm of S divided by R0 stays constant along every run <Cite id="hethcote2000" />. Starting from a nearly fully susceptible population with a vanishing infection, the constant fixes the whole path in the plane of S against I.</>}
        es={<>La línea base clásica del sustituto no necesita entrenamiento. El modelo tiene una integral primera: la suma de S e I menos el logaritmo de S dividido por R0 permanece constante en toda corrida <Cite id="hethcote2000" />. Partiendo de una población casi totalmente susceptible con una infección que tiende a cero, la constante fija toda la trayectoria en el plano de S contra I.</>}
      />
      <Equation tex="S + I - \frac{1}{R_0} \ln S = \text{const}" caption={t('The first integral of the SIR system, with S and I as shares of the population.', 'La integral primera del sistema SIR, con S e I como fracciones de la población.')} />
      <P
        en={<>The infected share peaks where its derivative is zero, which is where S equals one over R0. Substituting that value into the first integral gives the peak share in closed form <Cite id="km1927" />. It is the exact answer for a vanishing initial infection, and it is zero when R0 is at or below one, because then no outbreak starts.</>}
        es={<>La fracción de contagiados alcanza su pico donde su derivada es cero, que es donde S es igual a uno sobre R0. Al sustituir ese valor en la integral primera se obtiene la fracción del pico en forma cerrada <Cite id="km1927" />. Es la respuesta exacta para una infección inicial que tiende a cero, y es cero cuando R0 es igual o menor que uno, porque entonces no empieza un brote.</>}
      />
      <Equation tex="\frac{I_{\max}}{N} = 1 - \frac{1 + \ln R_0}{R_0} \quad (R_0 > 1), \qquad 0 \quad (R_0 \le 1)" caption={t('The peak infected share as a function of R0 alone.', 'La fracción de contagiados en el pico como función sólo de R0.')} />
      <P
        en="The formula is exact only in the limit of a vanishing initial infection, so its error against the engine is a property of the example and not something to assume. The Benchmark page computes both in the reader's browser over a range of reproduction numbers and plots them together, which is how the departure is seen."
        es="La fórmula es exacta sólo en el límite de una infección inicial que tiende a cero, así que su error frente al motor es una propiedad del ejemplo y no algo que suponer. La página Benchmark calcula ambos en el navegador del lector para un rango de números reproductivos y los grafica juntos, que es como se ve la separación."
      />
      <Figure caption={t('From the reproduction number to the peak share, with no simulation.', 'Del número reproductivo a la fracción del pico, sin simulación.')}>
        <FlowFigure stages={[t('R0 = β / γ', 'R0 = β / γ'), t('First integral', 'Integral primera'), t('S = 1 / R0 at the peak', 'S = 1 / R0 en el pico'), t('Peak share', 'Fracción del pico')]} label={t('The analytic peak', 'El pico analítico')} />
      </Figure>
      <P
        en="The baseline answers whenever no valid trained bundle is released, behind the same contract as the learned surrogate, so the site never shows an empty model slot. It also sets the bar: a learned model earns its place only if its held-out error is below this formula's error against the engine."
        es="La línea base responde siempre que no haya un paquete entrenado válido liberado, tras el mismo contrato que el sustituto aprendido, de modo que el sitio nunca muestra una ranura de modelo vacía. También fija el listón: un modelo aprendido se gana su lugar sólo si su error reservado es menor que el error de esta fórmula contra el motor."
      />
      <Callout variant="honest" title={t('Where it departs from the engine', 'Dónde se aparta del motor')}>
        {t('The formula assumes a vanishing initial infection and exact time. The engine starts from a real group of infected people and a quarter-day step, so the two differ, and the difference grows with the reproduction number.', 'La fórmula supone una infección inicial que tiende a cero y tiempo exacto. El motor parte de un grupo real de personas contagiadas y un paso de un cuarto de día, por lo que difieren, y la diferencia crece con el número reproductivo.')}
      </Callout>
    </DocSection>
  );
}

function Surrogate() {
  const t = useT();
  return (
    <DocSection title={{ en: 'The learned surrogate', es: 'El sustituto aprendido' }} area="method" kind="learned" refs={['hethcote2000', 'km1927']}>
      <P
        en={<>The learned model is a small surrogate that maps the basic reproduction number to the peak infected share without running the engine. The target is the quantity the analytic formula gives for a vanishing infection <Cite id="km1927" />; the surrogate learns it from engine runs, so it carries the real starting infection and the step of the scheme as well.</>}
        es={<>El modelo aprendido es un sustituto pequeño que asocia el número reproductivo básico con la fracción de contagiados en el pico sin correr el motor. El objetivo es la cantidad que da la fórmula analítica para una infección que tiende a cero <Cite id="km1927" />; el sustituto la aprende de corridas del motor, así que incorpora también la infección inicial real y el paso del esquema.</>}
      />
      <Equation tex="\hat{y}(R_0) = c_0 + c_1 R_0 + c_2 \ln R_0 + \frac{c_3}{R_0}" caption={t('The surrogate: a linear combination of four fixed functions of R0, clamped to the range 0 to 1.', 'El sustituto: una combinación lineal de cuatro funciones fijas de R0, limitada al rango de 0 a 1.')} />
      <P
        en={<>The four functions are not arbitrary. The analytic peak contains a logarithm of R0 and a term in one over R0 <Cite id="hethcote2000" />, so a constant, R0 itself, its logarithm and its inverse give the fit room to follow that shape and to absorb what the formula leaves out. Because the model is linear in its coefficients, the best fit is a direct least-squares solution, not an iterative search.</>}
        es={<>Las cuatro funciones no son arbitrarias. El pico analítico contiene un logaritmo de R0 y un término en uno sobre R0 <Cite id="hethcote2000" />, así que una constante, R0 mismo, su logaritmo y su inverso dan al ajuste espacio para seguir esa forma y para absorber lo que la fórmula deja fuera. Como el modelo es lineal en sus coeficientes, el mejor ajuste es una solución directa de mínimos cuadrados, no una búsqueda iterativa.</>}
      />
      <Equation tex="\mathbf{c} = \arg\min_{\mathbf{c}} \sum_{i} \left( \mathbf{x}_i^{\top} \mathbf{c} - y_i \right)^2, \qquad \mathbf{x}_i = \left(1,\, R_{0,i},\, \ln R_{0,i},\, 1 / R_{0,i}\right)" caption={t('Ordinary least squares over the training cases; y is the peak share the engine produced for each.', 'Mínimos cuadrados ordinarios sobre los casos de entrenamiento; y es la fracción del pico que produjo el motor en cada uno.')} />
      <P
        en="The training set is the cases of the registry that start with an infection, four of them: the sub-critical, the epidemic, the fast-burn and the slow-spread case. The control with no initial infection is left out because its peak is zero for a reason the surrogate cannot see in R0. The four coefficients are written to a small file, the released bundle."
        es="El conjunto de entrenamiento son los casos del registro que parten con una infección, cuatro: el subcrítico, la epidemia, la combustión rápida y la propagación lenta. El control sin infección inicial se deja fuera porque su pico es cero por una razón que el sustituto no puede ver en R0. Los cuatro coeficientes se escriben en un archivo pequeño, el paquete liberado."
      />
      <P
        en="A bundle is used only if it is valid: the declared kind, exactly the four basis functions in order and four finite numbers. Otherwise the analytic baseline answers and the manifest records which model did. The bundle is a few hundred bytes, so the live lane could carry it, and the contract that describes it is the same for a trained network a product might release instead."
        es="Un paquete se usa sólo si es válido: el tipo declarado, exactamente las cuatro funciones base en orden y cuatro números finitos. De lo contrario responde la línea base analítica y el manifiesto registra qué modelo respondió. El paquete pesa unos cientos de bytes, así que el carril en vivo podría llevarlo, y el contrato que lo describe es el mismo para una red entrenada que un producto liberara en su lugar."
      />
      <Figure caption={t('From engine runs to a released bundle, with the baseline as the fallback.', 'De las corridas del motor a un paquete liberado, con la línea base como respaldo.')}>
        <FlowFigure stages={[t('Four training runs', 'Cuatro corridas'), t('Least squares', 'Mínimos cuadrados'), t('Released bundle', 'Paquete liberado'), t('Baseline if invalid', 'Línea base si no es válido')]} label={t('Training the surrogate', 'Entrenamiento del sustituto')} tone="warn" />
      </Figure>
      <Callout variant="honest" title={t('A teaching model', 'Un modelo de enseñanza')}>
        {t('Four training points fit four coefficients: the surrogate is a demonstration of where a learned model sits in the pipeline, not evidence that learning beats the formula for this problem.', 'Cuatro puntos de entrenamiento ajustan cuatro coeficientes: el sustituto demuestra dónde se ubica un modelo aprendido en el pipeline, no prueba que aprender supere a la fórmula en este problema.')}
      </Callout>
    </DocSection>
  );
}

function HeldOut() {
  const t = useT();
  return (
    <DocSection title={{ en: 'Judging the learned model', es: 'Juzgar el modelo aprendido' }} area="method" kind="learned" refs={['km1927', 'hethcote2000']}>
      <P
        en="A learned model is judged on cases it never saw. The evaluation stage draws twenty parameter sets from a generator whose seed is the bake seed plus a fixed offset, so the draw is repeatable and disjoint from the training cases. The contact rate and the recovery rate are drawn uniformly over ranges that cover the sub-critical to the fast-burn regimes."
        es="Un modelo aprendido se juzga en casos que nunca vio. La etapa de evaluación sortea veinte conjuntos de parámetros con un generador cuya semilla es la semilla del precálculo más un desplazamiento fijo, de modo que el sorteo es repetible y disjunto de los casos de entrenamiento. La tasa de contacto y la de recuperación se sortean uniformemente en rangos que cubren desde los regímenes subcríticos hasta la combustión rápida."
      />
      <Equation tex="\mathrm{RMSE} = \sqrt{\frac{1}{n} \sum_{j=1}^{n} \left( \hat{y}_j - y_j \right)^2}" caption={t('Root-mean-square error of the peak share over the n held-out sets; y is the engine result, the truth of the example.', 'Error cuadrático medio de la fracción del pico sobre los n conjuntos reservados; y es el resultado del motor, la verdad del ejemplo.')} />
      <P
        en="The error measure is the root-mean-square error and not a percentage error. Sub-critical draws have a peak share near zero, where a percentage error divides by almost nothing and explodes, which would make a good model look bad. The coefficient of determination is reported beside it, to say how much of the spread of the peak share the model explains."
        es="La medida de error es el error cuadrático medio y no un error porcentual. Los sorteos subcríticos tienen una fracción del pico cercana a cero, donde un error porcentual divide por casi nada y se dispara, lo que haría ver mal a un buen modelo. El coeficiente de determinación se informa a su lado, para decir cuánta de la dispersión de la fracción del pico explica el modelo."
      />
      <Equation tex="R^2 = 1 - \frac{\sum_j (\hat{y}_j - y_j)^2}{\sum_j (y_j - \bar{y})^2}" caption={t('Coefficient of determination on the held-out sets; one is a perfect fit and zero is no better than the mean.', 'Coeficiente de determinación en los conjuntos reservados; uno es un ajuste perfecto y cero no es mejor que el promedio.')} />
      <P
        en={<>When no trained bundle exists, the same stage evaluates the analytic baseline <Cite id="hethcote2000" /> on the same draw, so the two are comparable by construction. The metrics are written into every manifest beside the name of the model that produced them, and the Benchmark page reads them from there instead of repeating a number typed by hand.</>}
        es={<>Cuando no existe un paquete entrenado, la misma etapa evalúa la línea base analítica <Cite id="hethcote2000" /> sobre el mismo sorteo, de modo que ambos son comparables por construcción. Las métricas se escriben en cada manifiesto junto al nombre del modelo que las produjo, y la página Benchmark las lee de allí en lugar de repetir una cifra escrita a mano.</>}
      />
      <P
        en="Reading the result takes three steps: check that the model answering is the released bundle and not the baseline, read the error against the spread of the peak share it is trying to predict, and compare it with the baseline's error on the same draw. A small error beside a tiny spread, or no better than the baseline, is not a success."
        es="Leer el resultado toma tres pasos: comprobar que el modelo que responde es el paquete liberado y no la línea base, leer el error frente a la dispersión de la fracción del pico que intenta predecir, y compararlo con el error de la línea base en el mismo sorteo. Un error pequeño junto a una dispersión diminuta, o no mejor que la línea base, no es un éxito."
      />
      <Figure caption={t('The held-out protocol, from the seed to the manifest.', 'El protocolo con datos reservados, de la semilla al manifiesto.')}>
        <FlowFigure stages={[t('Seed plus offset', 'Semilla más desplazamiento'), t('Twenty new sets', 'Veinte conjuntos nuevos'), t('Engine and model', 'Motor y modelo'), t('Metrics in the manifest', 'Métricas en el manifiesto')]} label={t('The held-out evaluation', 'La evaluación con datos reservados')} tone="warn" />
      </Figure>
      <Callout variant="honest" title={t('What twenty sets can show', 'Qué pueden mostrar veinte conjuntos')}>
        {t('Twenty draws from synthetic ranges give a rough error, not a guarantee. The truth is the example engine, so the error says how well one model imitates another, not how well either matches an outbreak.', 'Veinte sorteos de rangos sintéticos dan un error aproximado, no una garantía. La verdad es el motor del ejemplo, así que el error dice cuán bien un modelo imita a otro, no cuán bien alguno coincide con un brote.')}
      </Callout>
    </DocSection>
  );
}

export function Methodology() {
  const lang = useShellLang();
  const t = useT();
  return (
    <DocPage
      title={{ en: 'Methodology', es: 'Metodología' }}
      lede={t(
        'The methods behind the example, one per tab: the classical model and its threshold, the final-size relation, the numerical scheme and the analytic peak, then the learned surrogate and the held-out evaluation that judges it against that baseline.',
        'Los métodos detrás del ejemplo, uno por pestaña: el modelo clásico y su umbral, la relación de tamaño final, el esquema numérico y el pico analítico, y luego el sustituto aprendido y la evaluación con datos reservados que lo juzga frente a esa línea base.',
      )}
    >
      <Tabs
        ariaLabel={lang === 'es' ? 'Métodos' : 'Methods'}
        tabs={[
          { id: 'model', label: t('Model and threshold', 'Modelo y umbral'), content: <Model /> },
          { id: 'final-size', label: t('Final size', 'Tamaño final'), content: <FinalSize /> },
          { id: 'numerics', label: t('Numerical scheme', 'Esquema numérico'), content: <Numerics /> },
          { id: 'baseline', label: t('Analytic peak', 'Pico analítico'), content: <Baseline /> },
          { id: 'surrogate', label: t('Learned surrogate', 'Sustituto aprendido'), content: <Surrogate /> },
          { id: 'held-out', label: t('Held-out evaluation', 'Evaluación reservada'), content: <HeldOut /> },
        ]}
      />
    </DocPage>
  );
}
