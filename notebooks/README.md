# Notebooks

The didactic layer of DinHot: notebooks that teach, step by step and on the product's own cases, how holograms for optical trap
arrays are computed, where each method stands against the published ones, and what the product proposes. They import the
product's methods from `data-pipeline/pipeline/` by path (DinHot publishes no package of its own) and never re-implement them. Each
one is a worked lesson on one question, held to the measured floors of `scripts/check_notebooks.py` (method cells, figures read in
prose, one setup cell, an answer that quotes a number from an output). The rule is CAOS_MANAGE `conventions/product-notebooks.md`,
carried by the template (guide: [`docs/guides/08_notebooks.md`](../docs/guides/08_notebooks.md)).

La capa didáctica de DinHot: notebooks que enseñan, paso a paso y con los casos propios del producto, cómo se calculan los
hologramas de arreglos de trampas ópticas, dónde queda cada método frente a los publicados y qué propone el producto.
Importan los métodos del producto desde `data-pipeline/pipeline/` por su ruta (DinHot no publica ningún paquete propio) y nunca los
reimplementan. Cada uno es una lección sobre una sola pregunta.

## What the set teaches / Qué enseña el conjunto

Eight topics, from simple to complex, in two trees:

1. `01-fourier-optics`: where a phase pattern sends the light, the numbers that judge a trap array, and the engine-reference, readiness and API contracts.
2. `02-analytic-holograms`: the one-step holograms, the baselines, and the Laguerre-Gaussian vortex traps.
3. `03-gerchberg-saxton`: the Gerchberg-Saxton family, phase-fixed WGS against slmsuite, and device-aware WGS.
4. `04-shaped-potentials`: what a shaped potential asks, the signal and the noise region, MRAF and optimal-transport starts for shaped targets.
5. `05-optimization`: conjugate gradient and Wirtinger-Adam on the explicit cost, and the efficiency-uniformity front.
6. `06-device-and-aberrations`: what the device costs, Zernike correction, crosstalk-aware descent and robust holograms.
7. `07-feedback-and-dynamics`: a bead in the computed trap, atom rearrangement, camera feedback, flicker-bounded moves.
8. `08-learned-holography`: what the released network takes and returns, how it learns without labels, the network against the volumetric GS, and the refused warm start.

Levels: 1 fundamentals, 2 the method in practice, 3 comparison with published methods (the published methods of the SDD's ladder,
run against slmsuite 0.5.0 or as published), 4 proposed methods (the product's own claims, measured, including the negatives).

## Coverage of the tool / Cobertura de la herramienta

[`coverage.json`](coverage.json) maps each method of the SDD's ladder, each data contract, each pipeline stage and each method
package to the notebooks that teach it (paths relative to a language tree, present in both); a method counts as covered only by a
notebook of level 2 or above. The parts without a notebook yet are listed in the index of each tree.
[`coverage.json`](coverage.json) asigna cada método de la escalera del SDD, cada contrato de datos, cada etapa del pipeline y cada
paquete de métodos a los notebooks que lo enseñan (rutas relativas a un árbol de idioma, presentes en ambos); un método solo cuenta
como cubierto por un notebook de nivel 2 o superior. Las partes que aún no tienen notebook se listan en el índice de cada árbol.

## The two trees / Los dos árboles

| Language | Index | Folder |
|---|---|---|
| English | [en/README.md](en/README.md) | [en/](en/) |
| Español | [es/README.md](es/README.md) | [es/](es/) |

The two trees hold the same notebooks at the same relative paths (the slugs are English, so the mirror is checkable); each notebook
is written wholly in its tree's language. Los dos árboles tienen los mismos notebooks en las mismas rutas relativas; cada notebook
está escrito entero en el idioma de su árbol.

## Run them / Correrlos

```bash
./scripts/setup.sh --notebooks             # .venv-notebooks from notebooks/requirements.txt (setup.ps1 -Notebooks on Windows)
python scripts/run_notebooks.py            # executes every notebook top to bottom in a fresh kernel and writes the outputs in place
python scripts/run_notebooks.py --check --tmp <temp root>   # executes copies, writes nothing else, fails on any error or stale output
python scripts/check_notebooks.py          # the static check: layout, mirror, levels, tiers, anatomy, metadata, clean, pins, the floors
```

Only the runner writes a notebook's outputs, and the committed notebooks are the runner's output, so they read as finished material
on GitHub. A notebook finishes in under three minutes; the learned-holography notebooks read the released ONNX graph through
onnxruntime and print no measured wall-clock figure, because the check compares the committed bytes with a fresh run.

`requirements.txt` pins the notebook environment exactly: the packages the notebooks use (numpy, matplotlib, scipy, the pinned
reference implementation slmsuite, onnxruntime), then the runtime that executes them (nbclient, nbformat, ipykernel).
