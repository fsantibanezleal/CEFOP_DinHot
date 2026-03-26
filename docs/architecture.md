# System Architecture

## Overview

CEFOP DinHot v2.0 is a browser-based tool for computing and visualizing holographic phase masks used in optical tweezers. It replaces the original C++/.NET desktop application with a Python backend served over HTTP/WebSocket and a JavaScript frontend rendered entirely with HTML5 Canvas elements.

The system is split into two halves that communicate over a single network connection:

- **Backend (Python/FastAPI)** -- Runs the physics simulation, manages trap state, and computes phase masks using the Gerchberg-Saxton algorithm through NumPy.
- **Frontend (HTML5/Canvas/JS)** -- Presents a dual-panel interface where users interact with trap positions on one canvas while seeing the computed phase hologram on another.

![System Architecture](svg/architecture.svg)

## Why FastAPI + Canvas

The original application was built with Windows Forms, OpenGL rendering, and C++/CLI. That stack tied the project to Windows, Visual Studio 2008, and a non-trivial build process. The decision to move to FastAPI and HTML5 Canvas was driven by three factors:

1. **Cross-platform reach.** A web application runs on any operating system with a browser. There is no installer, no runtime dependency on .NET or OpenGL drivers.
2. **Development velocity.** Python with NumPy replaces thousands of lines of manual complex arithmetic and memory management. FastAPI provides automatic request validation, interactive API documentation, and WebSocket support with minimal boilerplate.
3. **Real-time interactivity.** WebSocket gives bidirectional, low-latency communication that matches the responsiveness of the original background-worker loop, without the threading complexity.

HTML5 Canvas was chosen over a heavier framework (Three.js, WebGL) because the rendering requirements are straightforward: one canvas draws colored circles on a grid, and the other draws a grayscale pixel image from an array. No 3D pipeline is needed.

## Component Descriptions

### PhaseMaskGenerator (`app/simulation/phase_mask.py`)

This is the computational core. It owns the phase mask array `phi(x,y)`, the list of `OpticalTrap` objects, and the precomputed dot-product matrices used in the GS algorithm.

Key responsibilities:
- Initialize coordinate grids normalized to [-1, 1] for scale-independent physics.
- Add, remove, and move traps while keeping precomputed rho matrices in sync.
- Run the weighted Gerchberg-Saxton iteration loop to find the optimal phase distribution.
- Normalize the phase mask to 8-bit grayscale for display or SLM output.
- Package the full simulation state (phase mask, trap info, convergence data) as a serializable dictionary.

The generator corresponds to the `MatDinHot` class in the legacy C++ code.

### TrapManager (`app/simulation/trap_manager.py`)

Acts as a controller between user input events and the `PhaseMaskGenerator`. It tracks the current interaction mode (create, move, or delete) and manages trap selection state during drag operations.

Key responsibilities:
- Translate mouse clicks into trap creation, deletion, or selection depending on the active mode.
- Forward drag coordinates to the generator's `move_trap()` method.
- Decide when to trigger a full phase mask recalculation (after creation, deletion, or drag release -- not during drag, matching the original C++ behavior for responsiveness).
- Expose the generator's state to the API and WebSocket layers.

The TrapManager corresponds to the mouse-handling code in the original `SistemaControl` class.

### Dual-Canvas Renderer (`app/static/js/renderer.js`)

The frontend rendering engine draws three canvases:

1. **Trap Canvas (left)** -- Shows trap positions as orange circles on a grid with crosshairs at the origin. Each trap is labeled with its index and coordinates. The canvas accepts mouse events for interaction.
2. **Phase Mask Canvas (right)** -- Displays the computed hologram as a grayscale image. Each pixel's brightness maps linearly from phase 0 (black) to phase 2pi (white). Small orange circles overlay the trap positions.
3. **Convergence Canvas** -- Plots the RMS error history from the most recent GS computation as an orange line graph, with a green dot indicating successful convergence.

### Complex Utilities (`app/simulation/complex_utils.py`)

Provides NumPy-based convenience functions that mirror the original C++ `BasicComplex` library: complex exponentials, phase extraction, magnitude computation, phase normalization, and the dot-product matrix calculation (`compute_rho`).

### Frontend Modules

| Module | File | Purpose |
|---|---|---|
| App Orchestrator | `app/static/js/app.js` | Initializes all components, binds mouse events, coordinates WebSocket messages with renderer updates |
| WebSocket Client | `app/static/js/websocket.js` | Manages the `/ws` connection lifecycle with automatic reconnection and typed message methods |
| Renderer | `app/static/js/renderer.js` | Draws all three canvases and converts pixel coordinates to normalized [-1, 1] space |
| Controls | `app/static/js/controls.js` | Manages mode buttons, parameter inputs, simulation info display, and trap list table |

## API Endpoints

### REST Endpoints (`app/api/routes.py`)

All REST endpoints use the `/api` prefix.

| Method | Path | Description | Request Body / Query |
|---|---|---|---|
| `POST` | `/api/init` | Initialize simulation with parameters | JSON: `{resolution_x, resolution_y, wavelength_nm, max_iterations, tolerance}` |
| `POST` | `/api/trap/add` | Add a trap and recalculate | Query: `x`, `y`, `z` (floats in [-1, 1]) |
| `POST` | `/api/trap/remove` | Remove a trap by index | Query: `index` (int >= 0) |
| `POST` | `/api/trap/move` | Move a trap and recalculate | Query: `index`, `x`, `y` |
| `GET` | `/api/state` | Retrieve current state (no recalculation) | None |
| `GET` | `/api/params` | Retrieve current physical parameters | None |

### WebSocket Protocol (`/ws`)

The WebSocket endpoint provides low-latency bidirectional communication for interactive trap manipulation. All messages are JSON objects.

**Client-to-server messages:**

```json
{"action": "click", "x": 0.3, "y": -0.2}
{"action": "drag", "x": 0.35, "y": -0.18}
{"action": "release"}
{"action": "mode", "mode": "move"}
{"action": "recalculate"}
{"action": "state"}
```

**Server-to-client responses:**

```json
{"action": "created", "state": {...}}
{"action": "deleted", "state": {...}}
{"action": "selected", "state": {...}}
{"action": "dragging", "state": {...}}
{"action": "released", "state": {...}}
{"action": "mode_changed", "mode": "move"}
{"action": "recalculated", "iterations": 23, "state": {...}}
{"state": {...}}
{"error": "Not initialized"}
```

**State object structure:**

```json
{
  "phase_mask": [[0, 128, 255, ...], ...],
  "mask_width": 256,
  "mask_height": 256,
  "traps": [
    {"x": 0.3, "y": -0.2, "z": 0.0, "amplitude": 1.02, "intensity": 0.198}
  ],
  "converged": true,
  "iterations": 23,
  "error_history": [0.45, 0.12, 0.03, ...]
}
```

The phase mask is downsampled by a factor of `resolution / 256` before transmission to limit payload size. The browser reconstructs the full-size image using nearest-neighbor scaling.

## Mouse Interaction Protocol

The following sequence describes what happens when a user interacts with the trap canvas:

1. **Page load** -- `app.js` auto-initializes by calling `POST /api/init` with default parameters, then opens the WebSocket connection.
2. **Click (create mode)** -- `mousedown` on canvas triggers coordinate conversion from pixels to [-1, 1], then sends `{"action": "click", "x": ..., "y": ...}` over WebSocket. The server adds a trap, runs the GS algorithm, and responds with the new state. Both canvases update.
3. **Click + drag (move mode)** -- `mousedown` sends a click event that selects the nearest trap. Subsequent `mousemove` events send drag messages that update the trap position without recalculating (for responsiveness). `mouseup` sends a release event that triggers recalculation.
4. **Click (delete mode)** -- `mousedown` sends a click event. The server finds and removes the nearest trap, recalculates, and responds.
5. **Leave canvas** -- If a drag is in progress and the cursor exits the canvas, a release event is automatically sent to prevent stuck selections.

This protocol mirrors the original `panelTab0Izq_MouseDown`, `MouseMove`, and `MouseUp` handlers from the C++ code, with the key difference that communication is asynchronous over WebSocket rather than synchronous method calls.

## Deployment

### Development

```bash
cd CEFOP_DinHot
python -m venv .venv
source .venv/Scripts/activate   # Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8003
```

The `--reload` flag enables automatic server restart on code changes.

### Production

For production deployment, run without `--reload` and consider:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8003 --workers 4
```

Note that the simulation state is stored in module-level variables (`sim_state` in `routes.py`), so each worker process maintains its own independent simulation. For a single-user tool this is appropriate; for multi-user scenarios, state would need to be moved to a shared store.

## Correspondence with Legacy Code

| Original C++ Component | Python Equivalent |
|---|---|
| `MatDinHot` class | `PhaseMaskGenerator` class |
| `MatDinHot::CalcMatriz()` | `PhaseMaskGenerator.calculate_phase_mask()` |
| `MatDinHot::AmplitudCampoElectrico()` | `PhaseMaskGenerator.compute_electric_field()` |
| `MatDinHot::CalcResultPhi()` | Phase reconstruction in `calculate_phase_mask()` step 4 |
| `MatDinHot::CalcAnguloPhi()` | Phase extraction in `calculate_phase_mask()` step 5 |
| `MatDinHot::AddTrampa()` | `PhaseMaskGenerator.add_trap()` |
| `MatDinHot::SelectMove()` | `TrapManager.handle_click()` in move mode |
| `MatDinHot::Move()` | `TrapManager.handle_drag()` |
| `MatDinHot::FreeMove()` | `TrapManager.handle_release()` |
| `SistemaControl` (WinForms) | `index.html` + JavaScript modules |
| `GL_Trampas` (OpenGL) | `renderer.js` trap canvas |
| `GL_Mascaras` (OpenGL) | `renderer.js` mask canvas |
| `BasicComplex.h/.cpp` | `complex_utils.py` |
| `bwControl_DoWork` (BackgroundWorker) | WebSocket event-driven recalculation |
