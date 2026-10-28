"""Stage 1, preprocess: read the raw parameter table and apply CONTRACT 1 (schema + outlier policy).
Output = a ContractReport (accepted SIRParams + rejected rows + flags). The bring-your-own-data entry point."""
from __future__ import annotations

from ..io.contract import ContractReport, validate_rows
from ..io.formats import read_csv_rows


def run(raw_csv_path: str) -> ContractReport:
    return validate_rows(read_csv_rows(raw_csv_path))
