# Notebooks

The didactic layer of the product: notebooks that teach, step by step and on the product's own data, how its methods
work, where each method stands against the state of the art and what the product adds beyond it. They import the
product's methods and never re-implement them. Each one is a worked lesson on one question, and from release 0.12.000 the
static check holds it to measured floors: method cells, figures read in prose, one setup cell, no pasted prose, an answer
that quotes a number from an output. The rule is `CAOS_MANAGE` `conventions/product-notebooks.md`, carried by the template
from release 0.10.000 (guide: [`docs/guides/08_notebooks.md`](../docs/guides/08_notebooks.md)).

La capa didáctica del producto: notebooks que enseñan, paso a paso y con los datos propios del producto, cómo
funcionan sus métodos, dónde queda cada método frente al estado del arte y qué agrega el producto más allá. Importan los
métodos del producto y nunca los reimplementan.

## The two trees / Los dos árboles

| Language | Index | Folder |
|---|---|---|
| English | [en/README.md](en/README.md) | [en/](en/) |
| Español | [es/README.md](es/README.md) | [es/](es/) |

The two trees hold the same notebooks at the same relative paths (the slugs are English, so the mirror is checkable);
each notebook is written wholly in its tree's language. Topics run from simple to complex, notebooks inside a topic by
level: 1 fundamentals, 2 the method in practice, 3 state of the art, 4 beyond the state of the art.

Los dos árboles tienen los mismos notebooks en las mismas rutas relativas (los nombres están en inglés, así que el
espejo se puede comprobar); cada notebook está escrito entero en el idioma de su árbol.

## Run them / Correrlos

```bash
./scripts/setup.sh --notebooks             # .venv-notebooks from notebooks/requirements.txt (setup.ps1 -Notebooks on Windows)
python scripts/run_notebooks.py            # executes every notebook top to bottom in a fresh kernel and writes the outputs in place
python scripts/run_notebooks.py --check --tmp <temp root>   # executes copies under the temp root, writes nothing else, fails on any error
                                                            # (CAOS_TEMP_ROOT=<temp root> works too; with neither it stops with exit 2; a local release gate, never CI)
python scripts/check_notebooks.py          # the static check: layout, mirror, levels, anatomy, metadata, clean, pins and the floors of the bar (CI and local)
python scripts/check_notebooks.py --pypi   # also reads PyPI for the pin of each method package (opt-in, needs the network, never CI)
```

Every product declares in `product.json` the dotted names that run its method, `"method_entrypoints": ["pipeline.model.sir.simulate", ...]`
(`module.function` or `module.Class`): the static check counts as method cells only the cells that call one of them, or a method of an object built
from one, and fails a product that declares none. A product whose methods live in PyPI packages lists them in `product.json` as `"method_packages": ["<distribution>"]` (empty in the template), each
with an exact `name==version` line in `notebooks/requirements.txt`. The static check then also fails a notebook cell that defines a function or a class
such a package defines (a notebook imports a method, never copies it); a package not installed where the check runs is an info line, and
`run_notebooks.py` stops before any notebook executes when one is not installed.

Only the runner writes a notebook's outputs; the committed notebooks are the runner's output. To read one, open it on
GitHub or in any Jupyter client (select the `.venv-notebooks` kernel to run it).

## The example set / El conjunto de ejemplo

The template's example product (the SIR epidemic model) ships two topics, five notebooks in each language, written to the bar.
A product replaces them with its own; `scripts/check_template_residue.py` lists them until it does.

- `01-getting-started`: one epidemic run day by day (level 1), how wrong the engine's Forward Euler step is (level 2), and
  how a higher-order solver, SciPy's RK45, compares with it (level 3, the reference implementation pinned in
  `requirements.txt`).
- `02-threshold-and-final-size`: when an outbreak takes off and which immune share stops it (level 1), and how large it
  gets and why that ignores the speed of the course (level 2).

`requirements.txt` pins the notebook environment exactly: the product's PyPI packages first, then the runtime that
executes the notebooks.
