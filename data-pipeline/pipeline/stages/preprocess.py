"""Stage 1, preprocess: read the source document of cases and apply CONTRACT 1 (schema + the rules a schema cannot state).
Output = a ContractReport (accepted records + rejected records with their reasons + flags). The bring-your-own-case entry
point: ``data/examples/cases.json`` when it exists, else the registry's twelve default records (readiness says ``missing``
for the source in that case)."""
from __future__ import annotations

from pathlib import Path

from .. import registry
from ..io.contract import REPO_ROOT, ContractReport, read_cases, validate_records
from . import feature_extraction

CASES_REL = "data/examples/cases.json"


def source_path(repo_root: Path | None = None) -> Path:
    return (repo_root or REPO_ROOT) / CASES_REL


def run(path: str | Path | None = None, repo_root: Path | None = None) -> tuple[ContractReport, str]:
    """``(report, source)`` where source is ``file`` or ``registry``; extra flags from the target features are added."""
    p = Path(path) if path else source_path(repo_root)
    if p.is_file():
        report, source = validate_records(read_cases(p), repo_root), "file"
    else:
        report, source = validate_records(registry.records(), repo_root), "registry"
    for rec in report.accepted:
        report.flagged += feature_extraction.flags(rec)
    return report, source
