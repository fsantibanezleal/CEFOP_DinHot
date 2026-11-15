"""Generic admission loads only the explicitly declared product validator.

Since 0.15.001 the provider is read from the checkout that holds the checker (the product root), never from the judged root
(issue #102): each case is a product whose own copy of check_readiness.py judges the product itself."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_readiness.py"


def invoke(root, config, code):
    folder = root / "scripts/local"
    folder.mkdir(parents=True)
    (folder / "workflow.json").write_text(json.dumps(config), encoding="utf-8")
    (folder / "provider.py").write_text(code, encoding="utf-8")
    shutil.copy2(SCRIPT, root / "scripts/check_readiness.py")
    return subprocess.run([sys.executable, str(root / "scripts/check_readiness.py"), str(root)], capture_output=True,
                          text=True, check=False)


def test_product_provider_does_not_need_the_template_engine(tmp_path):
    (tmp_path / "complete.json").write_text("{}", encoding="utf-8")
    code = 'def validate(root):\n    assert (root / "complete.json").is_file(), "missing complete payload"\n'
    result = invoke(tmp_path, {"readiness_provider": "scripts/local/provider.py"}, code)
    assert result.returncode == 0 and "declared product provider" in result.stdout
    (tmp_path / "complete.json").unlink()
    bad = subprocess.run([sys.executable, str(tmp_path / "scripts/check_readiness.py"), str(tmp_path)], capture_output=True,
                         text=True, check=False)
    assert bad.returncode == 1 and "missing complete payload" in bad.stdout


@pytest.mark.parametrize("config,code", [
    ({"product_admission": True}, "def validate(root): pass\n"),
    ({"readiness_provider": "../outside.py"}, "def validate(root): pass\n"),
    ({"readiness_provider": "scripts/local/absent.py"}, "def validate(root): pass\n"),
    ({"readiness_provider": "scripts/local/provider.py"}, "validate = None\n"),
    ({"readiness_provider": "scripts/local/provider.py"}, "def validate(root): return False\n"),
    ({"readiness_provider": "scripts/local/provider.py"}, "def validate(root): raise KeyError('incomplete payload')\n"),
])
def test_adversarial_malformed_or_unsuccessful_provider_is_refused(tmp_path, config, code):
    result = invoke(tmp_path, config, code)
    assert result.returncode == 1 and "invalid admission provider" in result.stdout
    assert "Traceback" not in result.stderr
