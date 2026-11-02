"""Adversarial admission and process tests using the production bootstrap helpers."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_local_bootstrap import ROOT, free_port, present, write
from test_local_bootstrap import fixture_repo as fixture_repo
from test_local_bootstrap import workflow as workflow


def stamp(root, config, module, name=".venv"):
    item = next(row for row in config["environments"] if row["path"] == name)
    write(
        root / name / ".bootstrap-requirements.sha256", module.requirements_digest(root, item["requirements"])
    )


def metadata(root, stage):
    shutil.copyfile(root / "VERSION", stage / "VERSION")
    shutil.copytree(root / "docs/contracts", stage / "docs/contracts", dirs_exist_ok=True)


def seal(module, root, config, stage):
    write(
        stage / "local-generation.json",
        json.dumps(
            {"source": module.source_identity(root, config), "files": module.payload_hashes(stage, config)}
        ),
    )


def test_adversarial_receipt_current_contract_and_recursive_pins(workflow, fixture_repo):
    root, config, env = fixture_repo
    write(root / "requirements.txt", "-r data-pipeline/requirements.txt\n-c constraints.txt\n")
    write(root / "data-pipeline/requirements.txt", "-r nested/more.txt\n")
    write(root / "data-pipeline/nested/more.txt", "numpy==2.4.6\n")
    write(root / "constraints.txt", "example==1\n")
    # Actual document validator and schema registry; the catalog mapping is fixture data.
    for name in (
        "scripts/check_documents.py",
        "scripts/check_contracts.py",
        "tests/contracts/contract_schemas.py",
    ):
        write(root / name, (ROOT / name).read_text(encoding="utf-8"))
    write(root / "docs/contracts/api.openapi.json", "{}")
    for name, required in (("lenient", []), ("strict", ["NEW_CONTRACT_FIELD"])):
        write(
            root / f"docs/contracts/schemas/{name}.schema.json",
            json.dumps({"type": "object", "required": required}),
        )
    header = (
        "id",
        "version",
        "kind",
        "schema file",
        "producer",
        "consumer",
        "example",
        "missing-data behavior",
        "producer test",
        "consumer test",
        "model io",
        "provider",
        "documents",
    )
    paths = config["required"]
    rows = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * 13) + " |"]
    for index, name in enumerate(paths):
        cells = [
            f"doc{index}",
            "1",
            "json",
            "docs/contracts/schemas/lenient.schema.json",
            "-",
            "-",
            "-",
            "-",
            "-",
            "-",
            "-",
            "-",
            name,
        ]
        rows.append("| " + " | ".join(cells) + " |")
    catalog = "\n".join(rows) + "\n"
    write(root / "docs/contracts/catalog.md", catalog)
    config["validators"] = [{"script": "scripts/check_documents.py", "args": ["{stage}"]}]
    write(root / "scripts/local/workflow.json", json.dumps(config))
    stage = root.parent / "candidate"
    for name in paths:
        write(stage / name, json.dumps({"engine_version": (root / "VERSION").read_text().strip()}))
    ready = {
        "product_version": (root / "VERSION").read_text().strip(),
        "catalog_sha256": hashlib.sha256(catalog.encode()).hexdigest(),
        "contracts": [{"id": f"doc{i}", "state": "available"} for i in range(4)],
    }
    write(stage / "data/derived/readiness.json", json.dumps(ready))
    metadata(root, stage)
    seal(workflow, root, config, stage)
    workflow.validate_stage(root, config, stage, sys.executable, env, receipt=True)
    original_identity = workflow.source_identity(root, config)
    for name, replacement in (
        ("data-pipeline/nested/more.txt", "numpy==2.4.5\n"),
        ("constraints.txt", "example==2\n"),
        ("docs/contracts/catalog.md", catalog.replace("lenient.schema", "strict.schema")),
        (
            "docs/contracts/schemas/strict.schema.json",
            '{"type":"object","required":["SECOND_REQUIRED_FIELD"]}',
        ),
        (
            "scripts/check_documents.py",
            (root / "scripts/check_documents.py").read_text() + "\n# revised admission\n",
        ),
        (
            "tests/contracts/contract_schemas.py",
            (root / "tests/contracts/contract_schemas.py").read_text() + "\n# revised registry\n",
        ),
    ):
        path = root / name
        before = path.read_bytes()
        write(path, replacement)
        assert workflow.source_identity(root, config) != original_identity, name
        with pytest.raises(workflow.Failure, match="fingerprint"):
            workflow.promote(root, config, stage, sys.executable, env)
        assert not (root / "models").exists()
        if name.endswith("catalog.md"):
            with pytest.raises(workflow.Failure, match="metadata|catalog"):
                workflow.validate_stage(root, config, stage, sys.executable, env)
        path.write_bytes(before)
    # Same IDs, new schema mapping: current validator fails old bytes, not just an identity string.
    strict_catalog = catalog.replace("lenient.schema", "strict.schema")
    write(root / "docs/contracts/catalog.md", strict_catalog)
    metadata(root, stage)
    bad = subprocess.run(
        [sys.executable, root / "scripts/check_documents.py", stage],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert bad.returncode == 1 and "NEW_CONTRACT_FIELD" in bad.stdout
    ready["catalog_sha256"] = hashlib.sha256(strict_catalog.encode()).hexdigest()
    write(stage / "data/derived/readiness.json", json.dumps(ready))
    for name in paths:
        value = json.loads((stage / name).read_text())
        value["NEW_CONTRACT_FIELD"] = True
        write(stage / name, json.dumps(value))
    seal(workflow, root, config, stage)
    workflow.promote(root, config, stage, sys.executable, env)
    workflow.check_shipped(root, config)
    write(root / "docs/contracts/catalog.md", strict_catalog + "\nChanged contract notes\n")
    with pytest.raises(workflow.Failure, match="stale admission catalog"):
        workflow.check_shipped(root, config)


def test_adversarial_actual_readiness_inventory(workflow, tmp_path):
    # Invoke the real compute API, preserving its genuine missing states. No engine solves.
    code = (
        "import json,sys; from pathlib import Path; from pipeline.core import readiness; "
        "root=Path(sys.argv[1]); stage=Path(sys.argv[2]); "
        "print(json.dumps(readiness.compute(repo_root=root,derived_root=stage/'data',models_dir=stage/'models')))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(ROOT), str(tmp_path)],
        cwd=ROOT / "data-pipeline",
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    ready = json.loads(result.stdout)
    config = workflow.settings(ROOT)
    workflow.check_readiness_inventory(ROOT, config, ready)
    is_template = (ROOT / ".template-source").is_file()
    # DinHot: 12 catalog rows less the readiness row it excludes (workflow.json readiness_excludes)
    assert len(ready["contracts"]) == (6 if is_template else 11)
    assert "readiness" not in {row["id"] for row in ready["contracts"]}
    for bad_rows in (
        ready["contracts"][:-1],
        ready["contracts"] + [ready["contracts"][0]],
        ready["contracts"] + [{"id": "unknown", "state": "available"}],
    ):
        with pytest.raises(workflow.Failure, match="inventory"):
            workflow.check_readiness_inventory(ROOT, config, {**ready, "contracts": bad_rows})
    with pytest.raises(workflow.Failure, match="stale admission catalog"):
        workflow.check_readiness_inventory(ROOT, config, {**ready, "catalog_sha256": "0" * 64})


def test_adversarial_actual_template_registry(tmp_path):
    bridge = ROOT / "scripts/local/producer_bridge.py"
    if not (ROOT / "data-pipeline/pipeline/registry.py").is_file():
        config = json.loads((ROOT / "scripts/local/workflow.json").read_text())
        assert all("template-validate" not in row.get("args", []) for row in config["validators"])
        return
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json;from pipeline import registry;print(json.dumps([c.id for c in registry.list_cases()]))",
        ],
        cwd=ROOT / "data-pipeline",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    ids = json.loads(result.stdout)
    assert ids
    index = tmp_path / "data/derived/manifests/index.json"
    for cases, expected in ((ids, 0), (ids[:-1], 1), (ids + [ids[0]], 1)):
        write(index, json.dumps({"cases": [{"case_id": name} for name in cases]}))
        checked = subprocess.run(
            [sys.executable, bridge, "template-validate", tmp_path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert checked.returncode == expected, checked.stderr
        if expected:
            assert "Partial case inventory" in checked.stderr


def test_adversarial_rollback_continues_and_preserves_recovery(workflow, fixture_repo, monkeypatch):
    root, config, env = fixture_repo
    present(root, config, workflow)
    originals = {name: (root / name).read_bytes() for name in config["required"]}
    stage = workflow.generate(root, config, env)
    real_replace = os.replace
    restores = []

    def replace(source, target):
        source, target = Path(source), Path(target)
        if ".bootstrap-incoming-" in source.name and target == root / "models":
            raise OSError("original install failure")
        if ".bootstrap-restore-" in source.name:
            restores.append(target)
            if target == root / "models":
                raise OSError("second restore failure")
        return real_replace(source, target)

    monkeypatch.setattr(workflow.os, "replace", replace)
    with pytest.raises(workflow.Failure, match="Rollback incomplete") as raised:
        workflow.promote(root, config, stage, sys.executable, env)
    message = str(raised.value)
    assert "original install failure" in message and "second restore failure" in message
    assert restores == [root / "models", root / "data/derived"]
    assert not (root / "models").exists()
    assert (root / "data/derived/cases/a.json").read_bytes() == originals["data/derived/cases/a.json"]
    for prefix, parent, child in (("models", root, "model.json"), ("derived", root / "data", "cases/a.json")):
        backups = list(parent.glob(f".{prefix}.bootstrap-backup-*"))
        assert len(backups) == 1 and backups[0].name in message
        key = f"models/{child}" if prefix == "models" else f"data/derived/{child}"
        assert (backups[0] / child).read_bytes() == originals[key]


def test_adversarial_dev_python_initialization_admission(workflow, fixture_repo, monkeypatch):
    root, config, env = fixture_repo
    present(root, config, workflow)
    config["frontend_command"] = [sys.executable, "-c", "pass"]
    config["web_port"] = free_port()
    monkeypatch.setattr(workflow, "environment", lambda *_: env)
    prepared = []
    actual_run = workflow.run
    config["frontend_prepare"] = [[sys.executable, "-c", "pass"]]

    def run(*args, **kwargs):
        prepared.append(args)
        return actual_run(*args, **kwargs)

    monkeypatch.setattr(workflow, "run", run)
    with pytest.raises(workflow.Failure, match="initialization fingerprint"):
        workflow.development(root, config)
    assert not prepared
    stamp(root, config, workflow)
    workflow.development(root, config)
    assert len(prepared) == 1
    write(root / "requirements.txt", "example==2\n")
    with pytest.raises(workflow.Failure, match="initialization fingerprint"):
        workflow.development(root, config)
    assert len(prepared) == 1
    stamp(root, config, workflow)
    config["api"].update(active=True, environment=".venv-api")
    config["environments"].append({"path": ".venv-api", "requirements": ["requirements-api.txt"]})
    write(root / "requirements-api.txt", "-r requirements.txt\n")
    write(root / "scripts/local/workflow.json", json.dumps(config))
    with pytest.raises(workflow.Failure, match=r"\.venv-api"):
        workflow.development(root, config)
    assert len(prepared) == 1
    stamp(root, config, workflow, ".venv-api")
    port = free_port()
    config["api"].update(
        port=port, health="/", command=[sys.executable, "-m", "http.server", "{port}", "--bind", "127.0.0.1"]
    )
    workflow.development(root, config)
    assert len(prepared) == 2
    write(root / "requirements-api.txt", "-r requirements.txt\napi-example==2\n")
    with pytest.raises(workflow.Failure, match=r"\.venv-api"):
        workflow.development(root, config)
    assert len(prepared) == 2


def reachable(port, token="owned-child"):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=0.2) as reply:
            return reply.read().decode() == token
    except OSError:
        return False


def wait_until(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    assert predicate(), "bounded fixture condition did not become true"


def test_adversarial_exited_parent_descendant_ownership(workflow, tmp_path):
    child = tmp_path / "http_child.py"
    write(
        child,
        """from http.server import BaseHTTPRequestHandler,HTTPServer
import sys
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.end_headers();self.wfile.write(sys.argv[2].encode())
 def log_message(self,*args): pass
HTTPServer(("127.0.0.1",int(sys.argv[1])),Handler).serve_forever()
""",
    )
    parent = tmp_path / "launcher.py"
    write(
        parent,
        """import socket,subprocess,sys,time
from pathlib import Path
p=subprocess.Popen([sys.executable,sys.argv[1],sys.argv[2],sys.argv[3]],stdin=subprocess.DEVNULL)
Path("owned-child.pid").write_text(str(p.pid))
for unused in range(100):
 try:
  with socket.create_connection(("127.0.0.1",int(sys.argv[2])),timeout=.1): break
 except OSError: time.sleep(.05)
else: raise SystemExit(7)
""",
    )
    # Hold both reservations together; Windows can reuse a just-released ephemeral port.
    with socket.socket() as first, socket.socket() as second:
        first.bind(("127.0.0.1", 0))
        second.bind(("127.0.0.1", 0))
        port, control_port = first.getsockname()[1], second.getsockname()[1]
    assert port != control_port
    control = subprocess.Popen(
        [sys.executable, child, str(control_port), "control-child"],
        cwd=tmp_path,
        env=os.environ.copy(),
        **workflow.process_group_options(),
    )
    owned = None
    try:
        wait_until(lambda: reachable(control_port, "control-child"))
        owned = subprocess.Popen(
            [sys.executable, parent, child, str(port), "owned-child"],
            cwd=tmp_path,
            env=os.environ.copy(),
            **workflow.process_group_options(),
        )
        wait_until(lambda: owned.poll() is not None)
        assert owned.returncode == 0 and reachable(port), "prove descendant outlived exited parent"
        workflow.stop(owned)
        wait_until(lambda: not reachable(port))
        assert reachable(control_port, "control-child"), "unowned service must survive cleanup"
    finally:
        if owned:
            workflow.stop(owned)
        workflow.stop(control)
        # Failure cleanup uses only this fixture's independently recorded child PID.
        record = tmp_path / "owned-child.pid"
        if record.is_file() and os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", record.read_text(), "/T", "/F"], capture_output=True, check=False
            )


def directory_alias(alias, destination):
    alias.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(alias), str(destination)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
    else:
        alias.symlink_to(destination, target_is_directory=True)


def test_adversarial_external_runtime_alias_and_cleanup(workflow, tmp_path, monkeypatch):
    root, outside = tmp_path / "repo", tmp_path / "outside-runtime"
    outside.mkdir()
    name = ".venv"
    config = {
        "environments": [{"path": name, "requirements": ["requirements.txt"]}],
        "generation_environments": [name],
    }
    write(root / "scripts/local/workflow.json", json.dumps(config))
    interpreter = outside / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    write(interpreter, "interpreter placeholder; never executed")
    write(root / "requirements.txt", "example==1\n")
    directory_alias(root / name, outside)
    try:
        assert workflow.venv_python(root, name).resolve() == interpreter.resolve()
        assert workflow.generation_python(root, config).resolve() == interpreter.resolve()
        # Initialization uses the declared alias too; fake pip never executes the placeholder.
        config.update(required=[], api={"active": False})
        write(root / ".env.example", "MODE=literal\n")
        calls = []
        monkeypatch.setattr(workflow, "prerequisites", lambda *_: None)
        monkeypatch.setattr(workflow, "install_frontend", lambda *_: None)
        monkeypatch.setattr(workflow, "check_shipped", lambda *_: None)
        monkeypatch.setattr(workflow, "run", lambda command, *args, **kw: calls.append(command))
        workflow.initialize(root, config)
        assert len(calls) == 1 and "pip" in calls[0]
        assert Path(calls[0][0]).resolve() == interpreter.resolve()
        assert (
            outside / ".bootstrap-requirements.sha256"
        ).read_text().strip() == workflow.requirements_digest(root, ["requirements.txt"])
        workflow.initialize(root, config)
        assert len(calls) == 1
        with pytest.raises(workflow.Failure, match="escapes"):
            workflow.relative(root, name)
        with pytest.raises(workflow.Failure, match="Undeclared"):
            workflow.environment_directory(root, "../outside-runtime")
        interpreter.unlink()
        with pytest.raises(workflow.Failure, match="Missing interpreter.*declared environment"):
            workflow.generation_python(root, config)
    finally:
        if os.name == "nt":
            os.rmdir(root / name)
        else:
            (root / name).unlink()
    reserved = root / ".models.bootstrap-backup-owned"
    write(outside / "sentinel", "keep")
    directory_alias(reserved, outside)
    calls = []
    original = shutil.rmtree
    monkeypatch.setattr(workflow.shutil, "rmtree", lambda *args: calls.append(args))
    try:
        with pytest.raises(workflow.Failure, match="symlink/junction"):
            workflow.remove_owned(reserved, root)
        assert not calls and (outside / "sentinel").read_text() == "keep"
    finally:
        if os.name == "nt":
            os.rmdir(reserved)
        else:
            reserved.unlink()
    monkeypatch.setattr(workflow.shutil, "rmtree", original)
    ordinary = root / ".models.bootstrap-incoming-owned"
    write(ordinary / "file", "remove only this")
    workflow.remove_owned(ordinary, root)
    assert not ordinary.exists() and (outside / "sentinel").exists()
    with pytest.raises(workflow.Failure, match="reserved"):
        workflow.remove_owned(outside, root)


def test_adversarial_tracked_shell_modes(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "bootstrap_integrity", ROOT / "scripts/check_base_integrity.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # NUL-delimited actual Git index syntax, including spaces in paths.
    def index(mode):
        return SimpleNamespace(
            stdout=f"{mode} abc 0\tscripts/local/00 install.sh\x00100644 def 0\tREADME.md\0".encode()
        )

    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kw: index("100755"))
    assert module.nonexecutable_shells(tmp_path) == []
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kw: index("100644"))
    assert module.nonexecutable_shells(tmp_path) == ["scripts/local/00 install.sh"]
    for mode, expected in (("100755", 0), ("100644", 1)):

        def git(command, **kwargs):
            if "--stage" in command:
                return index(mode)
            if "grep" in command:
                return SimpleNamespace(returncode=1, stdout=b"")
            return SimpleNamespace(stdout=b"scripts/local/00 install.sh\x00README.md\x00")

        monkeypatch.setattr(module.subprocess, "run", git)
        assert module.main(["check_base_integrity.py", str(tmp_path)]) == expected


def test_adversarial_locked_node_engines(workflow, tmp_path, monkeypatch, capsys):
    for name in ("package.json", "package-lock.json"):
        write(tmp_path / "frontend" / name, (ROOT / "frontend" / name).read_text())
    declared = json.loads((ROOT / "frontend/package.json").read_text())["engines"]["node"]
    assert declared == "^22.12.0 || ^24.0.0 || >=26.0.0"
    for version, accepted in (
        ((22, 0, 0), False),
        ((22, 11, 9), False),
        ((22, 12, 0), True),
        ((23, 0, 0), False),
        ((24, 14, 1), True),
        ((25, 0, 0), False),
        ((26, 0, 0), True),
        ((28, 1, 0), True),
    ):
        assert workflow.compatible_node(tmp_path, version) is accepted
        calls = []

        def run(command, *args, **kwargs):
            calls.append(command)
            return (
                "v" + ".".join(map(str, version))
                if command[0] == "node"
                else "git version 2.50.0"
                if command[0] == "git"
                else "Python 3.12.10"
            )

        monkeypatch.setattr(workflow, "run", run)
        if accepted:
            workflow.prerequisites(tmp_path)
        else:
            with pytest.raises(workflow.Failure, match="Repair with"):
                workflow.prerequisites(tmp_path)
            assert declared in capsys.readouterr().err
        assert len(calls) == 3 and all(command[-1] == "--version" for command in calls)
    lock = json.loads((tmp_path / "frontend/package-lock.json").read_text())
    lock["packages"][""]["engines"]["node"] = ">=22"
    write(tmp_path / "frontend/package-lock.json", json.dumps(lock))
    with pytest.raises(workflow.Failure, match="package and lock"):
        workflow.compatible_node(tmp_path, (24, 14, 1))


def test_adversarial_dinhot_readiness_admission(workflow):
    config = workflow.settings(ROOT)
    # DinHot admits its 11 rows with exactly its declared outcomes: the refused case C11 (params-record partial), the skipped
    # benchmark cells (benchmark-results partial), the refuted warm-start model (warmstart-model training) and the dormant API.
    ready = json.loads((ROOT / "data/derived/readiness.json").read_text())
    assert len(ready["contracts"]) == 11
    assert config["readiness_exceptions"] == {"params-record": "partial", "benchmark-results": "partial",
                                              "warmstart-model": "training", "api": "missing"}
    assert config["stage_inputs"] == ["data/examples/cases.json"]
    workflow.check_readiness_states(ROOT, config, ready, ROOT)
    rows = {row["id"]: i for i, row in enumerate(ready["contracts"])}
    for row_id, state in (("case-index", "missing"), ("trace", "partial"), ("cgh-net", None),
                          ("benchmark-results", "missing"), ("api", "partial"), ("warmstart-model", "missing")):
        bad = json.loads(json.dumps(ready))
        bad["contracts"][rows[row_id]]["state"] = state
        with pytest.raises(workflow.Failure, match="Partial readiness"):
            workflow.check_readiness_states(ROOT, config, bad, ROOT)


def test_adversarial_frontend_environment_isolation(workflow, fixture_repo, monkeypatch):
    root, config, _ = fixture_repo
    present(root, config, workflow)
    stamp(root, config, workflow)
    version = (root / "VERSION").read_text().strip()
    write(
        root / "data/derived/manifests/index.json",
        json.dumps(
            {"engine_version": version, "cases": [{"case_id": "a", "manifest_path": "manifests/a.json", "path": "manifests/a.json"}]}
        ),
    )
    write(root / "data/derived/manifests/a.json", json.dumps({"artifact": {"path": "cases/a.json"}}))
    # DinHot's copy-data also copies the benchmark and the learned models' metrics (catalog rows benchmark-results, model-metrics)
    write(root / "data/derived/benchmark/results.json", json.dumps({"engine_version": version}))
    write(root / "data/derived/models/metrics.json", json.dumps({"engine_version": version}))
    for name in ("copy-data.mjs", "declared.mjs"):
        target = root / "frontend/scripts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "frontend/scripts" / name, target)
    raw = root.parent / "global raw store"
    raw.mkdir()
    stores = {
        "CAOS_DATA_ROOT": str(raw),
        "CAOS_MODELS_ROOT": str(root.parent / "global models"),
        "CAOS_TEMP_ROOT": str(root.parent / "global scratch"),
    }
    for key, value in stores.items():
        monkeypatch.setenv(key, value)
    baseline = workflow.environment(root)
    producer = root / "producer.py"
    capture = (
        "import os,json\nfrom pathlib import Path\n"
        "(Path(os.environ['CAOS_MODELS_ROOT']).parent/'generation-env.json').write_text("
        "json.dumps({k:os.environ.get(k) for k in "
        "('CAOS_DATA_ROOT','CAOS_MODELS_ROOT','CAOS_TEMP_ROOT')}))\n"
    )
    write(producer, capture + producer.read_text())
    with socket.socket() as api_reservation, socket.socket() as web_reservation:
        api_reservation.bind(("127.0.0.1", 0))
        web_reservation.bind(("127.0.0.1", 0))
        api_port = api_reservation.getsockname()[1]
        config["web_port"] = web_reservation.getsockname()[1]
    write(
        root / "api.py",
        """import json,os,sys
from http.server import BaseHTTPRequestHandler,HTTPServer
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  body=json.dumps({k:os.environ.get(k) for k in
   ('CAOS_DATA_ROOT','CAOS_MODELS_ROOT','CAOS_TEMP_ROOT')}).encode()
  self.send_response(200);self.end_headers();self.wfile.write(body)
 def log_message(self,*args): pass
HTTPServer(('127.0.0.1',int(sys.argv[1])),Handler).serve_forever()
""",
    )
    write(
        root / "frontend/frontend-env.py",
        """import json,os,sys,urllib.request
from pathlib import Path
api=json.loads(urllib.request.urlopen('http://127.0.0.1:'+sys.argv[1]+'/health').read())
front={k:os.environ.get(k) for k in ('CAOS_DATA_ROOT','CAOS_MODELS_ROOT','CAOS_TEMP_ROOT')}
Path('frontend-env.json').write_text(json.dumps({'frontend':front,'api':api}))
""",
    )
    overlay = {"CAOS_DATA_ROOT": "{root}/data/derived"}
    config.update(
        frontend_environment=overlay,
        frontend_prepare=[["node", "scripts/copy-data.mjs"]],
        frontend_command=["{python}", "frontend-env.py", "{port}"],
    )
    config["api"].update(
        active=True, port=api_port, health="/health", command=["{python}", "api.py", "{port}"]
    )
    write(root / "scripts/local/workflow.json", json.dumps(config))
    stage = workflow.generate(root, config, baseline)
    generated = json.loads((stage / "generation-env.json").read_text())
    assert generated["CAOS_DATA_ROOT"] == stores["CAOS_DATA_ROOT"]
    assert generated["CAOS_TEMP_ROOT"] == stores["CAOS_TEMP_ROOT"]
    assert Path(generated["CAOS_MODELS_ROOT"]) == stage / "checkpoints"
    assert baseline == workflow.environment(root), "generation must not mutate caller storage settings"

    workflow.development(root, config)
    recorded = root / "frontend/frontend-env.json"
    observed = json.loads(recorded.read_text())
    assert Path(observed["frontend"]["CAOS_DATA_ROOT"]).resolve() == (root / "data/derived").resolve()
    assert observed["api"] == stores
    assert all(observed["frontend"][key] == stores[key] for key in ("CAOS_MODELS_ROOT", "CAOS_TEMP_ROOT"))
    assert (root / "frontend/public/data/cases/a.json").read_bytes() == (
        root / "data/derived/cases/a.json"
    ).read_bytes()
    assert baseline == workflow.environment(root)
    assert workflow.settings(ROOT)["frontend_environment"] == overlay

    # Without the opt-in, the actual legacy consumer must retain its original global-root behavior.
    config.pop("frontend_environment")
    recorded.unlink()
    with pytest.raises(workflow.Failure, match="Command failed"):
        workflow.development(root, config)
    assert not recorded.exists()
    with pytest.raises(OSError):
        urllib.request.urlopen(f"http://127.0.0.1:{api_port}/health", timeout=0.2)
    assert baseline == workflow.environment(root)

    # With no explicit global selector and no overlay, copy-data's existing local default still works.
    monkeypatch.delenv("CAOS_DATA_ROOT")
    workflow.development(root, config)
    observed = json.loads(recorded.read_text())
    assert observed["frontend"]["CAOS_DATA_ROOT"] is None and observed["api"]["CAOS_DATA_ROOT"] is None
    for key in ("CAOS_MODELS_ROOT", "CAOS_TEMP_ROOT"):
        assert observed["frontend"][key] == observed["api"][key] == stores[key]
