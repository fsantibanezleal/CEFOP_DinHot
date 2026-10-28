// The second group of the Implementation page, "What runs where?": the lanes and the lane gate (area `lanes`), the Python engine and its
// method interface, the live engine in the Web Worker, and the WebGPU backend (area `engine`, three topics). Sources: the code
// (data-pipeline/pipeline/core/gate.py, core/trace.py, model/holo/core/forward.py, model/holo/core/types.py, model/holo/methods/__init__.py,
// baseline/_gs.py, baseline/m07_phase_fixed_wgs.py; frontend/src/engine/holo/{client,runner,engine,fft,forward}.ts, gpu/{index,wgs}.ts;
// frontend/src/workbench/run.ts), the SDD sections "Lanes" and "Technology and versions", and the T1 fragment changes/t1.md for the
// measurements, each with the conditions it was taken under. The numbers of the live lane are ranges from one laptop, not portable claims.
import { Callout, Cite, DocSection, Equation, Figure } from '@fasl-work/caos-app-shell';
import { L, P, useT } from '../bi';
import { LanesFigure } from './figures';

const THIS_REPO = { en: 'Describes this repository.', es: 'Describe este repositorio.' };

export function LanesTopic() {
  const t = useT();
  return (
    <DocSection title={{ en: 'The lanes and the lane gate', es: 'Los carriles y la compuerta de carril' }} area="lanes" noRefsReason={THIS_REPO}>
      <P
        en="A case is computed in one of three places. Offline, on a workstation, the pipeline bakes every case and never runs in CI or in the browser. For replay, the committed documents are copied into the site and fetched as JSON with the version in the address. Live, a TypeScript port of the engine re-runs a method in the browser with the reader's values. The workbench labels each result with the lane that produced it, so a replayed number is never read as a live one."
        es="Un caso se calcula en uno de tres lugares. Fuera de línea, en una estación de trabajo, el pipeline precalcula cada caso y nunca corre en CI ni en el navegador. Para la reproducción, los documentos versionados se copian al sitio y se piden como JSON con la versión en la dirección. En vivo, una versión del motor en TypeScript vuelve a ejecutar un método en el navegador con los valores del lector. La mesa de trabajo rotula cada resultado con el carril que lo produjo, de modo que un número reproducido nunca se lee como uno en vivo."
      />
      <Figure caption={t('The three lanes and what each holds; the dashed arrow is the fallback of the optional WebGPU path to the CPU path.', 'Los tres carriles y lo que contiene cada uno; la flecha punteada es el recurso de la vía opcional WebGPU hacia la vía CPU.')}>
        <LanesFigure />
      </Figure>
      <P
        en="What admits a case to the live lane is decided by a gate in the pipeline, not by hand. The unit of judgement is the case's reference method: the case is live when that method's specification says live or both, its engine is pure Python with wheels inside an allowed set (numpy only), one warm run at the case's own grid and budget takes at most 1500 ms, and the trace is at most 256 KiB. Otherwise the case is precompute and the web only replays it. Each method also gets a lane of its own, live only if its specification allows it and its run fits, else baked."
        es="Lo que admite un caso en el carril en vivo lo decide una compuerta del pipeline, no una persona. La unidad de juicio es el método de referencia del caso: el caso es en vivo cuando la especificación de ese método dice live o both, su motor es Python puro con paquetes dentro de un conjunto permitido (sólo numpy), una corrida en caliente con la grilla y el presupuesto del caso toma a lo más 1500 ms, y la traza pesa a lo más 256 KiB. En otro caso el caso es de precálculo y la web sólo lo reproduce. Cada método recibe además un carril propio, en vivo sólo si su especificación lo permite y su corrida cabe, y si no, precalculado."
      />
      <P
        en="The cost the gate judges is the median of three runs after a warm-up, because timing the whole case once, validation and cold start included, once made the verdict depend on which case was baked first. The verdict and the deterministic budgets go into the manifest and the measured milliseconds do not, so a manifest stays a pure function of its parameters and seed. A trace over its byte budget is squeezed in five fixed steps (fewer decimals, a shorter history, a smaller focal crop, no axial cut) and the step used is recorded as a flag; one that still does not fit fails the bake."
        es="El costo que juzga la compuerta es la mediana de tres corridas tras un calentamiento, porque medir una sola vez el caso completo, con la validación y el arranque en frío incluidos, hizo una vez que el veredicto dependiera de qué caso se precalculaba primero. El veredicto y los presupuestos deterministas van al manifiesto y los milisegundos medidos no, de modo que un manifiesto sigue siendo una función pura de sus parámetros y su semilla. Una traza que excede su presupuesto de bytes se comprime en cinco pasos fijos (menos decimales, un historial más corto, un recorte focal menor, sin corte axial) y el paso usado se registra como una marca; la que aun así no cabe hace fallar el precálculo."
      />
      <L
        items={[
          {
            en: 'Live: 15 methods, those whose specification says live or both (M01 to M08, M10, M11, M12, M14, M15, M16, M19). Any other id raises NotLive and the view shows the replay: there is no silent fallback to another method.',
            es: 'En vivo: 15 métodos, los que su especificación declara live o both (M01 a M08, M10, M11, M12, M14, M15, M16, M19). Cualquier otro id levanta NotLive y la vista muestra la reproducción: no hay recurso silencioso a otro método.',
          },
          {
            en: 'Baked and replayed: M09, M13, M18, B1, B2, B4 and B5, and the learned slots M17 and B3 (their inference runs in the browser, described under Models and slots).',
            es: 'Precalculados y reproducidos: M09, M13, M18, B1, B2, B4 y B5, y los espacios aprendidos M17 y B3 (su inferencia corre en el navegador, descrita en Modelos y espacios).',
          },
          {
            en: 'The trace carries the phase mask and the focal map of the reference method only. For another method the maps stay the reference\'s and the card says so; its metrics, history and per-trap intensities are its own.',
            es: 'La traza lleva la máscara de fase y el mapa focal del método de referencia únicamente. Para otro método los mapas siguen siendo los de la referencia y la ficha lo dice; sus métricas, historial e intensidades por trampa son propias.',
          },
        ]}
      />
      <Callout variant="honest" title={t('The gate measures a proxy', 'La compuerta mide un sustituto')}>
        {t(
          'The 1500 ms of the gate is measured on the Python engine as a proxy for the TypeScript port; the browser is timed separately, by the web gate and by the Benchmark page. In the live-lane measurements of this build (Chromium 153 driven by Playwright, an i9-14900HX laptop, 30 iterations of M07 on the 256 x 256 padded-2 grid, a warm run in the worker, CPU path, scoring included) the 100-trap case C02 took 0.49 to 0.80 s, inside the budget, and the 1024-trap case C03 took 2.4 to 4.3 s, outside it. The ranges depend on the browser mode and the machine load.',
          'Los 1500 ms de la compuerta se miden sobre el motor en Python como sustituto de la versión en TypeScript; el navegador se mide aparte, con la compuerta web y con la página Benchmark. En las mediciones del carril en vivo de esta versión (Chromium 153 manejado con Playwright, un portátil i9-14900HX, 30 iteraciones de M07 sobre la grilla de 256 x 256 con relleno 2, una corrida en caliente en el worker, vía CPU, con el cálculo de métricas incluido) el caso C02 de 100 trampas tomó de 0,49 a 0,80 s, dentro del presupuesto, y el caso C03 de 1024 trampas tomó de 2,4 a 4,3 s, fuera de él. Los rangos dependen del modo del navegador y de la carga de la máquina.',
        )}
      </Callout>
    </DocSection>
  );
}

export function PythonEngineTopic() {
  const t = useT();
  return (
    <DocSection title={{ en: 'The Python engine and the method interface', es: 'El motor en Python y la interfaz de métodos' }} area="engine" refs={['dileonardo2007', 'kim2019']}>
      <P
        en={<>The canonical engine is numpy only, in data-pipeline/pipeline/model/holo/core/: the optical geometry, the trap sets, the two forward models, the metrics, the device model, Zernike modes, the camera emulation, the trap physics, the particle dynamics and a portable random generator. A method is a module with a SPEC (id, name, family, lane, target kinds, dimensions) and a run function that takes the setup, the target, the device, a budget, a seeded generator and an optional starting hologram. A registry scans the baseline, control, optimization and beyond packages at start and refuses a module without run, a duplicate id or a broken import. It lists 22 methods; the Methodology page explains what each does.</>}
        es={<>El motor canónico usa sólo numpy, en data-pipeline/pipeline/model/holo/core/: la geometría óptica, los conjuntos de trampas, los dos modelos directos, las métricas, el modelo del dispositivo, los modos de Zernike, la emulación de la cámara, la física de la trampa, la dinámica de la partícula y un generador aleatorio portable. Un método es un módulo con una SPEC (id, nombre, familia, carril, tipos de objetivo, dimensiones) y una función run que recibe el montaje, el objetivo, el dispositivo, un presupuesto, un generador con semilla y un holograma inicial opcional. Un registro recorre los paquetes de base, control, optimización y más allá al iniciar, y rechaza un módulo sin run, un id duplicado o una importación rota. Lista 22 métodos; la página de Metodología explica qué hace cada uno.</>}
      />
      <Equation
        tex="V_m=\frac{1}{N_{\mathrm{pix}}}\sum_{j} A_j\, e^{\,i(\phi_j-\Delta_j^m)},\qquad V_m = E[\mathrm{bin}_m]\,\frac{n_{\mathrm{pad}}}{n_{\mathrm{pix}}}\ \text{for a trap on a bin with } z_m=0,\ \ell_m=0"
        caption={t('The two forward models agree: the point-trap sum over the N_pix = n_pix² SLM pixels j, with input amplitude A_j, displayed phase φ_j and the delay Δ_j^m of trap m (lens, grating and vortex), and the read-out of the orthonormal zero-padded FFT E at the trap bin, scaled by n_pad / n_pix. The tests compare them to 1e-9 relative on grids from 32 to 512 pixels.', 'Los dos modelos directos coinciden: la suma de trampa puntual sobre los N_pix = n_pix² píxeles j del SLM, con amplitud de entrada A_j, fase mostrada φ_j y el retardo Δ_j^m de la trampa m (lente, rejilla y vórtice), y la lectura de la FFT ortonormal con relleno de ceros E en el bin de la trampa, escalada por n_pad / n_pix. Las pruebas los comparan a 1e-9 relativo en grillas de 32 a 512 píxeles.')}
      />
      <P
        en={<>The Gerchberg-Saxton family shares one iteration: map the trap fields of the current hologram to focal coefficients by the rule of the method, back-project them to the SLM and keep the phase. In the weighted form <Cite id="dileonardo2007" /> the weight of a trap is rescaled each iteration by the mean field over its own field, and in the phase-fixed form <Cite id="kim2019" /> the focal phase follows the field for the first n_fix iterations, 12 by default, and is then frozen. The point form and the FFT form are the same linear map for traps on bins, so they give the same hologram to rounding.</>}
        es={<>La familia de Gerchberg-Saxton comparte una iteración: llevar los campos de las trampas del holograma actual a coeficientes focales según la regla del método, retroproyectarlos al SLM y conservar la fase. En la forma ponderada <Cite id="dileonardo2007" /> el peso de una trampa se reescala en cada iteración por el cociente entre el campo medio y su propio campo, y en la forma de fase fija <Cite id="kim2019" /> la fase focal sigue al campo durante las primeras n_fix iteraciones, 12 por defecto, y luego se congela. La forma puntual y la forma FFT son el mismo mapa lineal para trampas en bins, así que dan el mismo holograma hasta el redondeo.</>}
      />
      <Equation
        tex="g_i(m)=\frac{\langle B_i\rangle}{B_i(m)}\,g_{i-1}(m),\ \ g_0=1;\qquad \psi_i=\arg V_m\ \ (i<n_{\mathrm{fix}}),\quad \psi_i=\psi_{n_{\mathrm{fix}}}\ \ (i\ge n_{\mathrm{fix}})"
        caption={t('The weight update and the phase freeze of M07 (phase-fixed weighted GS): B_i(m) is the focal amplitude at trap m in iteration i, normalised by the target amplitude, ⟨B_i⟩ its mean over the traps, g_i(m) the trap weight and ψ_i the focal phase imposed in the iteration.', 'La actualización de pesos y el congelamiento de fase de M07 (GS ponderado de fase fija): B_i(m) es la amplitud focal en la trampa m en la iteración i, normalizada por la amplitud objetivo, ⟨B_i⟩ su promedio sobre las trampas, g_i(m) el peso de la trampa y ψ_i la fase focal impuesta en la iteración.')}
      />
      <Callout variant="note" title={t('Where it works and where it fails', 'Dónde funciona y dónde falla')}>
        {t(
          'The FFT form needs traps on FFT bins with z = 0 and no vortex, and raises an error otherwise; the point form has no such limit and costs one pass over the SLM per trap column. M07 defaults to the FFT form, so running it through the Python registry on the off-bin case C02 returns that error today (checked by running the inference stage of the bake on the branch); the TypeScript client selects the point form when the traps are off the bins and says so. Whether the bake should do the same or snap the traps is an open decision recorded in changes/t1.md. The scalar model also carries a validity flag above a numerical aperture of 0.7.',
          'La forma FFT necesita trampas en bins de la FFT con z = 0 y sin vórtice, y levanta un error en otro caso; la forma puntual no tiene ese límite y cuesta una pasada sobre el SLM por columna de trampas. M07 usa por defecto la forma FFT, así que ejecutarlo por el registro de Python sobre el caso C02, con trampas fuera de los bins, devuelve hoy ese error (comprobado al correr la etapa de inferencia del precálculo en la rama); el cliente en TypeScript elige la forma puntual cuando las trampas están fuera de los bins y lo informa. Si el precálculo debe hacer lo mismo o ajustar las trampas a los bins es una decisión abierta registrada en changes/t1.md. El modelo escalar lleva además una marca de validez por encima de una apertura numérica de 0,7.',
        )}
      </Callout>
    </DocSection>
  );
}

export function LiveEngineTopic() {
  const t = useT();
  return (
    <DocSection title={{ en: 'The live engine in a Web Worker', es: 'El motor en vivo en un Web Worker' }} area="engine" refs={['fftjs']}>
      <P
        en={<>The live engine is a TypeScript port of the physics core and of the 15 live methods, in frontend/src/engine/holo/, and each module names the Python module it follows. It runs in a dedicated Web Worker so the interface never blocks; the client, createEngineClient, owns the worker and turns its messages into promises. The transforms use fft.js <Cite id="fftjs" /> in float64, with Bluestein for lengths that are not powers of two such as the crosstalk grid, and the random numbers come from the same xoshiro128** generator as Python, bit for bit.</>}
        es={<>El motor en vivo es una versión en TypeScript del núcleo de física y de los 15 métodos en vivo, en frontend/src/engine/holo/, y cada módulo nombra el módulo de Python que sigue. Corre en un Web Worker dedicado para que la interfaz nunca se bloquee; el cliente, createEngineClient, es dueño del worker y convierte sus mensajes en promesas. Las transformadas usan fft.js <Cite id="fftjs" /> en float64, con Bluestein para los largos que no son potencias de dos, como la grilla de diafonía, y los números aleatorios vienen del mismo generador xoshiro128** que en Python, bit a bit.</>}
      />
      <P
        en="A run is a generator that the worker steps one iteration at a time, yielding to the event loop after each one through a message channel, which has no timer clamp. A cancel message is therefore acted on within one iteration, and a new run cancels the previous one, which rejects with an AbortError. Progress is posted at most 30 times per second, the result transfers its buffers instead of copying them, and the metrics are always scored from the final phase, never from the method's own history. The workbench starts a run 200 ms after the last change of a control and replaces the replay maps only when the run finishes."
        es="Una corrida es un generador que el worker avanza una iteración a la vez, cediendo el control al bucle de eventos tras cada una a través de un canal de mensajes, que no tiene el mínimo de los temporizadores. Un mensaje de cancelación se atiende por tanto dentro de una iteración, y una corrida nueva cancela la anterior, que se rechaza con un AbortError. El progreso se publica a lo más 30 veces por segundo, el resultado transfiere sus búferes en lugar de copiarlos, y las métricas se calculan siempre desde la fase final, nunca desde el historial del propio método. La mesa de trabajo inicia una corrida 200 ms después del último cambio de un control y reemplaza los mapas de reproducción sólo cuando la corrida termina."
      />
      <Equation
        tex="t_{\mathrm{run}} = t_{\mathrm{method}} + t_{\mathrm{score}},\qquad t_{\mathrm{cancel}} \le t_{\mathrm{iter}},\qquad \Delta t_{\mathrm{progress}} \ge \tfrac{1000}{30}\ \mathrm{ms}"
        caption={t('The timing contract of a live run: the reported run time is the method time (yields included) plus the scoring of the final phase; a cancel takes effect within one iteration t_iter; and progress messages are at least 1000/30 ms apart.', 'El contrato de tiempos de una corrida en vivo: el tiempo informado es el del método (con las cesiones incluidas) más el cálculo de métricas de la fase final; una cancelación surte efecto dentro de una iteración t_iter; y los mensajes de progreso distan al menos 1000/30 ms.')}
      />
      <Callout variant="honest" title={t('Where it works and where it fails', 'Dónde funciona y dónde falla')}>
        {t(
          'In a real Worker in Chromium 153 the main thread kept answering: a 10 ms ticker saw a longest gap of 23 to 154 ms during runs of 1 to 3.5 s, and a cancel after the third progress message produced no further message. The cost is still the cost of the method: the 1024-trap case C03 is outside the 1500 ms lane budget in some runs (2.4 to 4.3 s in the runs under load), and the factor between the worker and Node on the same laptop (0.55 s for C03) is an unexplained variance of that machine, so the figures are ranges and not one number.',
          'En un Worker real en Chromium 153 el hilo principal siguió respondiendo: un temporizador de 10 ms vio un hueco máximo de 23 a 154 ms durante corridas de 1 a 3,5 s, y una cancelación tras el tercer mensaje de progreso no produjo ningún mensaje más. El costo sigue siendo el del método: el caso C03 de 1024 trampas queda fuera del presupuesto de carril de 1500 ms en algunas corridas (de 2,4 a 4,3 s en las corridas con carga), y el factor entre el worker y Node en el mismo portátil (0,55 s para C03) es una varianza sin explicar de esa máquina, así que las cifras son rangos y no un solo número.',
        )}
      </Callout>
    </DocSection>
  );
}

export function GpuTopic() {
  const t = useT();
  return (
    <DocSection title={{ en: 'The WebGPU backend and its agreement gate', es: 'El backend WebGPU y su compuerta de concordancia' }} area="engine" noRefsReason={{ en: 'Describes this repository; the WGSL kernel is validated by the agreement test, not by a citation.', es: 'Describe este repositorio; el kernel WGSL se valida con la prueba de concordancia, no con una cita.' }}>
      <P
        en="An optional backend runs the FFT-form iterations on the GPU when the browser offers one. It is detected at run time inside the worker: no navigator.gpu, no adapter or a failing device each give a reason string, and the run takes the CPU path. The kernel is a Stockham radix-2 FFT in WGSL, one dispatch per stage per axis, with the weighted amplitude pass of the method on the GPU in float32, and only the trap fields cross the bus each iteration. It covers M04, M06 and M07 for an ideal device and a trap target; everything else is CPU, by design."
        es="Un backend opcional ejecuta en la GPU las iteraciones de forma FFT cuando el navegador la ofrece. Se detecta en tiempo de ejecución dentro del worker: la ausencia de navigator.gpu, de un adaptador o un dispositivo que falla dan cada uno una cadena con la razón, y la corrida toma la vía CPU. El kernel es una FFT de Stockham de base 2 en WGSL, un despacho por etapa por eje, con la pasada de amplitud ponderada del método en la GPU en float32, y sólo los campos de las trampas cruzan el bus en cada iteración. Cubre M04, M06 y M07 con dispositivo ideal y objetivo de trampas; todo lo demás es CPU, por diseño."
      />
      <P
        en="A run is eligible only when the FFT size is a power of two, there are at most 65535 traps, every trap sits on its own FFT bin with z = 0 and no vortex. Because the cases C02 and C03 as defined have off-bin traps, the default cases take the CPU path with the reason recorded, and the browser agreement test moves their traps to the nearest bin to exercise the GPU. Every ineligible, absent or failing run falls back to the CPU path and records the reason in the result; an explicit CPU request records none."
        es="Una corrida es elegible sólo cuando el tamaño de la FFT es una potencia de dos, hay a lo más 65535 trampas y cada trampa está en su propio bin de la FFT con z = 0 y sin vórtice. Como los casos C02 y C03 tal como están definidos tienen trampas fuera de los bins, los casos por defecto toman la vía CPU con la razón registrada, y la prueba de concordancia en el navegador mueve sus trampas al bin más cercano para ejercitar la GPU. Toda corrida no elegible, ausente o fallida recurre a la vía CPU y registra la razón en el resultado; una petición explícita de CPU no registra ninguna."
      />
      <Equation
        tex="\max_m \frac{\left|I_m^{\mathrm{GPU}}-I_m^{\mathrm{CPU}}\right|}{\langle I^{\mathrm{CPU}}\rangle}\le 2\times 10^{-3}"
        caption={t('The agreement gate inside every GPU run: the final phase is read back and the trap intensities I_m recomputed on the CPU in float64; the run is rejected, and the CPU path answers, when any trap differs by more than 2e-3 of the mean CPU intensity. The metrics shown are scored from that final phase on the CPU.', 'La compuerta de concordancia dentro de cada corrida en GPU: se lee de vuelta la fase final y se recalculan las intensidades de las trampas I_m en la CPU en float64; la corrida se rechaza, y responde la vía CPU, cuando alguna trampa difiere en más de 2e-3 de la intensidad media de la CPU. Las métricas mostradas se calculan desde esa fase final en la CPU.')}
      />
      <Callout variant="honest" title={t('Where it works and where it fails', 'Dónde funciona y dónde falla')}>
        {t(
          'Measured on one integrated adapter (Intel gen-12lp, Chromium new headless mode, traps moved to FFT bins, 30 iterations of M07): 0.31 to 0.32 s on the GPU against 1.5 to 1.6 s on the CPU in that mode, about five times faster, with a phase difference of 3e-5 rad after one iteration and, after thirty, 5e-7 in efficiency and 9e-5 relative in the trap intensities. It is not a portable claim: no other adapter, no NVIDIA GPU and no other browser were measured, and the headless shell exposes no adapter at all, in which case the fallback reason says so.',
          'Medido en un adaptador integrado (Intel gen-12lp, modo headless nuevo de Chromium, trampas movidas a bins de la FFT, 30 iteraciones de M07): de 0,31 a 0,32 s en la GPU frente a 1,5 a 1,6 s en la CPU en ese modo, unas cinco veces más rápido, con una diferencia de fase de 3e-5 rad tras una iteración y, tras treinta, de 5e-7 en la eficiencia y 9e-5 relativo en las intensidades de las trampas. No es una afirmación portable: no se midió otro adaptador, ninguna GPU NVIDIA ni otro navegador, y el shell headless no expone adaptador alguno, caso en que la razón del recurso lo dice.',
        )}
      </Callout>
    </DocSection>
  );
}
