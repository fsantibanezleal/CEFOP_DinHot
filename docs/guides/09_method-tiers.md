# Guide: the three method tiers and the manuscripts

Every CAOS product implements, for the problem it covers, three tiers of methods, none optional, and keeps its results
on Zenodo. The rule is CAOS_MANAGE `conventions/method-tiers-and-manuscripts.md` (Felipe, 2026-10-28); this guide is how a
product applies it, and the gates below fail a product that does not. The template's own SIR example is the one tree that
may keep a single beyond-the-state-of-the-art line, `None claimed.`, because `.template-source` marks it as the template
(`instantiate.py` deletes that file, and a product is held to the whole rule from its first commit).

## The three tiers

| Tier (`tier` column) | What it is | What it needs before code |
|---|---|---|
| `classical` | The established methods of the problem, from a deep research of the classic literature | A research dossier of the classic methods, their sources and their assumptions |
| `sota` | The current solutions, replicated in the data processing and the engines or implemented as part of the tool, never only cited | A research dossier of current methods (recent, sourced), each replicated on the product's data or implemented |
| `beyond` | Proposed methods that explore new branches and paths for the problem: the product's own proposals | A written proposal per method in the SDD: the hypothesis, the method, the evaluation that would confirm or refute it |

Each tier is real code in the engine or the data processing (or in a published package the product consumes), run on the
product's data and compared with the other tiers on the same data and protocol. The Methodology page presents the three
as tiers, and the benchmark compares them.

A proposal beyond the state of the art answers the problem differently. A validation protocol, a calibration or a benchmark
design is welcome, but by itself it is not a beyond-the-state-of-the-art method: it checks other people's methods more
strictly and proposes none. A proposal that does not improve on the state of the art is still a result: report it as the
negative or partial result it is and keep it.

## In the SDD

The method ladder is a table, one row per method, and the `tier` column says which tier it belongs to:

```
## Method ladder

| id | tier | method | acceptance criterion | gate |
|---|---|---|---|---|
| M-1 | classical | the established method | one measurable criterion | `tests/test_x.py::test_classical` |
| M-2 | sota | the current solution | one measurable criterion | `notebooks/en/01-topic/03-sota.ipynb` |
| BS-1 | beyond | the product's own proposal | the criterion that confirms or refutes the hypothesis | `tests/test_x.py::test_beyond` |

## Beyond the state of the art

- BS-1: the hypothesis, the method and the evaluation that would confirm or refute it, with its source.
```

`M-<n>` identifies a classical or state-of-the-art method and `BS-<n>` a proposal; the id of a `beyond` row is the id of its
claim in `## Beyond the state of the art`. `scripts/check_sdd.py` fails a product when:

- the ladder is not a table with these five columns (an older ladder without the `tier` column fails and the message says to
  add it), a tier is none of `classical`, `sota`, `beyond`, an id repeats or a method is empty;
- a tier has no method, the section on the beyond is missing, says `None claimed.` or lists no `BS-<n>`;
- a `BS-<n>` of the section has no `beyond` row, or a `beyond` row has no claim.

Every finding names the rule file. The template passes with its two rows and `None claimed.`.

## In the notebooks

The notebooks carry level 3 (state of the art) and level 4 (beyond it) for the methods of each tier
([`08_notebooks.md`](08_notebooks.md)). The metadata links them to the ladder:

- a level 3 notebook lists in `caos.methods` the ids of the `sota` rows it runs (`"methods": ["M-2"]`); every `sota` row must
  be named by a level 3 notebook in each language tree, and `caos.methods` may name no other row;
- a level 4 notebook lists in `caos.beyond` the `BS-<n>` claims it demonstrates, and every claim has one in each language.

`scripts/check_notebooks.py` checks both. A topic may still lack level 3 only when it has no method of its own, and says why
in its index row.

## The manuscripts on Zenodo

Every product has a detailed technical report on Zenodo (Technical report, CC BY 4.0, under its own concept DOI) covering the
problem, the three tiers, the data, the protocols and the results. When a beyond-the-state-of-the-art method gives an
interesting approach or result, it gets a manuscript of its own (a preprint or a technical report) with its own concept DOI.
The product declares them in `product.json`:

```json
"manuscripts": [
  {"kind": "technical-report", "concept_doi": "10.5281/zenodo.1234567", "title": "Title as on Zenodo", "version": "0.13.000", "covers": []},
  {"kind": "manuscript", "concept_doi": "10.5281/zenodo.7654321", "title": "Title as on Zenodo", "version": "1.0", "covers": ["BS-1"]}
]
```

| Field | Meaning |
|---|---|
| `kind` | `technical-report` (at least one per product) or `manuscript` |
| `concept_doi` | the concept DOI of the record, `10.5281/zenodo.<N>`, unique in the list |
| `title` | the title as on Zenodo |
| `version` | the version of the Zenodo record; a technical report follows the product's releases (`X.XX.XXX`) and is never ahead of `VERSION` |
| `covers` | the `BS-<n>` claims of the SDD the entry reports; a technical report may cover none, a manuscript covers at least one |

`instantiate.py` writes `"manuscripts": []`, so a new product fails `scripts/check_manuscripts.py` until it declares its
technical report. The manuscripts follow CAOS_MANAGE `manuscript-header-standard.md` and `manuscript-scientific-voice.md`, are
authored in the product repository (`manuscripts/<slug>/`), are published with CAOS_MANAGE `tools/zenodo/` and are recorded in
CAOS_MANAGE `manuscripts/<product>/deposits.json`; the README and the Introduction's technical view link the concept DOIs.

## At each release

- A release that changes a method, a data source or a result publishes a new version of the technical report on Zenodo
  before or with the release, records its version in `product.json`, and runs `python scripts/check_manuscripts.py --release`,
  which fails when a technical report is not at the release's version. A release that changes none of them leaves the report
  as it is (the default run only requires it not to be ahead of `VERSION`).
- `python scripts/check_manuscripts.py --zenodo` reads each concept record on zenodo.org and fails a DOI with no record, a
  record of another concept DOI and a latest version that is not the declared one. It needs the network, so it is a local
  step of the release and never runs in CI (ADR-0074).
- Add `BS-<n>` manuscripts as the proposals produce results; a negative result is reported too.
