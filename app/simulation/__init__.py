"""
Simulation package for holographic optical tweezers.

Contains the core physics algorithms:
- phase_mask: Gerchberg-Saxton algorithm for phase mask computation
- trap_manager: Optical trap creation, movement, and deletion
- complex_utils: Complex number utility functions
"""

from .phase_mask import PhaseMaskGenerator, OpticalTrap
from .trap_manager import TrapManager

__all__ = ["PhaseMaskGenerator", "OpticalTrap", "TrapManager"]
