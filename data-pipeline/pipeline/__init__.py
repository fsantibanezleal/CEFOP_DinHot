"""pipeline, the offline engine of DinHot and the reference of its live lane (ADR-0057).

The engine is `model/holo/` (the forward models, the device model, the methods of the ladder and the learned slots), with
the stage bodies that bake, evaluate, benchmark and train. The two data contracts, the staged pipeline, the lane gate, the
manifest and trace and the cases-by-category registry are the template's frozen base.
"""

from pathlib import Path

# VERSION at the repository root is the only place the version is written (T4); every manifest records it.
__version__ = (Path(__file__).resolve().parents[2] / "VERSION").read_text(encoding="utf-8").strip()
