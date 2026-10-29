"""The cost functions of the optimization methods, public (no ``SPEC``: the registry skips this module).

``TrapCost`` is the trap-array cost that M10, M11, B1 and B4 minimize (Harte's ``C_t`` with an efficiency target), and
``FieldCost`` the shaped-field cost of M10, M11 and M13, each with its value and its Wirtinger gradient in closed form
(``_common.py`` holds them with the solvers). The didactic notebooks of topic 05 build and differentiate a cost with these
names rather than reaching into the private module.
"""
from __future__ import annotations

from ._common import FieldCost, TrapCost

__all__ = ["FieldCost", "TrapCost"]
