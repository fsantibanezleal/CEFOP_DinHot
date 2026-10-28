# The specification area

Where a product states what it will build and proves the statement can fail. It is written before any code
(ADR-0075) and kept current with it: a guard fails when a part is missing or disagrees with the repository.
The area is `docs/design/` (the design), `docs/contracts/` (the contracts as code) and `tests/` (the tests, with
`tests/adversarial/` for the planted defects).

## The order

Research, then the executive brief, then sizing, contracts and the units.

1. **Research basis.** What was researched before the plan and what it decided: each claim with a source (a DOI or a
   URL), at least three distinct sources (one work cited as a DOI and as its URL counts once; example and localhost
   hosts count for none), and a line starting `UNVERIFIED:` for what stayed unverified (it may say none). Section
   `Research basis` of [`SDD.md`](SDD.md). Checked by `scripts/check_sdd.py`.
2. **Executive view.** The problem space in its real context, framed for a decision maker in executive language, before any
   development, general (never a client, never a pitch): one data file, `content/executive.json`, valid against the
   shell's `executive.schema.json` 2.0.0 (a title, a key statement and headline figures; five sub-tabs: the pain, the
   context, the current situation, the trends and the proposal with the 4 C's; three illustrations; a linked source for
   every figure and claim). Section `Executive brief` of [`SDD.md`](SDD.md), right after `Problem and non-goals`, names the
   file in a `Data file: content/executive.json` line and restates nothing. Checked by `scripts/check_sdd.py` (the file,
   its schema, its rules, its sources, its illustrations, the section). How to write it:
   [`../guides/06_executive-brief.md`](../guides/06_executive-brief.md).
3. **Sizing, summarised.** The product dimensioned before it is built: its components, its boundaries, the
   technology and version matrix and the resources of each stage. The sizing's coordination records (the parallel
   units, who owns them) live with the product's coordination, not here; this repository holds the product's own
   design facts. Sections `Sizing and contracts`, `Technology and versions` and `Resources` of [`SDD.md`](SDD.md).
   Checked by `scripts/check_sdd.py` (the twelve sections are headings outside code fences, once, in order, each with
   a body; the resources table has one row for each of bake, tests, build and deploy and no empty or placeholder cell)
   and `scripts/check_tech_matrix.py` (the technology table is the pinned dependencies, version for version: every
   `requirements*.txt`, `pyproject.toml` dependencies and `frontend/package.json` including optional, peer and
   overrides; Python pins are exact `==`; a package.json range is allowed only when the lock records the same spec at
   its root and its locked version satisfies it, and the table holds the locked version).
4. **Contracts.** One row per boundary and per model slot in [`../contracts/catalog.md`](../contracts/catalog.md), one
   schema file each, an example, a test on each side, the missing-data behavior and a provider. A contract is mutable
   and versioned: its version follows its schema by semver, its history is a row per version whose kind is the semver
   step, and [`../contracts/versions.lock.json`](../contracts/versions.lock.json) holds the digest of each schema.
   Checked by `scripts/check_contracts.py`, `scripts/check_skeleton.py`, `scripts/check_readiness.py` and
   `scripts/check_contract_versions.py` (CI runs it with `--base`, against the schemas at a git ref, so a hand-edited
   lock proves nothing).
5. **Requirements.** Per feature, `features/<feature>/requirements.md`: `| ID | statement | gate |`, every statement
   with SHALL, every gate a test or guard that exists and can fail: a `path::name` that names a live test in a test file
   (not in a string, a comment, another test's body or a skipped test), or a plain path that is a test file or a script.
   A row that is malformed, indented or split across lines is a finding, and so is a status other than live without an
   entry and a reason in `features/.status-allow`. Checked by `scripts/check_sdd.py`.
6. **Tests, red first.** Each requirement and edge case becomes a test that fails for the right reason before the
   code exists (`tests/`, `frontend/src/**/*.test.ts`); the code that follows is the minimum that turns them green.
7. **Adversarial validation.** Per feature, `features/<feature>/validation.md`: `| requirement | adversarial check |
   gate |`, one row per requirement, the check stated as what was planted or refuted ("a NaN parameter is rejected")
   and the gate the test that plants it: a test under `tests/adversarial/`, or one named `test_adversarial_...` (Python) or
   `it('adversarial: ...')` (TypeScript). An ordinary test proves the requirement passes, not that it can fail. The adversarial name is a claim that a reviewer
   verifies against the planted defect, not proof: the guard checks the form (`test_adversarial_` and `adversarial: `
   with their separator), never what the test plants. A gate that skips for lack of a tool (a `skipif` mark, a
   `pytest.skip`, an `importorskip` of a package no requirements file pins) counts as not run: the row names a second
   gate that runs without the tool, or says `local-only: <why>` (five words or more) in its check cell, a reviewed
   exception for what needs node, a browser or the installed frontend. The
   guards are attacked too: `tests/adversarial/` copies the files a guard reads, plants one defect, runs the guard and
   asserts the exit code and the message. Checked by `scripts/check_sdd.py` and `python -m pytest tests/adversarial -q`.

## Where each part lives

| part | file | guard |
|---|---|---|
| research basis | `docs/design/SDD.md`, `Research basis` | `scripts/check_sdd.py` |
| executive view | `content/executive.json`, `docs/design/SDD.md`, `Executive brief` | `scripts/check_sdd.py`, the shell's gate |
| sizing summary, technology, resources | `docs/design/SDD.md`, `Sizing and contracts`, `Technology and versions`, `Resources` | `scripts/check_sdd.py`, `scripts/check_tech_matrix.py` |
| contracts, providers, states | `docs/contracts/catalog.md`, `docs/contracts/schemas/` | `scripts/check_contracts.py`, `scripts/check_skeleton.py`, `scripts/check_readiness.py` |
| contract versions and history | `docs/contracts/catalog.md` (`History`), `docs/contracts/versions.lock.json` | `scripts/check_contract_versions.py` |
| requirements | `docs/design/features/<feature>/requirements.md` | `scripts/check_sdd.py` |
| adversarial validation | `docs/design/features/<feature>/validation.md`, `tests/adversarial/` | `scripts/check_sdd.py`, `tests/adversarial/` |

## Changing a contract

Edit the schema, bump the version in the catalog by the semver rule (removed or renamed field, narrowed type or new
required field: major; new optional field: minor; description or example: patch), add the History row, then
`python scripts/check_contract_versions.py --update` and `python data-pipeline/run.py readiness`, and update both sides
in the same pull request. The check fails on a schema that changed under the same version (against the lock, and
against the base ref in CI), a version that went down, a lock that is not current, a History kind that is not the semver
step, a breaking change that is not a major bump, and a row without a History entry for its version. The breaking-change
test is a mechanical floor (a minimal JSON Schema diff, listed in the catalog); the reviewer still judges the semantic
breaks it cannot see.

CI runs the checks above in the `checks` job (ADR-0074: cheap checks, no new job); the product's own tests and the bake run
locally. The one pytest command CI may run is exactly `[pip install pytest==X.Y.Z && ]python -m pytest tests/adversarial[ -q]`;
`scripts/check_ci_budget.py` fails on anything broader.

## Known limits of the guards

Listed so nobody takes a pass for more than it is; none is fixed in 0.05.000 (found by the re-review of 2026-10-12).

- `check_contract_versions.py`: the mechanical floor does not see `contains`, `dependentRequired`, `propertyNames`,
  `if`/`then` or `unevaluatedProperties` added as new constraints. `--base ''` (an empty ref) is read as no base
  (CI cannot pass one: it falls back to `origin/develop`). In a product inside a subdirectory of a repository,
  `git show REF:docs/contracts/catalog.md` is relative to the repository top, so the base catalog is not found and the
  check reads it as a first release.
- `check_tech_matrix.py`: it has no `--base`; in `frontend/package-lock.json` it does not check that `resolved` names
  the locked version, and a git pin on a branch name passes as a pin (a SHA or a tag is better).
- `check_sdd.py`, the executive view: the shell's schema is read from `frontend/node_modules`, so the check needs
  `npm ci` first (it fails, and says so, without it, and with a schema that is not 2.0.0) and the `jsonschema` package. The
  rules a schema cannot say (the writing limits, the 4 C's, the owners, the weights, the sources by id, the wording) are
  held twice, in this script and in the shell's `validateExecutive` that `frontend/src/content/executive.test.ts` runs;
  the acronym rule, whether a figure says what its source says, and what an illustration draws are the shell's gate and a
  reviewer's judgement.
- `check_ci_budget.py`: a regular-expression detector cannot see every way to start pytest (for example
  `python -c "import pytest; pytest.main(...)"`).
