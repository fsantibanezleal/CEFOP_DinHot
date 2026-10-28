# Guide: write the executive view

The executive view is the first thing a CAOS product writes, before its sizing, its contracts and any code. It frames the
problem space the product works in, for a senior decision maker, in executive language, and it is kept in one data file,
`content/executive.json`, that the shell renders as the first view of the Introduction, where the product lands (the App stays the leftmost tab). This guide
is enough to fill it with no other context. The binding text is CAOS_MANAGE `conventions/problem-context-first.md` (Felipe,
2026-10-12 and 2026-10-13); the shell's own guide is its page `06_executive-view` (CAOS_APP_SHELL, folder `docs`). If they
differ from this page, they win.

A product writes content. It never designs this view: the shell's `ExecutiveView` takes no children, no section can be
added, removed or reordered, and the shell's gate cannot be waived for it.

## 1. Why it is the core, and what it is not

Felipe, 2026-10-12: "force that, it is the point of my apps, anyone can write code and release an app, but tailored
on a real problem context is the expected core." And: "the intro must have 2 visions, the executive and the technical."

Felipe, 2026-10-13: "It is an executive view to cover what the pain in the industry is, its context, its current
situation, its current trends, and the proposal." And: "the problem can be wider than what we cover in the app, they are
not the same." And: "That app is not designed for a specific client. It must be general ... I'm not selling or promoting
that to anybody."

So the view is a frame of the industry's problem, not a description of the product. It is never tied to a client (no named
bank, company, hospital or person, no "our client"), never a pitch (no offer, price, contact or call to buy), and it is not
filler: each sub-tab has real depth, written for a decision maker ("it requires a deep understanding of the problem, but
set as an executive problem framework"). Named institutions appear only as the sources of public facts.

## 2. The structure

**The landing block**, above the sub-tabs: the problem's `title`; a `key_statement` of one or two sentences naming the pain
and the direction proposed; two or three `headline_figures`, each a short heading, one figure with its unit and its linked
source. The model of a why-now is a sector-level figure from a public publication, with its deadline when it has one,
naming no organisation.

**Five sub-tabs**, the first open, titled by the shell. Each opens with one `key_message` line (a reader can stop at the
five lines), then its supporting content at its floor:

| # | Sub-tab | Key message | Floor | Avoid | The reader can then say |
|---|---|---|---|---|---|
| 1 | The pain | What goes wrong, for whom, how big | Two paragraphs; 3 to 5 bearers (who bears it, the cost, how it is measured); 2 to 4 sourced figures; 3 to 5 causes, non-overlapping, weighted by size; the pain illustration | A feature list, a pitch, one named organisation, an unsourced number | The pain is X, it falls on Y, it costs Z, and it comes mainly from these causes |
| 2 | The context | The force that keeps the pain going | One or two paragraphs; the setting; 3 or 4 forces, each with its direction; 1 to 4 sourced pieces of evidence | History of the field, long background | This is the world the problem lives in and what keeps it going |
| 3 | The current situation | How it is handled today and where that falls short | 3 to 5 roles (what each decides, what it needs) and how they interact; 3 to 5 approaches of the state of the art, each with what it achieves and where it falls short, fair to each; one sourced status figure with its date; the situation illustration | A product comparison, a vendor named as the problem | These are the roles, this is what exists, and why it is not enough |
| 4 | The trends | The shift that makes it urgent, with its horizon | 3 to 5 trends (regulatory, technological, market, practice), each with direction, horizon (now, two years, ten years), a sourced signal, its effect on the roles of tab 3 and how sure the signal is | Hype, a trend without its effect on a role, an unsourced forecast | This is changing, by when, and who it hits first |
| 5 | The proposal | The approach in one sentence and the first action with its owner | One or two paragraphs tied to the causes of tab 1; the 4 C's, each applied; 3 to 6 actions (owner, horizon, how success is checked); 1 to 4 risks and 1 to 4 unknowns; the proposal illustration; at most one closing line on the part the work explores | A call to buy, a price, a contact, a feature tour, an action without an owner | This is how the problem should be approached, who does what by when, and how we would know |

### 2.1 Cards that flip, and the carousel (shell 0.14.0)

The shell shows four groups of the view as small cards that flip: the bearers of the pain (`pain.bearers`), the roles
(`situation.roles`), the approaches of the state of the art (`situation.state_of_the_art`) and the 4 C's
(`proposal.four_cs`). The face shows the title; a click, Enter or Space turns the card and shows its content on the back;
Escape or another click turns it back. The other groups (`context.forces`, `trends.items`, `proposal.actions`) stay plain. A
product does not choose which groups flip; it writes the data so that those four groups fit the rule of use.

**The rule of use (Felipe, 2026-10-13): small cards only, where the reader scans the titles and opens the ones that matter.**
A card is small when its title has at most 8 words in English and 10 in Spanish and its back at most 40 words in English
and 50 in Spanish, the labels the shell prints on the back (such as "Cost" or "Falls short") counted. The gate (G16) fails a
longer title or back, so a longer text is cut, or the point is moved into a paragraph, where it reads whole. A card that
needs more than that is not a flip card and is not written as one.

**The carousel.** A group longer than four cards is shown as a carousel: as many cards as fit the width (at least one),
previous and next buttons, a swipe on touch, the arrow keys, Home and End, and a position ("2 of 5"). There is no autoplay,
every card is reachable by keyboard and the page never scrolls sideways. The floors allow up to five bearers, five roles and
five approaches; a group of five is a carousel, so write a fifth card only when it carries real content (the example holds
five bearers, the fifth being the ambulance crews held at the hospital door), never a filler to reach the number.

Below the sub-tabs the shell lists the numbered linked sources and two onward links, "How the work explores this problem"
(the technical view) and "Open the App". The App is at `/app`; the root opens this view.

## 3. The research it needs first

Never write the view from memory. Research the problem space and persist it as dated dossiers (cited in `Research basis`):

1. **What goes wrong, for whom, how big?** Primary sources you read: a public agency, a statistics office, a peer-reviewed
   study. Note the figure, its unit, its date and the page.
2. **What keeps it going?** The rules, the funding, the data and the habits of the setting, each with a source.
3. **Who is involved and what exists today?** The roles, how they interact, and the approaches in use with their evidence and
   their limits, fair to each.
4. **What is changing?** Regulatory, technological, market and practice signals, each with a date and how sure it is.

A figure or a claim of the state of the art or of the trends with no primary source you read is not written. Every source is
a title and an https link.

## 4. The data file

`content/executive.json`, English and Spanish together, valid against the shell's `executive.schema.json` 2.0.0 (installed
by `npm ci` at `frontend/node_modules/@fasl-work/caos-app-shell/src/content/executive.schema.json`). These fields and nothing
else; every text is `{ "en": ..., "es": ... }`.

| Where | Field | Rule |
|---|---|---|
| landing | `title`, `key_statement` | One sentence; one or two sentences |
| landing | `headline_figures` | 2 or 3: `heading`, `value`, `unit`, `source` (a source id) |
| 1 | `pain` | `key_message`; `paragraphs` (2 or 3); `bearers` (3 to 5: `who`, `cost`, `measure`; flip cards, a carousel at 5); `figures` (2 to 4, as above); `causes` (3 to 5: `cause`, `weight` a whole percent, adding to at most 100) |
| 2 | `context` | `key_message`; `paragraphs` (1 or 2); `setting`; `forces` (3 or 4: `force`, `direction` rising, easing or steady); `evidence` (1 to 4: `statement`, `source`) |
| 3 | `situation` | `key_message`; `roles` (3 to 5: `role`, `decides`, `needs`); `interaction`; `state_of_the_art` (3 to 5: `approach`, `achieves`, `falls_short`, `source`); `status` (`heading`, `value`, `unit`, `date`, `source`) |
| 4 | `trends` | `key_message`; `items` (3 to 5: `trend`, `kind`, `direction`, `horizon`, `signal` with `statement` and `source`, `effect`, `confidence`) |
| 5 | `proposal` | `key_message`; `paragraphs` (1 or 2); `four_cs` (exactly 4: `c`, `applies`); `actions` (3 to 6: `action`, `owner`, `horizon`, `check`); `risks`; `unknowns`; optional `handoff` |
| 1, 3, 5 | `illustrations` | Exactly `pain`, `situation`, `proposal`: each an SVG `file` (a path under `frontend/public/`, or one per language) and a `caption` (one sentence) |
| all | `sources` | `{ id, title, url, note? }`: see below |

**The 4 C's** frame the proposal, verbatim and in this order: Choice (flexibility across proprietary and open models),
Context (AI grounded in business meaning, so decisions are accurate), Cost (visibility of what the AI spends), Control (one
governance over data, models and agents). Each `c` is the name in both languages (Elección, Contexto, Costo, Control) and
`applies` says, in one sentence, what that C means for this proposal and its roles.

**Sources are links.** Each source has a lower-case `id`, a `title` (the publication in plain words), an https `url` and an
optional one-sentence `note`. Every figure and every claim of the state of the art and of the trends cites one by id, every
source is cited, and no sub-tab names more than about six. A source is never a file name, a file number or a prose citation.

**Owners are roles.** Each action's `owner` is one of the `situation.roles`, written the same in both languages.

**Weights are the author's judgement of relative size** unless the sizing measures them; say so in `unknowns` when they are an
estimate (the example does).

Writing limits, checked by `scripts/check_sdd.py`, by `validateExecutive` (run in `frontend/src/content/executive.test.ts`)
and by the gate on the rendered page, in both languages alike:

- every sentence at most 30 words; one sentence for the key messages, the interaction, the evidence statements, the signals,
  what each C means, the actions and their checks, the risks, the unknowns, the handoff and the captions; at most two for
  the key statement;
- a paragraph of at least 25 words (no one-line sections, no restating the title);
- no equation, no formula, no code (a `$`, `\(`, `\[` or a TeX command fails);
- no inline citation (`(Source`, `[1]`, a parenthesised author and year): the source goes in `sources`;
- no promotional or client-bound wording, whole words in either language and either case: our client, contact us, buy,
  price, offer (and their Spanish forms);
- no acronym without its words in full the first time (a reviewer's duty).

The template ships a filled example: hospital capacity in respiratory seasons, framed for no single hospital, every figure
read at its source. Replace every field.

## 5. The three illustrations

Felipe, 2026-10-12: "i need high quality diagrams, not graphs, illustrations of the initiative, the problem, the proposed
solutions." Three, authored for the product, as SVG files under `frontend/public/executive/`:

| Illustration | Placed in | What it shows |
|---|---|---|
| `pain` | Sub-tab 1 | What goes wrong in the industry: the actors, the systems and the failure, drawn as a scene. |
| `situation` | Sub-tab 3 | How the problem is handled today: the roles and the current approaches, and where they fall short. |
| `proposal` | Sub-tab 5 | The same setting with the proposed approach in place, and where it changes the outcome. |

Each meets this standard:

- An illustration, not a graph: a drawn scene of people, places, systems and their flow; no axes, no plotted data, no
  chart, no screenshot, no stock image, no boxes joined by arrows.
- Hand-authored SVG with a `viewBox`, inserted inline by the shell (never through an `img` tag, which cannot read the
  theme). Coloured only with the shell's theme tokens (`var(--color-...)`), `none` or `currentColor`, correct in light
  and dark. Give `text` no font family of its own.
- Labels in plain business words, in English and Spanish, inside the drawing: one file carries both sets, each `text`
  marked `data-lang="en"` or `data-lang="es"`. Readable at the rendered size: at least 9 px once scaled to the column, so
  in an 800 wide viewBox use a font size of 22 and keep each label short, on a chip that fits the wider language.
- No equation, no acronym, no `data-chart`, no named organisation.
- One caption sentence under each, saying what the reader should take from it.
- The pain and the proposal share the same setting and layout, so the change is visible between them (the example keeps the
  hospital, its wards, hall, theatre and lounge in the same places in both, with the queue, the full beds and the cancelled
  surgery replaced by the free beds, the planning board and the surgery that goes ahead).

### 5.1 Animation: when to animate, and the reduced-motion block (shell 0.14.0)

Felipe, 2026-10-13: "in the intro promote the use of animation, not only static illustration". **Animate an illustration
when it explains a change, a flow or a sequence**: the pain growing, the roles handing work over, the proposal's before and
after. A still stays right for a single state (a map of who is where, a snapshot). The example's pain illustration is
animated: the winter wave arrives, the queue of waiting patients grows one by one, a clock runs and the surgery is
cancelled, with the labels fixed in place.

An animated illustration is an SVG that carries its animation in the file (CSS keyframes or SMIL; CSS keyframes are the
choice for a figure in a documentation page) and keeps these rules:

- a gentle loop or a single play of **ten seconds at most**;
- theme tokens only, as for any illustration, and **labels that stay put**: only the scene moves;
- **a `@media (prefers-reduced-motion: reduce)` block in the file that stops every animation (`animation: none`) and shows the
  static final frame.** Draw the drawing without the animation as its final frame (everything visible, nothing translated),
  and let the keyframes start from the hidden or displaced state, so the reduced-motion block only has to switch them off.

The shell pauses a SMIL animation at its last frame under reduced motion in the executive view and removes an animation
that writes a link or an event handler. `scripts/check_svg_animation.py` (run in CI after `npm ci`) reads every `.svg` under
`frontend/public/` and `frontend/src/` with the shell's own analysis (`analyseSvgAnimation` and `animationFailures` of the
installed shell's `gate/areas.mjs`, so it and the gate's G17 cannot disagree) and fails an animated file with no
reduced-motion block, with a block that does not stop its animation, or that plays for more than ten seconds.

The shell's gate measures what a machine can: the three exist, are inline, use only tokens, declare no chart, and every
label sits inside its drawing at a readable size in both languages; G16 measures the flip cards and the carousel and G17 the
animated drawings, also under emulated reduced motion. Whether a drawing reads as a scene and not as a chart in
disguise is a reviewer's judgement.

## 6. The SDD names the file

The design document's `Executive brief` section (right after `Problem and non-goals`) says what the file is and where
it is, and nothing more: a short paragraph and the line

```
Data file: content/executive.json
```

It restates nothing: no part headings, no list, no table, no sentence copied from the file, at most 120 words.

## 7. What `scripts/check_sdd.py` fails

- `content/executive.json` is missing, is not JSON, breaks the schema or has a sub-tab below its floor (each finding names
  the field path, such as `pain.bearers[1].cost`);
- the shell's schema is not installed or is not version 2.0.0 (run `npm ci` in `frontend/`; the check fails rather than pass
  unvalidated);
- the 4 C's are out of order, the weights of the causes add to more than 100, an action's owner is no role of the situation;
- a sentence is over 30 words, a one-sentence field has two, a paragraph is under 25 words, a text holds an equation, an
  inline citation or promotional or client-bound wording;
- a figure or claim cites an id that is no source, a source is cited by nothing, two sources share an id, a source is not an
  https link or cites a file in place of the link;
- an illustration file is missing, leaves `frontend/public/`, or is not an SVG with a viewBox;
- (`scripts/check_svg_animation.py`, not `check_sdd.py`) an animated SVG has no `prefers-reduced-motion` block that stops it, or
  plays for more than ten seconds;
- the SDD has no `Executive brief` section in its place, lacks the `Data file:` line or restates the view.

## 8. Checklist

- [ ] The dossiers answer the four questions of section 3 and are cited in `Research basis`.
- [ ] The view frames the industry's problem: no client, no product, no pitch, no feature list.
- [ ] Two or three headline figures and at least seven sourced figures and claims across the sub-tabs, each a link.
- [ ] Each sub-tab meets its row of the table in section 2: its key message, its floor, what it avoids, what the reader can say.
- [ ] The 4 C's each applied in one sentence; every action has an owner that is a role, a horizon and a check.
- [ ] Three illustrations that are scenes, in tokens, with both languages, the pain and proposal sharing a setting.
- [ ] The four flip groups hold small cards (a title of at most 8 words, a back of at most 40; in Spanish 10 and 50), and a
  group of five is a carousel of real content, not filler.
- [ ] Each illustration that explains a change, a flow or a sequence is animated (ten seconds at most, labels fixed) and
  carries its `prefers-reduced-motion` block with the static final frame; a single state stays a still.
- [ ] `python scripts/check_sdd.py .` and `npm test` pass, `npm run gate` reports 0 failures, and a reviewer has read the
  rendered view against the row of each sub-tab.

Next: [guide 07, the five documentation pages](07_documentation-pages.md) carries the technical view of the page.
