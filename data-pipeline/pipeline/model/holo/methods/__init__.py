"""Registry of the hologram methods.

A method is a module (anywhere below the subpackages ``baseline``, ``control``, ``optim`` and ``beyond`` of this package,
which the method units E2 and E3 create) that exposes ``SPEC`` (a ``core.types.MethodSpec``) and
``run(setup, target, *, device=None, budget, rng, init=None) -> Result``. Discovery imports every module below those
subpackages recursively; a missing subpackage is skipped, any other import error is raised (a broken method must not
vanish silently). With no method modules the registry is empty.
"""
from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable
from dataclasses import dataclass

from ..core.types import MethodSpec

SUBPACKAGES = ("baseline", "control", "optim", "beyond")


@dataclass(frozen=True)
class Method:
    spec: MethodSpec
    run: Callable


def _import_tree(name: str) -> list:
    try:
        pkg = importlib.import_module(name)
    except ModuleNotFoundError as e:
        if e.name == name:
            return []
        raise
    mods = [pkg]
    if hasattr(pkg, "__path__"):
        def onerror(n):
            raise ImportError(f"cannot import method module {n}")

        for info in pkgutil.walk_packages(pkg.__path__, prefix=name + ".", onerror=onerror):
            mods.append(importlib.import_module(info.name))
    return mods


def discover(base_package: str = __name__) -> list[Method]:
    """Import the method tree below ``base_package`` and return its methods sorted by id."""
    found: dict[str, Method] = {}
    for sub in SUBPACKAGES:
        for mod in _import_tree(f"{base_package}.{sub}"):
            spec = getattr(mod, "SPEC", None)
            if spec is None:
                continue
            if not isinstance(spec, MethodSpec):
                raise ValueError(f"{mod.__name__}: SPEC must be a MethodSpec")
            run = getattr(mod, "run", None)
            if not callable(run):
                raise ValueError(f"{mod.__name__}: a method module must define run(...)")
            if spec.id in found:
                raise ValueError(f"duplicate method id {spec.id!r} in {mod.__name__}")
            found[spec.id] = Method(spec, run)
    return [found[k] for k in sorted(found)]


_cache: dict[str, list[Method]] = {}
_base: str = __name__


def reload(base_package: str | None = None) -> None:
    """Drop the cached discovery; ``base_package`` redirects the default registry (tests), None restores it."""
    global _base
    _base = __name__ if base_package is None else base_package
    _cache.clear()


def _methods() -> list[Method]:
    if _base not in _cache:
        _cache[_base] = discover(_base)
    return _cache[_base]


def all_specs() -> list[MethodSpec]:
    """The specs of every registered method, sorted by id (empty when no method module exists)."""
    return [m.spec for m in _methods()]


def get(method_id: str) -> Method:
    """The method with that id; ``KeyError`` naming the known ids otherwise."""
    for m in _methods():
        if m.spec.id == method_id:
            return m
    raise KeyError(f"unknown method {method_id!r}; registered: {[m.spec.id for m in _methods()]}")
