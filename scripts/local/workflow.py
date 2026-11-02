#!/usr/bin/env python3
"""Sequenced local workflows. Standard library only; no producer logic lives here."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


class Failure(Exception):
    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code if code > 0 else 1


def run(command, root, env=None, capture=False):
    result = subprocess.run(
        list(map(str, command)),
        cwd=root,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=capture,
        check=False,
    )
    if capture and result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        raise Failure(f"Command failed ({result.returncode}): {command[0]}", result.returncode)
    return result.stdout if capture else ""


def json_read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(path, parent):
    return path.resolve().is_relative_to(parent.resolve())


def external(path, root):
    result = Path(path).expanduser().resolve()
    if inside(result, root):
        raise Failure("CAOS_TEMP_ROOT and generation stages must be outside the repository.")
    return result


def relative(root, name):
    result = (root / name).resolve()
    if not inside(result, root) or result == root:
        raise Failure(f"Configured path escapes the repository: {name}")
    return result


def settings(root):
    return json_read(root / "scripts/local/workflow.json")


def next_step(number, detail=""):
    names = {"01": "01_init", "02": "02_generate-data", "03": "03_dev"}
    print(f"Next: scripts/local/{names[number]}.ps1 (or bash scripts/local/{names[number]}.sh){detail}")


NODE_RANGE = "^22.12.0 || ^24.0.0 || >=26.0.0"


def compatible_node(root, version):
    """The declared toolchain range, deliberately not a general SemVer parser."""
    package = json_read(root / "frontend/package.json")
    lock = json_read(root / "frontend/package-lock.json")
    declared = package.get("engines", {}).get("node")
    locked = lock.get("packages", {}).get("", {}).get("engines", {}).get("node")
    if declared != NODE_RANGE or locked != declared:
        raise Failure(f"Frontend package and lock must declare the supported Node range {NODE_RANGE}.")
    major, minor, patch = version
    return (major == 22 and (minor, patch) >= (12, 0)) or major == 24 or major >= 26


def prerequisites(root, install=False, announce=True):
    probes = [
        ("Python", [sys.executable, "--version"], (3, 12), "Python.Python.3.12", "python@3.12"),
        ("Node", ["node", "--version"], (22,), "OpenJS.NodeJS.LTS", "node@22"),
        ("git", ["git", "--version"], (2,), "Git.Git", "git"),
    ]
    missing = []
    for name, command, minimum, windows, brew in probes:
        try:
            value = run(command, root, capture=True)
            match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", value)
            version = tuple(int(v or 0) for v in match.groups()) if match else ()
            if version[: len(minimum)] < minimum:
                raise Failure(f"{name} is too old")
            if name == "Node" and not compatible_node(root, version):
                raise Failure(f"Node must satisfy {NODE_RANGE}; found {value.strip()}")
            print(f"{name}: {value.strip()}")
        except (OSError, Failure) as error:
            print(f"{name}: {error}", file=sys.stderr)
            missing.append((name, windows, brew))
    if missing and install:
        manager = shutil.which("winget") if os.name == "nt" else shutil.which("brew")
        if not manager:
            raise Failure(
                f"No supported system installer; install Python>=3.12, Node {NODE_RANGE} and git, then run 00 again."
            )
        for _, windows, brew in missing:
            command = (
                [manager, "install", "--id", windows, "--exact"]
                if os.name == "nt"
                else [manager, "install", brew]
            )
            run(command, root)
        return prerequisites(root, False, announce)
    if missing:
        raise Failure(
            "Missing/incompatible "
            + ", ".join(item[0] for item in missing)
            + ". Repair with scripts/local/00_install-prereqs.ps1 -Install or the shell --install option."
        )
    if announce:
        next_step("01")


def environment(root):
    values = dict(os.environ)
    path = root / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key.strip()):
                raise Failure(
                    "Invalid .env assignment; use literal KEY=value lines, never executable shell text."
                )
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            values.setdefault(key.strip(), value)
    values["PYTHONDONTWRITEBYTECODE"] = "1"
    for key in (
        "OPENBLAS_NUM_THREADS",
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        values[key] = "1"
    return values


def environment_directory(root, name):
    declared = {item["path"] for item in settings(root)["environments"]}
    candidate = Path(name)
    if name not in declared or candidate.is_absolute() or ".." in candidate.parts:
        raise Failure(f"Undeclared or invalid environment alias: {name}")
    directory = root / candidate
    if os.path.lexists(directory) and not directory.is_dir():
        raise Failure(f"Declared environment alias is unavailable or not a directory: {directory}")
    return directory


def venv_python(root, name):
    directory = environment_directory(root, name)
    for suffix in ("Scripts/python.exe", "bin/python"):
        path = directory / suffix
        if path.is_file():
            return path
    raise Failure(
        f"Missing interpreter in declared environment {name} -> {directory.resolve()}; run 01_init."
    )


def requirement_files(root, names):
    hashes = {}

    def visit(name):
        path = relative(root, name)
        if name in hashes:
            return
        if not path.is_file():
            raise Failure(f"Missing declared requirement file: {name}")
        hashes[name] = digest(path)
        for line in path.read_text(encoding="utf-8").splitlines():
            tokens = shlex.split(line, comments=True)
            for index, token in enumerate(tokens):
                include = None
                if token in ("-r", "-c", "--requirement", "--constraint"):
                    if index + 1 >= len(tokens):
                        raise Failure(f"Missing include in {name}")
                    include = tokens[index + 1]
                elif token.startswith(("-r", "-c")) and len(token) > 2:
                    include = token[2:]
                elif token.startswith(("--requirement=", "--constraint=")):
                    include = token.split("=", 1)[1]
                if include:
                    child = relative(root, (path.parent / include).relative_to(root))
                    visit(child.relative_to(root).as_posix())

    for name in names:
        visit(name)
    return hashes


def requirements_digest(root, names):
    return hashlib.sha256(json.dumps(requirement_files(root, names), sort_keys=True).encode()).hexdigest()


def api_active(root, config):
    declared = config["api"]["active"]
    if declared != "auto":
        return bool(declared)
    path = root / "requirements-api.txt"
    return (
        (root / "app/main.py").is_file()
        and path.is_file()
        and any(
            line.strip() and not line.lstrip().startswith("#")
            for line in path.read_text(encoding="utf-8").splitlines()
        )
    )


def install_frontend(root, config, env):
    front = root / "frontend"
    fingerprint = digest(front / "package-lock.json")
    stamp = front / "node_modules" / config["node_stamp"]
    markers = [
        (front / "node_modules/.package-lock.json").is_file(),
        any((front / "node_modules/.bin" / name).is_file() for name in ("vite", "vite.cmd")),
    ]
    if not all(markers) or not stamp.is_file() or stamp.read_text().strip() != fingerprint:
        run([shutil.which("npm") or "npm", "ci", "--no-audit", "--no-fund"], front, env)
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text(fingerprint + "\n", encoding="ascii")


def required_paths(root, config):
    result = set(config["required"])
    catalog = root / "docs/contracts/catalog.md"
    if catalog.is_file():
        header = None
        for line in catalog.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                continue
            cells = [value.strip().strip(chr(96)) for value in line.strip("|").split("|")]
            if "documents" in cells:
                header = cells
            elif header and len(cells) == len(header):
                for name in cells[header.index("documents")].split(","):
                    name = name.strip().strip(chr(96))
                    if name.startswith(("data/derived/", "models/")):
                        matches = list(root.glob(name))
                        result.update(p.relative_to(root).as_posix() for p in matches)
                        if not matches:
                            result.add(name)
    return sorted(result)


def check_shipped(root, config):
    version = (root / "VERSION").read_text().strip()
    index = json_read(root / "data/derived/manifests/index.json")
    ready = json_read(root / "data/derived/readiness.json")
    if index.get("engine_version") != version or ready.get("product_version") != version:
        raise Failure(
            "Shipped artifacts are stale/mixed. Run 02_generate-data, validate its complete stage, "
            "then explicitly promote with --release before 03_dev."
        )
    check_readiness_inventory(root, config, ready)
    check_readiness_states(root, config, ready, root)
    if config.get("readiness_check"):
        commands(
            root,
            config["validators"],
            substitutions(root, root, generation_python(root, config)),
            environment(root),
        )
    if config.get("requires_validation"):
        validation = json_read(root / "data/derived/validation.json")
        if (
            validation.get("engine_version") != version
            or not validation.get("passed")
            or validation.get("errors")
        ):
            raise Failure("Shipped whole-bake validation is missing, stale or failed.")


def initialize(root, config, gpu=False, notebooks=False):
    prerequisites(root, False, False)
    local = root / ".env"
    if not local.exists():
        with local.open("x", encoding="utf-8") as stream:
            stream.write((root / ".env.example").read_text(encoding="utf-8"))
    env = environment(root)
    for item in config["environments"]:
        when = item.get("when")
        if when and not {"gpu": gpu, "notebooks": notebooks, "api": api_active(root, config)}[when]:
            continue
        fingerprint = requirements_digest(root, item["requirements"])
        directory = environment_directory(root, item["path"])
        if not directory.exists():
            run([sys.executable, "-m", "venv", directory], root, env)
        python = venv_python(root, item["path"])
        stamp = directory / ".bootstrap-requirements.sha256"
        if not stamp.is_file() or stamp.read_text().strip() != fingerprint:
            command = [python, "-m", "pip", "install"]
            for name in item["requirements"]:
                command += ["-r", relative(root, name)]
            run(command, root, env)
            stamp.write_text(fingerprint + "\n", encoding="ascii")
    install_frontend(root, config, env)
    missing = [name for name in required_paths(root, config) if not list(root.glob(name))]
    if missing:
        print("Missing shipped artifacts: " + ", ".join(missing[:5]))
        stage = generate(root, config, env)
        raise Failure(
            f"Complete sandbox prepared at {stage}. Explicit promotion is required: "
            f'02_generate-data --release --from-stage "{stage}"; then rerun 01_init.'
        )
    check_shipped(root, config)
    next_step("03")


def generation_python(root, config):
    causes = []
    for name in config["generation_environments"]:
        try:
            return venv_python(root, name)
        except (Failure, OSError) as error:
            causes.append(f"{name}: {error}")
    raise Failure(
        "No generation environment: "
        + "; ".join(causes)
        + ". Run 01_init, adding --gpu/-Gpu for the optional accelerator lane."
    )


def substitutions(root, stage, python):
    return {
        "root": str(root),
        "stage": str(stage),
        "derived": str(stage / "data/derived"),
        "models": str(stage / "models"),
        "checkpoints": str(stage / "checkpoints"),
        "python": str(python),
        "npm": shutil.which("npm") or "npm",
    }


def commands(root, rows, values, env):
    for item in rows:
        script = relative(root, item["script"])
        run([values["python"], script, *[arg.format_map(values) for arg in item.get("args", [])]], root, env)


def source_identity(root, config):
    paths = [
        root / "VERSION",
        root / "scripts/local/workflow.json",
        root / "scripts/local/workflow.py",
        root / "scripts/local/producer_bridge.py",
    ]
    for pattern in (
        "data-pipeline/**/*.py",
        "data-pipeline/**/*.json",
        "docs/contracts/**/*",
        "scripts/local/*.py",
        "scripts/check_*.py",
        "tests/contracts/*.py",
    ):
        paths.extend(root.glob(pattern))
    requirement_names = [
        p.relative_to(root).as_posix()
        for pattern in ("requirements*.txt", "data-pipeline/requirements*.txt")
        for p in root.glob(pattern)
    ]
    paths.extend(root / name for name in requirement_files(root, requirement_names))
    paths.extend(authored_inputs(root, config).values())
    paths.extend(relative(root, row["script"]) for row in config["generation"] + config["validators"])
    values = {p.relative_to(root).as_posix(): digest(p) for p in sorted(set(paths)) if p.is_file()}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def payload_hashes(stage, config):
    result = {}
    for name in config["promote"]:
        directory = relative(stage, name)
        if not directory.is_dir():
            raise Failure(f"Incomplete stage: {name} is missing.")
        for path in directory.rglob("*"):
            if path.is_symlink() or not inside(path, stage):
                raise Failure("A staged payload cannot contain symlinks or escaped paths.")
            if path.is_file():
                result[path.relative_to(stage).as_posix()] = digest(path)
    return result


def authored_inputs(root, config):
    inputs = {name: relative(root, name) for name in config.get("stage_inputs", [])}
    for name, path in inputs.items():
        if not path.is_file():
            raise Failure(f"Missing authored stage input: {name}")
    return inputs


def check_metadata_current(root, stage, config):
    for name in ("VERSION", "product.json", "app/openapi.json"):
        if (root / name).is_file() and (
            not (stage / name).is_file() or digest(root / name) != digest(stage / name)
        ):
            raise Failure(f"Staged admission metadata is stale: {name}")
    for name, source in authored_inputs(root, config).items():
        target = relative(stage, name)
        if not target.is_file() or digest(source) != digest(target):
            raise Failure(f"Staged authored input differs from current source: {name}")
    source = root / "docs/contracts"
    expected = {p.relative_to(source).as_posix(): digest(p) for p in source.rglob("*") if p.is_file()}
    target = stage / "docs/contracts"
    actual = {p.relative_to(target).as_posix(): digest(p) for p in target.rglob("*") if p.is_file()}
    if expected != actual:
        raise Failure("Staged admission catalog/schema metadata differs from the current contract.")


def check_readiness_inventory(root, config, ready):
    catalog_ids = set()
    catalog = root / "docs/contracts/catalog.md"
    raw = catalog.read_bytes().replace(b"\r\n", b"\n")
    for line in raw.decode("utf-8").splitlines():
        columns = [part.strip() for part in line.strip().strip("|").split("|")]
        if (
            line.startswith("|")
            and len(columns) >= 13
            and columns[0] != "id"
            and set(columns[0]) - {"-", ":"}
        ):
            catalog_ids.add(columns[0])
    excluded = set(config.get("readiness_excludes", []))
    if excluded - catalog_ids:
        raise Failure("Configured readiness exclusions do not belong to the actual catalog.")
    expected = catalog_ids - excluded
    ids = [row.get("id") for row in ready["contracts"]]
    if catalog_ids and (set(ids) != expected or len(ids) != len(set(ids))):
        raise Failure("Partial readiness inventory does not match the producer's current contract.")
    if catalog_ids and ready.get("catalog_sha256") != hashlib.sha256(raw).hexdigest():
        raise Failure("Readiness is bound to a stale admission catalog.")


def check_readiness_states(root, config, ready, view):
    """Declared input/API outcomes are admitted only with the real recomputation guard."""
    exceptions = config.get("readiness_exceptions", {})
    checker = config.get("readiness_check")
    if exceptions and not checker:
        raise Failure("Readiness exceptions require the actual current-readiness validator.")
    if not ready.get("contracts") or any(
        row.get("state") != "available"
        and (row.get("id") not in exceptions or exceptions[row["id"]] != row.get("state"))
        for row in ready["contracts"]
    ):
        raise Failure("Partial readiness outside the declared input/API outcomes cannot be admitted.")
    if checker:
        # This existing guard is stdlib-only and recomputes source facts, reasons and exact bytes.
        run([sys.executable, "-B", relative(root, checker), view], root)


def validate_stage(root, config, stage, python, env, receipt=False):
    stage = external(stage, root)
    if stage == stage.parent:
        raise Failure("A filesystem root is not a generation stage.")
    if receipt:
        record = json_read(stage / "local-generation.json")
        if record["source"] != source_identity(root, config) or record["files"] != payload_hashes(
            stage, config
        ):
            raise Failure("Stage source or payload fingerprint changed; generate a complete new candidate.")
    check_metadata_current(root, stage, config)
    version = (root / "VERSION").read_text().strip()
    missing = [name for name in required_paths(root, config) if not list(stage.glob(name))]
    if missing:
        raise Failure("Partial stage: " + ", ".join(missing[:5]))
    for name in payload_hashes(stage, config):
        path = stage / name
        if path.suffix == ".json":
            value = json_read(path)
            if isinstance(value, dict):
                for key in ("engine_version", "product_version"):
                    if key in value and value[key] != version:
                        raise Failure(f"Mixed/stale version in {name}.")
    ready = json_read(stage / "data/derived/readiness.json")
    check_readiness_inventory(root, config, ready)
    check_readiness_states(root, config, ready, stage)
    validation = stage / "data/derived/validation.json"
    if config.get("requires_validation") and (
        not validation.is_file() or not json_read(validation).get("passed")
    ):
        raise Failure("Missing or failed whole-bake validation.")
    commands(root, config["validators"], substitutions(root, stage, python), env)


def generate(root, config, env):
    initial_source = source_identity(root, config)
    temp = env.get("CAOS_TEMP_ROOT", "").strip()
    if not temp:
        raise Failure("Configure external CAOS_TEMP_ROOT before 02_generate-data.")
    base = external(temp, root)
    base.mkdir(parents=True, exist_ok=True)
    if config.get("needs_sources") and not env.get("CAOS_DATA_ROOT", "").strip():
        raise Failure(
            "Configure external CAOS_DATA_ROOT with pinned measured sources; see scripts/fetch-data."
        )
    if config.get("needs_sources"):
        external(env["CAOS_DATA_ROOT"], root)
    python = generation_python(root, config)
    required = config.get("generation_modules", [])
    if required:
        probe = (
            "import importlib.util,sys; names=sys.argv[1:]; "
            "missing=[name for name in names if importlib.util.find_spec(name) is None]; "
            "print('Missing generation dependencies: '+', '.join(missing)+'; rerun 01_init --gpu' if missing else "
            "'Generation dependencies available'); sys.exit(bool(missing))"
        )
        run([python, "-c", probe, *required], root, env)
    stage = Path(tempfile.mkdtemp(prefix="caos-local-", dir=base))
    (stage / "data/derived").mkdir(parents=True)
    (stage / "models").mkdir()
    (stage / "checkpoints").mkdir()
    shutil.copy2(root / "VERSION", stage / "VERSION")
    shutil.copytree(root / "docs/contracts", stage / "docs/contracts")
    for name, source in authored_inputs(root, config).items():
        target = relative(stage, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for name in ("product.json", "app/openapi.json"):
        if (root / name).is_file():
            (stage / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / name, stage / name)
    child_env = {**env, "CAOS_MODELS_ROOT": str(stage / "checkpoints")}
    commands(root, config["generation"], substitutions(root, stage, python), child_env)
    if source_identity(root, config) != initial_source:
        raise Failure(
            "Producer/contract/validation inputs changed during generation; the stage cannot be admitted."
        )
    validate_stage(root, config, stage, python, child_env)
    record = {"source": initial_source, "files": payload_hashes(stage, config)}
    (stage / "local-generation.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Validated sandbox: {stage}")
    return stage


def remove_owned(path, parent):
    if path.parent.resolve() != parent.resolve() or ".bootstrap-" not in path.name:
        raise Failure("Refusing removal outside a reserved bootstrap sibling.")
    if os.path.lexists(path):
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise Failure("Refusing recursive removal of a symlink/junction recovery path.")
        resolved = path.resolve()
        if (
            resolved.parent != parent.resolve()
            or not inside(resolved, parent)
            or resolved == parent.resolve()
        ):
            raise Failure("Resolved cleanup target escapes its declared parent.")
        shutil.rmtree(path)


def promote(root, config, stage, python, env):
    validate_stage(root, config, stage, python, env, receipt=True)
    transaction = []
    try:
        for name in config["promote"]:
            target = relative(root, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            suffix = uuid.uuid4().hex
            incoming = target.parent / f".{target.name}.bootstrap-incoming-{suffix}"
            backup = target.parent / f".{target.name}.bootstrap-backup-{suffix}"
            restore = target.parent / f".{target.name}.bootstrap-restore-{suffix}"
            transaction.append(
                {
                    "target": target,
                    "incoming": incoming,
                    "backup": backup,
                    "restore": restore,
                    "installed": False,
                }
            )
            shutil.copytree(relative(stage, name), incoming)
        for item in transaction:
            if item["target"].exists():
                os.replace(item["target"], item["backup"])
            os.replace(item["incoming"], item["target"])
            item["installed"] = True
        if payload_hashes(root, config) != payload_hashes(stage, config):
            raise Failure("Promoted bytes differ from the validated candidate.")
    except BaseException as original:
        errors = []
        for item in reversed(transaction):
            if item["installed"]:
                try:
                    os.replace(item["target"], item["incoming"])
                except BaseException as error:
                    errors.append(f"withdraw {item['target']}: {error}")
            if item["backup"].exists():
                try:
                    # Retain the old backup until every target is restored successfully.
                    shutil.copytree(item["backup"], item["restore"])
                    os.replace(item["restore"], item["target"])
                except BaseException as error:
                    errors.append(f"restore {item['target']}: {error}")
        if errors:
            locations = [
                {key: str(item[key]) for key in ("target", "backup", "incoming", "restore")}
                for item in transaction
            ]
            raise Failure(
                f"Promotion failed: {original}. Rollback incomplete: {'; '.join(errors)}. "
                f"Recovery paths preserved: {json.dumps(locations)}"
            ) from original
        for item in transaction:
            for key in ("incoming", "backup", "restore"):
                remove_owned(item[key], item["target"].parent)
        raise
    for item in transaction:
        for key in ("incoming", "backup", "restore"):
            remove_owned(item[key], item["target"].parent)
    print("Complete validated artifact/model set promoted.")


def process_group_options():
    return (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        if os.name == "nt"
        else {"start_new_session": True}
    )


def stop(process):
    """Always address the recorded tree/group, including after its leader exits."""
    if os.name == "nt":
        # Console groups outlive their leader; taskkill alone cannot find an exited PID.
        try:
            os.kill(process.pid, signal.CTRL_BREAK_EVENT)
        except OSError:
            pass
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=5)


def development(root, config):
    env = environment(root)
    api = api_active(root, config)
    runtime = (
        config["api"].get("environment", config["primary_environment"])
        if api
        else config["primary_environment"]
    )
    names = {config["primary_environment"], runtime}
    for name in names:
        item = next((entry for entry in config["environments"] if entry["path"] == name), None)
        if item is None:
            raise Failure(f"Required Python environment is undeclared: {name}")
        stamp = environment_directory(root, name) / ".bootstrap-requirements.sha256"
        expected = requirements_digest(root, item["requirements"])
        if not stamp.is_file() or stamp.read_text().strip() != expected:
            raise Failure(f"Python initialization fingerprint is missing/stale for {name}; rerun 01_init.")
    python = venv_python(root, runtime)
    front = root / "frontend"
    stamp = front / "node_modules" / config["node_stamp"]
    if not stamp.is_file() or stamp.read_text().strip() != digest(front / "package-lock.json"):
        raise Failure("Frontend lock fingerprint is missing/stale; run 01_init before 03_dev.")
    if any(not list(root.glob(name)) for name in required_paths(root, config)):
        raise Failure(
            "Shipped artifacts are incomplete; run 01_init for the explicit sandbox-generation path."
        )
    check_shipped(root, config)
    api_port = int(env.get("APP_PORT", config["api"]["port"]))
    for port in [config["web_port"]] + ([api_port] if api else []):
        if not 0 < port < 65536:
            raise Failure("Local service ports must be integers from 1 to 65535.")
        try:
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise Failure(f"Port {port} is occupied; stop that service or configure another port.") from error
    values = {
        "python": str(python),
        "npm": shutil.which("npm") or "npm",
        "port": str(api_port),
        "web_port": str(config["web_port"]),
        "root": str(root),
    }
    frontend_env = {
        **env,
        **{key: value.format_map(values) for key, value in config.get("frontend_environment", {}).items()},
    }
    for command in config.get("frontend_prepare", []):
        run([v.format_map(values) for v in command], front, frontend_env)
    children = []
    try:
        if api:
            child = subprocess.Popen(
                [v.format_map(values) for v in config["api"]["command"]],
                cwd=root,
                env=env,
                **process_group_options(),
            )
            children.append(child)
            deadline = time.monotonic() + 20
            while True:
                if child.poll() is not None:
                    raise Failure("API exited before readiness; repair 01_init.", child.returncode or 1)
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{api_port}{config['api']['health']}", timeout=1
                    ) as reply:
                        if reply.status == 200:
                            break
                except (OSError, urllib.error.URLError):
                    pass
                if time.monotonic() >= deadline:
                    raise Failure("API readiness timed out; inspect the API startup error.")
                time.sleep(0.1)
        child = subprocess.Popen(
            [v.format_map(values) for v in config["frontend_command"]],
            cwd=front,
            env=frontend_env,
            **process_group_options(),
        )
        children.append(child)
        print(f"Frontend: http://127.0.0.1:{config['web_port']}", flush=True)
        if api:
            print(f"API: http://127.0.0.1:{api_port} (bounded operations and /docs)", flush=True)
        print("Local services started; Ctrl+C stops this workflow's process trees.", flush=True)
        while child.poll() is None:
            if api and children[0].poll() is not None:
                raise Failure("API stopped unexpectedly.", children[0].returncode or 1)
            time.sleep(0.1)
        if child.returncode:
            raise Failure("Frontend exited.", child.returncode)
    finally:
        for process in reversed(children):
            stop(process)
    next_step("03", " to restart; follow scripts/local/README.md for tests.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prereqs", "init", "generate", "dev"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--notebooks", action="store_true")
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--from-stage", type=Path)
    options = parser.parse_args(argv)
    root = options.root.resolve()
    try:
        config = settings(root)
        if options.action == "prereqs":
            prerequisites(root, options.install)
        elif options.action == "init":
            initialize(root, config, options.gpu, options.notebooks)
        elif options.action == "dev":
            development(root, config)
        else:
            env = environment(root)
            if options.from_stage and not options.release:
                raise Failure("--from-stage requires explicit --release.")
            stage = external(options.from_stage, root) if options.from_stage else generate(root, config, env)
            if options.release:
                promote(root, config, stage, generation_python(root, config), env)
            next_step(
                "03" if options.release else "02",
                f' --release --from-stage "{stage}"' if not options.release else "",
            )
        return 0
    except (Failure, OSError, ValueError, KeyError, TypeError) as error:
        print(f"[local] {error}", file=sys.stderr)
        return getattr(error, "code", 1)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
