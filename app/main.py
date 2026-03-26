"""
CEFOP DinHot - Dynamic Holographic Optical Tweezers.

FastAPI web application for real-time generation and visualization of
holographic phase masks for optical tweezers using the Gerchberg-Saxton
algorithm.

This is the modernized Python port of the original C++/.NET DinHotSys
application. The original used:
    - Windows Forms for the GUI
    - OpenGL for rendering (GL_Trampas, GL_Mascaras)
    - BackgroundWorker threads for continuous computation
    - Two-panel layout: traps on left, phase mask on right

This version replaces all of that with:
    - FastAPI for the web server
    - WebSocket for real-time bidirectional communication
    - HTML5 Canvas for dual-panel visualization
    - NumPy for vectorized phase mask computation

Run with:
    uvicorn app.main:app --reload --port 8003
"""
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .api.routes import router as api_router, sim_state
from .simulation.trap_manager import TrapManager

app = FastAPI(
    title="CEFOP DinHot",
    description="Dynamic Holographic Optical Tweezers - Phase Mask Generator",
    version="2.0.0",
)

# Include REST API routes
app.include_router(api_router)

# Serve static files (HTML, CSS, JS)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the main application page.

    Returns the single-page application HTML that provides the dual-canvas
    interface for trap positioning and phase mask visualization.
    """
    return FileResponse(str(static_dir / "index.html"))


@app.websocket("/ws")
async def ws_handler(websocket: WebSocket):
    """WebSocket endpoint for real-time trap interaction.

    Handles the following message types:
    - click: User clicked on the trap canvas (create/delete/select)
    - drag: User is dragging a selected trap
    - release: User released the mouse button
    - mode: Change interaction mode (create/move/delete)
    - recalculate: Force a phase mask recalculation
    - state: Request current simulation state

    This replaces the continuous background worker loop
    (bwControl_DoWork) from the original C++ code. Instead of polling,
    the WebSocket handler responds to discrete user events.

    The protocol is JSON-based:
        Client sends: {"action": "click", "x": 0.5, "y": -0.3}
        Server responds: {"action": "created", "state": {...}}
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if sim_state["manager"] is None:
                await websocket.send_json({"error": "Not initialized"})
                continue

            action = msg.get("action")
            manager = sim_state["manager"]

            if action == "click":
                result = manager.handle_click(msg["x"], msg["y"])
                if manager.needs_recalculation:
                    manager.recalculate_if_needed()
                await websocket.send_json({
                    "action": result,
                    "state": manager.get_state(),
                })

            elif action == "drag":
                manager.handle_drag(msg["x"], msg["y"])
                # Send state without full recalculation for responsiveness.
                # The original C++ code also skipped CalcMatriz during drag
                # (_reArmar was not set in Move()).
                await websocket.send_json({
                    "action": "dragging",
                    "state": manager.get_state(),
                })

            elif action == "release":
                manager.handle_release()
                manager.recalculate_if_needed()
                await websocket.send_json({
                    "action": "released",
                    "state": manager.get_state(),
                })

            elif action == "mode":
                manager.mode = msg.get("mode", "create")
                await websocket.send_json({
                    "action": "mode_changed",
                    "mode": manager.mode,
                })

            elif action == "recalculate":
                iters = manager.generator.calculate_phase_mask()
                await websocket.send_json({
                    "action": "recalculated",
                    "iterations": iters,
                    "state": manager.get_state(),
                })

            elif action == "state":
                await websocket.send_json({
                    "state": manager.get_state(),
                })

    except WebSocketDisconnect:
        pass
