# Notebooks, español

El índice del árbol en español: ocho temas, desde el modelo directo de un holograma hasta los métodos aprendidos. Los temas van de lo
simple a lo complejo; dentro de un tema el orden de lectura es el número del notebook y el nivel nunca baja. El equivalente en inglés de
cada notebook está en la misma ruta bajo [`../en/`](../en/README.md). Cómo ejecutarlos está en [`../README.md`](../README.md).

Niveles: 1 fundamentos, 2 el método en la práctica, 3 comparación con métodos publicados, 4 métodos propuestos.

Cada notebook es una lección sobre una sola pregunta: la plantea en su primera celda, ejecuta los métodos del producto paso a paso con
los casos de `data/examples/cases.json`, muestra lo que encuentra en figuras y responde la pregunta en sus Resultados con números que
calculó él mismo ([`docs/guides/08_notebooks.md`](../../docs/guides/08_notebooks.md)). DinHot no publica ningún paquete propio: los
notebooks importan por su ruta los módulos de su pipeline, y la implementación de referencia de los notebooks de nivel 3 es slmsuite 0.5.0.

## Cómo cubren los notebooks los métodos

Cada método de la escalera del producto se nombra en los notebooks por su nombre ([`docs/guides/09_method-tiers.md`](../../docs/guides/09_method-tiers.md)),
y los notebooks los cubren así:

- Las líneas base (Gerchberg-Saxton simple, el lazo ponderado) se enseñan en los notebooks de nivel 1 y 2 de los temas 01 a 03 y en las líneas base de los temas siguientes.
- Los métodos publicados son los notebooks de nivel 3, una comparación con el método como se publicó o como lo implementa slmsuite: cada uno nombra el método que ejecuta en su metadato
  `caos.methods` (GS ponderado con fase fija en 03, MRAF y MRAF con transporte óptimo en 04, gradiente conjugado y gradiente de Wirtinger con Adam en 05, CG con modelo del dispositivo en 06, WGS en lazo cerrado y reordenamiento húngaro en 07, CNN no supervisada en 08).
- Los métodos propuestos son los notebooks de nivel 4, cada uno con la afirmación que prueba en `caos.beyond`
  (WGS con modelo del dispositivo en 03, frente eficiencia-uniformidad en 05, holograma robusto a aberraciones en 06, secuencia acotada por parpadeo en 07, arranque aprendido en 08, un negativo medido).

## Cobertura de toda la herramienta

[`../coverage.json`](../coverage.json) asigna cada parte de la herramienta a los notebooks que la enseñan: cada método de la escalera
del SDD (cubierto solo por un notebook de nivel 2 o superior), cada contrato de datos de `docs/contracts/catalog.md`, cada etapa del
pipeline de `data-pipeline/pipeline/stages/` y cada paquete de métodos (el producto no declara ninguno). Las rutas son relativas a un
árbol de idioma y existen en ambos. Todo notebook de nivel 2 o superior tiene una sección de tercer nivel sobre dónde su método
cambia o falla y otra sobre cómo usarlo con datos propios, y los notebooks de los topics 01 y 02 leen además los documentos
comprometidos de los contratos que explican. El control es `tools/notebooks/check_notebook_depth.py` de CAOS_MANAGE. Cada método de la escalera, cada contrato y cada etapa tiene un notebook en el mapa; una parte que
más adelante no tuviera ninguno la listaría el control.

## Temas

Un tema sin notebook de nivel 3 dice por qué en su fila.

| Tema | Requiere | Nivel 3 |
|---|---|---|
| [01-fourier-optics](01-fourier-optics/) | ninguno, es el tema de entrada | Sin nivel 3: el tema enseña el modelo directo y las métricas, que son el propio motor y no tienen un método publicado propio |
| [02-analytic-holograms](02-analytic-holograms/) | tema 01-fourier-optics | Sin nivel 3: los hologramas de un paso son las líneas base de un paso, y los lazos publicados parten en el tema 03 |
| [03-gerchberg-saxton](03-gerchberg-saxton/) | tema 02-analytic-holograms | [03-phase-fixed-wgs-against-slmsuite](03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite.ipynb) |
| [04-shaped-potentials](04-shaped-potentials/) | tema 03-gerchberg-saxton | [03-mraf-and-the-signal-region](04-shaped-potentials/03-mraf-and-the-signal-region.ipynb) y [04-optimal-transport-start](04-shaped-potentials/04-optimal-transport-start.ipynb) |
| [05-optimization](05-optimization/) | tema 03-gerchberg-saxton | 03 y 04 |
| [06-device-and-aberrations](06-device-and-aberrations/) | tema 05-optimization | 03 |
| [07-feedback-and-dynamics](07-feedback-and-dynamics/) | tema 03-gerchberg-saxton | 03 y 04 |
| [08-learned-holography](08-learned-holography/) | temas 01-fourier-optics y 03-gerchberg-saxton | [03-a-network-start-for-volume-holograms](08-learned-holography/03-a-network-start-for-volume-holograms.ipynb) |

## Notebooks

| Notebook | Nivel | La pregunta que responde |
|---|---|---|
| [01-fourier-optics/01-where-the-light-goes.ipynb](01-fourier-optics/01-where-the-light-goes.ipynb) | 1 | adónde envía la luz un patrón de fase: bin y ventana focales, réplicas fuera de ella, la envolvente del píxel, niveles de fase y orden cero (caso C01) |
| [01-fourier-optics/02-reading-a-trap-array.ipynb](01-fourier-optics/02-reading-a-trap-array.ipynb) | 2 | qué dicen la eficiencia, la uniformidad, la dispersión relativa y el balance de potencia de un arreglo de 10 por 10, dónde discrepan y por qué el balance necesita su radio (caso C12) |
| [01-fourier-optics/03-engine-reference-and-readiness.ipynb](01-fourier-optics/03-engine-reference-and-readiness.ipynb) | 2 | cómo el motor del navegador se mantiene dentro del de Python con los documentos de referencia del motor, cómo leer el documento de disponibilidad y el contrato de la API, y cómo escribir una referencia para una función propia |
| [02-analytic-holograms/01-superposition-and-random-mask.ipynb](02-analytic-holograms/01-superposition-and-random-mask.ipynb) | 1 | qué dan los tres hologramas de un paso (superposición, superposición aleatoria, máscara aleatoria) en C12 y qué limita a cada uno |
| [02-analytic-holograms/02-the-ten-by-ten-benchmark.ipynb](02-analytic-holograms/02-the-ten-by-ten-benchmark.ipynb) | 2 | cómo se comparan las tres líneas base con la tabla publicada de 10 por 10 en cinco tamaños de SLM |
| [02-analytic-holograms/03-laguerre-gaussian-vortex-traps.ipynb](02-analytic-holograms/03-laguerre-gaussian-vortex-traps.ipynb) | 2 | cómo un término agregado al retardo hace un anillo con el centro oscuro: el enrollamiento de la fase, el radio del anillo, el momento angular por fotón, el arreglo del caso C06 y la carga en que la verificación del producto produce aliasing |
| [03-gerchberg-saxton/01-the-gs-loop.ipynb](03-gerchberg-saxton/01-the-gs-loop.ipynb) | 1 | las dos mitades de una iteración de Gerchberg-Saxton hechas a mano con nueve trampas (caso C01), comprobadas contra Gerchberg-Saxton |
| [03-gerchberg-saxton/02-weights-for-uniformity.ipynb](03-gerchberg-saxton/02-weights-for-uniformity.ipynb) | 2 | qué ganan el GS ponderado y el adaptativo sobre el GS simple en C12: los primeros pesos, iteraciones hasta 5, 2 y 1 por ciento, el barrido de alfa, la dependencia de la semilla |
| [03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite.ipynb](03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite.ipynb) | 3 | cómo se comparan GS ponderado y GS ponderado con fase fija con WGS-Leonardo y WGS-Kim de slmsuite 0.5.0 en las 1024 trampas de C03 con un mismo conjunto de métricas |
| [03-gerchberg-saxton/04-device-aware-wgs.ipynb](03-gerchberg-saxton/04-device-aware-wgs.ipynb) | 4 | si el WGS consciente del dispositivo supera al WGS de fase fija y al gradiente conjugado con diafonía en el dispositivo del caso C08, y con qué intensidad de diafonía |
| [04-shaped-potentials/01-what-a-shaped-potential-asks.ipynb](04-shaped-potentials/01-what-a-shaped-potential-asks.ipynb) | 1 | qué le pide un potencial en forma de disco al holograma que no le piden nueve trampas puntuales, el error calculado a mano y dónde se detiene Gerchberg-Saxton simple en el disco del caso C04 |
| [04-shaped-potentials/02-the-signal-and-the-noise-region.ipynb](04-shaped-potentials/02-the-signal-and-the-noise-region.ipynb) | 2 | cuánto del plano focal debe ceder un holograma con forma para ser preciso: regiones de señal hechas a mano, el reparto de potencia, MRAF frente a Gerchberg-Saxton simple, el margen oscuro |
| [04-shaped-potentials/03-mraf-and-the-signal-region.ipynb](04-shaped-potentials/03-mraf-and-the-signal-region.ipynb) | 3 | cómo se compara MRAF con GS en un disco y un anillo, el parámetro de mezcla, el inicio y el MRAF de slmsuite sobre los mismos objetivos |
| [04-shaped-potentials/04-optimal-transport-start.ipynb](04-shaped-potentials/04-optimal-transport-start.ipynb) | 3 | cómo se compara el MRAF con transporte óptimo con el MRAF de slmsuite en el disco de C04, con la misma mezcla y el mismo inicio, y qué agrega el inicio de transporte óptimo |
| [05-optimization/01-the-cost-and-its-gradient.ipynb](05-optimization/01-the-cost-and-its-gradient.ipynb) | 1 | el costo explícito de un arreglo de trampas y su gradiente comprobado, y un primer descenso de gradiente conjugado contra el GS ponderado en C12 |
| [05-optimization/02-the-wirtinger-gradient-and-adams-step.ipynb](05-optimization/02-the-wirtinger-gradient-and-adams-step.ipynb) | 2 | el retroceso de Wirtinger por los modelos ideal y con diafonía, qué hace Adam con un gradiente de escala desconocida, el barrido de la tasa de aprendizaje |
| [05-optimization/03-conjugate-gradient-against-weighted-gs.ipynb](05-optimization/03-conjugate-gradient-against-weighted-gs.ipynb) | 3 | cómo se compara el gradiente conjugado con el lazo de GS ponderado: el refinamiento que baja el costo y sube la dispersión, y la eficiencia que el gradiente conjugado devuelve exacta |
| [05-optimization/04-wirtinger-adam-against-gerchberg-saxton.ipynb](05-optimization/04-wirtinger-adam-against-gerchberg-saxton.ipynb) | 3 | cómo se compara el gradiente de Wirtinger con Adam con el GS simple y ponderado a igual número de iteraciones en tres semillas y a 100 iteraciones |
| [05-optimization/05-the-efficiency-uniformity-front.ipynb](05-optimization/05-the-efficiency-uniformity-front.ipynb) | 4 | el frente completo eficiencia-uniformidad por continuación contra seis métodos de punto único en C12 |
| [06-device-and-aberrations/01-what-the-device-costs.ipynb](06-device-and-aberrations/01-what-the-device-costs.ipynb) | 1 | cuánto le cuestan al holograma de C08 la apertura del píxel, la cuantización y la diafonía |
| [06-device-and-aberrations/02-zernike-correction.ipynb](06-device-and-aberrations/02-zernike-correction.ipynb) | 2 | los modos de Zernike en orden de Noll, la estimación de Strehl contra la pérdida medida en C09 y la recuperación modal sin sensor de la corrección de Zernike |
| [06-device-and-aberrations/03-crosstalk-aware-cg-against-cg.ipynb](06-device-and-aberrations/03-crosstalk-aware-cg-against-cg.ipynb) | 3 | cómo se compara el CG con modelo del dispositivo con el gradiente conjugado en el dispositivo de C08, la detención temprana de la búsqueda de línea y el CG con modelo del dispositivo sin dispositivo |
| [06-device-and-aberrations/04-robust-holograms.ipynb](06-device-and-aberrations/04-robust-holograms.ipynb) | 4 | el holograma robusto a aberraciones contra WGS de fase fija en 100 sorteos de aberración residual, y el negativo medido en errores de puntería |
| [07-feedback-and-dynamics/01-a-bead-in-the-computed-trap.ipynb](07-feedback-and-dynamics/01-a-bead-in-the-computed-trap.ipynb) | 1 | la intensidad focal de C01 como potencial, una cuenta de Langevin en él, su espectro lorentziano contra la rigidez y su histograma contra la ley de Boltzmann |
| [07-feedback-and-dynamics/02-assigning-atoms-to-sites.ipynb](07-feedback-and-dynamics/02-assigning-atoms-to-sites.ipynb) | 2 | la asignación húngara de C10 para seis exponentes del costo, los cruces y el plan que construye el método de reordenamiento húngaro con ella |
| [07-feedback-and-dynamics/03-closed-loop-feedback.ipynb](07-feedback-and-dynamics/03-closed-loop-feedback.ipynb) | 3 | cómo se comparan la actualización de Nogrette del WGS en lazo cerrado (la lectura acumulada de su Ec. 3 que hace DinHot, con la regla literal corrida al lado) y la de Kim en la cámara emulada de C02, contra el GS ponderado con fase fija a lazo abierto |
| [07-feedback-and-dynamics/04-moving-atoms-by-linear-phase-interpolation.ipynb](07-feedback-and-dynamics/04-moving-atoms-by-linear-phase-interpolation.ipynb) | 3 | cómo se compara la secuencia de hologramas del método de reordenamiento húngaro en el ordenamiento de C10 con hologramas independientes y con un paso más fino |
| [07-feedback-and-dynamics/05-flicker-bounded-moves.ipynb](07-feedback-and-dynamics/05-flicker-bounded-moves.ipynb) | 4 | la secuencia acotada por parpadeo contra LPI en su tarea de aceptación, y los movimientos largos de C10 donde necesita las fases finales |
| [08-learned-holography/01-what-a-network-sees-of-a-hologram.ipynb](08-learned-holography/01-what-a-network-sees-of-a-hologram.ipynb) | 1 | qué entra a la red publicada y qué sale de ella para un objetivo de tres planos, la exactitud con que se la evalúa y una fase plana y una aleatoria en la misma escala (óptica de C05) |
| [08-learned-holography/02-training-without-labels.ipynb](08-learned-holography/02-training-without-labels.ipynb) | 2 | cómo aprende la red sin hologramas de ejemplo: la pérdida a mano en volúmenes nuevos, su cuenco suave alrededor de la fase de la red, lo que no ve en las trampas y el registro con datos reservados de 162 volúmenes |
| [08-learned-holography/03-a-network-start-for-volume-holograms.ipynb](08-learned-holography/03-a-network-start-for-volume-holograms.ipynb) | 3 | si la red publicada supera al GS volumétrico (CNN no supervisada contra GS multiplano) en la exactitud del volumen (por plano y en la forma coseno del artículo) y en los números propios de las trampas |
| [08-learned-holography/04-is-a-learned-warm-start-worth-it.ipynb](08-learned-holography/04-is-a-learned-warm-start-worth-it.ipynb) | 4 | si una red que predice fases de trampas acelera el WGS de fase fija, o un congelado sin red explica toda la ganancia (un negativo medido) |

## Métodos propuestos

Cinco afirmaciones del SDD del producto, cada una con un notebook de nivel 4 en ambos idiomas: el WGS consciente del dispositivo
(03-04), la secuencia acotada por parpadeo (07-05), el arranque aprendido, probado y refutado (08-04), el holograma robusto a aberraciones
(06-04) y el frente eficiencia-uniformidad (05-05). Dos de ellas, el arranque aprendido y la parte de puntería del holograma robusto a aberraciones, son negativos medidos y
los notebooks lo dicen.
