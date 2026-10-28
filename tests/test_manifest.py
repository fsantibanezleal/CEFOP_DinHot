"""CONTRACT 2 (artifact) tests: the manifest points to a real artifact with the recorded byte size, and the lane
verdict is consistent with the gate."""
from pipeline import pipeline


def test_manifest_matches_artifact_and_gate():
    m = pipeline.precompute("EX02_epidemic", seed=7)
    artifact = pipeline.DERIVED / m["artifact"]["path"]
    assert artifact.exists(), "manifest points to a non-existent artifact"
    assert artifact.stat().st_size == m["artifact"]["bytes"], "manifest byte size drifted from the artifact"
    assert m["schema"].startswith("example.manifest/")
    assert m["lane"] in ("live", "precompute")
    assert m["gate"]["lane"] == m["lane"], "manifest lane disagrees with the gate verdict"
    # the example SIR case is pure-python + numpy + small => must be classified LIVE
    assert m["lane"] == "live", f"expected live lane, got {m['lane']} ({m['gate']['reasons']})"


def test_every_light_case_is_live_whatever_its_place_in_the_bake(tmp_path):
    # the lane gate times the engine alone, warmed up; the first case baked is judged like the others
    entries = pipeline.run_all(seed=42, output_root=tmp_path / "derived")
    lanes = {}
    for e in entries:
        m = (tmp_path / "derived" / e["manifest_path"]).read_text(encoding="utf-8")
        lanes[e["case_id"]] = '"lane": "live"' in m or '"lane":"live"' in m
    assert all(lanes.values()), f"cases labelled precompute: {[k for k, v in lanes.items() if not v]}"
