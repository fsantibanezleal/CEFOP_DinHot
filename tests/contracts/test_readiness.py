"""Catalog row readiness 1.0.0 (producer side): data-pipeline/pipeline/core/readiness.py computes every row's
declared state from docs/contracts/catalog.md and the repository. One test per state, each reached through the real
``compute`` on a temporary copy of the repository inputs; each document is checked against the schema and each reason
against the catalog's own Missing-data table (parsed here, never copied)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pipeline import pipeline
from pipeline.core import readiness
from pipeline.io.formats import write_json

from contract_schemas import ROOT, errors, run_readiness_guard

CATALOG = ROOT / "docs" / "contracts" / "catalog.md"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
OLDER = VERSION.rsplit(".", 1)[0] + ".999"  # an engine version that is not VERSION
GOOD_PARAMS = "case_id,beta,gamma,N,I0,days\nEX02_epidemic,0.55,0.20,100000,50,160\nEX01_subcritical,0.18,0.25,100000,50,160\n"


def _table(section: str) -> list[list[str]]:
    text = CATALOG.read_text(encoding="utf-8").replace("\r\n", "\n")
    body = text.split(f"## {section}\n", 1)[1].split("\n## ", 1)[0]
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in body.splitlines() if ln.startswith("|")]
    return rows[2:]  # the header and the separator


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


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A temporary repository: the catalog, VERSION, a clean params table, the committed bake re-labelled with the
    current engine version, and the released bundle."""
    r = tmp_path / "repo"
    (r / "docs" / "contracts").mkdir(parents=True)
    shutil.copy(CATALOG, r / "docs" / "contracts" / "catalog.md")
    shutil.copy(ROOT / "VERSION", r / "VERSION")
    (r / "data" / "examples").mkdir(parents=True)
    (r / "data" / "examples" / "params.csv").write_text(GOOD_PARAMS, encoding="utf-8")
    shutil.copytree(ROOT / "data" / "derived", r / "data" / "derived", ignore=shutil.ignore_patterns("readiness.json"))
    shutil.copytree(ROOT / "models", r / "models")
    idx = r / "data" / "derived" / "manifests" / "index.json"
    doc = json.loads(idx.read_text(encoding="utf-8"))
    doc["engine_version"] = VERSION
    write_json(idx, doc)
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
    assert [r["id"] for r in rows] == ["params-record", "case-index", "case-manifest", "trace", "surrogate-model",
                                        "readiness", "api"]
    assert {"id", "version", "status", "provider"} <= set(rows[0])
    doc = readiness.compute(repo_root=ROOT, derived_root=ROOT / "data" / "derived", models_dir=ROOT / "models")
    assert [e["id"] for e in doc["contracts"]] == [r["id"] for r in rows if r["id"] != "readiness"]
    assert doc["product_version"] == VERSION


def test_state_available(repo):
    doc = run(repo)
    for e in doc["contracts"]:
        if e["id"] != "api":
            assert (e["state"], e["provenance"], e["reason"], e["missing"]) == ("available", "real", None, []), e["id"]
    assert entry(doc, "api")["state"] == "missing"
    assert entry(doc, "api")["provenance"] is None
    assert entry(doc, "api")["reason"] == fill(template("always, in the static document"))


def test_adversarial_state_partial_manifests(repo):
    (repo / "data" / "derived" / "manifests" / "EX01_subcritical.json").unlink()
    doc = run(repo)
    e = entry(doc, "case-manifest")
    assert (e["state"], e["provenance"]) == ("partial", "real")
    assert e["reason"] == fill(template("a manifest the index lists is absent"), n=1, total=5)
    assert e["missing"] == ["manifests/EX01_subcritical.json"]
    assert entry(doc, "trace")["state"] == "available"  # the absent manifest names no artifact to count


def test_state_partial_traces(repo):
    (repo / "data" / "derived" / "EX02_epidemic" / "trace.json").unlink()
    (repo / "data" / "derived" / "EX03_fast_burn" / "trace.json").unlink()
    doc = run(repo)
    e = entry(doc, "trace")
    assert (e["state"], e["provenance"]) == ("partial", "real")
    assert e["reason"] == fill(template("an artifact a present manifest names is absent"), n=2, total=5)
    assert e["missing"] == ["EX02_epidemic/trace.json", "EX03_fast_burn/trace.json"]
    assert entry(doc, "case-manifest")["state"] == "available"


def test_state_partial_params(repo):
    (repo / "data" / "examples" / "params.csv").write_text(
        GOOD_PARAMS + "zz_bad,-1,0.2,1000,5,160\naa_bad,0.5,0.2,10,500,160\n", encoding="utf-8")
    e = entry(run(repo), "params-record")
    assert (e["state"], e["provenance"]) == ("partial", "real")
    assert e["reason"] == fill(template("contract 1 rejects some rows"), n=2, total=4)
    assert e["missing"] == ["aa_bad", "zz_bad"]


def test_adversarial_state_stale(repo):
    idx = repo / "data" / "derived" / "manifests" / "index.json"
    doc = json.loads(idx.read_text(encoding="utf-8"))
    doc["engine_version"] = OLDER
    write_json(idx, doc)
    out = run(repo)
    for row in ("case-index", "case-manifest", "trace"):
        e = entry(out, row)
        assert (e["state"], e["provenance"]) == ("stale", "real"), row
        assert e["reason"] == fill(template("differs from `VERSION`"), engine_version=OLDER, version=VERSION)
        assert e["missing"] == []


def test_first_matching_rule_wins(repo):
    """A bake that is both partial and stale reports partial (the order of the catalog's table)."""
    idx = repo / "data" / "derived" / "manifests" / "index.json"
    doc = json.loads(idx.read_text(encoding="utf-8"))
    doc["engine_version"] = OLDER
    write_json(idx, doc)
    (repo / "data" / "derived" / "manifests" / "EX01_subcritical.json").unlink()
    out = run(repo)
    assert entry(out, "case-manifest")["state"] == "partial"
    assert entry(out, "case-index")["state"] == "stale"


def test_adversarial_state_provider_through_a_catalog_copy(repo):
    cat = repo / "docs" / "contracts" / "catalog.md"
    text = cat.read_text(encoding="utf-8")
    row = next(ln for ln in text.splitlines() if ln.startswith("| case-index |"))
    cells = row.split("|")
    cells[-2] = " active "
    cat.write_text(text.replace(row, "|".join(cells)), encoding="utf-8")
    doc = run(repo)
    e = entry(doc, "case-index")
    provider = "fixture:docs/contracts/fixtures/data/derived/manifests/index.json"
    assert (e["state"], e["status"], e["provenance"]) == ("provider", "active", "fixture")
    assert e["reason"] == fill(template("the catalog `status` is `active`"), provider=provider)
    assert entry(doc, "case-manifest")["state"] == "available"
    ref = readiness.compute(repo_root=ROOT, derived_root=ROOT / "data" / "derived", models_dir=ROOT / "models")
    assert doc["catalog_sha256"] != ref["catalog_sha256"]


def test_state_training_without_a_bundle(repo):
    (repo / "models" / "surrogate.json").unlink()
    e = entry(run(repo), "surrogate-model")
    assert (e["state"], e["provenance"]) == ("training", "baseline")
    assert e["reason"] == fill(template("is absent or fails its schema"))


def test_adversarial_state_training_with_an_invalid_bundle(repo):
    bundle = repo / "models" / "surrogate.json"
    bundle.write_text('{"kind":"linear-lstsq","basis":["1"],"coeffs":[1]}', encoding="utf-8")
    assert entry(run(repo), "surrogate-model")["provenance"] == "baseline"
    bundle.write_text("not json", encoding="utf-8")
    e = entry(run(repo), "surrogate-model")
    assert (e["state"], e["provenance"]) == ("training", "baseline")


def set_status(r: Path, row_id: str, status: str) -> None:
    """Rewrite the status cell of catalog row ``row_id`` in the repository copy ``r``."""
    cat = r / "docs" / "contracts" / "catalog.md"
    text = cat.read_text(encoding="utf-8")
    row = next(ln for ln in text.splitlines() if ln.startswith(f"| {row_id} |"))
    cells = row.split("|")
    cells[-2] = f" {status} "
    cat.write_text(text.replace(row, "|".join(cells)), encoding="utf-8")


@pytest.mark.parametrize("bad", ["stub", "live", "Active", "REAL", "real extra", "baseline", ""])
def test_a_status_other_than_real_or_active_fails(repo, bad):
    set_status(repo, "case-index", bad)
    with pytest.raises(ValueError) as exc:
        readiness.compute(repo_root=repo, derived_root=repo / "data" / "derived", models_dir=repo / "models")
    assert "case-index" in str(exc.value) and "real" in str(exc.value) and "active" in str(exc.value)


def test_table_padding_is_formatting_not_a_status(repo):
    set_status(repo, "case-index", "   real   ")
    assert entry(run(repo), "case-index")["state"] == "available"


def test_adversarial_check_readiness_reports_an_unknown_status(repo):
    set_status(repo, "case-index", "stub")
    p = run_readiness_guard(repo)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "case-index" in p.stdout and "real" in p.stdout and "active" in p.stdout
    assert "Traceback" not in p.stdout + p.stderr


def bake_with_the_baseline(r: Path) -> None:
    """Re-bake the repository copy's derived tree with no released bundle in reach: every manifest is a baseline's."""
    shutil.rmtree(r / "data" / "derived")
    pipeline.run_all(output_root=r / "data" / "derived", train=False)
    shutil.rmtree(r / "data" / "derived" / "models", ignore_errors=True)
    (r / "data" / "derived" / "readiness.json").unlink()


def test_adversarial_a_baseline_bake_stays_baseline_after_a_bundle_appears(repo):
    assert (repo / "models" / "surrogate.json").is_file()  # a valid released bundle is in place now
    bake_with_the_baseline(repo)
    for m in (repo / "data" / "derived" / "manifests").glob("EX*.json"):
        assert json.loads(m.read_text(encoding="utf-8"))["models"] == {"surrogate-model": "baseline"}
    e = entry(run(repo), "surrogate-model")
    assert (e["state"], e["provenance"]) == ("training", "baseline")
    assert e["reason"] == fill(template("a manifest records that the baseline produced"))


def test_one_baseline_manifest_is_enough(repo):
    path = repo / "data" / "derived" / "manifests" / "EX01_subcritical.json"
    m = json.loads(path.read_text(encoding="utf-8"))
    m["models"] = {"surrogate-model": "baseline"}
    write_json(path, m)
    assert entry(run(repo), "surrogate-model")["provenance"] == "baseline"


def test_a_real_bake_with_a_bundle_is_available(repo):
    for m in (repo / "data" / "derived" / "manifests").glob("EX*.json"):
        assert json.loads(m.read_text(encoding="utf-8"))["models"] == {"surrogate-model": "real"}
    assert entry(run(repo), "surrogate-model")["state"] == "available"


def test_the_baseline_rule_comes_before_the_marker(repo):
    path = repo / "data" / "derived" / "manifests" / "EX01_subcritical.json"
    m = json.loads(path.read_text(encoding="utf-8"))
    m["models"] = {"surrogate-model": "baseline"}
    write_json(path, m)
    (repo / "models" / "training").mkdir()
    (repo / "models" / "training" / "surrogate-model").write_text("started", encoding="utf-8")
    assert entry(run(repo), "surrogate-model")["provenance"] == "baseline"


def test_adversarial_state_training_with_the_marker(repo):
    (repo / "models" / "training").mkdir()
    (repo / "models" / "training" / "surrogate-model").write_text("started", encoding="utf-8")
    e = entry(run(repo), "surrogate-model")
    assert (e["state"], e["provenance"]) == ("training", "real")
    assert e["reason"] == fill(template("the marker file"))


def test_adversarial_state_missing_without_an_index(repo):
    (repo / "data" / "derived" / "manifests" / "index.json").unlink()
    doc = run(repo)
    for row in ("case-index", "case-manifest", "trace"):
        e = entry(doc, row)
        assert (e["state"], e["provenance"], e["missing"]) == ("missing", None, []), row
        assert e["reason"] == fill(template("`data/derived/manifests/index.json` is absent")), row


def test_state_missing_without_a_params_table(repo):
    (repo / "data" / "examples" / "params.csv").unlink()
    e = entry(run(repo), "params-record")
    assert (e["state"], e["provenance"]) == ("missing", None)
    assert e["reason"] == fill(template("`data/examples/params.csv` is absent"))


def test_unknown_row_gets_only_the_generic_rules(repo):
    cat = repo / "docs" / "contracts" / "catalog.md"
    text = cat.read_text(encoding="utf-8")
    row = next(ln for ln in text.splitlines() if ln.startswith("| params-record |"))
    own = row.replace("| params-record |", "| my-own-row |", 1)
    cat.write_text(text.replace(row, row + "\n" + own), encoding="utf-8")
    assert entry(run(repo), "my-own-row")["state"] == "available"
    own_active = own.split("|")
    own_active[-2] = " active "
    cat.write_text(text.replace(row, row + "\n" + "|".join(own_active)), encoding="utf-8")
    assert entry(run(repo), "my-own-row")["state"] == "provider"


def test_determinism_and_normalised_hash(repo):
    a, b = run(repo), run(repo)
    assert a == b
    cat = repo / "docs" / "contracts" / "catalog.md"
    cat.write_bytes(cat.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert run(repo)["catalog_sha256"] == a["catalog_sha256"]


def test_run_all_writes_a_valid_readiness(tmp_path):
    out = tmp_path / "bake"
    pipeline.run_all(seed=42, output_root=out)
    doc = json.loads((out / "readiness.json").read_text(encoding="utf-8"))
    assert errors("readiness", doc) == []
    for row in ("case-index", "case-manifest", "trace", "surrogate-model"):
        assert entry(doc, row)["state"] == "available", row  # baked and trained by this version


def test_check_readiness_passes_on_the_repository():
    p = run_readiness_guard()
    assert p.returncode == 0, p.stdout + p.stderr
    assert "readiness: current" in p.stdout


def test_adversarial_check_readiness_runs_without_numpy():
    p = run_readiness_guard(no_numpy=True)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "readiness: current" in p.stdout


def test_adversarial_check_readiness_fails_on_a_changed_catalog(tmp_path):
    r = tmp_path / "repo"
    shutil.copytree(ROOT / "data", r / "data")
    shutil.copytree(ROOT / "models", r / "models")
    (r / "docs" / "contracts").mkdir(parents=True)
    shutil.copy(ROOT / "VERSION", r / "VERSION")
    cat = CATALOG.read_text(encoding="utf-8")
    (r / "docs" / "contracts" / "catalog.md").write_text(cat.replace("One row per", "One Row per", 1), encoding="utf-8")
    p = run_readiness_guard(r)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "catalog_sha256" in p.stdout
    assert "python data-pipeline/run.py readiness" in p.stdout
