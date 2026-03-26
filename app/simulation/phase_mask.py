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

        E_j = (1/N) * sum_xy exp(i * [phi(x,y) - K_j(x,y)])

    where:
        phi(x,y)   = phase value at SLM pixel (x,y)
        K_j(x,y)   = phase kernel encoding the optical path from pixel
                     (x,y) to trap j, defined as:
                     K_j = (k/f)*(x*x_j + y*y_j) - (k/f^2)*(x^2+y^2)*z_j

    The first term of K_j is the linear phase (beam steering) and the
    second is the quadratic phase (defocus for z-axis control).

    The intensity at trap j is I_j = |E_j|^2.

    The weighted GS algorithm iterates (Di Leonardo et al., 2007):
    1. Start with random phase phi_0(x,y)
    2. For each iteration n:
       a. Forward propagation: compute E_j at each trap
       b. Amplitude correction: update weights
              w_j^{n+1} = w_j^n * <|V|> / |V_j^n|
          This weighted update drives all traps toward equal intensity.
       c. Backward propagation: reconstruct SLM field
              F(x,y) = sum_j w_j * exp(i * [K_j(x,y) + angle(V_j)])
       d. Apply aperture function to suppress edge artifacts
       e. Phase extraction: phi_{n+1} = arg(F(x,y))
       f. Convergence check on intensity uniformity

    References:
    - Gerchberg & Saxton (1972), Optik 35, 237-246
    - Di Leonardo et al. (2007), Opt. Express 15, 1913-1922

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
           Nonzero values shift the trap along the optical axis via a
           quadratic phase term on the SLM.
        amplitude: Current trap amplitude maintained by the GS iteration.
           This is the magnitude of the electric field at the trap, updated
           at every iteration step during forward propagation.
        intensity: Computed trap intensity |E|^2 after the last GS
           iteration. This is the physically observable quantity (proportional
           to the optical power delivered to the trap).
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
    - A circular aperture (pupil function) to model the SLM active area
    - Convergence and uniformity history for monitoring algorithm progress

    The phase mask is a 2D array of values in [0, 2*pi) that, when applied
    to an SLM illuminated by a plane wave, produces the desired pattern of
    focused spots in the focal plane.
    """

    def __init__(self, resolution: Tuple[int, int] = (512, 512),
                 wavelength: float = 632e-9,
                 focal_distance: float = 500e-9):
        """Initialize the phase mask generator.

        Sets up coordinate grids, physical parameters, and the aperture
        function. The coordinate system is normalized to [-1, 1] on both
        axes, matching the original C++ code's approach of mapping pixel
        indices to physical positions via a scale factor
        (FACTORESPACIO in MatDinHot.cpp).

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

        # Wave vector magnitude k = 2*pi / lambda
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

        # Circular aperture (pupil function)
        # Models the finite extent of the SLM active area.
        # A super-Gaussian profile provides a smooth roll-off at the edges,
        # reducing ringing artifacts in the reconstructed intensity pattern
        # compared to a hard circular aperture.
        r_grid = np.sqrt(self.coord_x ** 2 + self.coord_y ** 2)
        self.aperture = np.exp(-(r_grid / 1.0) ** 8)

        # Traps and precomputed dot products
        self.traps: List[OpticalTrap] = []
        self._rho: List[np.ndarray] = []

        # Convergence tracking
        self.error_history: List[float] = []
        self.uniformity_history: List[float] = []
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
            z: Z position (defocus, default 0). Nonzero values add a
               quadratic phase to the kernel, shifting the trap along
               the optical axis.
        """
        trap = OpticalTrap(x=x, y=y, z=z, amplitude=1.0)
        self.traps.append(trap)

        # Precompute dot product matrix (mirrors _rrho in C++)
        rho = compute_rho(self.coord_x, self.coord_y, x, y)
        self._rho.append(rho)

    def remove_trap(self, index: int):
        """Remove a trap by index.

        Corresponds to MatDinHot::DeleteTrampa in the original C++ code.
        Removes both the trap object and its precomputed rho matrix.

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

        Note: The z-coordinate is preserved during a move operation.

        Args:
            index: Zero-based index of the trap to move.
            x: New X position in normalized coordinates.
            y: New Y position in normalized coordinates.
        """
        if 0 <= index < len(self.traps):
            self.traps[index].x = x
            self.traps[index].y = y
            self._rho[index] = compute_rho(self.coord_x, self.coord_y, x, y)

    def set_trap_z(self, index: int, z: float):
        """Set the z-coordinate (defocus) of an existing trap.

        Adjusting z shifts the trap along the optical axis without
        changing its lateral position. This enables 3D trap arrangements.

        Args:
            index: Zero-based index of the trap to modify.
            z: New Z position (defocus parameter).
        """
        if 0 <= index < len(self.traps):
            self.traps[index].z = z

    def find_nearest_trap(self, x: float, y: float,
                          threshold: float = 0.05) -> int:
        """Find the trap nearest to (x, y) within a distance threshold.

        Used for mouse-based selection of traps. Corresponds to
        MatDinHot::SelectMove in the C++ code, which searched for traps
        within 5*FACTORESPACIO of the click position.

        Uses Euclidean distance in the normalized coordinate space.

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

    def _phase_kernel(self, trap_index: int) -> np.ndarray:
        """Compute the phase kernel for a given trap.

        The kernel encodes the optical path difference between the SLM
        pixel at (x,y) and the trap at position (x_j, y_j, z_j):

            K_j(x,y) = (k/f) * (x*x_j + y*y_j) - (k/f^2) * (x^2+y^2) * z_j

        The first term is the linear phase (beam steering): tilting the
        wavefront to direct light toward the lateral position (x_j, y_j).

        The second term is the quadratic phase (defocus): adding a lens-like
        curvature to shift the focal point along the optical axis by z_j.

        Args:
            trap_index: Index of the target trap (0 to N_traps - 1).

        Returns:
            2D array of phase values (radians) at each SLM pixel.
        """
        # Linear phase: beam steering toward lateral position
        # k/f scales the normalized coordinates to optical phase
        kf = self.wave_vector / self.focal_distance
        kernel = kf * self._rho[trap_index]

        # Quadratic phase: defocus for z-axis positioning
        # Only computed when z != 0 to save unnecessary arithmetic
        if self.traps[trap_index].z != 0:
            kf2 = self.wave_vector / (self.focal_distance ** 2)
            kernel -= kf2 * (self.coord_x_sq + self.coord_y_sq) * self.traps[trap_index].z

        return kernel

    def compute_electric_field(self, trap_index: int) -> complex:
        """Compute the complex electric field at a specific trap position.

        Evaluates the coherent sum of all SLM pixel contributions at
        the focal plane position of the specified trap:

            E_j = (1/N) * sum_{x,y} exp(i * [phi(x,y) - K_j(x,y)])

        where N = res_x * res_y is the total pixel count and K_j is
        the phase kernel for trap j.

        The normalization by N ensures the field magnitude is
        independent of the SLM resolution, allowing fair comparison
        across different grid sizes.

        Args:
            trap_index: Index of the trap (0 to N_traps - 1).

        Returns:
            Complex electric field amplitude at the trap position.
        """
        # Phase difference between SLM pattern and kernel for this trap
        phase = self.phi - self._phase_kernel(trap_index)

        # Coherent sum over all SLM pixels, normalized by pixel count
        return np.sum(np.exp(1j * phase)) / (self.res_x * self.res_y)

    def calculate_phase_mask(self) -> int:
        """Run the Weighted Gerchberg-Saxton algorithm for phase mask generation.

        This implements the iterative Fourier transform algorithm with
        amplitude freedom, adapted for holographic optical tweezers.

        The algorithm alternates between the SLM plane (where only phase
        is controllable) and the focal plane (where trap intensities
        must match the target pattern).

        Algorithm outline:
            1. Start with random phase phi_0(x,y)
            2. For each iteration n:
                a. Forward propagation: compute E_j at each trap
                b. Amplitude correction: adjust w_j for uniformity
                c. Backward propagation: reconstruct SLM field
                d. Apply aperture function to suppress edge artifacts
                e. Phase extraction: phi_{n+1} = arg(F)
                f. Convergence check on intensity uniformity

        The weighted variant (after Di Leonardo et al., 2007) modifies
        the trap amplitudes at each iteration to enforce uniform
        intensity across all traps:

            w_j^{(n+1)} = w_j^{(n)} * <|V|> / |V_j^{(n)}|

        where V_j is the field at trap j and <|V|> is the mean amplitude.

        Returns:
            Number of iterations performed before convergence or timeout.
        """
        if len(self.traps) == 0:
            # No traps: reset phase mask to flat (zero phase)
            self.phi = np.zeros((self.res_y, self.res_x))
            return 0

        n_traps = len(self.traps)

        # Initialize with random phase (matches RandomizePhi in C++)
        self.phi = np.random.uniform(0, 2 * np.pi, (self.res_y, self.res_x))

        # Initialize uniform weights for all traps
        weights = np.ones(n_traps)

        self.error_history = []
        self.uniformity_history = []
        self.converged = False
        prev_error = float('inf')

        for iteration in range(self.max_iterations):
            # ---- FORWARD PROPAGATION ----
            # Compute complex field amplitude at each trap position
            # by evaluating the discrete Fourier component corresponding
            # to each trap's spatial frequency
            fields = np.zeros(n_traps, dtype=complex)
            for j in range(n_traps):
                # Phase at each SLM pixel contributing to trap j
                phase = self.phi - self._phase_kernel(j)
                # Coherent sum over all pixels (discrete Fourier component)
                fields[j] = np.sum(np.exp(1j * phase)) / (self.res_x * self.res_y)

            # Decompose fields into amplitude and phase
            amplitudes = np.abs(fields)
            intensities = amplitudes ** 2
            phases_at_traps = np.angle(fields)

            # Store computed values back into trap objects for external access
            for j in range(n_traps):
                self.traps[j].intensity = float(intensities[j])
                self.traps[j].amplitude = float(amplitudes[j])

            # ---- AMPLITUDE CORRECTION (Weighted GS) ----
            # Update weights to equalize trap intensities.
            # The weight update rule pushes all amplitudes toward the mean:
            #   w_j^{new} = w_j^{old} * <|V|> / |V_j|
            # Traps that are too bright get their weight reduced;
            # traps that are too dim get their weight increased.
            mean_amplitude = np.mean(amplitudes) if np.mean(amplitudes) > 1e-12 else 1.0
            for j in range(n_traps):
                if amplitudes[j] > 1e-12:
                    weights[j] *= mean_amplitude / amplitudes[j]

            # Normalize weights to prevent numerical drift over iterations
            weight_mean = np.mean(weights)
            if weight_mean > 1e-12:
                weights /= weight_mean

            # ---- BACKWARD PROPAGATION ----
            # Reconstruct the SLM field from weighted trap contributions.
            # Each trap contributes a plane wave at its spatial frequency,
            # weighted by w_j and carrying the phase it acquired during
            # forward propagation.
            complex_field = np.zeros((self.res_y, self.res_x), dtype=complex)
            for j in range(n_traps):
                # Each trap contributes a plane wave with its kernel phase
                # plus the phase observed at the trap position
                complex_field += weights[j] * np.exp(
                    1j * (self._phase_kernel(j) + phases_at_traps[j])
                )

            # Apply aperture function to suppress edge artifacts.
            # The super-Gaussian aperture models the finite SLM active area
            # and reduces ringing in the reconstructed intensity pattern.
            complex_field *= self.aperture

            # ---- PHASE EXTRACTION ----
            # Keep only the phase (discard amplitude -- the SLM is phase-only).
            # The modulo operation wraps the result to [0, 2*pi).
            self.phi = np.angle(complex_field) % (2 * np.pi)

            # ---- CONVERGENCE CHECK ----
            # RMS intensity deviation (uniformity metric):
            # measures how far the current intensities are from being uniform
            mean_intensity = np.mean(intensities) if np.mean(intensities) > 0 else 1.0
            rms_error = np.sqrt(np.mean((intensities - mean_intensity) ** 2)) / (mean_intensity + 1e-12)

            # Uniformity: ratio of minimum to maximum intensity.
            # A value of 1.0 means perfectly uniform traps.
            if np.max(intensities) > 0:
                uniformity = float(np.min(intensities) / np.max(intensities))
            else:
                uniformity = 0.0

            self.error_history.append(float(rms_error))
            self.uniformity_history.append(uniformity)

            # Check convergence: if the relative change in error is below
            # the tolerance, the algorithm has converged
            if iteration > 0 and prev_error > 1e-12:
                rel_change = abs(prev_error - rms_error) / (prev_error + 1e-12)
                if rel_change < self.tolerance:
                    self.converged = True
                    return iteration + 1

            prev_error = rms_error

        return self.max_iterations

    def compute_intensity_preview(self, preview_size: int = 128) -> np.ndarray:
        """Compute the reconstructed intensity pattern at the focal plane.

        This evaluates the far-field diffraction pattern produced by the
        current phase mask, showing where light actually focuses.

        Uses a 2D FFT of the phase-only SLM field:
            I(u,v) = |FFT{exp(i * phi(x,y))}|^2

        The result is a preview of the actual trap pattern that would
        be produced by the hologram on a real SLM.

        Args:
            preview_size: Resolution of the output intensity map.
                The phase mask is downsampled to this size before computing
                the FFT, balancing detail against computation time.

        Returns:
            2D numpy array of intensity values, normalized to [0, 1].
        """
        # Downsample phase mask to preview resolution
        step_y = max(1, self.res_y // preview_size)
        step_x = max(1, self.res_x // preview_size)
        phi_small = self.phi[::step_y, ::step_x]

        # Create phase-only field (unit amplitude, variable phase)
        field = np.exp(1j * phi_small)

        # Compute far-field via 2D FFT and center the zero-frequency component
        far_field = np.fft.fftshift(np.fft.fft2(field))

        # Intensity is the squared magnitude of the complex field
        intensity = np.abs(far_field) ** 2

        # Normalize to [0, 1] for display
        max_val = np.max(intensity)
        if max_val > 0:
            intensity /= max_val

        return intensity

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
        """Return complete state for WebSocket transmission.

        Includes downsampled phase mask, trap positions, convergence info,
        uniformity metrics, and intensity reconstruction preview.

        Returns:
            Dictionary containing:
            - phase_mask: 2D list of grayscale values (downsampled)
            - mask_width, mask_height: dimensions of the downsampled mask
            - traps: list of trap position/intensity dictionaries
            - converged: whether the GS algorithm has converged
            - iterations: number of iterations performed
            - error_history: last 20 error values for convergence plot
            - uniformity: latest uniformity metric (I_min / I_max)
            - uniformity_history: last 20 uniformity values
            - intensity_preview: 2D list of reconstructed intensity values
        """
        # Downsample phase mask for efficient transmission
        step = max(1, self.res_x // 256)
        mask_small = self.phi[::step, ::step]
        normalized = (mask_small / (2 * np.pi) * 255).astype(int).tolist()

        # Compute intensity reconstruction preview
        try:
            intensity = self.compute_intensity_preview(preview_size=128)
            intensity_list = (intensity * 255).astype(int).tolist()
        except Exception:
            intensity_list = []

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
            'uniformity': self.uniformity_history[-1] if self.uniformity_history else 0,
            'uniformity_history': [float(u) for u in self.uniformity_history[-20:]],
            'intensity_preview': intensity_list,
        }
