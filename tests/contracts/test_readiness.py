"""Catalog row readiness 1.0.0 (producer side): data-pipeline/pipeline/core/readiness.py computes every row's declared state from
docs/contracts/catalog.md and the repository. One test per state, each reached through the real ``compute`` on a temporary copy of
the repository inputs whose catalog rows are set to ``real`` (the committed catalog still serves most rows by a provider); each
document is checked against the schema and each reason against the catalog's own Missing-data table (parsed here, never copied)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
from contract_schemas import FIXTURE_ROOT, ROOT, errors, run_readiness_guard

from pipeline.core import readiness
from pipeline.io.formats import write_json

CATALOG = ROOT / "docs" / "contracts" / "catalog.md"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
OLDER = VERSION.rsplit(".", 1)[0] + ".999"
REAL_ROWS = ("params-record", "case-index", "case-manifest", "trace", "benchmark-results", "cgh-net", "warmstart-model",
             "model-metrics", "engine-reference")
ROW_IDS = ["params-record", "case-index", "case-manifest", "trace", "benchmark-results", "cgh-net", "warmstart-model",
           "model-metrics", "engine-reference", "readiness", "api"]


def _table(section: str) -> list[list[str]]:
    text = CATALOG.read_text(encoding="utf-8").replace("\r\n", "\n")
    body = text.split(f"## {section}\n", 1)[1].split("\n## ", 1)[0]
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in body.splitlines() if ln.startswith("|")]
    return rows[2:]


def template(condition: str) -> tuple[str, str]:
    """The English and Spanish reason of the Missing-data row whose condition contains ``condition``."""
    for cells in _table("Missing-data states"):
        if len(cells) == 6 and condition in cells[1]:
            return cells[4], cells[5]
    raise AssertionError(f"no Missing-data row mentions {condition!r}")


def fill(tpl: tuple[str, str], **vals: object) -> dict:
    out = {}
    for lang, text in zip(("en", "es"), tpl):
        for k, v in vals.items():
            text = text.replace("{" + k + "}", str(v))
        out[lang] = text
    return out


def set_status(r: Path, row_id: str, status: str) -> None:
    cat = r / "docs" / "contracts" / "catalog.md"
    text = cat.read_text(encoding="utf-8")
    row = next(ln for ln in text.splitlines() if ln.startswith(f"| {row_id} |"))
    cells = row.split("|")
    cells[-2] = f" {status} "
    cat.write_text(text.replace(row, "|".join(cells)), encoding="utf-8")


@pytest.fixture()
def repo(tmp_path: Path, sandbox_bake) -> Path:
    """A temporary repository: the catalog with the producer rows ``real``, VERSION, the twelve cases, a bake, a benchmark and a
    metrics document of the current version, an engine reference file, and no released model."""
    r = tmp_path / "repo"
    (r / "docs" / "contracts").mkdir(parents=True)
    shutil.copy(CATALOG, r / "docs" / "contracts" / "catalog.md")
    shutil.copy(ROOT / "VERSION", r / "VERSION")
    (r / "data" / "examples").mkdir(parents=True)
    shutil.copy(ROOT / "data" / "examples" / "cases.json", r / "data" / "examples" / "cases.json")
    derived = r / "data" / "derived"
    shutil.copytree(sandbox_bake[0], derived, ignore=shutil.ignore_patterns("readiness.json"))
    (derived / "benchmark").mkdir()
    (derived / "models").mkdir()
    for rel in ("benchmark/results.json", "models/metrics.json"):
        doc = json.loads((FIXTURE_ROOT / "data" / "derived" / rel).read_text(encoding="utf-8"))
        doc["engine_version"] = VERSION
        doc.pop("skipped", None)
        write_json(derived / rel, doc)
    (r / "models").mkdir()
    (r / "tests" / "fixtures" / "engine").mkdir(parents=True)
    (r / "tests" / "fixtures" / "engine" / "ref.json").write_text("{}", encoding="utf-8")
    for row in REAL_ROWS:
        set_status(r, row, "real")
    return r


def run(r: Path) -> dict:
    doc = readiness.compute(repo_root=r, derived_root=r / "data" / "derived", models_dir=r / "models")
    assert errors("readiness", doc) == []
    return doc


def entry(doc: dict, row: str) -> dict:
    return next(e for e in doc["contracts"] if e["id"] == row)


def test_committed_readiness_is_current(tmp_path):
    doc = readiness.compute(repo_root=ROOT, derived_root=ROOT / "data" / "derived", models_dir=ROOT / "models")
    out = tmp_path / "derived"
    readiness.write(out, doc)
    assert (out / "readiness.json").read_bytes() == (ROOT / "data" / "derived" / "readiness.json").read_bytes()


def test_catalog_rows_in_order_without_readiness():
    rows = readiness.parse_catalog(CATALOG.read_text(encoding="utf-8"))
    assert [r["id"] for r in rows] == ROW_IDS
    assert {"id", "version", "status", "provider"} <= set(rows[0])
    doc = readiness.compute(repo_root=ROOT, derived_root=ROOT / "data" / "derived", models_dir=ROOT / "models")
    assert [e["id"] for e in doc["contracts"]] == [r for r in ROW_IDS if r != "readiness"]
    assert doc["product_version"] == VERSION


def test_state_available_for_the_rows_the_bake_serves(repo):
    doc = run(repo)
    for rid in ("case-index", "case-manifest", "trace", "benchmark-results", "model-metrics", "engine-reference"):
        e = entry(doc, rid)
        assert (e["state"], e["provenance"], e["reason"], e["missing"]) == ("available", "real", None, []), rid
    api = entry(doc, "api")
    assert (api["state"], api["provenance"]) == ("missing", None) and api["reason"] == fill(template("always, in the static document"))


def test_state_partial_params_lists_the_rejected_case_ids(repo):
    e = entry(run(repo), "params-record")
    assert (e["state"], e["provenance"]) == ("partial", "real")
    assert e["reason"] == fill(template("contract 1 rejects some records"), n=1, total=14)
    assert e["missing"] == ["C11_outside_field"]


def test_adversarial_state_partial_manifests_and_traces(repo):
    d = repo / "data" / "derived"
    (d / "manifests" / "C91_mini.json").unlink()
    (d / "C93_rearr" / "trace.json").unlink()
    doc = run(repo)
    m, t = entry(doc, "case-manifest"), entry(doc, "trace")
    assert (m["state"], m["provenance"]) == ("partial", "real") and m["missing"] == ["manifests/C91_mini.json"]
    assert m["reason"] == fill(template("a manifest the index lists as baked is absent"), n=1, total=3)
    assert t["state"] == "partial" and t["missing"] == ["C93_rearr/trace.json"]
    assert t["reason"] == fill(template("an artifact a present manifest names is absent"), n=1, total=2)


def test_state_partial_benchmark_lists_the_skipped_cells(repo):
    p = repo / "data" / "derived" / "benchmark" / "results.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["skipped"] = [{"method": "M19", "geometry": "G5", "reason": {"en": "x", "es": "x"}},
                      {"method": "M19", "geometry": "G1", "reason": {"en": "x", "es": "x"}}]
    write_json(p, doc)
    e = entry(run(repo), "benchmark-results")
    assert (e["state"], e["provenance"]) == ("partial", "real") and e["missing"] == ["M19/G1", "M19/G5"]
    ran = {(r["method"], r["geometry"]) for r in doc["rows"]}
    assert e["reason"] == fill(template("`skipped` is not empty"), n=2, total=len(ran) + 2)


def test_adversarial_state_stale(repo):
    d = repo / "data" / "derived"
    for rel in ("manifests/index.json", "benchmark/results.json", "models/metrics.json"):
        doc = json.loads((d / rel).read_text(encoding="utf-8"))
        doc["engine_version"] = OLDER
        write_json(d / rel, doc)
    out = run(repo)
    for rid in ("case-index", "case-manifest", "trace", "benchmark-results", "model-metrics"):
        e = entry(out, rid)
        assert (e["state"], e["provenance"], e["missing"]) == ("stale", "real", []), rid
        assert e["reason"] == fill(template("differs from `VERSION`"), engine_version=OLDER, version=VERSION), rid


def test_first_matching_rule_wins(repo):
    d = repo / "data" / "derived"
    idx = json.loads((d / "manifests" / "index.json").read_text(encoding="utf-8"))
    idx["engine_version"] = OLDER
    write_json(d / "manifests" / "index.json", idx)
    (d / "manifests" / "C91_mini.json").unlink()
    out = run(repo)
    assert entry(out, "case-manifest")["state"] == "partial" and entry(out, "case-index")["state"] == "stale"


def test_adversarial_state_provider_through_the_catalog(repo):
    set_status(repo, "case-index", "active")
    e = entry(run(repo), "case-index")
    provider = "fixture:docs/contracts/fixtures/data/derived/manifests/index.json"
    assert (e["state"], e["status"], e["provenance"]) == ("provider", "active", "fixture")
    assert e["reason"] == fill(template("the catalog `status` is `active`"), provider=provider)
    assert entry(run(repo), "case-manifest")["state"] == "available"


@pytest.mark.parametrize("slot", ["cgh-net", "warmstart-model"])
def test_state_training_without_a_released_model_and_with_a_marker(repo, slot):
    e = entry(run(repo), slot)
    assert (e["state"], e["provenance"]) == ("training", "baseline")
    assert e["reason"] == fill(template("is absent or fails its schema"))
    # a manifest that records the baseline stays baseline, and the marker comes last
    (repo / "models" / "training").mkdir()
    (repo / "models" / "training" / slot).write_text("started", encoding="utf-8")
    assert entry(run(repo), slot)["reason"] == fill(template("is absent or fails its schema"))


def release(repo: Path, slot: str) -> None:
    import hashlib

    stem = {"cgh-net": "cgh-net", "warmstart-model": "warmstart"}[slot]
    onnx = repo / "models" / f"{stem}.onnx"
    onnx.write_bytes(b"onnx-bytes" * 10)
    card = json.loads((ROOT / "docs" / "contracts" / "examples" / f"{slot}.json").read_text(encoding="utf-8"))
    card.update(onnx=f"models/{stem}.onnx", bytes=onnx.stat().st_size, sha256=hashlib.sha256(onnx.read_bytes()).hexdigest())
    (repo / "models" / f"{stem}.json").write_text(json.dumps(card), encoding="utf-8")


def test_released_model_baseline_bake_and_marker_rules(repo):
    release(repo, "cgh-net")
    assert errors("model-card", json.loads((repo / "models" / "cgh-net.json").read_text(encoding="utf-8"))) == []
    # the released model is available, unless a manifest says the baseline made the metrics, unless a marker says one trains
    assert entry(run(repo), "cgh-net")["state"] == "training" and entry(run(repo), "cgh-net")["provenance"] == "baseline"
    for p in (repo / "data" / "derived" / "manifests").glob("C9*.json"):
        m = json.loads(p.read_text(encoding="utf-8"))
        m["models"]["cgh-net"] = "real"
        write_json(p, m)
    e = entry(run(repo), "cgh-net")
    assert (e["state"], e["provenance"]) == ("available", "real")
    (repo / "models" / "training").mkdir()
    (repo / "models" / "training" / "cgh-net").write_text("started", encoding="utf-8")
    e = entry(run(repo), "cgh-net")
    assert (e["state"], e["provenance"]) == ("training", "real") and e["reason"] == fill(template("the marker file"))
    onnx = repo / "models" / "cgh-net.onnx"
    onnx.write_bytes(onnx.read_bytes() + b"x")                                     # sha256 and bytes no longer match
    assert entry(run(repo), "cgh-net")["provenance"] == "baseline"


def test_adversarial_state_missing(repo):
    d = repo / "data" / "derived"
    (repo / "data" / "examples" / "cases.json").unlink()
    (d / "benchmark" / "results.json").unlink()
    (d / "models" / "metrics.json").unlink()
    shutil.rmtree(repo / "tests" / "fixtures" / "engine")
    out = run(repo)
    for rid, cond in (("params-record", "`data/examples/cases.json` is absent"),
                      ("benchmark-results", "`data/derived/benchmark/results.json` is absent"),
                      ("model-metrics", "`data/derived/models/metrics.json` is absent"),
                      ("engine-reference", "no JSON file under `tests/fixtures/engine/`")):
        e = entry(out, rid)
        assert (e["state"], e["provenance"], e["missing"]) == ("missing", None, []), rid
        assert e["reason"] == fill(template(cond)), rid
    (d / "manifests" / "index.json").unlink()
    out = run(repo)
    for rid in ("case-index", "case-manifest", "trace"):
        e = entry(out, rid)
        assert (e["state"], e["provenance"]) == ("missing", None) and e["reason"] == fill(template("`data/derived/manifests/index.json` is absent"))


@pytest.mark.parametrize("bad", ["stub", "live", "Active", "REAL", "real extra", "baseline", ""])
def test_a_status_other_than_real_or_active_fails(repo, bad):
    set_status(repo, "case-index", bad)
    with pytest.raises(ValueError) as exc:
        readiness.compute(repo_root=repo, derived_root=repo / "data" / "derived", models_dir=repo / "models")
    assert "case-index" in str(exc.value) and "real" in str(exc.value) and "active" in str(exc.value)


def test_table_padding_is_formatting_not_a_status(repo):
    set_status(repo, "case-index", "   real   ")
    assert entry(run(repo), "case-index")["state"] == "available"


def test_determinism_and_normalised_hash(repo):
    a, b = run(repo), run(repo)
    assert a == b
    cat = repo / "docs" / "contracts" / "catalog.md"
    cat.write_bytes(cat.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert run(repo)["catalog_sha256"] == a["catalog_sha256"]


def test_run_all_writes_a_valid_readiness(sandbox_bake):
    doc = json.loads((sandbox_bake[0] / "readiness.json").read_text(encoding="utf-8"))
    assert errors("readiness", doc) == []


def test_check_readiness_passes_on_the_repository():
    p = run_readiness_guard()
    assert p.returncode == 0, p.stdout + p.stderr
    assert "readiness: current" in p.stdout


def test_adversarial_check_readiness_runs_without_numpy():
    p = run_readiness_guard(no_numpy=True)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "readiness: current" in p.stdout


def test_adversarial_check_readiness_reports_an_unknown_status(repo):
    set_status(repo, "case-index", "stub")
    p = run_readiness_guard(repo)
    assert p.returncode == 1 and "case-index" in p.stdout and "Traceback" not in p.stdout + p.stderr


def test_adversarial_check_readiness_fails_on_a_changed_catalog(tmp_path):
    r = tmp_path / "repo"
    shutil.copytree(ROOT / "data", r / "data")
    shutil.copytree(ROOT / "models", r / "models")
    (r / "docs" / "contracts").mkdir(parents=True)
    shutil.copy(ROOT / "VERSION", r / "VERSION")
    (r / "docs" / "contracts" / "catalog.md").write_text(CATALOG.read_text(encoding="utf-8").replace("One row per", "One Row per", 1),
                                                          encoding="utf-8")
    p = run_readiness_guard(r)
    assert p.returncode == 1 and "catalog_sha256" in p.stdout and "python data-pipeline/run.py readiness" in p.stdout
    assert sys.executable
