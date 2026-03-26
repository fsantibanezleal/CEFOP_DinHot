"""
Phase mask generation for Holographic Optical Tweezers.

Implements the weighted Gerchberg-Saxton (GS) iterative algorithm for
computing phase-only holograms that produce desired optical trap patterns.

The algorithm finds a phase distribution phi(x,y) on the SLM (Spatial Light
Modulator) plane that, when illuminated by a plane wave, produces focused
spots at the desired trap positions.

Physical parameters:
    - Wavelength lambda = 632 nm (He-Ne laser)
    - Wave vector k = 2*pi/lambda
    - Focal distance f = 500 nm
    - SLM resolution: configurable (default 512x512 for web)

Mathematical model:
    The electric field at the j-th trap position is the coherent sum of
    contributions from all SLM pixels:

        E_j = (1/N) * sum_xy exp(i * [phi(x,y) - (k/f) * rho_j(x,y)])

    where:
        phi(x,y)   = phase value at SLM pixel (x,y)
        k          = 2*pi/lambda, the wave vector magnitude
        f          = focal distance of the Fourier lens
        rho_j(x,y) = x*x_j + y*y_j, the dot product between pixel
                     coordinates and the j-th trap position

    For traps with nonzero z (defocus), an additional quadratic phase
    term is added:
        + (k / f^2) * (x^2 + y^2) * z_j

    The intensity at trap j is I_j = |E_j|^2.

    The GS algorithm iterates:
    1. Start with random phase phi_0(x,y)
    2. Compute E_j for all traps j
    3. Update trap amplitudes: alpha_new = ((1-tol) + tol*(alpha/|E|)) * alpha
       This weighted update drives all traps toward equal intensity.
    4. Reconstruct the full complex field on the SLM:
       F(x,y) = sum_j alpha_j * exp(i * (k/f) * rho_j(x,y))
    5. Extract phase: phi_new(x,y) = arg(F(x,y))
    6. Check convergence via RMS intensity error

    The algorithm is based on:
    - Gerchberg & Saxton (1972), Optik 35, 237-246
    - Leonardo et al. (2007), Opt. Express 15, 1913-1922

Implementation notes:
    The original C++ code (MatDinHot.cpp) used:
    - _vectorOnda = 2*PI/lambda as the wave vector
    - _distFocal for the focal distance
    - _rrho[trap][x][y] for precomputed dot products
    - OpenMP parallel sections for the field summation
    - A convergence criterion: (xICiclo - xI0) / xICiclo < tolerance

    This Python port uses NumPy vectorized operations to replace the
    explicit loops and OpenMP parallelism of the C++ version.
"""
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from .complex_utils import compute_rho, normalize_phase, phase_to_grayscale


@dataclass
class OpticalTrap:
    """Represents a single optical trap position.

    An optical trap (or optical tweezer) is a tightly focused laser beam
    that can hold and manipulate microscopic particles. Each trap is
    defined by its position in the focal plane of the objective lens.

    Attributes:
        x: X position in normalized coordinates [-1, 1].
        y: Y position in normalized coordinates [-1, 1].
        z: Z position (defocus parameter), default 0 for in-focus traps.
        amplitude: Desired trap amplitude (iteratively updated by GS).
        intensity: Computed trap intensity |E|^2 after GS iteration.
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    amplitude: float = 1.0
    intensity: float = 0.0


class PhaseMaskGenerator:
    """Generates phase masks for holographic optical tweezers.

    Uses the weighted Gerchberg-Saxton algorithm to compute optimal
    phase distributions for creating multiple optical traps simultaneously.

    The generator maintains:
    - A phase mask array phi(x,y) representing the SLM pattern
    - A list of optical traps with positions and amplitudes
    - Precomputed coordinate grids and dot-product matrices for efficiency

    The phase mask is a 2D array of values in [0, 2*pi) that, when applied
    to an SLM illuminated by a plane wave, produces the desired pattern of
    focused spots in the focal plane.
    """

    def __init__(self, resolution: Tuple[int, int] = (512, 512),
                 wavelength: float = 632e-9,
                 focal_distance: float = 500e-9):
        """Initialize the phase mask generator.

        Sets up coordinate grids and physical parameters. The coordinate
        system is normalized to [-1, 1] on both axes, matching the
        original C++ code's approach of mapping pixel indices to physical
        positions via a scale factor (FACTORESPACIO in MatDinHot.cpp).

        Args:
            resolution: (width, height) of the phase mask in pixels.
                The original C++ code used 1280x1024 for the SLM;
                we default to 512x512 for responsive web display.
            wavelength: Laser wavelength in meters.
                Default 632e-9 m corresponds to a He-Ne laser (632 nm).
            focal_distance: Focal distance of the Fourier lens in meters.
                Default 500e-9 m. In the original code this was 0.0000005f.
        """
        self.res_x, self.res_y = resolution
        self.wavelength = wavelength
        self.focal_distance = focal_distance
        self.wave_vector = 2 * np.pi / wavelength
        self.tolerance = 1e-6
        self.max_iterations = 50

        # Phase mask array -- initialized to random values
        self.phi = np.random.uniform(0, 2 * np.pi, (self.res_y, self.res_x))

        # Coordinate grids (normalized to [-1, 1])
        # In the original C++ code, coordinates were pixel indices (1-based).
        # Here we normalize to make the physics scale-independent.
        x = np.linspace(-1, 1, self.res_x)
        y = np.linspace(-1, 1, self.res_y)
        self.coord_x, self.coord_y = np.meshgrid(x, y)
        self.coord_x_sq = self.coord_x ** 2
        self.coord_y_sq = self.coord_y ** 2

        # Traps and precomputed dot products
        self.traps: List[OpticalTrap] = []
        self._rho: List[np.ndarray] = []

        # Convergence tracking
        self.error_history: List[float] = []
        self.converged = False

    def add_trap(self, x: float, y: float, z: float = 0.0):
        """Add a new optical trap at the specified position.

        Creates a new trap and precomputes the dot-product matrix (rho)
        for this trap position. The rho matrix stores:
            rho(px, py) = coord_x(px,py) * trap_x + coord_y(px,py) * trap_y

        This corresponds to the _rrho array in the original C++ code
        (MatDinHot::AddTrampa).

        Args:
            x: X position in normalized coordinates [-1, 1].
            y: Y position in normalized coordinates [-1, 1].
            z: Z position (defocus, default 0).
        """
        trap = OpticalTrap(x=x, y=y, z=z, amplitude=1.0)
        self.traps.append(trap)

        # Precompute dot product matrix (mirrors _rrho in C++)
        rho = compute_rho(self.coord_x, self.coord_y, x, y)
        self._rho.append(rho)

    def remove_trap(self, index: int):
        """Remove a trap by index.

        Corresponds to MatDinHot::DeleteTrampa in the original C++ code.

        Args:
            index: Zero-based index of the trap to remove.
        """
        if 0 <= index < len(self.traps):
            self.traps.pop(index)
            self._rho.pop(index)

    def move_trap(self, index: int, x: float, y: float):
        """Move an existing trap to a new position.

        Updates both the trap's coordinates and the precomputed rho matrix.
        Corresponds to MatDinHot::Move in the original C++ code, which
        recalculated _rrho for the moved trap.

        Args:
            index: Zero-based index of the trap to move.
            x: New X position in normalized coordinates.
            y: New Y position in normalized coordinates.
        """
        if 0 <= index < len(self.traps):
            self.traps[index].x = x
            self.traps[index].y = y
            self._rho[index] = compute_rho(self.coord_x, self.coord_y, x, y)

    def find_nearest_trap(self, x: float, y: float,
                          threshold: float = 0.05) -> int:
        """Find the trap nearest to (x, y) within a distance threshold.

        Used for mouse-based selection of traps. Corresponds to
        MatDinHot::SelectMove in the C++ code, which searched for traps
        within 5*FACTORESPACIO of the click position.

        Args:
            x: X coordinate to search near.
            y: Y coordinate to search near.
            threshold: Maximum distance for a match (in normalized coords).

        Returns:
            Index of the nearest trap within threshold, or -1 if none found.
        """
        best_idx = -1
        best_dist = threshold
        for i, trap in enumerate(self.traps):
            dist = np.sqrt((trap.x - x) ** 2 + (trap.y - y) ** 2)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        return best_idx

    def compute_electric_field(self, trap_index: int) -> complex:
        """Compute the electric field amplitude at a given trap.

        Evaluates the coherent sum of contributions from all SLM pixels
        to the specified trap position:

            E_j = (1/N) * sum_xy exp(i * [phi(x,y) - (k/f) * rho_j(x,y)])

        The (1/N) normalization factor matches the original C++ code
        (MatDinHot::AmplitudCampoElectrico), where:
            factor = 1.0 / (resMaskX * resMaskY)

        For traps with nonzero z, a quadratic defocus phase is added:
            + (k / f^2) * (x^2 + y^2) * z_j

        This corresponds to the imaginario[2] term in the C++ code.

        Args:
            trap_index: Index of the trap to compute the field for.

        Returns:
            Complex electric field amplitude at the trap position.
        """
        # Phase contribution: phi(x,y) - (k/f) * rho
        # In the original C++ code this was:
        #   imaginario[0] = _phi[i][j]
        #   imaginario[1] = -(_vectorOnda / _distFocal) * _rrho[trap][i][j]
        kf = self.wave_vector / self.focal_distance
        phase = self.phi - kf * self._rho[trap_index]

        # Add quadratic phase for defocus (z != 0)
        # Original C++ code:
        #   imaginario[2] = (_vectorOnda / (_distFocal*_distFocal))
        #                   * (xSq + ySq) * z_trap
        if self.traps[trap_index].z != 0:
            kf2 = self.wave_vector / (self.focal_distance ** 2)
            phase += kf2 * (self.coord_x_sq + self.coord_y_sq) * self.traps[trap_index].z

        # Sum over all pixels and normalize
        # Original C++ code: factor = 1.0 / (resMaskX * resMaskY)
        field = np.sum(np.exp(1j * phase))
        normalization = 1.0 / (self.res_x * self.res_y)
        return field * normalization

    def calculate_phase_mask(self) -> int:
        """Run the Gerchberg-Saxton algorithm to compute the optimal phase mask.

        This is the main computation method, corresponding to
        MatDinHot::CalcMatriz in the original C++ code.

        The algorithm:
        1. Initialize phi with random values (RandomizePhi in C++)
        2. For each iteration:
           a. Compute E_j at each trap (AmplitudCampoElectrico)
           b. Compute intensities I_j = |E_j|^2
           c. Update amplitudes using weighted correction:
              alpha_new = ((1-tol) + tol*(alpha/|E|)) * alpha
              This matches the C++ line:
              alfaN[i] = ((1-tol) + tol*(alfa/alfaN[i])) * alfa
           d. Reconstruct complex field on SLM:
              F(x,y) = sum_j alpha_j * exp(i*(k/f)*rho_j)
              This corresponds to CalcResultPhi in C++
           e. Extract phase: phi = arg(F)
              This corresponds to CalcAnguloPhi in C++
           f. Check convergence: |(error_new - error_old) / error_new| < tol
              Matches the C++ criterion: xN = (xICiclo - xI0) / xICiclo

        Returns:
            Number of iterations performed.
        """
        if len(self.traps) == 0:
            return 0

        # Initialize random phase (matches RandomizePhi in C++)
        self.phi = np.random.uniform(0, 2 * np.pi, (self.res_y, self.res_x))
        self.error_history = []
        self.converged = False

        n_traps = len(self.traps)
        prev_error = float('inf')
        kf = self.wave_vector / self.focal_distance

        for iteration in range(self.max_iterations):
            # Step 1: Compute field at each trap
            # (AmplitudCampoElectrico in C++)
            fields = np.zeros(n_traps, dtype=complex)
            for j in range(n_traps):
                fields[j] = self.compute_electric_field(j)

            # Step 2: Compute intensities and amplitudes
            amplitudes = np.abs(fields)
            intensities = amplitudes ** 2

            for j in range(n_traps):
                self.traps[j].intensity = float(intensities[j])

            # Step 3: Update trap amplitudes (weighted GS correction)
            # Original C++ code:
            #   alfaN[i] = ((1 - _tolerancia) + _tolerancia * (_alfaTrampa[i]/alfaN[i])) * _alfaTrampa[i]
            # The _factorTolerancia in C++ was 0.5, used as the exponent for
            # the amplitude correction. Here we use the same weighted update.
            for j in range(n_traps):
                if amplitudes[j] > 1e-10:
                    correction = (1.0 - self.tolerance) + self.tolerance * (
                        self.traps[j].amplitude / amplitudes[j]
                    )
                    self.traps[j].amplitude *= correction

            # Step 4: Reconstruct complex field on SLM plane
            # This corresponds to CalcResultPhi in C++:
            #   ExpImaginariaF(temp, (k/f)*rho + defocus_term, alpha)
            # which computes alpha * exp(i * phase_term) and accumulates.
            complex_field = np.zeros((self.res_y, self.res_x), dtype=complex)
            for j in range(n_traps):
                phase_term = kf * self._rho[j]

                # Add defocus term (negative sign for inverse propagation)
                if self.traps[j].z != 0:
                    kf2 = self.wave_vector / (self.focal_distance ** 2)
                    phase_term -= kf2 * (self.coord_x_sq + self.coord_y_sq) * self.traps[j].z

                complex_field += self.traps[j].amplitude * np.exp(1j * phase_term)

            # Step 5: Extract phase (CalcAnguloPhi in C++)
            # arg() returns [-pi, pi], we shift to [0, 2*pi)
            self.phi = np.angle(complex_field) % (2 * np.pi)

            # Step 6: Compute RMS intensity error for convergence check
            # Original C++ code:
            #   xICiclo += (I_desired - I_actual)^2
            #   xICiclo = sqrt(xICiclo / (N^2))
            #   xN = (xICiclo - xI0) / xICiclo
            mean_intensity = np.mean(intensities) if np.mean(intensities) > 0 else 1.0
            error = np.sqrt(np.mean((intensities - mean_intensity) ** 2)) / (mean_intensity + 1e-10)
            self.error_history.append(float(error))

            # Convergence check (matches C++ criterion)
            if iteration > 0 and prev_error > 0:
                convergence = abs(prev_error - error) / (prev_error + 1e-10)
                if convergence < self.tolerance:
                    self.converged = True
                    return iteration + 1

            prev_error = error

        return self.max_iterations

    def get_phase_mask_normalized(self) -> np.ndarray:
        """Return phase mask normalized to [0, 255] for display.

        Maps the full 2*pi phase range to 8-bit grayscale, suitable for
        rendering on an HTML5 canvas or sending to a physical SLM.

        In the original C++ code, the phase mask was normalized by dividing
        by _maximo (the maximum phase value). Here we use the full [0, 2*pi)
        range for a proper grayscale mapping.

        Returns:
            2D numpy array of uint8 values in [0, 255].
        """
        return phase_to_grayscale(self.phi)

    def get_state(self) -> dict:
        """Return serializable state for WebSocket transmission.

        Downsamples the phase mask for efficient network transfer and
        packages it with trap positions and convergence information.

        Returns:
            Dictionary containing:
            - phase_mask: 2D list of grayscale values (downsampled)
            - mask_width, mask_height: dimensions of the downsampled mask
            - traps: list of trap position/intensity dictionaries
            - converged: whether the GS algorithm has converged
            - iterations: number of iterations performed
            - error_history: last 20 error values for convergence plot
        """
        # Downsample phase mask for efficient transmission
        step = max(1, self.res_x // 256)
        mask_small = self.phi[::step, ::step]
        normalized = (mask_small / (2 * np.pi) * 255).astype(int).tolist()

        return {
            'phase_mask': normalized,
            'mask_width': mask_small.shape[1],
            'mask_height': mask_small.shape[0],
            'traps': [
                {
                    'x': float(t.x),
                    'y': float(t.y),
                    'z': float(t.z),
                    'amplitude': float(t.amplitude),
                    'intensity': float(t.intensity),
                }
                for t in self.traps
            ],
            'converged': self.converged,
            'iterations': len(self.error_history),
            'error_history': [float(e) for e in self.error_history[-20:]],
        }
