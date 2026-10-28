"""Pipeline smoke + determinism: a case regenerates deterministically (same seed -> identical artifact), the
degenerate control runs without crashing, and run_all writes the flat index."""
import hashlib
import json

from pipeline import pipeline, registry


def sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_adversarial_same_seed_bakes_identical_bytes_and_a_changed_byte_of_equal_size_is_seen(tmp_path):
    """The same case and seed baked twice into two roots writes the same bytes (not only the same size); the control is a
    copy of the trace with one digit changed, which has the size of the original and must be told apart from it."""
    a = pipeline.precompute("EX02_epidemic", seed=7, output_root=tmp_path / "a")
    b = pipeline.precompute("EX02_epidemic", seed=7, output_root=tmp_path / "b")
    first, second = tmp_path / "a" / a["artifact"]["path"], tmp_path / "b" / b["artifact"]["path"]
    assert first != second and first.read_bytes() == second.read_bytes() and sha(first) == sha(second)
    assert a["artifact"]["bytes"] == b["artifact"]["bytes"] == first.stat().st_size
    trace = json.loads(first.read_text(encoding="utf-8"))
    assert trace["summary"]["peak_I"] > 0  # an empty run would also be equal to itself
    raw = bytearray(first.read_bytes())
    at = next(i for i in range(len(raw) - 1, -1, -1) if chr(raw[i]).isdigit())
    raw[at] = ord("0") if raw[at] != ord("0") else ord("1")
    changed = tmp_path / "changed.json"
    changed.write_bytes(bytes(raw))
    assert changed.stat().st_size == first.stat().st_size and changed.read_bytes() != first.read_bytes() and sha(changed) != sha(first)


def test_a_different_seed_is_a_different_bake_record(tmp_path):
    a = pipeline.precompute("EX02_epidemic", seed=7, output_root=tmp_path / "a")
    b = pipeline.precompute("EX02_epidemic", seed=8, output_root=tmp_path / "b")
    assert a["seed"] == 7 and b["seed"] == 8


def test_degenerate_control_runs(tmp_path):
    out = tmp_path / "derived"
    m = pipeline.precompute("CTRL_degenerate", seed=1, output_root=out)
    trace = json.loads((out / m["artifact"]["path"]).read_text(encoding="utf-8"))
    assert trace["summary"]["peak_I"] == 0.0
    assert trace["summary"]["attack_rate"] == 0.0


def test_run_all_writes_index(tmp_path):
    out = tmp_path / "derived"
    entries = pipeline.run_all(seed=42, output_root=out)
    assert len(entries) == len(registry.list_cases()) >= 4
    idx = json.loads((out / "manifests" / "index.json").read_text(encoding="utf-8"))
    assert idx["n_cases"] == len(entries)
    assert idx["schema"].startswith("example.index/")
