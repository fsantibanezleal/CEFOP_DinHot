"""pipeline, the offline+live engine for the CAOS product-repo template (ADR-0057).

Rename this package to `pipeline` per product and replace the EXAMPLE engine (model/ + the stage bodies) with the
deep-research-chosen SOTA engine. Everything else (the two data contracts, the staged pipeline, the lane gate, the
manifest/trace, the cases-by-category registry) is the FROZEN base, instantiate it, do not redesign it.
"""

from pathlib import Path

# VERSION at the repository root is the only place the version is written (T4); every manifest records it.
__version__ = (Path(__file__).resolve().parents[2] / "VERSION").read_text(encoding="utf-8").strip()
