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
- Los métodos publicados son los notebooks de nivel 3, una comparación con el método como se publicó o como lo implementa slmsuite: cada uno nombra la fila de la escalera que ejecuta en su metadato
  `caos.methods` (M07 en 03, M08 y M18 en 04, M10 y M11 en 05, M13 en 06, M12 y M16 en 07, M17 en 08).
- Los métodos propuestos son los notebooks de nivel 4, cada uno con la afirmación que prueba en `caos.beyond`
  (B1 en 03, B5 en 05, B4 en 06, B2 en 07, B3 en 08, un negativo medido).

## Temas

Un tema sin notebook de nivel 3 dice por qué en su fila.

| Tema | Requiere | Nivel 3 |
|---|---|---|
| [01-fourier-optics](01-fourier-optics/) | ninguno, es el tema de entrada | Sin nivel 3: el tema enseña el modelo directo y las métricas, que son el propio motor y no tienen un método publicado propio |
| [02-analytic-holograms](02-analytic-holograms/) | tema 01-fourier-optics | Sin nivel 3: los hologramas de un paso son las líneas base clásicas, y los lazos publicados parten en el tema 03 |
| [03-gerchberg-saxton](03-gerchberg-saxton/) | tema 02-analytic-holograms | [03-phase-fixed-wgs-against-slmsuite](03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite.ipynb) (M07) |
| [04-shaped-potentials](04-shaped-potentials/) | tema 03-gerchberg-saxton | [03-mraf-and-the-signal-region](04-shaped-potentials/03-mraf-and-the-signal-region.ipynb) (M08) y [04-optimal-transport-start](04-shaped-potentials/04-optimal-transport-start.ipynb) (M18) |
| [05-optimization](05-optimization/) | tema 03-gerchberg-saxton | 03 (M10) y 04 (M11) |
| [06-device-and-aberrations](06-device-and-aberrations/) | tema 05-optimization | 03 (M13) |
| [07-feedback-and-dynamics](07-feedback-and-dynamics/) | tema 03-gerchberg-saxton | 03 (M12) y 04 (M16) |
| [08-learned-holography](08-learned-holography/) | temas 01-fourier-optics y 03-gerchberg-saxton | [03-a-network-start-for-volume-holograms](08-learned-holography/03-a-network-start-for-volume-holograms.ipynb) (M17) |

## Notebooks

| Notebook | Nivel | La pregunta que responde |
|---|---|---|
| [01-fourier-optics/01-where-the-light-goes.ipynb](01-fourier-optics/01-where-the-light-goes.ipynb) | 1 | adónde envía la luz un patrón de fase: bin y ventana focales, réplicas fuera de ella, la envolvente del píxel, niveles de fase y orden cero (caso C01) |
| [01-fourier-optics/02-reading-a-trap-array.ipynb](01-fourier-optics/02-reading-a-trap-array.ipynb) | 2 | qué dicen la eficiencia, la uniformidad, la dispersión relativa y el balance de potencia de un arreglo de 10 por 10, dónde discrepan y por qué el balance necesita su radio (caso C12) |
| [02-analytic-holograms/01-superposition-and-random-mask.ipynb](02-analytic-holograms/01-superposition-and-random-mask.ipynb) | 1 | qué dan los tres hologramas de un paso (superposición, superposición aleatoria, máscara aleatoria) en C12 y qué limita a cada uno |
| [02-analytic-holograms/02-the-ten-by-ten-benchmark.ipynb](02-analytic-holograms/02-the-ten-by-ten-benchmark.ipynb) | 2 | cómo se comparan las tres líneas base con la tabla publicada de 10 por 10 en cinco tamaños de SLM |
| [03-gerchberg-saxton/01-the-gs-loop.ipynb](03-gerchberg-saxton/01-the-gs-loop.ipynb) | 1 | las dos mitades de una iteración de Gerchberg-Saxton hechas a mano con nueve trampas (caso C01), comprobadas contra M04 |
| [03-gerchberg-saxton/02-weights-for-uniformity.ipynb](03-gerchberg-saxton/02-weights-for-uniformity.ipynb) | 2 | qué ganan el GS ponderado y el adaptativo sobre el GS simple en C12: los primeros pesos, iteraciones hasta 5, 2 y 1 por ciento, el barrido de alfa, la dependencia de la semilla |
| [03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite.ipynb](03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite.ipynb) | 3 | cómo se comparan M06 y M07 con WGS-Leonardo y WGS-Kim de slmsuite 0.5.0 en las 1024 trampas de C03 con un mismo conjunto de métricas |
| [03-gerchberg-saxton/04-device-aware-wgs.ipynb](03-gerchberg-saxton/04-device-aware-wgs.ipynb) | 4 | si el WGS consciente del dispositivo (B1) supera al WGS de fase fija y al gradiente conjugado con diafonía en el dispositivo del caso C08, y con qué intensidad de diafonía |
| [04-shaped-potentials/01-what-a-shaped-potential-asks.ipynb](04-shaped-potentials/01-what-a-shaped-potential-asks.ipynb) | 1 | qué le pide un potencial en forma de disco al holograma que no le piden nueve trampas puntuales, el error calculado a mano y dónde se detiene Gerchberg-Saxton simple en el disco del caso C04 |
| [04-shaped-potentials/02-the-signal-and-the-noise-region.ipynb](04-shaped-potentials/02-the-signal-and-the-noise-region.ipynb) | 2 | cuánto del plano focal debe ceder un holograma con forma para ser preciso: regiones de señal hechas a mano, el reparto de potencia, MRAF frente a Gerchberg-Saxton simple, el margen oscuro |
| [04-shaped-potentials/03-mraf-and-the-signal-region.ipynb](04-shaped-potentials/03-mraf-and-the-signal-region.ipynb) | 3 | cómo se compara MRAF con GS en un disco y un anillo, el parámetro de mezcla, el inicio y el MRAF de slmsuite sobre los mismos objetivos |
| [04-shaped-potentials/04-optimal-transport-start.ipynb](04-shaped-potentials/04-optimal-transport-start.ipynb) | 3 | cómo se compara M18 con el MRAF de slmsuite en el disco de C04, con la misma mezcla y el mismo inicio, y qué agrega el inicio de transporte óptimo |
| [05-optimization/01-the-cost-and-its-gradient.ipynb](05-optimization/01-the-cost-and-its-gradient.ipynb) | 1 | el costo explícito de un arreglo de trampas y su gradiente comprobado, y un primer descenso de gradiente conjugado contra el GS ponderado en C12 |
| [05-optimization/02-the-wirtinger-gradient-and-adams-step.ipynb](05-optimization/02-the-wirtinger-gradient-and-adams-step.ipynb) | 2 | el retroceso de Wirtinger por los modelos ideal y con diafonía, qué hace Adam con un gradiente de escala desconocida, el barrido de la tasa de aprendizaje |
| [05-optimization/03-conjugate-gradient-against-weighted-gs.ipynb](05-optimization/03-conjugate-gradient-against-weighted-gs.ipynb) | 3 | cómo se compara M10 con el lazo clásico M06: el refinamiento que baja el costo y sube la dispersión, y la eficiencia que M10 devuelve exacta |
| [05-optimization/04-wirtinger-adam-against-gerchberg-saxton.ipynb](05-optimization/04-wirtinger-adam-against-gerchberg-saxton.ipynb) | 3 | cómo se compara M11 con el GS simple y ponderado a igual número de iteraciones en tres semillas y a 100 iteraciones |
| [05-optimization/05-the-efficiency-uniformity-front.ipynb](05-optimization/05-the-efficiency-uniformity-front.ipynb) | 4 | el frente completo eficiencia-uniformidad por continuación (B5) contra seis métodos de punto único en C12 |
| [06-device-and-aberrations/01-what-the-device-costs.ipynb](06-device-and-aberrations/01-what-the-device-costs.ipynb) | 1 | cuánto le cuestan al holograma de C08 la apertura del píxel, la cuantización y la diafonía |
| [06-device-and-aberrations/02-zernike-correction.ipynb](06-device-and-aberrations/02-zernike-correction.ipynb) | 2 | los modos de Zernike en orden de Noll, la estimación de Strehl contra la pérdida medida en C09 y la recuperación modal sin sensor de M14 |
| [06-device-and-aberrations/03-crosstalk-aware-cg-against-cg.ipynb](06-device-and-aberrations/03-crosstalk-aware-cg-against-cg.ipynb) | 3 | cómo se compara M13 con M10 en el dispositivo de C08, la detención temprana de la búsqueda de línea y M13 sin dispositivo |
| [06-device-and-aberrations/04-robust-holograms.ipynb](06-device-and-aberrations/04-robust-holograms.ipynb) | 4 | B4 contra WGS de fase fija en 100 sorteos de aberración residual, y el negativo medido en errores de puntería |
| [07-feedback-and-dynamics/01-a-bead-in-the-computed-trap.ipynb](07-feedback-and-dynamics/01-a-bead-in-the-computed-trap.ipynb) | 1 | la intensidad focal de C01 como potencial, una cuenta de Langevin en él, su espectro lorentziano contra la rigidez y su histograma contra la ley de Boltzmann |
| [07-feedback-and-dynamics/02-assigning-atoms-to-sites.ipynb](07-feedback-and-dynamics/02-assigning-atoms-to-sites.ipynb) | 2 | la asignación húngara de C10 para seis exponentes del costo, los cruces y el plan que M16 construye con ella |
| [07-feedback-and-dynamics/03-closed-loop-feedback.ipynb](07-feedback-and-dynamics/03-closed-loop-feedback.ipynb) | 3 | cómo se comparan las actualizaciones de Nogrette y de Kim de M12 en la cámara emulada de C02, contra el M07 a lazo abierto |
| [07-feedback-and-dynamics/04-moving-atoms-by-linear-phase-interpolation.ipynb](07-feedback-and-dynamics/04-moving-atoms-by-linear-phase-interpolation.ipynb) | 3 | cómo se compara la secuencia de hologramas de M16 en el ordenamiento de C10 con hologramas independientes y con un paso más fino |
| [07-feedback-and-dynamics/05-flicker-bounded-moves.ipynb](07-feedback-and-dynamics/05-flicker-bounded-moves.ipynb) | 4 | B2 contra LPI en su tarea de aceptación, y los movimientos largos de C10 donde B2 necesita las fases finales |
| [08-learned-holography/01-what-a-network-sees-of-a-hologram.ipynb](08-learned-holography/01-what-a-network-sees-of-a-hologram.ipynb) | 1 | qué entra a la red publicada y qué sale de ella para un objetivo de tres planos, la exactitud con que se la evalúa y una fase plana y una aleatoria en la misma escala (óptica de C05) |
| [08-learned-holography/02-training-without-labels.ipynb](08-learned-holography/02-training-without-labels.ipynb) | 2 | cómo aprende la red sin hologramas de ejemplo: la pérdida a mano en volúmenes nuevos, su cuenco suave alrededor de la fase de la red, lo que no ve en las trampas y el registro con datos reservados de 162 volúmenes |
| [08-learned-holography/03-a-network-start-for-volume-holograms.ipynb](08-learned-holography/03-a-network-start-for-volume-holograms.ipynb) | 3 | si la red publicada supera al GS volumétrico clásico (M17 contra M19) en la exactitud del volumen y en los números propios de las trampas |
| [08-learned-holography/04-is-a-learned-warm-start-worth-it.ipynb](08-learned-holography/04-is-a-learned-warm-start-worth-it.ipynb) | 4 | si una red que predice fases de trampas acelera el WGS de fase fija, o un congelado sin red explica toda la ganancia (un negativo medido) |

## Métodos propuestos

Cinco afirmaciones del SDD del producto, cada una con un notebook de nivel 4 en ambos idiomas: B1 WGS consciente del dispositivo
(03-04), B2 secuencias acotadas en parpadeo (07-05), B3 el inicio aprendido, probado y refutado (08-04), B4 el holograma robusto
(06-04) y B5 el frente eficiencia-uniformidad (05-05). Dos de ellas, B3 y la parte de puntería de B4, son negativos medidos y
los notebooks lo dicen.
