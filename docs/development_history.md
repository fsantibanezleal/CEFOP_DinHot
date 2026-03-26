# Development History

## v2.0.0 (2026-03-26) -- Python/FastAPI Rewrite

A ground-up rewrite of the entire application, moving from a Windows-only desktop tool to a cross-platform web application.

### What Changed

- **Language and runtime**: Replaced C++/CLI (.NET Framework) with Python 3.9+ and FastAPI.
- **User interface**: Replaced Windows Forms with OpenGL panels with a browser-based single-page application using HTML5 Canvas and vanilla JavaScript.
- **Communication model**: Replaced synchronous background worker threads (`BackgroundWorker` with `DoWork` loop) with an event-driven WebSocket protocol for real-time interaction.
- **Numerical computation**: Replaced hand-written complex arithmetic loops (with OpenMP parallelization) with NumPy vectorized array operations. The entire GS iteration loop now uses NumPy broadcasting and `np.exp` instead of explicit nested `for` loops.
- **Dual-canvas rendering**: The original used two separate OpenGL panels (`GL_Trampas` for traps, `GL_Mascaras` for the phase mask) rendered with OpenGL immediate mode. The new version uses two HTML5 Canvas elements with 2D context drawing and `ImageData` pixel manipulation.
- **Test suite**: Added 59 automated tests covering the phase mask generator, trap manager, and integration scenarios. The original C++ code had no automated tests.
- **Platform support**: No longer requires Windows, Visual Studio, or .NET Framework. Runs on any platform with Python and a web browser.

### Architecture Decisions

- **FastAPI over Flask/Django**: FastAPI provides native WebSocket support, automatic request validation via Pydantic models, and async-first design. Flask would have required additional libraries for WebSocket; Django would have been unnecessarily heavy for a single-page tool.
- **Vanilla JS over React/Vue**: The frontend is small enough (4 JS files, 1 HTML file) that a framework would add complexity without benefit. The rendering is all direct Canvas API calls, which frameworks do not help with.
- **NumPy over SciPy/CuPy**: The core computation is dominated by `np.exp(1j * array)` and `np.sum(...)`. NumPy handles this efficiently for the default 512x512 resolution. SciPy is included as a dependency for potential future use (e.g., FFT-based approaches) but is not currently used in the GS loop.

## v0.1.2 (2014) -- Original C++/.NET Application [Legacy]

The original DinHotSys application, preserved in the `legacy/` directory.

### Technology Stack

- **Language**: C++/CLI targeting .NET Framework 3.5
- **IDE**: Visual Studio 2008 (solution and project files included)
- **GUI**: Windows Forms with a tabbed interface
- **Rendering**: OpenGL (via custom managed wrappers) for both the trap visualization panel and the phase mask display panel
- **Threading**: `BackgroundWorker` component running a continuous computation loop (`bwControl_DoWork`) that checked a `_reArmar` flag to decide when to recalculate
- **Parallelism**: OpenMP `#pragma omp parallel sections` for the forward propagation step of the GS algorithm
- **Platform**: Windows only (required .NET CLR, OpenGL, and Win32 APIs)

### Key Files

| File | Purpose |
|---|---|
| `MatDinHot.h/.cpp` | Core phase mask computation (GS algorithm, trap management) |
| `BasicComplex.h/.cpp` | Complex number arithmetic (exp, arg, abs) |
| `SistemaControl.h/.cpp` | Main form with controls, mouse handlers, background worker |
| `GL_Trampas.h/.cpp` | OpenGL panel for rendering trap positions |
| `GL_Mascaras.h/.cpp` | OpenGL panel for rendering the phase mask |
| `DinHotSys.sln` | Visual Studio 2008 solution file |

### Features

- Dual-monitor support: the trap control window could run on one monitor while the phase mask was displayed full-screen on the SLM monitor.
- Radio button mode switching between create, move, and delete modes.
- Real-time phase mask updates through the background worker loop.
- Configurable SLM resolution (originally 1280x1024 to match hardware).

### Limitations

- Windows-only with hard dependency on .NET 3.5 and Visual Studio 2008.
- No automated tests.
- Manual memory management for the rho matrices and phase arrays.
- Fixed to the C++ build toolchain -- no easy way to experiment with algorithm changes.
