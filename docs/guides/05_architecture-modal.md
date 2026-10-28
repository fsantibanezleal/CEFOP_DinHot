# Guide: the architecture modal (ADR-0058)

Every product carries the "How it works" modal: at least five tabs, each a hand-authored diagram and a short body, in both languages. The configuration is `frontend/src/architecture/index.ts`, passed to the shell as
`architecture` in `frontend/src/App.tsx`.

## The five tabs, for DinHot

1. The app: what the reader chooses (a case, a method, a device, the traps) and what the six groups of the workbench show.
2. The lanes: what runs offline, what is replayed, what runs live in the browser ([the lanes](../architecture/01_overview.md), [the live lane](../architecture/04_live-lane.md)).
3. The web flow: from the case index to a view, and the gate before a deploy.
4. The science: the chain from the phase mask through the device and the lens to the traps and the trapped particle, and the ladder of methods that produce the mask
   ([the physics chain](../architecture/01_overview.md), [frameworks](../frameworks.md)).
5. The data contracts: what enters the pipeline (a params record) and what it commits for the web (index, manifest, trace, benchmark, model cards, readiness) ([the data contracts](../architecture/08_data-contracts.md)).

A product may add tabs; it never drops below five.

## How a diagram is written

- Inline only. Each SVG lives in `frontend/src/architecture/` and is imported with `?raw`, so it is part of the page and reads the theme's tokens. An `<img>` or a fetched file cannot, and renders black in one theme.
  (The figures in this wiki, in `docs/assets/`, are different: they are viewed on a repository page, so they carry their own light and dark colours.)
- Shell tokens only. Every colour and font is `var(--color-...)` or `var(--font-...)` from the shell's list; no hex colour, no undefined token.
- Both languages in one file. Every translatable `<text>` is written twice at the same place, with the classes `l-en` and `l-es`; the modal shows one. Language-neutral text (numbers, file names, formulas) is written once.
- Marker ids are unique per diagram (for example `id="dc5-arrow"`), because all five can be in the page.

The shell checks the configuration when the app mounts: at least five tabs, inline SVG strings, defined tokens, no hex colours, labels and bodies in both languages. A violation is reported with `console.error`, and the gate
fails a page on any console error, so a broken modal does not ship.

## What the body says

Two to four sentences per tab, in both languages, that say what the diagram shows and why it matters for this product. Numbers in a body are read from the artifacts or are stable facts of the design (a grid size, a schema
version); a count that changes with the data does not belong in a body.
