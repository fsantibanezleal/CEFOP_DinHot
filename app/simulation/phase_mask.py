"""
Phase mask generation for Holographic Optical Tweezers.

Implements the weighted Gerchberg-Saxton (GS) iterative algorithm for
computing phase-only holograms that produce desired optical trap patterns.

The algorithm finds a phase distribution phi(x,y) on the SLM (Spatial Light
Modulator) plane that, when illuminated by a plane wave, produces focused
spots at the desired trap positions.

Physical parameters (dimensionless formulation):
    - phase_scale alpha ~ pi : controls maximum beam deflection angle
    - defocus_scale beta ~ 1 : controls z-axis trap positioning range
    - Resolution: configurable (default 512x512 for web)

The dimensionless formulation absorbs all physical constants (wavelength,
focal length, pixel pitch) into two scaling factors. This makes the
algorithm resolution-independent and avoids numerical overflow from
carrying SI units (which produce phase values of ~10^16 radians).

Mathematical model:
    The electric field at the j-th trap position is the coherent sum of
    contributions from all SLM pixels:

        E_j = (1/N) * sum_xy exp(i * [phi(x,y) - K_j(x,y)])

    where:
        phi(x,y)   = phase value at SLM pixel (x,y)
        K_j(x,y)   = phase kernel encoding the optical path from pixel
                     (x,y) to trap j, defined as:
                     K_j = alpha*(x*x_j + y*y_j) - beta*(x^2+y^2)*z_j

    The first term of K_j is the linear phase (beam steering) and the
    second is the quadratic phase (defocus for z-axis control).
    alpha (phase_scale) and beta (defocus_scale) are dimensionless
    parameters that absorb all physical constants.

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

    The original SI parameters (k/f ~ 10^16) produced phase values
    that wrapped around 2*pi ~10^15 times per pixel, making the
    exp(i*phase) essentially random. This port replaces k/f with a
    dimensionless phase_scale ~ pi, giving O(1) radian phases that
    allow the GS algorithm to converge properly.
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
    topological_charge: int = 0  # l=0: point trap, l!=0: optical vortex


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
                 phase_scale: float = None,
                 defocus_scale: float = 1.0):
        """Initialize the phase mask generator.

        ===== PHASE SCALE: THE KEY PARAMETER =====

        The phase_scale controls how many interference fringes appear
        in the hologram for an off-center trap. It determines the
        relationship between normalized trap coordinates [-1, 1] and
        the number of 2pi phase cycles across the SLM.

        For a trap at normalized position x_j, the phase tilt is:
            total_phase_tilt = phase_scale * x_j * 2  (from u=-1 to u=+1)
            number_of_fringes = total_phase_tilt / (2*pi)

        Default: phase_scale = 2*pi * N / 4, where N is the SLM resolution.
        This gives N/4 fringes for a trap at the edge (x_j = 1), producing
        visually correct holographic patterns with clear blazed gratings
        for single traps and interference fringes for multiple traps.

        ===== WHY NOT pi? =====

        A previous version used phase_scale = pi. This gave only 0.5
        fringes for an edge trap — the mask looked nearly flat and did
        not resemble a real hologram. The GS algorithm converged but
        produced featureless phase distributions.

        ===== WHY NOT k/f? =====

        The original C++ code used k/f = 2*pi / (lambda * f) which gave
        ~10^16 radians, wrapping ~10^15 times per pixel. This was
        numerical noise that prevented convergence entirely.

        The current default (2*pi*N/4) is the sweet spot: enough fringes
        for visually correct holograms, but not so many that numerical
        precision is lost.

        ===== PHYSICAL CORRESPONDENCE =====

        A trap at normalized position x_j produces fringes with period:
            Lambda_fringe = 2 / (x_j * N_fringes_max) * SLM_width

        For N=512 SLM, a trap at x_j=0.5 produces ~64 fringes,
        corresponding to a deflection of ~64 * lambda / SLM_width.

        Args:
            resolution: (width, height) of the phase mask in pixels.
            phase_scale: Controls fringe density. Default: 2*pi*N/4
                balance between trap range and diffraction efficiency.
                Increase for wider trap spacing, decrease for finer.
            defocus_scale: Scaling factor for the quadratic (z-axis)
                phase term. Default 1.0.
        """
        self.res_x, self.res_y = resolution
        # Default: 2*pi * N/4 gives N/4 fringes for a trap at edge position
        if phase_scale is None:
            phase_scale = 2 * np.pi * min(self.res_x, self.res_y) / 4
        self.phase_scale = phase_scale
        self.defocus_scale = defocus_scale

        self.tolerance = 1e-6
        self.max_iterations = 100

        # Phase mask array
        self.phi = np.random.uniform(0, 2 * np.pi, (self.res_y, self.res_x))

        # Normalized coordinate grids [-1, 1]
        x = np.linspace(-1, 1, self.res_x)
        y = np.linspace(-1, 1, self.res_y)
        self.coord_x, self.coord_y = np.meshgrid(x, y)
        self.coord_r_sq = self.coord_x**2 + self.coord_y**2

        # Super-Gaussian aperture (pupil function)
        # Models the circular active area of the SLM.
        # The super-Gaussian (order 8) provides a smooth roll-off that
        # reduces Gibbs ringing compared to a hard circular aperture.
        r_grid = np.sqrt(self.coord_r_sq)
        self.aperture = np.exp(-(r_grid / 0.95)**8)

        # Aberration correction (Zernike polynomial coefficients)
        self._aberration = np.zeros((self.res_y, self.res_x))

        # Trap list and precomputed dot-product matrices
        self.traps: List[OpticalTrap] = []
        self._rho: List[np.ndarray] = []

        # Convergence tracking
        self.error_history: List[float] = []
        self.uniformity_history: List[float] = []
        self.converged = False

    def compute_zernike(self, n: int, m: int) -> np.ndarray:
        """Compute Zernike polynomial Z_n^m on the normalized aperture.

        First few Zernike modes:
            Z_1^1  = 2r*cos(theta)           (tilt X)
            Z_1^-1 = 2r*sin(theta)           (tilt Y)
            Z_2^0  = sqrt(3)*(2r^2-1)        (defocus)
            Z_2^2  = sqrt(6)*r^2*cos(2theta) (astigmatism)
            Z_3^1  = sqrt(8)*(3r^3-2r)*cos(theta)  (coma X)
            Z_4^0  = sqrt(5)*(6r^4-6r^2+1)         (spherical)
        """
        r = np.sqrt(self.coord_r_sq)
        theta = np.arctan2(self.coord_y, self.coord_x)

        # Radial polynomial R_n^m
        if (n, abs(m)) == (1, 1):
            R = 2 * r
        elif (n, abs(m)) == (2, 0):
            R = np.sqrt(3) * (2 * r**2 - 1)
        elif (n, abs(m)) == (2, 2):
            R = np.sqrt(6) * r**2
        elif (n, abs(m)) == (3, 1):
            R = np.sqrt(8) * (3 * r**3 - 2 * r)
        elif (n, abs(m)) == (3, 3):
            R = np.sqrt(8) * r**3
        elif (n, abs(m)) == (4, 0):
            R = np.sqrt(5) * (6 * r**4 - 6 * r**2 + 1)
        else:
            R = np.zeros_like(r)

        if m >= 0:
            return R * np.cos(m * theta)
        else:
            return R * np.sin(abs(m) * theta)

    def set_aberration_correction(self, coefficients: dict):
        """Apply Zernike aberration correction.

        Args:
            coefficients: Dict mapping (n, m) tuples to coefficient values.
                Example: {(2,0): -0.5, (2,2): 0.3} for defocus + astigmatism.
        """
        self._aberration = np.zeros((self.res_y, self.res_x))
        for (n, m), coeff in coefficients.items():
            self._aberration += coeff * self.compute_zernike(n, m)

    def clear_aberration(self):
        """Remove aberration correction."""
        self._aberration = np.zeros((self.res_y, self.res_x))

    def add_trap(self, x: float, y: float, z: float = 0.0):
        """Add a new optical trap at the specified position.

        Creates a new trap and precomputes the dot-product matrix (rho)
        for this trap position. The rho matrix stores:
            rho(px, py) = coord_x(px,py) * trap_x + coord_y(px,py) * trap_y

        The phase contribution of this trap to the hologram is then:
            K_j(u,v) = phase_scale * rho(u,v)
        which keeps values in the O(1) radian range for normalized
        trap coordinates in [-1, 1].

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

    def set_trap_charge(self, index: int, charge: int):
        """Set the topological charge of an existing trap.

        A nonzero topological charge l converts the point trap into an
        optical vortex carrying orbital angular momentum (OAM) of l*hbar
        per photon. The resulting donut-shaped intensity profile can trap
        and rotate absorptive or birefringent particles.

        Args:
            index: Zero-based index of the trap to modify.
            charge: Integer topological charge (l). l=0 is a standard
                point trap; l=+/-1 is the fundamental vortex mode.
        """
        if 0 <= index < len(self.traps):
            self.traps[index].topological_charge = charge

    def find_nearest_trap(self, x: float, y: float,
                          threshold: float = 0.15) -> int:
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

        ===== PHASE KERNEL DECOMPOSITION =====

        The kernel encodes the optical path from each SLM pixel to the
        trap position, decomposed into two terms:

        Linear (beam steering):
            K_linear = alpha * (u*x_j + v*y_j)

            This tilts the wavefront to redirect the beam toward the
            lateral position (x_j, y_j). The tilt angle increases
            linearly with trap displacement from center.

        Quadratic (defocus):
            K_quad = -beta * (u^2 + v^2) * z_j

            This adds a lens-like curvature that shifts the focal point
            along the optical axis by z_j. Positive z moves the trap
            toward the SLM (closer), negative z moves it away.

        Total kernel:
            K_j(u,v) = alpha * (u*x_j + v*y_j) - beta * (u^2 + v^2) * z_j

        Args:
            trap_index: Index of the target trap.

        Returns:
            2D array of kernel phase values (radians).
        """
        # Linear phase: beam steering
        kernel = self.phase_scale * self._rho[trap_index]

        # Quadratic phase: defocus for z-axis positioning
        if self.traps[trap_index].z != 0:
            kernel -= self.defocus_scale * self.coord_r_sq * self.traps[trap_index].z

        # Helical phase for optical vortex (OAM l*hbar per photon)
        if self.traps[trap_index].topological_charge != 0:
            l = self.traps[trap_index].topological_charge
            theta_grid = np.arctan2(self.coord_y, self.coord_x)
            kernel += l * theta_grid

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
            # After phase extraction, apply aberration correction
            self.phi = (np.angle(complex_field) + self._aberration) % (2 * np.pi)

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

        Uses a 2D FFT of the phase-only SLM field:
            I(u,v) = |FFT{ A(x,y) * exp(i * phi(x,y)) }|^2

        With the current phase_scale (~ 2*pi*N/4), a trap at normalized
        position x_j appears at FFT bin ~ x_j * N/4, which is well above
        1 bin and correctly resolved by the FFT.

        The FFT approach is fast (O(N^2 log N)) and produces the physically
        correct far-field diffraction pattern including all diffraction
        orders and speckle structure.

        Note: A previous version used direct summation because phase_scale
        was too small (pi), causing sub-bin trap positions. With the
        corrected phase_scale, the FFT works correctly.

        Args:
            preview_size: Resolution of the output intensity map.

        Returns:
            2D numpy array of intensity values, normalized to [0, 1].
        """
        # Downsample phase mask to preview resolution
        step_y = max(1, self.res_y // preview_size)
        step_x = max(1, self.res_x // preview_size)
        phi_small = self.phi[::step_y, ::step_x]
        aperture_small = self.aperture[::step_y, ::step_x]

        # Phase-only SLM field with aperture
        field = aperture_small * np.exp(1j * phi_small)

        # Far-field via 2D FFT (Fraunhofer diffraction)
        far_field = np.fft.fftshift(np.fft.fft2(field))

        # Intensity = |E|^2
        intensity = np.abs(far_field) ** 2

        # Normalize to [0, 1]
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
                    'topological_charge': int(t.topological_charge),
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
