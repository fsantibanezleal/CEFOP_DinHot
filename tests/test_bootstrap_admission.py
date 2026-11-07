"""Late-mutation and role-root adversaries for local artifact promotion."""

import json
import importlib.util
import shutil
from pathlib import Path
import sys
import runpy

import pytest

from test_local_bootstrap import fixture_repo as fixture_repo
from test_local_bootstrap import workflow as workflow
from test_local_bootstrap import present
from test_bootstrap_regressions import directory_alias


def test_adversarial_external_defaults_and_instantiation_are_bound():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "scripts/local/workflow.json").read_text())
    assert config["external_environments_required"] is True
    product = json.loads((root / "product.json").read_text(encoding="utf-8"))
    expected = "caos-product-template" if (root / ".template-source").exists() else product["slug"]
    assert config["environment_namespace"] == expected


@pytest.mark.parametrize("slug", ["con", "aux", "nul", "prn", "com1", "lpt9", "demo"])
def test_adversarial_instantiation_validates_namespace_before_identity_writes(tmp_path, monkeypatch, slug):
    source = Path(__file__).resolve().parents[1]
    if not (source / ".template-source").exists():
        pytest.skip("Instantiation is upstream template behavior; products cannot instantiate again.")
    spec = importlib.util.spec_from_file_location("instantiation_admission", source / "scripts/instantiate.py")
    inst = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inst)
    root = tmp_path / "identity not yet written"
    (root / ".github/workflows").mkdir(parents=True)
    (root / ".template-source").write_text("preserve template sentinel")
    (root / "VERSION").write_text((source / "VERSION").read_text())
    shutil.copyfile(source / ".github/workflows/ci.yml", root / ".github/workflows/ci.yml")
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    monkeypatch.setattr(inst, "ROOT", root)

    class FirstIdentityWrite(Exception):
        pass

    def first_write(*args):
        raise FirstIdentityWrite

    monkeypatch.setattr(inst, "write", first_write)
    monkeypatch.setattr(sys, "argv", ["instantiate", "--slug", slug, "--name", "Example", "--repo", "CAOS_Example",
                                    "--deploy", "pages", "--visibility", "public", "--tagline-en", "English line",
                                    "--tagline-es", "Spanish line", "--no-run"])
    if slug == "demo":
        with pytest.raises(FirstIdentityWrite):
            inst.main()
    else:
        assert inst.main() == 2
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("mutation", ["payload", "source", "receipt", "product-metadata", "api-metadata"])
def test_adversarial_validator_cannot_change_accepted_identity(workflow, fixture_repo, monkeypatch, mutation):
    root, config, env = fixture_repo
    if mutation.endswith("metadata"):
        path = root / ("product.json" if mutation == "product-metadata" else "app/openapi.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"identity":"original"}')
    present(root, config, workflow)
    stage = workflow.generate(root, config, env)
    before = workflow.payload_hashes(root, config)
    original = workflow.commands

    def commands(repo, rows, values, values_env):
        original(repo, rows, values, values_env)
        if mutation == "payload":
            path = stage / "data/derived/cases/a.json"
            path.write_text(json.dumps({"engine_version": (root / "VERSION").read_text().strip(), "value": "tampered"}))
        elif mutation == "source":
            path = root / "producer.py"
            path.write_text(path.read_text() + "\n# source changed during validation\n")
        elif mutation == "receipt":
            path = stage / "local-generation.json"
            path.write_text(path.read_text() + "\n")
        else:
            name = "product.json" if mutation == "product-metadata" else "app/openapi.json"
            for tree in (root, stage):
                (tree / name).write_text('{"identity":"changed in both places"}')

    monkeypatch.setattr(workflow, "commands", commands)
    with pytest.raises(workflow.Failure):
        workflow.promote(root, config, stage, Path(sys.executable), env)
    assert workflow.payload_hashes(root, config) == before


@pytest.mark.parametrize("mutation", ["incoming", "copy-source", "commit-source", "commit-payload"])
def test_adversarial_copy_and_install_are_bound_to_original_receipt(workflow, fixture_repo, monkeypatch, mutation):
    root, config, env = fixture_repo
    present(root, config, workflow)
    stage = workflow.generate(root, config, env)
    expected = json.loads((stage / "local-generation.json").read_text())
    before = workflow.payload_hashes(root, config)
    copy = workflow.shutil.copytree
    replace = workflow.os.replace
    changed = False

    def mutate_source():
        path = root / "producer.py"
        path.write_text(path.read_text() + "\n# source changed after validation\n")

    def copytree(source, target, *args, **kwargs):
        nonlocal changed
        result = copy(source, target, *args, **kwargs)
        if not changed and ".bootstrap-incoming-" in Path(target).name:
            if mutation == "incoming":
                (Path(target) / "cases/a.json").write_text(json.dumps({"engine_version": (root / "VERSION").read_text().strip(), "value": "changed"}))
                changed = True
            elif mutation == "copy-source":
                mutate_source()
                changed = True
        return result

    def replacing(source, target):
        nonlocal changed
        result = replace(source, target)
        if not changed and Path(target) == root / "data/derived":
            if mutation == "commit-source":
                mutate_source()
                changed = True
            elif mutation == "commit-payload":
                path = root / "data/derived/cases/a.json"
                path.write_text(json.dumps({"engine_version": (root / "VERSION").read_text().strip(), "value": "changed"}))
                # Match the mutable stage too: it is not the original authority.
                (stage / "data/derived/cases/a.json").write_bytes(path.read_bytes())
                changed = True
        return result

    monkeypatch.setattr(workflow.shutil, "copytree", copytree)
    monkeypatch.setattr(workflow.os, "replace", replacing)
    with pytest.raises(workflow.Failure):
        workflow.promote(root, config, stage, Path(sys.executable), env)
    assert changed
    assert workflow.payload_hashes(root, config) == before
    assert expected["files"] != before


def test_adversarial_external_environment_policy_refuses_internal_targets(workflow, fixture_repo, monkeypatch):
    root, config, _ = fixture_repo
    config.update(external_environments_required=True, environment_namespace="fixture-product")
    path = root / "scripts/local/workflow.json"
    path.write_text(json.dumps(config))
    monkeypatch.delenv("CAOS_VENVS_ROOT", raising=False)
    with pytest.raises(workflow.Failure, match="CAOS_VENVS_ROOT"):
        workflow.environment_directory(root, ".venv")
    assert not (root / ".venv").exists()
    monkeypatch.setenv("CAOS_VENVS_ROOT", str(root / "forbidden"))
    with pytest.raises(workflow.Failure, match="outside"):
        workflow.environment_directory(root, ".venv")
    assert not (root / "forbidden").exists()
    external = root.parent / "external environments"
    monkeypatch.setenv("CAOS_VENVS_ROOT", str(external))
    expected = external / "fixture-product/.venv"
    assert workflow.environment_directory(root, ".venv") == expected
    assert not expected.exists(), "Resolving an environment is read-only."
    (root / ".venv").mkdir()
    with pytest.raises(workflow.Failure, match="external"):
        workflow.environment_directory(root, ".venv")


@pytest.mark.parametrize("namespace", [None, "", ".", "..", "../escape", "a/b", "a\\b", "CON", "com1.foo", "trailing."])
def test_adversarial_external_namespace_is_a_safe_required_component(workflow, fixture_repo, monkeypatch, namespace):
    root, config, _ = fixture_repo
    config.update(external_environments_required=True, environment_namespace=namespace)
    (root / "scripts/local/workflow.json").write_text(json.dumps(config))
    monkeypatch.setenv("CAOS_VENVS_ROOT", str(root.parent / "outside"))
    with pytest.raises(workflow.Failure):
        workflow.environment_directory(root, ".venv")
    assert not (root.parent / "outside").exists()


@pytest.mark.parametrize("name", [".venv:alt", "bad*name", "bad?name", "CON", "trailing.", "LPT9.env", "space name"])
def test_adversarial_external_runtime_name_is_portable(workflow, fixture_repo, monkeypatch, name):
    root, config, _ = fixture_repo
    config.update(external_environments_required=True, environment_namespace="product")
    config["environments"][0]["path"] = name
    (root / "scripts/local/workflow.json").write_text(json.dumps(config))
    monkeypatch.setenv("CAOS_VENVS_ROOT", str(root.parent / "outside"))
    with pytest.raises(workflow.Failure):
        workflow.environment_directory(root, name)
    assert not (root.parent / "outside").exists()


@pytest.mark.parametrize("alias", ["correct", "wrong-external", "namespace-to-repo", "namespace-to-other", "runtime-to-other"])
def test_adversarial_external_alias_containment(workflow, fixture_repo, monkeypatch, alias):
    root, config, _ = fixture_repo
    external = root.parent / "outside"
    config.update(external_environments_required=True, environment_namespace="product")
    (root / "scripts/local/workflow.json").write_text(json.dumps(config))
    monkeypatch.setenv("CAOS_VENVS_ROOT", str(external))
    external.mkdir()
    link = root / ".venv"
    if alias == "namespace-to-repo":
        directory_alias(external / "product", root)
    elif alias in ("namespace-to-other", "runtime-to-other"):
        other = external / "another-product/.venv"
        other.mkdir(parents=True)
        if alias == "namespace-to-other":
            directory_alias(external / "product", other.parent)
        else:
            (external / "product").mkdir()
            directory_alias(external / "product/.venv", other)
    else:
        target = external / ("product" if alias == "correct" else "another-product") / ".venv"
        target.mkdir(parents=True)
        directory_alias(link, target)
    if alias == "correct":
        assert workflow.environment_directory(root, ".venv").resolve() == target.resolve()
    else:
        with pytest.raises(workflow.Failure):
            workflow.environment_directory(root, ".venv")


@pytest.mark.parametrize("root_mode", ["relative", "internal", "external"])
def test_adversarial_initializer_enforces_external_location_before_writes(workflow, fixture_repo, monkeypatch, root_mode):
    root, config, _ = fixture_repo
    real_lookup = runpy.run_path(str(workflow.__file__))["venv_python"]
    monkeypatch.setattr(workflow, "venv_python", real_lookup)
    present(root, config, workflow)
    config.update(external_environments_required=True, environment_namespace="product")
    (root / "scripts/local/workflow.json").write_text(json.dumps(config))
    external = root.parent / "outside"
    requested = {"relative": "relative-runtime", "internal": str(root / "inside"), "external": str(external)}[root_mode]
    monkeypatch.setenv("CAOS_VENVS_ROOT", requested)
    monkeypatch.setattr(workflow, "prerequisites", lambda *_: None)
    monkeypatch.setattr(workflow, "install_frontend", lambda *_: None)
    monkeypatch.setattr(workflow, "check_shipped", lambda *_: None)
    calls = []

    def run(args, cwd, env=None, capture=False):
        calls.append(args)
        if "venv" in args:
            target = Path(args[-1])
            assert target.is_relative_to(external)
            target.mkdir(parents=True)
            interpreter = target / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            interpreter.parent.mkdir(parents=True)
            interpreter.write_text("fake interpreter; never executed")
        else:
            assert Path(args[0]).is_relative_to(external)
        return ""

    monkeypatch.setattr(workflow, "run", run)
    if root_mode == "external":
        workflow.initialize(root, config)
        assert len(calls) == 2
        assert not (root / ".venv").exists()
        workflow.initialize(root, config)
        assert len(calls) == 2, "A matching external environment remains idempotent."
    else:
        with pytest.raises(workflow.Failure):
            workflow.initialize(root, config)
        assert calls == [] and not (root / ".env").exists()
        assert not (root / "inside").exists()


def test_adversarial_receipt_is_one_parse_and_hash_snapshot(workflow, fixture_repo, monkeypatch):
    root, config, env = fixture_repo
    present(root, config, workflow)
    stage = workflow.generate(root, config, env)
    path = stage / "local-generation.json"
    original_bytes = Path.read_bytes
    original_text = Path.read_text
    changed = False
    before = workflow.payload_hashes(root, config)

    def change_once(current):
        nonlocal changed
        if current == path and not changed:
            replacement = json.loads(original_bytes(path))
            replacement["source"] = "forged authority after the read"
            path.write_text(json.dumps(replacement))
            changed = True

    def read_bytes(current):
        data = original_bytes(current)
        change_once(current)
        return data

    def read_text(current, *args, **kwargs):
        data = original_text(current, *args, **kwargs)
        change_once(current)
        return data

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setattr(Path, "read_text", read_text)
    with pytest.raises(workflow.Failure):
        workflow.promote(root, config, stage, Path(sys.executable), env)
    assert changed and workflow.payload_hashes(root, config) == before


@pytest.mark.parametrize("kind", ["role-root-file", "namespace-file", "runtime-file"])
def test_adversarial_external_non_directory_target_refuses_before_writes(workflow, fixture_repo, monkeypatch, kind):
    root, config, _ = fixture_repo
    external = root.parent / "outside"
    config.update(external_environments_required=True, environment_namespace="product")
    (root / "scripts/local/workflow.json").write_text(json.dumps(config))
    path = (external if kind == "role-root-file" else external / "product"
            if kind == "namespace-file" else external / "product/.venv")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("preserve this existing file")
    monkeypatch.setenv("CAOS_VENVS_ROOT", str(external))
    monkeypatch.setattr(workflow, "prerequisites", lambda *_: None)
    calls = []
    monkeypatch.setattr(workflow, "run", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(workflow.Failure):
        workflow.initialize(root, config)
    assert calls == [] and not (root / ".env").exists()
    assert path.read_text() == "preserve this existing file"
