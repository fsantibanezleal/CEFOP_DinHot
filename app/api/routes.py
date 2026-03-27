"""
REST API routes for the DinHot web application.

Provides HTTP endpoints for initialization, trap manipulation, and
state retrieval. These complement the WebSocket endpoint (defined in
main.py) which handles real-time interactive operations.

Endpoints:
    POST /api/init          - Initialize the simulation with parameters
    POST /api/trap/add      - Add a new optical trap
    POST /api/trap/remove   - Remove a trap by index
    POST /api/trap/move     - Move a trap to a new position
    GET  /api/state         - Get current simulation state
    GET  /api/params        - Get current physical parameters
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from typing import Optional

from ..simulation.trap_manager import TrapManager

router = APIRouter(prefix="/api", tags=["simulation"])


class DinHotConfig(BaseModel):
    """Configuration for initializing the simulation.

    Attributes:
        resolution_x: Phase mask width in pixels (32-2048).
        resolution_y: Phase mask height in pixels (32-2048).
        phase_scale: Dimensionless phase scaling factor (default pi).
            Controls beam deflection range. See PhaseMaskGenerator docs.
        max_iterations: Maximum GS algorithm iterations per computation.
        tolerance: Convergence tolerance for the GS algorithm.
    """
    resolution_x: int = Field(default=512, ge=32, le=2048)
    resolution_y: int = Field(default=512, ge=32, le=2048)
    phase_scale: float = Field(default=3.141592653589793, gt=0)
    max_iterations: int = Field(default=50, ge=1, le=500)
    tolerance: float = Field(default=1e-6, gt=0)


# Module-level simulation state, shared with main.py's WebSocket handler
sim_state = {"manager": None, "running": False}


def get_manager() -> Optional[TrapManager]:
    """Get the current TrapManager instance, or None if not initialized."""
    return sim_state.get("manager")


@router.post("/init")
async def init(config: DinHotConfig):
    """Initialize the simulation with the given configuration.

    Creates a new TrapManager and PhaseMaskGenerator with the specified
    physical parameters. Any existing simulation state is replaced.

    Args:
        config: Simulation configuration parameters.

    Returns:
        Status and the effective resolution.
    """
    manager = TrapManager(
        resolution=(config.resolution_x, config.resolution_y),
        phase_scale=config.phase_scale,
    )
    manager.generator.max_iterations = config.max_iterations
    manager.generator.tolerance = config.tolerance
    sim_state["manager"] = manager
    return {
        "status": "initialized",
        "resolution": [config.resolution_x, config.resolution_y],
    }


@router.post("/trap/add")
async def add_trap(
    x: float = Query(..., ge=-1, le=1),
    y: float = Query(..., ge=-1, le=1),
    z: float = Query(default=0.0),
):
    """Add a new optical trap at the specified position.

    After adding the trap, immediately runs the GS algorithm to compute
    the updated phase mask.

    Args:
        x: X position in normalized coordinates [-1, 1].
        y: Y position in normalized coordinates [-1, 1].
        z: Z position (defocus), default 0.

    Returns:
        Status, iteration count, and full simulation state.
    """
    manager = get_manager()
    if manager is None:
        return {"error": "Not initialized"}
    manager.generator.add_trap(x, y, z)
    iters = manager.generator.calculate_phase_mask()
    return {
        "status": "added",
        "iterations": iters,
        "state": manager.get_state(),
    }


@router.post("/trap/remove")
async def remove_trap(index: int = Query(..., ge=0)):
    """Remove a trap by its zero-based index.

    Recalculates the phase mask if traps remain.

    Args:
        index: Index of the trap to remove.

    Returns:
        Status and updated simulation state.
    """
    manager = get_manager()
    if manager is None:
        return {"error": "Not initialized"}
    manager.generator.remove_trap(index)
    if len(manager.generator.traps) > 0:
        manager.generator.calculate_phase_mask()
    return {"status": "removed", "state": manager.get_state()}


@router.post("/trap/move")
async def move_trap(
    index: int = Query(..., ge=0),
    x: float = Query(..., ge=-1, le=1),
    y: float = Query(..., ge=-1, le=1),
):
    """Move a trap to a new position and recalculate.

    Args:
        index: Index of the trap to move.
        x: New X position in normalized coordinates.
        y: New Y position in normalized coordinates.

    Returns:
        Status and updated simulation state.
    """
    manager = get_manager()
    if manager is None:
        return {"error": "Not initialized"}
    manager.generator.move_trap(index, x, y)
    manager.generator.calculate_phase_mask()
    return {"status": "moved", "state": manager.get_state()}


@router.get("/state")
async def get_state():
    """Get the current simulation state.

    Returns the phase mask, trap positions, and convergence information
    without triggering any recalculation.

    Returns:
        Full simulation state dictionary, or error if not initialized.
    """
    manager = get_manager()
    if manager is None:
        return {"error": "Not initialized"}
    return manager.get_state()


@router.get("/params")
async def get_params():
    """Get the current physical parameters.

    Returns:
        Dictionary of wavelength, focal distance, resolution, etc.
    """
    manager = get_manager()
    if manager is None:
        return {"error": "Not initialized"}
    gen = manager.generator
    return {
        "phase_scale": gen.phase_scale,
        "defocus_scale": gen.defocus_scale,
        "resolution": [gen.res_x, gen.res_y],
        "max_iterations": gen.max_iterations,
        "tolerance": gen.tolerance,
        "num_traps": len(gen.traps),
    }
