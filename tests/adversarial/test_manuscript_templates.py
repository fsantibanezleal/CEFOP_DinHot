"""Native blueprints preserve the canonical style but cannot pass as authored papers."""
import hashlib
import json
import shutil
from pathlib import Path

from test_manuscript_depth import depth

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "templates/manuscripts"


def test_report_and_paper_use_one_native_canonical_base_without_invented_dois():
    provenance = json.loads((TEMPLATES / "provenance.json").read_text(encoding="utf8"))
    base = (TEMPLATES / "shared/base.tex").read_bytes()
    assert hashlib.sha256(base).hexdigest() == provenance["base_sha256"]
    assert provenance["derived_from"]["sha256"] == "1bd6177174edbc62e483cac0430aa697ca34f127a3d11dce4813e1bdcc74b3cf"
    for token in (b"margin=1.1in", b"{25,55,125}", b"{orcidlink}", b"\\fbox", b"\\pagestyle{fancy}", b"not assigned", b"\\newtheorem{theorem}{Theorem}[section]"):
        assert token in base
    for slug, kind in (("technical-report", "Technical report"), ("research-paper", "Working manuscript")):
        source = (TEMPLATES / slug / "main.tex").read_text(encoding="utf8")
        assert source.startswith("\\documentclass[11pt]{article}")
        assert f"\\newcommand{{\\doctype}}{{{kind}}}" in source
        assert "\\input{../shared/base.tex}" in source
        assert "\\chapter" not in source
        assert "\\newcommand{\\versiondoi}{}" in source
        assert "\\newcommand{\\conceptdoi}{}" in source
        assert source.index("\\maketitle") < source.index("\\headerblock") < source.index("\\begin{abstract}")


def test_unfilled_blueprints_are_refused_as_authored_manuscripts(tmp_path):
    root = tmp_path / "product"
    root.mkdir()
    shutil.copytree(TEMPLATES / "shared", root / "manuscripts/shared")
    for slug in ("technical-report", "research-paper"):
        shutil.copytree(TEMPLATES / slug, root / "manuscripts" / slug)
    (root / "product.json").write_text('{"manuscripts": []}', encoding="utf8")
    findings = depth.check(root)
    for slug in ("technical-report", "research-paper"):
        assert any(f"manuscripts/{slug}:" in f and "words" in f and "floor" in f for f in findings), findings
        assert any(f"manuscripts/{slug}/coverage.json: title_support is empty" in f for f in findings), findings
    assert not (ROOT / "manuscripts/technical-report").exists()
