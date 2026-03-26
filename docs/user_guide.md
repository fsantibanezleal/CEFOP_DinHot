# User Guide

## Prerequisites

- **Python 3.9 or later** -- The application uses type hints, dataclasses, and f-strings that require Python 3.9+.
- **A modern web browser** -- Chrome, Firefox, or Edge. Safari should work but has not been tested.
- **No GPU required** -- All computation is done on the CPU with NumPy. A discrete GPU is not needed.

## Installation

```bash
cd CEFOP_DinHot

# Create and activate a virtual environment
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash / MSYS2)
# source .venv/bin/activate     # Linux / macOS

# Install dependencies
pip install -r requirements.txt
```

The main dependencies are FastAPI (web framework), Uvicorn (ASGI server), NumPy (numerical computation), and Pydantic (data validation). The full list is pinned in `requirements.txt`.

## Starting the Application

```bash
python -m uvicorn app.main:app --reload --port 8003
```

Then open your browser and navigate to **http://localhost:8003**.

The `--reload` flag tells Uvicorn to watch for file changes and restart automatically, which is useful during development. For normal usage you can omit it.

The application auto-initializes with default parameters (512x512 resolution, 632 nm wavelength, 50 max iterations) on page load. You should see the dual-canvas interface with an empty trap canvas on the left and a blank phase mask on the right.

## Interface Overview

The application window has three main areas:

![App Interface](svg/app_screenshot.svg)

### 1. Trap Position Canvas (Left Panel)

This canvas shows the positions of optical traps in a normalized coordinate system ranging from -1 to +1 on both axes. A faint grid and a crosshair through the center (0, 0) help with positioning.

Each trap appears as an orange circle labeled with its index and coordinates. The canvas responds to mouse events differently depending on the current interaction mode.

### 2. Phase Mask Canvas (Right Panel)

This canvas displays the holographic phase mask computed by the Gerchberg-Saxton algorithm. The image is a grayscale map where:

- **Black (0)** represents phase = 0
- **White (255)** represents phase = 2*pi

The pattern you see is the hologram that would be loaded onto a physical SLM to create the desired trap arrangement. Small orange circles overlaid on the mask mark where the trap positions correspond in the output plane.

When traps are arranged symmetrically, the phase mask typically shows recognizable interference-like patterns (concentric rings, linear fringes, or combinations). Asymmetric arrangements produce more complex, less intuitive patterns.

### 3. Controls Bar (Bottom)

The controls bar contains four sections:

#### Interaction Mode

Three buttons control how mouse clicks on the trap canvas are interpreted:

- **Create** (default, highlighted in orange) -- Click anywhere on the left canvas to place a new trap at that position. The phase mask recalculates immediately after each placement.
- **Move** -- Click on an existing trap to select it (the cursor changes to a grab hand). While holding the mouse button, drag to reposition the trap. The trap position updates visually during the drag, but the phase mask only recalculates when you release the mouse button (this matches the original application's behavior and keeps the interface responsive).
- **Delete** -- Click on an existing trap to remove it. The nearest trap within a small radius of the click position is deleted.

Below the mode buttons are two action buttons:

- **Recalculate** -- Forces a fresh phase mask computation using the current trap configuration. Useful if you want to try a different random initialization (the GS algorithm starts from a random phase each time).
- **Clear All** -- Removes all traps and resets the simulation with the current parameter values.

#### Parameters

Adjustable physical and algorithmic parameters:

- **Resolution** -- Width and height of the phase mask in pixels. Range: 32 to 2048. Default: 512x512. Lower values (128 or 256) compute faster and are good for experimentation. Higher values (512 or 1024) produce more accurate masks for actual SLM use.
- **Wavelength** -- Laser wavelength in nanometers. Default: 632 nm (He-Ne). Other common values: 532 nm (frequency-doubled Nd:YAG, green), 1064 nm (Nd:YAG, infrared).
- **Max Iterations** -- Upper limit on GS algorithm iterations. Default: 50. The algorithm may converge earlier. Increase this if the convergence graph shows the error is still decreasing when it stops.
- **Tolerance** -- Convergence threshold. Default: 1e-6. The algorithm stops when the relative change in error between consecutive iterations falls below this value.

Click **Initialize** to apply parameter changes. This resets the simulation (all traps are removed) with the new settings.

#### Simulation Info

Displays real-time statistics:

- **Traps** -- Number of active traps.
- **Iterations** -- How many GS iterations were performed in the most recent computation.
- **Converged** -- Whether the algorithm reached the convergence threshold (Yes/No).
- **Error** -- The final RMS intensity error (coefficient of variation of trap intensities). Lower is better; zero would mean perfectly uniform traps.

Below the stats is a table listing each trap's index, (x, y) position, and computed intensity. Ideally all intensities should be approximately equal.

#### Convergence Graph

A small canvas that plots the error metric over iterations from the most recent phase mask computation. The orange line should show a decreasing trend. A green dot at the end indicates that the algorithm converged before reaching the iteration limit.

## Typical Workflow

1. **Launch the server** and open the browser. The interface loads with default parameters.
2. **Place traps** -- In Create mode, click several positions on the left canvas. Start with 2-4 traps to see clear effects. After each click, the phase mask updates and the convergence graph shows the GS iteration history.
3. **Observe the phase mask** -- Notice how the grayscale pattern on the right changes with each trap you add. Symmetric trap arrangements (e.g., corners of a square) produce recognizable interference fringes.
4. **Move traps** -- Switch to Move mode. Click on a trap to select it, then drag it to a new position. The phase mask recalculates when you release the mouse.
5. **Delete traps** -- Switch to Delete mode. Click on unwanted traps to remove them.
6. **Experiment with parameters** -- Try lowering the resolution to 128x128 for fast iteration, or raising it to 1024x1024 for high-fidelity masks. Adjust the wavelength to see how it affects the phase pattern scale.
7. **Force recalculation** -- Click Recalculate to restart the GS algorithm from a new random phase. Different random starts may produce slightly different final masks, all equally valid.
8. **Reset** -- Click Clear All to start over with a clean canvas.

## Tips and Best Practices

- **Start small.** Two or three well-separated traps are the best way to understand what the phase mask looks like and how the GS algorithm behaves. Adding many traps at once makes patterns hard to interpret.
- **Watch the convergence graph.** A healthy computation shows the error dropping steeply in the first few iterations, then leveling off. If it plateaus at a high value, the algorithm may need more iterations or the trap configuration may be challenging (e.g., traps very close together).
- **Symmetry produces beautiful patterns.** Traps placed at the vertices of regular polygons (triangle, square, hexagon) produce phase masks with striking symmetry that correspond to well-known diffraction patterns.
- **Resolution vs. speed trade-off.** The computation time scales as O(N * M) where N is the number of pixels and M is the number of traps per iteration. For real-time interactivity, 256x256 with a handful of traps is very responsive. For accurate results, use 512x512 or higher.
- **Uniform intensity check.** Look at the intensity column in the trap list table. If all values are close to each other, the weighted GS algorithm is doing its job. Large disparities suggest the algorithm did not fully converge -- try increasing max iterations.

## Running Tests

The project includes a comprehensive test suite:

```bash
cd CEFOP_DinHot
source .venv/Scripts/activate   # Windows
# source .venv/bin/activate     # Linux / macOS

# Run individual test files
python tests/test_phase_mask.py
python tests/test_trap_manager.py
python tests/test_integration.py

# Or run all tests with pytest (if installed)
python -m pytest tests/ -v
```

The tests cover:

- **`test_phase_mask.py`** -- PhaseMaskGenerator initialization, trap operations, GS algorithm convergence, intensity uniformity, edge cases.
- **`test_trap_manager.py`** -- TrapManager mode handling, click/drag/release sequences, mode switching, recalculation triggers.
- **`test_integration.py`** -- End-to-end scenarios combining multiple operations, REST API endpoint behavior, state serialization.

## Troubleshooting

| Symptom | Likely Cause | Solution |
|---|---|---|
| Browser shows "Disconnected" | Server not running or wrong port | Check that `uvicorn` is running on port 8003 |
| Phase mask is all black | No traps placed, or initialization failed | Add at least one trap, or click Initialize |
| Convergence graph flat at high error | Too many traps or traps too close together | Reduce trap count or spread them further apart; increase max iterations |
| Slow computation | High resolution with many traps | Lower resolution to 256x256 for interactive use |
| WebSocket keeps reconnecting | Server crashed or was restarted | Check the terminal for Python errors; the client reconnects automatically |
