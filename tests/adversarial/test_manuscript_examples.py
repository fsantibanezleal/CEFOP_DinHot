"""Immutable real-source controls complement the deliberately synthetic parser tests."""
import hashlib
import json
from pathlib import Path

from test_manuscript_depth import depth

HERE = Path(__file__).resolve().parents[1] / "fixtures/manuscript-depth"


def test_real_published_native_examples_are_complete_and_exact(tmp_path):
    manifest = json.loads((HERE / "source.json").read_text(encoding="utf8"))
    root = HERE / "softqp-published"
    assert manifest["source_commit"] == "bbdd7909b2ee523881383764eb969eaab079d4de"
    assert manifest["manuscript_license"] == "CC BY 4.0"
    assert manifest["technical_report"]["outcome"] == "negative timing criterion"
    assert manifest["paper"]["outcome"] == "negative registered directional comparison"
    files = manifest["files"]
    assert len(files) == 155
    assert not any(name.endswith("/main.pdf") for name in files), "Source-only fixtures exclude compiled manuscripts"
    assert {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} == {entry.get("storage", name) for name, entry in files.items()}
    restored = tmp_path / "historical-product"
    for name, expected in files.items():
        path = root / expected.get("storage", name)
        assert path.resolve().is_relative_to(root.resolve())
        raw = path.read_bytes()
        assert len(raw) == expected["bytes"], name
        assert hashlib.sha256(raw).hexdigest() == expected["sha256"], name
        target = restored / name
        assert target.resolve().is_relative_to(restored.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    assert depth.check(restored) == []
