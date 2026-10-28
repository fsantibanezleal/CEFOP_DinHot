"""The contract tests share the sandbox bake of tests/bake/bakefix.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bake"))

from bakefix import planted_registry, sandbox_bake  # noqa: E402,F401
