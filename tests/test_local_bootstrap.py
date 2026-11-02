"""Behavioral local-workflow tests: external fixture repositories, never installs or science."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def workflow():
    path = ROOT / "scripts/local/workflow.py"
    spec = importlib.util.spec_from_file_location("tested_local_workflow", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


@pytest.fixture
def fixture_repo(tmp_path, monkeypatch, workflow):
    root = tmp_path / "fixture repo with spaces"
    write(root / "VERSION", (ROOT / "VERSION").read_text())
    write(root / ".env.example", "APP_ENV=dev\nLITERAL=$(never_execute_this)\n")
    write(root / "requirements.txt", "example==1\n")
    write(root / "requirements-dev.txt", "-r requirements.txt\n")
    write(root / "docs/contracts/catalog.md", "# Fixture catalog\n")
    write(root / "frontend/package-lock.json", "{}")
    write(
        root / "producer.py",
        """import json, os, sys
from pathlib import Path
mode, stage = sys.argv[1], Path(sys.argv[2])
version = (stage/"VERSION").read_text().strip()
if mode == "validate":
    assert (stage/"models/model.json").is_file()
    print("validator warning", file=sys.stderr)
    raise SystemExit(0)
assert Path(os.environ["CAOS_MODELS_ROOT"]).is_relative_to(stage)
files = {"data/derived/manifests/index.json": {"engine_version":version,"cases":[{"case_id":"a"}]},
         "data/derived/cases/a.json": {"engine_version":version,"value":"new"},
         "data/derived/readiness.json": {"product_version":version,"contracts":[{"state":"available"}]},
         "models/model.json": {"engine_version":version,"value":"new"}}
for name,value in files.items():
    path=stage/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value))
checkpoint=Path(os.environ["CAOS_MODELS_ROOT"])/"oreflow/weights"
checkpoint.parent.mkdir(parents=True,exist_ok=True)
checkpoint.write_text("external-only")
print("producer warning",file=sys.stderr)
""",
    )
    config = {
        "primary_environment": ".venv",
        "generation_environments": [".venv"],
        "environments": [{"path": ".venv", "requirements": ["requirements-dev.txt"]}],
        "node_stamp": ".fixture-lock.sha256",
        "promote": ["data/derived", "models"],
        "required": [
            "data/derived/manifests/index.json",
            "data/derived/cases/a.json",
            "data/derived/readiness.json",
            "models/model.json",
        ],
        "generation": [{"script": "producer.py", "args": ["generate", "{stage}"]}],
        "validators": [{"script": "producer.py", "args": ["validate", "{stage}"]}],
        "api": {"active": False, "port": 8000, "health": "/health", "command": []},
        "web_port": 5173,
        "frontend_command": [],
        "frontend_prepare": [],
    }
    write(root / "scripts/local/workflow.json", json.dumps(config))
    monkeypatch.setattr(workflow, "venv_python", lambda *_: Path(sys.executable))
    env = {**os.environ, "CAOS_TEMP_ROOT": str(tmp_path / "external scratch"), "PYTHONDONTWRITEBYTECODE": "1"}
    return root, config, env


def present(root, config, workflow):
    version = (root / "VERSION").read_text().strip()
    for name in config["required"]:
        write(root / name, json.dumps({"engine_version": version, "old": True}))
    write(
        root / "data/derived/readiness.json",
        json.dumps({"product_version": version, "contracts": [{"state": "available"}]}),
    )
    write(root / "frontend/node_modules/.bin/vite", "fixture")
    write(root / "frontend/node_modules/.package-lock.json", "{}")
    write(
        root / "frontend/node_modules" / config["node_stamp"],
        workflow.digest(root / "frontend/package-lock.json"),
    )


def test_adversarial_prerequisites_are_check_only(workflow, tmp_path, monkeypatch):
    for name in ("package.json", "package-lock.json"):
        write(tmp_path / "frontend" / name, (ROOT / "frontend" / name).read_text())
    calls = []

    def command(args, root, env=None, capture=False):
        calls.append(args)
        return (
            "Python 3.13.2"
            if args[0] == sys.executable
            else "v24.14.0"
            if args[0] == "node"
            else "git version 2.50"
        )

    monkeypatch.setattr(workflow, "run", command)
    workflow.prerequisites(tmp_path)
    assert len(calls) == 3 and all(args[-1] == "--version" for args in calls)

    def absent(args, *unused, **kw):
        if args[0] == "node":
            raise FileNotFoundError("node")
        return command(args, *unused, **kw)

    monkeypatch.setattr(workflow, "run", absent)
    with pytest.raises(workflow.Failure, match="00_install-prereqs"):
        workflow.prerequisites(tmp_path)
    assert not any("install" in args for args in calls)


def test_adversarial_init_preserves_env_and_installs_by_fingerprint(workflow, fixture_repo, monkeypatch):
    root, config, _ = fixture_repo
    present(root, config, workflow)
    original = "KEEP=unchanged\nLITERAL=$(never_execute_this)\n"
    write(root / ".env", original)
    monkeypatch.setattr(workflow, "prerequisites", lambda *_: None)
    calls = []

    def command(args, cwd, env=None, capture=False):
        calls.append(list(map(str, args)))
        if "venv" in args:
            (root / ".venv").mkdir()
        if "ci" in args:
            write(root / "frontend/node_modules/.bin/vite", "")
            write(root / "frontend/node_modules/.package-lock.json", "{}")
        return ""

    monkeypatch.setattr(workflow, "run", command)
    workflow.initialize(root, config)
    first = len(calls)
    assert first == 2  # venv + environment-local pip; matching frontend lock is preserved
    assert (root / ".env").read_text() == original
    assert workflow.environment(root)["LITERAL"] == "$(never_execute_this)"
    workflow.initialize(root, config)
    assert len(calls) == first
    write(root / "requirements.txt", "example==2\n")
    workflow.initialize(root, config)
    assert len(calls) == first + 1 and "pip" in calls[-1]
    write(root / "frontend/package-lock.json", '{"changed":true}')
    workflow.initialize(root, config)
    assert "ci" in calls[-1]
    stamp = root / ".venv/.bootstrap-requirements.sha256"
    stamp.unlink()

    def failed(*args, **kwargs):
        raise workflow.Failure("simulated pip warning plus failure", 19)

    monkeypatch.setattr(workflow, "run", failed)
    with pytest.raises(workflow.Failure) as error:
        workflow.initialize(root, config)
    assert error.value.code == 19 and not stamp.exists()
    assert (root / ".env").read_text() == original
    write(root / "data/derived/manifests/index.json", '{"engine_version":"stale"}')
    with pytest.raises(workflow.Failure, match="stale/mixed"):
        workflow.check_shipped(root, config)


def test_adversarial_generation_is_sandboxed_and_absence_is_actionable(workflow, fixture_repo, monkeypatch):
    root, config, env = fixture_repo
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    stage = workflow.generate(root, config, env)
    assert not stage.is_relative_to(root)
    assert (stage / "checkpoints/oreflow/weights").read_text() == "external-only"
    assert (stage / "models/model.json").is_file()
    assert all((root / name).read_bytes() == value for name, value in before.items())
    assert not (root / "models").exists() and not (root / "data/derived").exists()
    with pytest.raises(workflow.Failure, match="CAOS_TEMP_ROOT"):
        workflow.generate(root, config, {**env, "CAOS_TEMP_ROOT": str(root / "forbidden")})
    monkeypatch.setattr(workflow, "prerequisites", lambda *_: None)
    monkeypatch.setattr(workflow, "install_frontend", lambda *_: None)
    monkeypatch.setattr(workflow, "environment", lambda *_: env)
    (root / ".venv").mkdir()
    write(
        root / ".venv/.bootstrap-requirements.sha256",
        workflow.requirements_digest(root, config["environments"][0]["requirements"]),
    )
    with pytest.raises(workflow.Failure, match="Explicit promotion"):
        workflow.initialize(root, config)
    assert (root / ".env").read_text() == (root / ".env.example").read_text()
    assert not (root / "data/derived").exists()


def test_adversarial_release_rejects_mixed_partial_and_rolls_back(workflow, fixture_repo, monkeypatch):
    root, config, env = fixture_repo
    present(root, config, workflow)
    stage = workflow.generate(root, config, env)
    old = {
        p.relative_to(root): p.read_bytes()
        for folder in ("data/derived", "models")
        for p in (root / folder).rglob("*")
        if p.is_file()
    }
    record = stage / "local-generation.json"

    def seal():
        write(
            record,
            json.dumps(
                {
                    "source": workflow.source_identity(root, config),
                    "files": workflow.payload_hashes(stage, config),
                }
            ),
        )

    target = stage / "data/derived/cases/a.json"
    write(target, '{"engine_version":"mismatched"}')
    seal()
    with pytest.raises(workflow.Failure, match="Mixed"):
        workflow.promote(root, config, stage, Path(sys.executable), env)
    version = (root / "VERSION").read_text().strip()
    write(target, json.dumps({"engine_version": version, "value": "new"}))
    readiness = stage / "data/derived/readiness.json"
    write(readiness, json.dumps({"product_version": version, "contracts": [{"state": "partial"}]}))
    seal()
    with pytest.raises(workflow.Failure, match="Partial readiness"):
        workflow.promote(root, config, stage, Path(sys.executable), env)
    write(readiness, json.dumps({"product_version": version, "contracts": [{"state": "available"}]}))
    seal()
    real_replace = workflow.os.replace
    tripped = False

    def fail_second(source, destination):
        nonlocal tripped
        if (
            not tripped
            and ".bootstrap-incoming-" in Path(source).name
            and Path(destination) == root / "models"
        ):
            tripped = True
            raise OSError("simulated second-directory promotion failure")
        real_replace(source, destination)

    monkeypatch.setattr(workflow.os, "replace", fail_second)
    with pytest.raises(OSError, match="second-directory"):
        workflow.promote(root, config, stage, Path(sys.executable), env)
    assert all((root / name).read_bytes() == content for name, content in old.items())
    assert not list(root.rglob("*.bootstrap-*"))
    monkeypatch.setattr(workflow.os, "replace", real_replace)
    workflow.promote(root, config, stage, Path(sys.executable), env)
    assert json.loads((root / "models/model.json").read_text())["value"] == "new"
    assert not list(root.rglob("*.bootstrap-*"))


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_declared_producer_plan_keeps_all_outputs_external(workflow, fixture_repo):
    root, _, env = fixture_repo
    config = workflow.settings(ROOT)
    config["generation_modules"] = []
    config["generation_environments"] = [".venv"]
    config["readiness_excludes"] = []  # This output-routing fixture has no contract table.
    config["stage_inputs"] = []  # Actual authored input/admission is covered by the real-pipeline test.
    config.pop("readiness_check", None)
    config.pop("readiness_exceptions", None)
    write(root / "scripts/local/workflow.json", json.dumps(config))
    shutil.copyfile(ROOT / "scripts/local/producer_bridge.py", root / "scripts/local/producer_bridge.py")
    for name in ("pipeline/__init__.py", "pipeline/core/__init__.py", "pipeline/cases/__init__.py"):
        write(root / "data-pipeline" / name, "")
    write(
        root / "data-pipeline/pipeline/core/readiness.py",
        """import json
def compute(repo_root,derived_root,models_dir):
    return {"product_version":(repo_root/"VERSION").read_text().strip(),"contracts":[{"state":"available"}]}
def write(derived_root,document):
    (derived_root/"readiness.json").write_text(json.dumps(document))
""",
    )
    write(
        root / "data-pipeline/pipeline/registry.py",
        'from types import SimpleNamespace\ndef list_cases(): return [SimpleNamespace(id="a")]\n',
    )
    # This unsafe API default is deliberate: the bridge must pass an external output.
    write(
        root / "data-pipeline/run_geomet.py",
        """import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build(source_path=None, output_path=ROOT/"LEAK.json"):
    assert not output_path.is_relative_to(ROOT)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps({"fixture":"measured"}))
def fit_checkpoint(source_path=None, checkpoint_path=None):
    assert checkpoint_path is not None and not checkpoint_path.is_relative_to(ROOT)
    checkpoint_path.parent.mkdir(parents=True,exist_ok=True)
    checkpoint_path.write_text("checkpoint")
""",
    )
    stub = """import json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
version=(root/"VERSION").read_text().strip()
args=sys.argv[1:]
if Path(__file__).name=="fetch.py":
    assert args==["--dataset","all"]
    assert not Path(os.environ["CAOS_DATA_ROOT"]).is_relative_to(root)
    raise SystemExit(0)
output=Path(args[args.index("--output")+1])
assert not output.is_relative_to(root)
if Path(__file__).name=="run_particles.py":
    model=Path(args[args.index("--onnx-output")+1])
    checkpoint=Path(args[args.index("--models-root")+1])
    assert not model.is_relative_to(root) and not checkpoint.is_relative_to(root)
    model.parent.mkdir(parents=True,exist_ok=True);model.write_text("onnx")
    raise SystemExit(0)
if Path(__file__).name=="run_iron_plant.py":
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text("{}")
    raise SystemExit(0)
stage=output.parents[1]
config=json.loads((root/"scripts/local/workflow.json").read_text())
if "--models" in args:
    assert Path(args[args.index("--models")+1])==stage/"models"
    assert Path(args[args.index("--checkpoint-dir")+1]).is_relative_to(stage)
for name in config["required"]:
    path=stage/name
    if "--models" not in args and name.startswith("models/"):
        path=output/name
    path.parent.mkdir(parents=True,exist_ok=True)
    value={"engine_version":version}
    if name.endswith("index.json"):value["cases"]=[{"case_id":"a"}]
    if name.endswith("readiness.json"):value={"product_version":version,"contracts":[{"state":"available"}]}
    if name.endswith("validation.json"):value["passed"]=True
    path.write_text(json.dumps(value))
"""
    for name in ("fetch.py", "run_particles.py", "run_iron_plant.py", "run.py"):
        write(root / "data-pipeline" / name, stub)
    for row in config["validators"]:
        if row["script"].endswith("producer_bridge.py"):
            continue
        write(root / row["script"], "print('fixture semantic/schema validator')\n")
    env = {**env, "CAOS_DATA_ROOT": str(root.parent / "source cache")}
    stage = workflow.generate(root, config, env)
    assert not (root / "LEAK.json").exists()
    assert not (root / "models").exists() and not (root / "data/derived").exists()
    assert all(list(stage.glob(name)) for name in config["required"])


def test_adversarial_dev_supervises_api_and_frontend(workflow, fixture_repo, monkeypatch):
    root, config, env = fixture_repo
    present(root, config, workflow)
    write(
        root / ".venv/.bootstrap-requirements.sha256",
        workflow.requirements_digest(root, ["requirements-dev.txt"]),
    )
    port = free_port()
    write(
        root / "api.py",
        """from http.server import BaseHTTPRequestHandler,HTTPServer
import sys
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
HTTPServer(("127.0.0.1",int(sys.argv[1])),Handler).serve_forever()
""",
    )
    write(
        root / "frontend/front.py",
        """import os,urllib.request
urllib.request.urlopen("http://127.0.0.1:"+os.environ["APP_PORT"]+"/health").read()
raise SystemExit(int(os.environ.get("FRONT_EXIT","0")))
""",
    )
    config["api"] = {
        "active": True,
        "port": port,
        "health": "/health",
        "command": ["{python}", "api.py", "{port}"],
    }
    config["web_port"] = free_port()
    config["frontend_command"] = ["{python}", "front.py"]
    monkeypatch.setattr(workflow, "environment", lambda *_: {**env, "APP_PORT": str(port)})
    workflow.development(root, config)
    with pytest.raises((OSError, urllib.error.URLError)):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
    monkeypatch.setattr(
        workflow, "environment", lambda *_: {**env, "APP_PORT": str(port), "FRONT_EXIT": "23"}
    )
    with pytest.raises(workflow.Failure) as error:
        workflow.development(root, config)
    assert error.value.code == 23
    config["api"]["active"] = False
    config["frontend_command"] = ["{python}", "-c", "print('dormant API stays stopped')"]
    workflow.development(root, config)
    with socket.socket() as held:
        held.bind(("127.0.0.1", config["web_port"]))
        held.listen()
        with pytest.raises(workflow.Failure, match="occupied"):
            workflow.development(root, config)


def bash_executable():
    directory = os.environ.get("ProgramFiles")
    git_bash = Path(directory) / "Git/bin/bash.exe" if directory else None
    return str(git_bash) if git_bash and git_bash.is_file() else shutil.which("bash")


def test_adversarial_shell_entrypoints_propagate_failure(workflow, tmp_path):
    root = tmp_path / "shell repo with spaces"
    destination = root / "scripts/local"
    destination.mkdir(parents=True)
    for path in (ROOT / "scripts/local").glob("*"):
        if path.suffix in (".sh", ".ps1"):
            shutil.copyfile(path, destination / path.name)
    helper = destination / "workflow.py"
    shell = shutil.which("powershell") or shutil.which("pwsh")
    bash = bash_executable()
    invocations = []
    for name, action in (
        ("00_install-prereqs", "prereqs"),
        ("01_init", "init"),
        ("02_generate-data", "generate"),
        ("03_dev", "dev"),
    ):
        ps_extra = (
            ["-Release", "-FromStage", str(tmp_path / "stage with spaces")] if action == "generate" else []
        )
        sh_extra = (
            ["--release", "--from-stage", str(tmp_path / "stage with spaces")] if action == "generate" else []
        )
        if shell:
            invocations.append(
                ([shell, "-NoProfile", "-File", str(destination / (name + ".ps1")), *ps_extra], action)
            )
        if bash:
            invocations.append(([bash, str(destination / (name + ".sh")), *sh_extra], action))
    assert invocations, "a supported shell is required for entrypoint verification"
    env = {**os.environ, "PYTHON": sys.executable.replace("\\", "/")}
    for code in (0, 23):
        write(
            helper,
            f"import json,sys\nprint(json.dumps(sys.argv[1:]))\n"
            f"print('native warning',file=sys.stderr)\nraise SystemExit({code})\n",
        )
        for command, action in invocations:
            result = subprocess.run(
                command, cwd=tmp_path, env=env, capture_output=True, text=True, check=False
            )
            assert result.returncode == code, (command, result.stdout, result.stderr)
            assert "native warning" in result.stderr
            forwarded = json.loads(result.stdout)
            assert forwarded[0] == action
            if action == "generate":
                assert forwarded[1:] == ["--release", "--from-stage", str(tmp_path / "stage with spaces")]
