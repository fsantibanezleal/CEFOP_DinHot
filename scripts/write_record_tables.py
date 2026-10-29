"""Write the per-case table of the canonical bake in every method design record from the measured values.

A design record in ``docs/design/methods/`` states what its method measured in the canonical bake: one row per case, the mean
over the measured seeds with the range, of the efficiency, the uniformity and the relative standard deviation. The values are
those of ``data-pipeline/pipeline/cases/measured_ranges.json`` (``measured``, written by ``python data-pipeline/run.py
ranges``), so the rows are generated, never typed: this script rewrites the rows that follow the header
``| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |`` of each record and leaves the rest
of the record, the sentence that introduces the table included, untouched. The method of a record is the ladder id that
starts its file name (``M07-...``); a beyond record (``BS-1-...``) reads its engine id (``B1``). A case appears when the
measured values hold the three metrics of that method for it; the iterations are the budget of the case's record.

Usage:
    python scripts/write_record_tables.py            # rewrite the rows
    python scripts/write_record_tables.py --check    # exit 1 naming each record whose rows are not current
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = "| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |"
MEASURED = "data-pipeline/pipeline/cases/measured_ranges.json"
CASES = "data/examples/cases.json"
METRICS = ("efficiency", "uniformity", "rel_std_pct")


def method_of(path: Path) -> str | None:
    m = re.match(r"(M\d\d|BS-\d)-", path.name)
    if not m:
        return None
    return m.group(1).replace("BS-", "B")


def _g(x: float) -> str:
    return format(float(x), ".3g")


def cell(values: list[float]) -> str:
    mean = sum(values) / len(values)
    return f"{_g(mean)} ({_g(min(values))} to {_g(max(values))})"


def rows(method: str, measured: dict, iterations: dict, kept: dict | None = None) -> list[str]:
    out = []
    kept = kept or {}
    for case_id in sorted(measured):
        vals = measured[case_id]
        keys = [f"{method}.{m}" for m in METRICS]
        if not all(k in vals for k in keys):
            continue
        short = case_id.split("_")[0]
        its = kept.get(short, iterations.get(case_id, "-"))
        out.append(f"| {short} | {its} | " + " | ".join(cell(vals[k]) for k in keys) + " |")
    return out


def kept_iterations(text: str) -> dict:
    """The Iterations column of the rows a record states, by case."""
    lines = text.replace("\r\n", "\n").split("\n")
    if HEADER not in lines:
        return {}
    h = lines.index(HEADER)
    out = {}
    for line in lines[h + 2:]:
        if not line.startswith("| C"):
            break
        parts = [x.strip() for x in line.strip("|").split("|")]
        out[parts[0]] = parts[1]
    return out


def existing_rows(text: str) -> list[str]:
    """The rows a record states, in order."""
    lines = text.replace("\r\n", "\n").split("\n")
    if HEADER not in lines:
        return []
    h = lines.index(HEADER)
    out = []
    for line in lines[h + 2:]:
        if not line.startswith("| C"):
            break
        out.append(line)
    return out


def merge(generated: list[str], existing: list[str]) -> list[str]:
    """The generated rows, plus any stated row of a case the measured values cannot rebuild (kept as written), by case."""
    case = lambda line: line.strip("|").split("|")[0].strip()
    have = {case(r) for r in generated}
    return sorted(generated + [r for r in existing if case(r) not in have], key=case)


def rewrite(text: str, new_rows: list[str], where: str) -> str:
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    try:
        h = lines.index(HEADER)
    except ValueError:
        return text
    if h + 1 >= len(lines) or not lines[h + 1].startswith("|---"):
        raise ValueError(f"{where}: the table header is not followed by its rule line")
    end = h + 2
    while end < len(lines) and lines[end].startswith("| C"):
        end += 1
    return nl.join(lines[:h + 2] + new_rows + lines[end:])


def run(root: Path, check: bool) -> list[str]:
    measured = json.loads((root / MEASURED).read_text(encoding="utf-8"))["measured"]
    iterations = {r["case_id"]: r["budget"]["iterations"] for r in json.loads((root / CASES).read_text(encoding="utf-8"))}
    stale = []
    for path in sorted((root / "docs" / "design" / "methods").glob("*.md")):
        method = method_of(path)
        if method is None:
            continue
        text = path.read_bytes().decode("utf-8")
        if HEADER not in text:
            continue
        generated = rows(method, measured, iterations, kept_iterations(text))
        new = rewrite(text, merge(generated, existing_rows(text)), str(path))
        if new != text:
            stale.append(str(path.relative_to(root)).replace("\\", "/"))
            if not check:
                path.write_bytes(new.encode("utf-8"))
    return stale


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="report the records whose rows are not current; write nothing")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args(argv)
    stale = run(Path(args.root), args.check)
    if args.check:
        if stale:
            print("record tables: stale (run python scripts/write_record_tables.py)\n  " + "\n  ".join(stale))
            return 1
        print("record tables: every design record states the measured values of the bake")
        return 0
    print(f"record tables: wrote {len(stale)} record(s)" + "".join(f"\n  {s}" for s in stale))
    return 0


if __name__ == "__main__":
    sys.exit(main())
