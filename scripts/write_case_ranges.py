"""Write the section "Expected ranges (checked by the bake)" of every case card from the ranges the bake applies.

The bake checks each case against the ``expect`` of its record in ``data-pipeline/pipeline/cases/library.py``: the measured
ranges of ``data-pipeline/pipeline/cases/measured_ranges.json`` (written by ``python data-pipeline/run.py ranges``) for a case whose
basis is ``provisional``, and the declared published bands plus the measured keys it does not declare for a case whose basis is
``anchor``. A card that states other bands describes a check that does not run, so the section is generated, never typed:
this script replaces the text between the heading ``### Expected ranges (checked by the bake)`` and the next ``## `` heading
of ``docs/cases/<category>/<case_id>.md`` and leaves the rest of the card untouched.

Usage:
    python scripts/write_case_ranges.py            # rewrite the sections
    python scripts/write_case_ranges.py --check    # exit 1 naming each card whose section is not current
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADING = "### Expected ranges (checked by the bake)"
MEASURED = "data-pipeline/pipeline/cases/measured_ranges.json"

MEANING = {
    "efficiency": "fraction of the input power in the trap peaks",
    "uniformity": "1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect",
    "rel_std_pct": "relative standard deviation of the trap intensities, in percent",
    "signal_efficiency": "fraction of the input power in the signal region of the shaped field",
    "signal_rms_error_pct": "RMS fractional error of the shaped field over its measure region after the scale fit, in percent",
    "feedback_initial_rel_std_pct": "measured spread before the camera loop, in percent",
    "feedback_final_rel_std_pct": "measured spread after the camera loop, in percent",
    "fc_ratio": "fitted corner frequency over the expected one (bead), or fitted over expected trap frequency (atom)",
    "boltzmann_tv": "total variation between the position histogram and the Boltzmann law, 0 is a perfect match",
    "final_filling": "fraction of the target sites filled after the rearrangement",
    "min_transient": "lowest intensity of a moving trap over the sequence, over the mean trap intensity",
}


def _g(x: float, digits: int) -> str:
    return format(float(x), f".{digits}g")


def _meaning(key: str) -> str:
    metric = key.split(".")[-1]
    if metric not in MEANING:
        raise KeyError(f"no meaning for the metric {metric!r}: add it to MEANING in scripts/write_case_ranges.py")
    return MEANING[metric]


def section(case, measured_doc: dict, refused: bool) -> str:
    """The generated section for one case (heading included, ending with a blank line)."""
    expect = case.record["expect"]
    values = measured_doc["measured"].get(case.id, {})
    seeds, rule = measured_doc["seeds"], measured_doc["rule"]
    rel_pct = _g(100 * rule["rel"], 3)
    out = [HEADING, ""]
    if refused or not values:
        out += [f"Basis of the bands: **{case.expect_basis}**, declared in the case library. The case is refused by contract 1 and never computed,",
                "so these bands are never checked; they state what a valid record of this kind would be held to.", "",
                "| Key | Range | Meaning |", "|---|---|---|"]
        out += [f"| `{k}` | {_g(lo, 4)} to {_g(hi, 4)} | {_meaning(k)} |" for k, (lo, hi) in sorted(expect.items())]
        return "\n".join(out) + "\n\n"
    if case.expect_basis == "anchor":
        out += ["Basis of the bands: **anchor**. The keys without a method name are the published bands of the validation anchor, kept as",
                "declared (they apply to the reference method); the `<method>.<metric>` keys are measured and added where the anchor declares",
                f"nothing: {seeds} seeds (the case seed and the next ones), range = mean plus or minus the wider of {rel_pct} percent of the mean",
                "and the seed spread, clipped to the domain."]
    else:
        out += [f"Basis of the bands: **measured**, {seeds} seeds (the case seed and the next ones), range = mean plus or minus the wider of",
                f"{rel_pct} percent of the mean and the seed spread, clipped to the domain."]
    out += [f"The values are in `{MEASURED}` (`data-pipeline/pipeline/ranges.py`); every method range is keyed `<method>.<metric>`,",
            "so it is never applied to another method. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).",
            "This section is written by `scripts/write_case_ranges.py`."]
    fixed = sorted({k.split(".")[0] for k, v in values.items() if "." in k and len(set(v)) == 1 and len(v) > 1})
    if fixed:
        out += [f"The seeds of {', '.join(fixed)} give the same value (the method does not depend on the seed here), so the band is the "
                f"{rel_pct} percent floor."]
    out += ["", f"| Key | Range | Measured on the {seeds} seeds | Meaning |", "|---|---|---|---|"]
    for k, (lo, hi) in sorted(expect.items()):
        got = values.get(k)
        shown = ", ".join(_g(x, 6) for x in got) if got else "declared (anchor)"
        out.append(f"| `{k}` | {_g(lo, 4)} to {_g(hi, 4)} | {shown} | {_meaning(k)} |")
    return "\n".join(out) + "\n\n"


def replace_section(text: str, new: str, where: str) -> str:
    i = text.find(HEADING)
    if i < 0:
        raise ValueError(f"{where}: no heading {HEADING!r}")
    j = text.find("\n## ", i)
    if j < 0:
        raise ValueError(f"{where}: no '## ' heading after {HEADING!r}")
    return text[:i] + new + text[j + 1:]


def cards(root: Path) -> dict[str, Path]:
    return {p.stem: p for p in (root / "docs" / "cases").glob("*/C*.md")}


def run(root: Path, check: bool) -> list[str]:
    sys.path.insert(0, str(root / "data-pipeline"))
    from pipeline.cases import library  # noqa: PLC0415 (the pipeline lives beside this script)
    from pipeline.io import contract  # noqa: PLC0415

    measured_doc = json.loads((root / MEASURED).read_text(encoding="utf-8"))
    # the cases contract 1 refuses are never computed (C11 by design): the same test the bake applies
    refused = {r["case_id"] for r in contract.validate_records([c.record for c in library.CASES], root).rejected}
    found = cards(root)
    stale: list[str] = []
    for case in library.CASES:
        path = found.get(case.id)
        if path is None:
            stale.append(f"{case.id}: no card docs/cases/*/{case.id}.md")
            continue
        text = path.read_bytes().decode("utf-8")
        new = replace_section(text, section(case, measured_doc, case.id in refused), str(path.relative_to(root)))
        if new != text:
            stale.append(str(path.relative_to(root)).replace("\\", "/"))
            if not check:
                path.write_bytes(new.encode("utf-8"))
    return stale


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="report the cards whose section is not current; write nothing")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args(argv)
    stale = run(Path(args.root), args.check)
    if args.check:
        if stale:
            print("case ranges: stale (run python scripts/write_case_ranges.py)\n  " + "\n  ".join(stale))
            return 1
        print("case ranges: every card states the ranges the bake checks")
        return 0
    print(f"case ranges: wrote {len(stale)} card(s)" + ("".join(f"\n  {s}" for s in stale)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
