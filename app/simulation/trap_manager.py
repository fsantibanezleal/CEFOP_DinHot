"""
Optical trap management for holographic tweezers.

Handles creation, deletion, movement, and selection of optical traps.
Coordinates between user input (mouse events from the web frontend)
and the phase mask generator.

This module corresponds to the mouse event handling code in the original
C++ SistemaControl class (SistemaControl.cpp):
    - panelTab0Izq_MouseDown: Create, delete, or select traps
    - panelTab0Izq_MouseMove: Move selected traps during drag
    - panelTab0Izq_MouseUp: Release selection and trigger recalculation
    - rbCreateMove_CheckedChanged: Toggle between create and move modes
    - rBDelete_CheckedChanged: Toggle delete mode

The original code maintained two MatDinHot instances (_masker) that were
kept in sync -- one for the control panel and one for the SLM display
window. This Python version uses a single TrapManager that serves both
the API and WebSocket endpoints.
"""
import numpy as np

from .phase_mask import PhaseMaskGenerator, OpticalTrap


class TrapManager:
    """Manages optical traps and coordinates phase mask computation.

    Acts as the controller between user input and the phase mask generator.
    Tracks interaction mode (create/move/delete) and manages trap selection
    state for drag operations.

    The three interaction modes correspond to the original C++ UI:
    - 'create': rbCreateMove checked -- clicking adds a new trap
    - 'move': default (neither radio button) -- clicking selects, drag moves
    - 'delete': rBDelete checked -- clicking removes the nearest trap
    """

    def __init__(self, resolution: tuple = (512, 512),
                 phase_scale: float = np.pi):
        """Initialize trap manager.

        Args:
            resolution: Phase mask resolution (width, height) in pixels.
            phase_scale: Dimensionless phase scaling factor (default: pi).
                Controls the maximum beam deflection angle. See
                PhaseMaskGenerator.__init__ for details.
        """
        self.generator = PhaseMaskGenerator(
            resolution=resolution, phase_scale=phase_scale
        )
        self.selected_trap = -1
        self.mode = 'create'  # 'create', 'move', 'delete'
        self.needs_recalculation = False

    def handle_click(self, x: float, y: float) -> str:
        """Handle mouse click at normalized coordinates.

        Behavior depends on the current interaction mode:
        - create: Adds a new trap at (x, y)
        - delete: Removes the nearest trap to (x, y)
        - move: Selects the nearest trap for subsequent dragging

        This corresponds to the panelTab0Izq_MouseDown handler in the
        original C++ SistemaControl class.

        Args:
            x: X coordinate in normalized range [-1, 1].
            y: Y coordinate in normalized range [-1, 1].

        Returns:
            String describing the action performed:
            'created', 'deleted', 'selected', or None.
        """
        if self.mode == 'create':
            self.generator.add_trap(x, y)
            self.needs_recalculation = True
            return 'created'

        elif self.mode == 'delete':
            idx = self.generator.find_nearest_trap(x, y)
            if idx >= 0:
                self.generator.remove_trap(idx)
                self.needs_recalculation = True
                return 'deleted'

        else:  # move mode -- select nearest trap
            self.selected_trap = self.generator.find_nearest_trap(x, y)
            if self.selected_trap >= 0:
                return 'selected'

        return None

    def handle_drag(self, x: float, y: float):
        """Handle mouse drag to move the selected trap.

        Only effective when a trap has been selected via handle_click
        in 'move' mode. Corresponds to panelTab0Izq_MouseMove in the
        original C++ code, which called _masker->Move(x, y).

        Note: The original C++ code did NOT trigger recalculation during
        drag (the _reArmar flag was not set in Move()), only updating
        the trap position and rho matrix. We follow the same approach
        for responsiveness -- recalculation happens on release.

        Args:
            x: New X coordinate in normalized range [-1, 1].
            y: New Y coordinate in normalized range [-1, 1].
        """
        if self.selected_trap >= 0:
            self.generator.move_trap(self.selected_trap, x, y)
            self.needs_recalculation = True

    def handle_release(self):
        """Handle mouse release after a drag operation.

        Deselects the current trap and marks the system for recalculation.
        Corresponds to panelTab0Izq_MouseUp, which called
        _masker->FreeMove(), setting _selectedtrampa = -1 and
        _reArmar = true.
        """
        if self.selected_trap >= 0:
            self.selected_trap = -1
            self.needs_recalculation = True

    def recalculate_if_needed(self) -> int:
        """Recalculate the phase mask if the trap configuration has changed.

        This is called after user interactions that modify the trap layout.
        The original C++ code ran CalcMatriz() in a continuous loop in
        the background worker thread (bwControl_DoWork), but only when
        _reArmar was true.

        Returns:
            Number of GS iterations performed, or 0 if no recalculation.
        """
        if self.needs_recalculation:
            self.needs_recalculation = False
            return self.generator.calculate_phase_mask()
        return 0

    def get_state(self) -> dict:
        """Return full simulation state for WebSocket transmission.

        Returns:
            Dictionary with phase mask data, trap positions, and
            convergence information. See PhaseMaskGenerator.get_state().
        """
        return self.generator.get_state()
