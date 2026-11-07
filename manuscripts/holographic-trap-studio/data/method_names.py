r"""The English names of the engine's methods and the keys that carry them in the report's macro files.

The report shows a reader the name of each method, never the engine's compact label. ``NAME`` holds the name as a heading or a
table row label shows it, ``RUN`` the same name as running text writes it, and ``SLUG`` the lower-case key of the macros
(``\defv{pfwgs}{nfix}``). The names are those of the method modules' ``SPEC`` in ``data-pipeline/pipeline/model/holo/methods``.
``named`` turns the labels that a measured text or a table cell still holds into the running name, so a text written by an
earlier run of a measure script reads the same as one written now.
"""
from __future__ import annotations

import re

NAME = {
    "M01": "Superposition of prisms and lenses", "M02": "Random superposition", "M03": "Random mask",
    "M04": "Gerchberg-Saxton", "M05": "Generalized adaptive additive GS", "M06": "Weighted GS",
    "M07": "Phase-fixed weighted GS", "M08": "Mixed-region amplitude freedom", "M09": "Direct search",
    "M10": "Conjugate-gradient minimization", "M11": "Wirtinger gradient descent with Adam",
    "M12": "Closed-loop weighted GS", "M13": "Device-aware CG with pixel crosstalk",
    "M14": "Zernike correction and sensorless modal recovery", "M15": "Laguerre-Gaussian vortex traps",
    "M16": "Hungarian assignment and linear phase interpolation", "M17": "Multi-plane CNN hologram",
    "M18": "Optimal-transport initialized MRAF", "M19": "Volumetric 3D GS",
    "B1": "Device-aware weighted GS", "B2": "Flicker-bounded phase-continuous sequence",
    "B3": "Learned warm start for phase-fixed WGS", "B4": "Aberration- and pointing-robust hologram",
    "B5": "Efficiency-uniformity Pareto front",
}
RUN = {
    "M01": "superposition of prisms and lenses", "M02": "random superposition", "M03": "random mask",
    "M04": "GS", "M05": "generalized adaptive additive GS", "M06": "weighted GS",
    "M07": "phase-fixed weighted GS", "M08": "mixed-region amplitude freedom", "M09": "direct search",
    "M10": "conjugate-gradient minimization", "M11": "Wirtinger gradient descent with Adam",
    "M12": "closed-loop weighted GS", "M13": "device-aware CG with pixel crosstalk",
    "M14": "Zernike correction", "M15": "Laguerre-Gaussian vortex traps",
    "M16": "Hungarian assignment with phase interpolation", "M17": "multi-plane CNN hologram",
    "M18": "optimal-transport initialized MRAF", "M19": "volumetric 3D GS",
    "B1": "device-aware weighted GS", "B2": "flicker-bounded phase-continuous sequence",
    "B3": "learned warm start", "B4": "aberration-robust hologram",
    "B5": "efficiency-uniformity Pareto front",
}
SLUG = {
    "M01": "prisms", "M02": "randsup", "M03": "randmask", "M04": "gs", "M05": "gaa", "M06": "wgs", "M07": "pfwgs",
    "M08": "mraf", "M09": "directsearch", "M10": "cgmin", "M11": "wirtadam", "M12": "closedloop", "M13": "crosstalkcg",
    "M14": "zernike", "M15": "vortex", "M16": "rearrange", "M17": "cgnet", "M18": "otmraf", "M19": "volumetric",
    "B1": "devicewgs", "B2": "flicker", "B3": "warmstart", "B4": "robust", "B5": "paretofront",
}
# the inverse of SLUG: code that has to read a measured file by its keys writes ``ID["gs"]``, never the label itself
ID = {v: k for k, v in SLUG.items()}
# a possessive of a label ("<label>'s plan") reads badly with a long name: it is turned into a phrase
_POSSESSIVE = re.compile(r"(?<![\w-])" + re.escape(ID["rearrange"]) + r"'s plan")
_LABEL = re.compile(r"(?<![\w-])(?:M(?:0[1-9]|1[0-9])|B[1-5])(?![\w-])")


def named(text: str) -> str:
    """``text`` with every engine label replaced by the running name of its method (capitalized at the start of the text)."""
    text = _POSSESSIVE.sub("the plan of the Hungarian assignment with phase interpolation", text)
    def one(m: re.Match[str]) -> str:
        s = RUN[m.group(0)]
        return s[0].upper() + s[1:] if m.start() == 0 else s
    return _LABEL.sub(one, text)


def slug(label: str) -> str:
    """The macro key of a method: ``SLUG[label]``; a key that is not a method label passes through."""
    return SLUG.get(label, label)


def label_name(label: str) -> str:
    """The row label of a method in a table; a label that is not a method's passes through."""
    return NAME.get(label, label)
