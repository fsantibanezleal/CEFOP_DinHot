"""A pytest plugin that plants defects in the product's code around chosen tests of a child pytest process.

``plant_run.py`` loads it with ``-p plant_plugin`` and passes the plants in the environment variable ``DINHOT_PLANTS``:
a JSON object ``{"<test node id>": [{"target": "module:name", "wrap": "<expression>"}, ...]}``. Around the whole protocol of that test
(its fixtures, its call and its teardown; and only that test) each ``wrap`` expression is evaluated with ``orig`` (the product's own function or method), ``np``,
``math`` and ``dataclasses`` in scope and returns the defective replacement, which is installed in the defining module and
in every loaded module that holds the same function (the tests import names with ``from x import f``) and removed again
afterwards. A target that does not exist makes that test error, never pass. The outcome of every test and the plants it
met are written to the JSON file named by ``DINHOT_PLANT_REPORT``.
"""
from __future__ import annotations

import dataclasses
import importlib
import json
import math
import os
import sys

import numpy as np
import pytest

_PLANTS: dict = json.loads(os.environ.get("DINHOT_PLANTS", "{}"))
_REPORT: dict = {}


def _resolve(target: str):
    module, _, attr = target.partition(":")
    owner = importlib.import_module(module)
    parts = attr.split(".")
    for part in parts[:-1]:
        owner = getattr(owner, part)
    return owner, parts[-1]


def _plants_for(nodeid: str) -> list:
    for key, plants in _PLANTS.items():
        if nodeid == key or nodeid.startswith(key + "["):
            return plants
    return []


def _apply(plants: list) -> list:
    undo: list = []
    for plant in plants:
        owner, name = _resolve(plant["target"])
        orig = getattr(owner, name)
        scope = {"orig": orig, "np": np, "math": math, "dataclasses": dataclasses}
        planted = eval(plant["wrap"], scope)  # noqa: S307  (the expression is written in the adversarial test itself)
        undo.append((vars(owner) if not isinstance(owner, type) else owner, name, orig, isinstance(owner, type)))
        setattr(owner, name, planted)
        if isinstance(owner, type):
            continue  # a method: the class is the one place every caller reaches it
        for module in list(sys.modules.values()):
            try:
                names = [k for k, v in vars(module).items() if v is orig]
            except TypeError:
                continue
            for k in names:
                undo.append((vars(module), k, orig, False))
                setattr(module, k, planted)
    return undo


def _restore(undo: list) -> None:
    for holder, name, orig, is_class in reversed(undo):
        if is_class:
            setattr(holder, name, orig)
        else:
            holder[name] = orig


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    plants = _plants_for(item.nodeid)
    undo: list = []
    if plants:
        try:
            undo = _apply(plants)
            _REPORT.setdefault(item.nodeid, {})["applied"] = [p["target"] for p in plants]
        except Exception as e:  # a plant that cannot be applied must not look like a pass
            _REPORT.setdefault(item.nodeid, {})["plant_error"] = f"{type(e).__name__}: {e}"
            _restore(undo)
            raise
    try:
        yield
    finally:
        _restore(undo)


def pytest_runtest_logreport(report) -> None:
    entry = _REPORT.setdefault(report.nodeid, {})
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        entry["outcome"] = report.outcome if report.when == "call" else "error"
        if report.outcome == "failed":
            crash = getattr(report.longrepr, "reprcrash", None)
            entry["crash"] = crash.message[:300] if crash else str(report.longrepr)[-300:]


def pytest_sessionfinish(session) -> None:
    path = os.environ.get("DINHOT_PLANT_REPORT")
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_REPORT, f)
