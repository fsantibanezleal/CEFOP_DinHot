# Notebooks, español

El índice del árbol en español. Los temas van de lo simple a lo complejo; dentro de un tema el orden de lectura es el
número del notebook y el nivel nunca baja. El equivalente en inglés de cada notebook está en la misma ruta bajo
[`../en/`](../en/README.md). Cómo correrlos está en [`../README.md`](../README.md).

Niveles: 1 fundamentos, 2 el método en la práctica, 3 estado del arte, 4 más allá del estado del arte.

Cada notebook es una lección trabajada sobre una pregunta: la plantea en su primera celda, corre el motor paso a paso sobre
los casos del ejemplo, muestra lo que encuentra en figuras, y responde la pregunta en sus Resultados con números que él mismo
calculó ([`docs/guides/08_notebooks.md`](../../docs/guides/08_notebooks.md)).

## Temas

Un tema sin notebook de nivel 3 explica por qué en su fila.

| Tema | Requiere | Nivel 3 |
|---|---|---|
| [01-getting-started](01-getting-started/) | ninguno, es el tema de entrada | [03-a-higher-order-solver](01-getting-started/03-a-higher-order-solver.ipynb) |
| [02-threshold-and-final-size](02-threshold-and-final-size/) | tema 01-getting-started | Sin nivel 3: la base de investigación no nombra un método más nuevo para el umbral ni para el tamaño final, y la única comparación con el estado del arte del ejemplo, el resolvedor de orden mayor, está en el tema 01 |

## Notebooks

| Notebook | Nivel | La pregunta que responde |
|---|---|---|
| [01-getting-started/01-the-problem-and-the-data.ipynb](01-getting-started/01-the-problem-and-the-data.ipynb) | 1 | cómo recorre una epidemia un pueblo de 100000 personas día a día: el pico, su día y el saldo final, y cómo se mueven cuando cambian los primeros casos o el periodo infeccioso |
| [01-getting-started/02-the-method-step-by-step.ipynb](01-getting-started/02-the-method-step-by-step.ipynb) | 2 | cuánto se equivoca el paso de Euler hacia adelante del motor, frente al tamaño final y al pico exactos, para qué casos importa, y qué recupera la extrapolación |
| [01-getting-started/03-a-higher-order-solver.ipynb](01-getting-started/03-a-higher-order-solver.ipynb) | 3 | cómo se compara el RK45 de SciPy con el motor en los mismos casos, por el error según el paso y según el costo |
| [02-threshold-and-final-size/01-the-threshold.ipynb](02-threshold-and-final-size/01-the-threshold.ipynb) | 1 | con qué tasas de contacto y de recuperación despega un brote, cómo se ve justo sobre el umbral, y qué parte inmune lo detiene |
| [02-threshold-and-final-size/02-the-final-size.ipynb](02-threshold-and-final-size/02-the-final-size.ipynb) | 2 | qué parte infecta un brote al final, por qué ignora la velocidad del curso, y dónde la corrida del motor no la alcanza |

## Más allá del estado del arte

Nada declarado: el ejemplo es un modelo didáctico, así que no tiene notebook de nivel 4. Un producto que declara un
componente más allá del estado del arte lo lista en su SDD y lo cubre con un notebook de nivel 4 en cada idioma
([`docs/guides/08_notebooks.md`](../../docs/guides/08_notebooks.md)).
