# Requirements: the architecture modal

Status: planned

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.
The architecture modal (ADR-0058) shows five bilingual diagrams, `frontend/src/architecture/01-the-app.svg` to `05-data-contracts.svg`. The shell's
measured gate (`npm run gate`) opens it; no product test reads the five diagrams yet, so the feature is planned (`.status-allow`).

| ID | Requirement | Gate |
|---|---|---|
| AR-001 | THE modal SHALL list five diagrams, each an SVG with a view box, a title and a description in English and in Spanish, and no literal colour. | `frontend/scripts/gate.mjs` |
| AR-002 | EVERY animated diagram SHALL carry a `@media (prefers-reduced-motion: reduce)` block that stops its animation. | `scripts/check_svg_animation.py` |
