# Guide: the five documentation pages

Every product carries five documentation pages: Introduction, Methodology, Implementation, Experiments and
Benchmark. This guide says what each must contain. It is transcribed from ADR-0017 section 2.1 of CAOS_MANAGE
(`conventions/architecture/1-frontend/ADR-0017-rotorvitals-frontend-bar.md`, amended 2026-10-12), which is the binding
text; if the two differ, the ADR wins and this guide is wrong.

Two rules hold for the header and the layout, whatever a product adds (Felipe, 2026-10-13, shell 0.13.1). The header
order is always App, Introduction, Methodology, Implementation, Experiments, Benchmark: the App is the leftmost tab, and
the product lands on the Introduction's executive view without moving any tab (the shell's `STANDARD_ROUTES` carries the
order; a product never reorders it). Every documentation route, the Introduction included, takes the full width of the
page: the shell's `DocPage` always renders the wide document layout (its `wide` prop is kept and changes nothing), so a
page never sets a centred reading column of its own.

Status: the checks below run in the shell's gate (`caos-shell-gate`, check `ADR-0017.2`) from shell 0.11.0, which ships
the page components, and the template's example carries every area of the five pages from release 0.06.000 (shell
0.12.0): Methodology has six topics (four classical, two learned), Implementation nine topics in four groups, Experiments
six topics, Benchmark its six areas, the Introduction its two views. A product replaces the content and keeps the
structure, so it needs no rework. The executive view of the Introduction is the shell's standard ([guide 06](06_executive-brief.md)).

## 1. How a section declares its area

A section declares the area it covers: `<DocSection area="...">`, rendered as `data-area`. The vocabulary is fixed per
page (the tables below); an unknown area fails. The gate fails a built page that lacks a required area, or whose
area lacks the content the area requires, in either language (EN and ES). The gate reads
these attributes: `data-stat` (a quantified statement: a value, its unit, its source), `data-qa` (a business question
with its answer) and `data-glossary` (the symbol glossary). The shell renders them from 0.11.0, with equations,
figures and callouts; the component names and props are in the shell's own documentation, which this guide does not
repeat. Do not hand-roll substitutes.

Terms the gate counts:

- A **topic** is a leaf panel of the page: a tab of `Tabs`, a sub-tab of `SubTabs`, or an item of `TabGroups` (at most
  six top-level groups; topics are counted across the groups).
- A **dense paragraph** is a `<p>` of at least 40 words in the displayed language.
- Every documentation page: a lede of at least 35 words; every equation captioned; references in one block at the end
  of the page or the open topic.

## 2. Introduction: two views, the executive one first

The page opens for a decision maker and then serves the engineer. Its two top-level topics are `executive` (the
default, first) and `technical`. The executive view is the shell's `ExecutiveView`, fed by `content/executive.json`: the
landing block (the problem's title, a key statement, headline figures) and five sub-tabs with their fixed titles (the pain,
the context, the current situation, the trends, the proposal), three illustrations and numbered linked sources. It has no
areas to declare and nothing is placed beside it; the product fills the data file and never designs the view
([guide 06](06_executive-brief.md)). It cannot be waived.

Since shell 0.14.0 the executive view shows four groups as small cards that flip (the bearers, the roles, the approaches of
the state of the art and the 4 C's), turns a group of five or more cards into a carousel, and accepts animated
illustrations that carry a `prefers-reduced-motion` block with their static final frame. The rules of use (a title of at
most 8 words and a back of at most 40 in English, 10 and 50 in Spanish; animate what explains a change, a flow or a
sequence; the ten second limit) are in [guide 06](06_executive-brief.md), sections 2.1 and 5.1.

The executive view holds no `Equation` and no symbol glossary (an equation there fails). The technical view holds the
five areas below, with at least 1 overview figure and 3 captioned equations.

| Area (technical view) | What it is | What the gate requires in it |
|---|---|---|
| `problem` | the industrial or scientific problem, with the concrete equipment, setting and who it serves | at least 2 dense paragraphs |
| `principles` | the physics or the domain principles the product rests on | at least 2 dense paragraphs |
| `math` | the governing mathematics | at least 1 captioned equation and a symbol glossary (`data-glossary`) of at least 10 items |
| `pipeline` | the end-to-end pipeline, from the data to the screen | an ordered list of at least 4 steps, and the overview figure here or elsewhere in the view |
| `honesty` | what is exact and what is illustrative; what the product is not | exactly 1 honest callout and at least 1 dense paragraph |

## 3. Methodology (at least 6 topics, one per method family)

| Area | What it is | What the gate requires in it |
|---|---|---|
| `method` (one per topic, with `kind="classical"` or `kind="learned"`) | one method family, as the build runs it: its exact behaviour and constants | at least 4 dense paragraphs, at least 2 captioned equations, at least 1 figure, exactly 1 honest callout (scope, exact versus illustrative), references |
| page level | the ladder from baseline to the state of the art of the domain | at least 2 topics of kind `learned` (the learned methods that are the state of the art for the domain, each beside its classical baseline) |

## 4. Implementation (at least 8 topics)

| Area | What it is | What the gate requires in it |
|---|---|---|
| `architecture` | offline pipeline, compact artifacts, the thin live lane, the browser | 1 figure (the architecture diagram) |
| `reproducibility` | determinism, seeds, versions, how a result is reproduced | at least 1 callout and 1 dense paragraph |
| `engine` (one per engine topic) | the exact algorithm steps, constants, windows and scaling | at least 2 dense paragraphs, at least 1 captioned equation, a where-it-works and where-it-fails callout |
| `lanes` | the live and precompute boundary, and what admits a feature to the live lane | at least 2 dense paragraphs |
| `contract` | the artifact and data contracts | at least 1 table or code block and 1 dense paragraph |
| `deployment` | where and how it is deployed | at least 1 dense paragraph |

## 5. Experiments (at least 6 topics, prose and tabs, never info-box cards)

| Area | What it is | What the gate requires in it |
|---|---|---|
| `question` (one per experimental question) | a distinct experimental question and its answer | at least 2 dense paragraphs |
| `metrics` | the exact metric equations with their real constants | at least 2 captioned equations |
| `protocol` | the leakage-safe, held-out protocol, with the forbidden anti-pattern shown | 1 figure |
| `datasets` | the datasets, their redistribution class and their live or roadmap status | 1 table |

## 6. Benchmark

| Area | What it is | What the gate requires in it |
|---|---|---|
| `results` | held-out numbers read from committed artifacts | 1 table or chart |
| `comparison` | a learned model and a classical baseline on the same real data | 1 table or chart |
| `robustness` | an honest robustness or degradation curve | 1 chart |
| `live` | a live in-browser inference panel on real held-out data | at least 1 control |
| `provenance` | per row: dataset, difficulty source, redistribution | 1 table |
| `caveat` | the honest limits of the comparison | exactly 1 honest or strong callout |

## 7. What the gate cannot measure (a review duty)

That the paragraphs are rigorous and name the build's real constants, that the equations' symbols are defined, that
no visible string holds an internal reference, and that the Benchmark numbers come from committed artifacts. A
reviewer reads these against the rubric before a release is called ready.

## 8. The waiver, and when it is legitimate

A page that cannot carry an area for a stated reason declares it on the page: `floorWaivers` on `DocPage`, rendered as
`data-floor-waiver="<area or floor>: <reason>"`. Legitimate: a product with no learned method (Methodology's
`learned` topics), no live lane (`live`) or no governing equation (`math`). Not legitimate: the executive view or any of its five sub-tabs, which cannot be waived (ADR-0017 section 2.1), or an area
skipped for lack of time. The gate lists every waiver in its report, fails a waiver
without a reason or naming an unknown area, and the waiver is reviewed with the pull request that adds it.

## 9. The order to build a page in

1. Write the executive brief in the SDD ([guide 06](06_executive-brief.md)) and have it reviewed with the plan.
2. Build the Introduction from it: the executive view first (transcribe the landing block and the five sub-tabs, both languages), then the
   technical view from the research dossiers.
3. For each other page, take its area table above as the outline: one `DocSection area="..."` per row, content
   transcribed from the dossiers, the code and its tests, never from memory.
4. Build vertically: finish a topic completely (text, equations with captions, figures, references) before the next.
5. Run the shell's gate (`npm run gate`, from shell 0.11.0), fix what it names, and declare a waiver only for a reason
   the table above allows.
