# Development History

## v2.2.0 (2026-03-26) — Optical Physics Fix

### Critical Fix: Dimensionless Phase Scaling

**Problem**: v2.0 used SI physical parameters directly:

```
k = 2π/λ = 2π/(632×10⁻⁹) ≈ 9.94 × 10⁶ rad/m
f = 500 × 10⁻⁹ m
k/f ≈ 1.99 × 10¹⁶ rad/m²
```

The phase kernel K_j = (k/f)·ρ produced values up to ~4×10¹⁶ radians. This means the phase wraps around 2π approximately 6.3×10¹⁵ times across the SLM — effectively **random noise**. The GS algorithm cannot converge because adjacent pixels have no phase correlation.

**Root cause**: The value `0.0000005f` in the original C++ code was in an internal coordinate system (pixel-based), NOT in SI meters. When ported to Python with normalized [-1,1] coordinates, the physical constant interpretation breaks.

**Solution**: Replace all physical constants with a single dimensionless scaling factor α:

```
K_j(u,v) = α · (u·x_j + v·y_j) - β · (u² + v²) · z_j
```

where:
- α = phase_scale ≈ π (default)
- β = defocus_scale ≈ 1.0 (default)
- u, v ∈ [-1, 1] (normalized SLM coordinates)
- x_j, y_j ∈ [-1, 1] (normalized trap positions)

**Physical correspondence**: α absorbs all hardware-dependent constants:

```
α = (2π / λf) · Δp² · N
```

For He-Ne laser (λ=632nm), f=200mm, Δp=20μm, N=512: α ≈ π

With α = π, maximum phase per pixel is ~2π for edge traps — the correct regime for constructive interference and GS convergence.

> See `docs/svg/architecture.svg` for visual reference.

### Verification

After the fix:
- GS converges in 15-30 iterations (was: never converged)
- Trap intensities are non-zero and uniform
- Phase mask shows smooth spatial structure (was: pixel-level noise)
- Intensity preview (FFT reconstruction) shows correct focused spots

### Phase Kernel Decomposition

```
K_j(u,v) = K_linear + K_quadratic

K_linear   = α · (u·x_j + v·y_j)     ← beam steering (lateral position)
K_quadratic = -β · (u² + v²) · z_j    ← defocus (axial position)
```

The linear term tilts the wavefront by angle ∝ α·x_j, steering the beam
to lateral position x_j. The quadratic term adds curvature, shifting
the focal point along the optical axis by z_j.

### Weighted GS Algorithm (Unchanged, Now Functional)

The algorithm remains the same but now actually converges:

```
Forward:  E_j = (1/N²) Σ_{u,v} exp(i·[φ(u,v) - K_j(u,v)])
Weights:  w_j ← w_j · ⟨|E|⟩ / |E_j|
Backward: F(u,v) = Σ_j w_j · exp(i·[K_j(u,v) + arg(E_j)])
Aperture: F ← F · A(u,v)    [super-Gaussian, order 8]
Phase:    φ ← arg(F) mod 2π
```

Convergence criterion: relative RMS error change < 10⁻⁶

### Aperture Function Update

Changed from radius 1.0 to 0.95 for the super-Gaussian pupil:
```
A(r) = exp(-(r/0.95)⁸)
```
This provides better edge roll-off and reduces ringing artifacts in the reconstructed intensity pattern.

## v2.1.0 (2026-03-26)

### Algorithmic Improvements

#### Weighted Gerchberg-Saxton (Di Leonardo et al., 2007)
Implemented proper weighted GS with weight update rule:

```
w_j^{(n+1)} = w_j^{(n)} * <|V|> / |V_j^{(n)}|
```

This drives all trap intensities toward uniformity.

#### Intensity Reconstruction Preview
Added FFT-based focal plane reconstruction:

```
I(u,v) = |FFT{exp(i * φ(x,y))}|²
```

Shows the actual diffraction pattern produced by the phase mask.

#### Super-Gaussian Aperture Function
Applied smooth aperture to model SLM active area:

```
A(r) = exp(-(r/r₀)⁸)
```

Reduces edge ringing compared to hard circular aperture.

#### Uniformity Metric
Added quantitative trap uniformity measurement:

```
U = I_min / I_max
```

Displayed in real-time during computation.

#### Phase Kernel Separation
Separated optical path computation into reusable kernel:

```
K_j(x,y) = (k/f) * ρ_j - (k/f²) * (x²+y²) * z_j
```

where ρ_j = x*x_j + y*y_j (precomputed dot product).

### Frontend Improvements
- Help modal with optical tweezers usage guide
- Tooltips on all parameters and controls
- Intensity preview visualization
- Uniformity percentage display

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
