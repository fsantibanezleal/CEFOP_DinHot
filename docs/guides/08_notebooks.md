# Guide: write the product's notebooks

The notebooks are the product's didactic layer: they teach a reader, step by step and on the product's own data, how
its methods work, where each method stands against the state of the art, and what the product adds beyond it. They
import the product's methods and never re-implement them; logic that exists only in a notebook is incomplete. The
rule is CAOS_MANAGE `conventions/product-notebooks.md`; this guide is how a product applies it, and it opens with the bar. The template ships an
example set on the SIR model, which a product replaces (`scripts/check_template_residue.py` lists it).

## The bar: a notebook is a worked lesson

A notebook is a worked lesson. A reader who works through it learns one method of the product well enough to use it on
their own data: the question the method answers, how it works step by step, what it gives on the product's real data, how
it compares with the alternatives, and where it stops being valid. Passing the gates is the floor, not the bar: a notebook
that passes them and teaches nothing fails its review. On 2026-10-26 five of 175 English notebooks across eight products met
the floors below; most read a baked JSON file, printed its keys and wrapped it in prose pasted across notebooks, and the
template's own example, copied by products, spent a quarter of its code cells checking the engine against itself. The
example set of this repository (`notebooks/en/` and `notebooks/es/`) is written to the bar and illustrates each point.

What every notebook of a product does:

1. **Answers one question.** The first cell states it (`**Question:**`, in Spanish `**Pregunta:**`): a question of the
   product's problem in its context, never "inspect the artifact". The Results section answers it (`**Answer:**`,
   `**Respuesta:**`) with numbers the notebook computed. No two notebooks of a tree share a question. The example's notebook on
   the threshold asks for which contact and recovery rates an outbreak takes off, and answers with the growth rates and the
   immune share it printed.
2. **Runs the method.** The method runs in the notebook, through the product's package or its named pipeline, on input data,
   one step per cell, each step showing its intermediate result. Reading baked results and printing them is not a method: it
   may illustrate a point, never carry the notebook. The example reads only the five cases' parameters and runs `simulate`,
   `final_size` and `peak_frac` itself.
3. **Explains before and after.** Before each step: what it does, why, the equation with its source when there is one, and
   what to look for. After each figure or table: what it shows, what it does not show, and what follows from it.
4. **Argues with figures.** Figures and tables carry the results, not print statements: at least one figure at level 1 and
   two from level 2, each with a title, labelled axes and units, each read in the prose that follows it.
5. **Is its own text.** Written for this notebook: no paragraph pasted from another notebook of the set (the Setup install
   line, the Data source lines and the reference format excepted), no generic sentence that would fit any product
   ("Interpret the method with its units", "Trace the evidence from source contract to result").
6. **Keeps the machinery out of the way.** One setup cell: imports, versions, the data loader. Readers and path discovery
   live in that cell or in the product's package, never redefined further down.
7. **Keeps the tests in the tests.** Checking that the notebook reproduces a committed artifact is the test suite's job. A
   notebook holds at most one reproduction check, and it never counts as the lesson.
8. **Shows the state of the art by running it.** A level 3 notebook runs the state-of-the-art method (the package's
   implementation or a pinned reference implementation) on the same data as the product's method, and compares the two with
   numbers and a figure. The example's level 3 notebook runs SciPy's RK45 and DOP853 (pinned in `notebooks/requirements.txt`)
   on the engine's cases and compares error against step and against cost. A level 4 notebook measures the claim it
   demonstrates, including the case where the state of the art fails.
9. **Reads as code a practitioner would write.** One idea per cell, at most 30 lines of logic, one statement per line, lines
   of at most 120 characters, names that say what they hold; comments say why, not what.
10. **Earns its place.** The set follows the product's methods, not the coverage table: fewer, deeper notebooks over many
    thin ones. A topic with too little to teach in a level 1 and a level 2 notebook is not a topic; it merges into its
    neighbour.

### The measured floors

`scripts/check_notebooks.py` enforces these from template 0.12.000, statically, on the committed cells and outputs; the
thresholds are in `scripts/notebook_bar.json`. A finding names the notebook, the measure, the value and the floor (for
example `notebooks/en/01-x/02-y.ipynb: bar: method cells 2, the floor at level 2 is 5`). The floors catch the failure
described above; they do not certify a lesson, the review does.

| Measure, per notebook | Level 1 | Levels 2 to 4 |
|---|---|---|
| Method cells: code cells that call the product's method package (`product.json` `method_packages`), its pipeline modules (`data-pipeline/`) or, at level 3, a pinned reference implementation (calls into the standard library, numpy, pandas and plotting, into a function the notebook defines, and readers, loaders, version prints and the pipeline's io, schema and config modules do not count; an object built from a method class and its `.fit` and `.predict` do) | at least 3 | at least 5 |
| Figures (image outputs) | at least 1 | at least 2 |
| A markdown cell of at least 40 words right after each figure | every figure | every figure |
| Explanatory prose, in words, outside Setup, Data and References | at least 500 | at least 800 |
| Setup and input/output cells (imports, versions, paths, readers, nothing else) | at most 2 | at most 2 |
| Reproduction checks (cells comparing a recomputed value with a committed one) | at most 1 | at most 1 |
| Sentences over 50 characters shared with another notebook of the tree, outside Setup, Data and References | at most 2 | at most 2 |
| Generic filler sentences (the list in `notebook_bar.json`) | none | none |
| Lines with two statements, code lines over 120 characters, cells over 30 lines of logic | none | none |
| `**Question:**` in the first cell; `**Answer:**` in Results quoting a number that appears in an output | required | required |
| Level 3: a method cell and a figure under State of the art. Level 4: a figure or a table under Beyond the state of the art | | required |
| Not a copy of the template's example notebooks (`scripts/check_template_residue.py` finds them by content) | required | required |

A notebook with no valid level is measured at level 2 (the missing level is a finding of its own). The Spanish tree is held to
the same floors with its own markers and section names.

How the floors read a notebook, so that a product can write to them:

- **The product declares its method.** `product.json` carries `method_entrypoints`, a list of dotted names (`module.function` or
  `module.Class`) that run the product's method: its predictors, solvers, estimators, split and scoring functions, the pipeline's stages.
  A method cell is a cell that calls one of them, or calls a method (with an argument the notebook read or computed) of an object built
  from a declared class (or from a function listed in the optional `method_factories`, for packages that hand out models through a
  factory such as `make_pipeline`); only the object's own methods count, never a method of one of its attributes (`m.curve.mean(...)`): `model = pkg.Model(k=3).fit(x)` then `model.predict(x)`, a classmethod factory bound to a name, a table of models
  (never the return value of a function, and never `index`, `get`, `keys`, `items`, `count` and the other methods of lists, dicts and
  strings). An alias by assignment is followed; a re-export is resolved from the package's `__init__.py` in the repository or from
  `reexports` in `notebook_bar.json`; a comprehension over an empty literal never runs. Lookups,
  loaders, registries, readers and version prints are never on the list, so they earn nothing. A product without the key, or with it empty (`instantiate.py` writes it empty), fails with one
  finding. `artifact_loaders` (optional) lists the loaders of committed results of the product: a
  value read from one, or from a `data/derived/` path, compared with a value the notebook computed is a reproduction check; residuals
  against measured data are the lesson and are not.
- **Static, the same verdict everywhere.** The gate never asks the environment which module a distribution is imported as. It reads
  `product.json` (`method_packages`, and the optional `import_names` map `{"distribution": "module"}`), the pins of the notebook and the
  static `import_names` map of `scripts/notebook_bar.json` (scikit-learn is `sklearn`); a product with another renamed package adds it
  to its `product.json`. The pipeline's modules are those under `data-pipeline/` and `data-pipeline/src/`.
- **The answer** quotes a number an output of the notebook shows, outside Setup, at the precision the answer writes it: `0.42` against
  `0.4213`, `42 %` against `0.42`, `12,345` or `12.345` against `12345`. A version, a date, a year or a lone digit never counts.
- **At level 3** at least 2 method cells call the product's own method; the pinned reference implementation counts toward the
  method-cell floor and not toward that minimum.
- **Prose** is counted without HTML comments, indented code and tables; a sentence, of any length, that comes back in a notebook
  counts once, and a sentence of four words or more that occurs more than twice is a finding (headings and short labels such as `Units: days.` may come back). No two notebooks of a tree share a question.
- **A copy of the template's example** is found by fingerprints of its long sentences (`example_fingerprints` in
  `notebook_bar.json`; `python scripts/check_notebooks.py --write-fingerprints` rewrites them when the example changes). The template
  itself, which has the `.template-source` sentinel, is left out, as in the residue guard.
- **What a static gate cannot judge.** A sentence reworded by one word, a question that only inspects an artifact and a figure that
  says nothing pass the floors; the review is where they fail.

### The review

Before a release that adds or changes notebooks, every new or changed notebook is read against points 1 to 10 by someone
other than its writer: the main session, or a reviewer. The verdict per notebook (pass, or the points it misses) is recorded in
the coordination repository, and a release ships only notebooks that passed. A writer never reviews its own notebooks.

## 1. Lay out the folder

```
notebooks/
  README.md          the entry (both languages): what the set teaches, how to run it
  requirements.txt   exact pins: the product's PyPI packages first, then the notebook runtime
  en/README.md       the index: topics in order, each notebook with its level, what it teaches, and a reason for a missing level 3
  en/01-<topic>/01-<notebook>.ipynb
  es/README.md       the same index, in Spanish
  es/01-<topic>/01-<notebook>.ipynb
```

- The two trees hold the same notebooks at the same relative paths; the slugs are English so the mirror is checkable.
  Each notebook is written wholly in its tree's language: prose, comments, labels and printed text.
- Topics and notebooks are numbered with two digits, contiguous from `01`. Topic `01` is the entry: install the package,
  load the product's data, get a first result. Each later topic says which earlier ones it needs.
- A topic folder holds only notebooks, and a notebook lives only at `notebooks/<language>/<topic>/<notebook>.ipynb`: one
  loose at a root or nested deeper is refused by the check and never run by the runner.

## 2. Choose the levels

| Level | Name | What it holds |
|---|---|---|
| 1 | Fundamentals | the problem in its context, the data, the idea of the method, a first run on a small real slice |
| 2 | The method in practice | the full algorithm step by step on the data, every intermediate shown, the product's validation of the result |
| 3 | State of the art | the current methods the product's research found, with sources, run or reproduced and compared with level 2 on the same data |
| 4 | Beyond the state of the art | the product's own components that go further, with the evidence |

- Every topic has levels 1 and 2. The level never decreases with the notebook number.
- A topic whose method has state-of-the-art research in the product's dossiers has a level 3 notebook. A topic without
  one says why on its row of each language's index, as `No level 3: <reason>` (`Sin nivel 3: <motivo>` in Spanish),
  four words or more.
- Every component the SDD claims beyond the state of the art has a level 4 notebook (next section).

## 3. Claim and cover a component beyond the state of the art

The SDD's section `## Beyond the state of the art` is either `None claimed.` (the example) or a list of claims, each
with an identifier of the form `BS-<n>` (the first is `BS-1`, then `BS-2`, and so on), its evidence and its source. For
each claim:

1. State it in the SDD section with its identifier, what it adds, the measured evidence and the source it goes beyond.
2. Write a level 4 notebook in each language whose `caos.beyond` lists the identifier, with the sections
   `State of the art` and `Beyond the state of the art` and the evidence: measured size and power, a reconciliation, a
   case the state of the art gets wrong.
3. `scripts/check_notebooks.py` fails an identifier no level 4 notebook covers in each language, and a notebook that
   claims one the SDD does not list.

## 4. Write each notebook

The first cell is markdown: title, level, prerequisites (the earlier notebooks), reading time. Then these second-level
sections, in this order, named in the tree's language:

| English | Spanish | Required |
|---|---|---|
| Objectives | Objetivos | always |
| Setup | Preparación | always |
| Data | Datos | always |
| Method | Método | always |
| State of the art | Estado del arte | level 3 and 4 |
| Beyond the state of the art | Más allá del estado del arte | level 4 |
| Results | Resultados | always |
| Summary | Resumen | always |
| References | Referencias | always |

- **Setup:** the install line in a markdown code block with the exact pins of `notebooks/requirements.txt`
  (`pip install <package>==<version>`), then a code cell that imports the packages and prints their versions
  (`importlib.metadata.version`). A product's own package that is not yet on PyPI is installed from its release tag:
  `notebooks/requirements.txt` holds the line `<name> @ git+https://github.com/<owner>/<repo>.git@<tag>`, the Setup block
  `pip install "git+https://github.com/<owner>/<repo>.git@<tag>"`, and the Setup text the sentence "not yet published on PyPI;
  installed from its release tag" (in Spanish "todavía no publicado en PyPI; instalado desde su etiqueta de versión"). A
  notebook never runs `pip` or `conda`: the check refuses a `%pip` or `!pip` line, a `-m pip` call and a `pip install` in a code
  cell outside a comment.
- **Data:** the owner, the URL, the licence class and the file each source gives; read committed artifacts by a path
  relative to the repository root. No machine path, ever: the check refuses a drive letter in any form (followed by a slash, by one backslash, or by the
  doubled backslashes of a Python literal or a `repr`), a home folder and the POSIX roots `/opt/`, `/tmp/`, `/root/`, `/var/`
  and `/srv/`, in a cell or an output. It cannot know a user name or a host name: the template holds no list of them, so a
  product reads its notebooks' outputs for them before a release.
- **Method:** each equation in markdown with its source (DOI or URL), then run through the product's package, one step per
  cell. A method is imported and never defined in a notebook, an oracle included: the example's final-size solver is
  `final_size` of `data-pipeline/pipeline/oracles.py`, which shares no code with the engine, and the check refuses a cell that
  defines a name the engine (`model/`) or the oracles module already define. The example imports the pipeline by path (`data-pipeline/`) because it publishes no package; a product imports its
  own PyPI package.
- **Step by step:** every code cell is directly preceded by a markdown cell that says what it does and why, and carries at
  least one comment line. One idea per cell, one statement per line, at most 30 lines of logic and 120 characters a line.
- **Results** interprets every figure and table: what it shows, what a validator concludes, what it does not show. Its first
  paragraph is the answer (`**Answer:**`) and quotes a number that an output of the notebook shows.
- **References** lists every source cited with its DOI or URL, and every link of `caos.sources` appears in it (checked). Content comes from the persisted research (the dossiers,
  addenda and SDD), never from memory; each state-of-the-art claim carries its source line.
- Every random draw is seeded.

### The metadata

The notebook metadata holds `kernelspec`, `language_info` and one `caos` block; a cell's metadata holds only `tags`:

```json
"caos": {
  "language": "en",
  "topic": "01-getting-started",
  "level": 2,
  "title": "How wrong is Forward Euler, and when does it matter?",
  "packages": ["numpy==2.4.6", "matplotlib==3.11.2"],
  "data": ["data/derived/manifests/index.json"],
  "sources": ["https://doi.org/10.1007/978-3-540-78862-1"],
  "beyond": []
}
```

`language` is the tree, `topic` the folder, every `packages` entry an exact line of `notebooks/requirements.txt` (`name==version`,
or `name @ git+https://github.com/<owner>/<repo>.git@<tag>` for a package installed from its release tag) shown in the
notebook's Setup text as its `pip install` line, every `data` path a file of the repository, `sources` a non-empty list of links, and `beyond` the
SDD's `BS-` identifiers a level 4 notebook demonstrates (empty below level 4). A notebook and its counterpart in the other
language carry the same level, packages, data, beyond claims and the same sequence of cell kinds.

## 5. Run and check

```bash
./scripts/setup.sh --notebooks             # .venv-notebooks from notebooks/requirements.txt (setup.ps1 -Notebooks on Windows)
python scripts/run_notebooks.py            # every notebook, top to bottom, fresh kernel, outputs written in place
python scripts/run_notebooks.py --only notebooks/en/01-getting-started/01-the-problem-and-the-data.ipynb
python scripts/run_notebooks.py --check --tmp DIR   # executes copies under the temp root DIR (or CAOS_TEMP_ROOT), writes nothing, fails on any error
python scripts/check_notebooks.py          # the static check
python scripts/check_readme_areas.py       # the README by areas
```

- Only the runner writes outputs, so execution counts run 1, 2, 3 with no gap and volatile metadata (timings, the kernel's
  version, widget state) never reaches the commit. Consecutive stream outputs of one name are coalesced into one, so a second
  run writes the same bytes whatever the kernel's flush timing. The outputs are committed: the notebooks read as finished material on
  GitHub. A missing artifact fails the run with its path; nothing stands in for it.
- `scripts/check_notebooks.py` is static and runs in CI and locally: layout, mirror, numbering, levels and their coverage,
  anatomy, metadata, the floors of the bar above, and cleanliness (no error output or stderr stream, no machine path, no token, a notebook up to 3 MB and
  an image up to 400 KB, the limits in the script, no traceback printed to stdout, no `pip` in a code cell). It also fails a CI workflow that executes the notebooks.
- `scripts/run_notebooks.py --check` is a local release gate: run it before every release. It never runs in CI (ADR-0074). It
  executes each notebook in a copy and fails on an error and on committed bytes that differ from the fresh result ("stale": an
  output edited by hand, or a notebook changed without a new run). Figures are compared as bytes, so run the gate on the
  platform and with the pins that wrote the committed outputs.
- The notebook environment `.venv-notebooks` is never committed; on a device with a venvs root it is a junction to it.

## 6. The README by areas

The README's `## Areas` section has one row per area (Web, API, Core pipelines, Packages, Notebooks, Data, Contracts,
Documentation, Tests and gates, Deploy) with its folder as a link, its status (`active`, or `dormant: <reason>`) and what
it holds (three words or more). `scripts/check_readme_areas.py` fails a missing section, area or status, a section placed
before the one-paragraph purpose and the live URLs, a thin "what it holds" cell and a relative link, to a folder or to the
area's own README or doc, that does not exist. The Packages row lists each package the product publishes or consumes for its methods with its version and its PyPI
and repository links; a package installed from its release tag links that tag on GitHub (`https://github.com/<owner>/<repo>/releases/tag/<tag>`) instead of PyPI.
