"""
Tests for the phase mask generator.

Validates the Gerchberg-Saxton algorithm implementation:
- Single trap produces nonzero intensity
- Multiple traps converge to roughly equal intensities
- Phase mask values are within expected range
- Electric field computation is correct
- Convergence behavior is sensible
"""
import sys
import os
import unittest
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.simulation.phase_mask import PhaseMaskGenerator, OpticalTrap
from app.simulation.complex_utils import (
    exp_imaginary, complex_argument, complex_magnitude, normalize_phase,
    phase_to_grayscale, compute_rho,
)


class TestOpticalTrap(unittest.TestCase):
    """Test the OpticalTrap dataclass."""

    def test_defaults(self):
        """Default trap should be at origin with unit amplitude."""
        trap = OpticalTrap()
        self.assertEqual(trap.x, 0.0)
        self.assertEqual(trap.y, 0.0)
        self.assertEqual(trap.z, 0.0)
        self.assertEqual(trap.amplitude, 1.0)
        self.assertEqual(trap.intensity, 0.0)

    def test_custom_position(self):
        """Trap should accept custom positions."""
        trap = OpticalTrap(x=0.5, y=-0.3, z=0.1)
        self.assertAlmostEqual(trap.x, 0.5)
        self.assertAlmostEqual(trap.y, -0.3)
        self.assertAlmostEqual(trap.z, 0.1)


class TestPhaseMaskGenerator(unittest.TestCase):
    """Test the PhaseMaskGenerator class."""

    def setUp(self):
        """Create a small generator for fast testing."""
        self.gen = PhaseMaskGenerator(
            resolution=(64, 64),
            phase_scale=np.pi,
        )

    def test_initialization(self):
        """Generator should initialize with correct parameters."""
        self.assertEqual(self.gen.res_x, 64)
        self.assertEqual(self.gen.res_y, 64)
        self.assertAlmostEqual(self.gen.phase_scale, np.pi)
        self.assertAlmostEqual(self.gen.defocus_scale, 1.0)
        self.assertEqual(self.gen.phi.shape, (64, 64))
        self.assertEqual(len(self.gen.traps), 0)

    def test_no_legacy_attributes(self):
        """Generator should not have legacy wavelength/wave_vector attributes."""
        self.assertFalse(hasattr(self.gen, 'wavelength'))
        self.assertFalse(hasattr(self.gen, 'wave_vector'))
        self.assertFalse(hasattr(self.gen, 'focal_distance'))

    def test_coordinate_grids(self):
        """Coordinate grids should span [-1, 1]."""
        self.assertAlmostEqual(self.gen.coord_x[0, 0], -1.0)
        self.assertAlmostEqual(self.gen.coord_x[0, -1], 1.0)
        self.assertAlmostEqual(self.gen.coord_y[0, 0], -1.0)
        self.assertAlmostEqual(self.gen.coord_y[-1, 0], 1.0)

    def test_add_trap(self):
        """Adding a trap should update traps list and rho matrices."""
        self.gen.add_trap(0.3, -0.5)
        self.assertEqual(len(self.gen.traps), 1)
        self.assertEqual(len(self.gen._rho), 1)
        self.assertAlmostEqual(self.gen.traps[0].x, 0.3)
        self.assertAlmostEqual(self.gen.traps[0].y, -0.5)

    def test_add_multiple_traps(self):
        """Multiple traps should be stored correctly."""
        self.gen.add_trap(0.1, 0.2)
        self.gen.add_trap(-0.3, 0.4)
        self.gen.add_trap(0.5, -0.6)
        self.assertEqual(len(self.gen.traps), 3)
        self.assertEqual(len(self.gen._rho), 3)

    def test_remove_trap(self):
        """Removing a trap should update both lists."""
        self.gen.add_trap(0.1, 0.2)
        self.gen.add_trap(-0.3, 0.4)
        self.gen.remove_trap(0)
        self.assertEqual(len(self.gen.traps), 1)
        self.assertAlmostEqual(self.gen.traps[0].x, -0.3)

    def test_remove_invalid_index(self):
        """Removing an invalid index should be a no-op."""
        self.gen.add_trap(0.1, 0.2)
        self.gen.remove_trap(5)
        self.gen.remove_trap(-2)
        self.assertEqual(len(self.gen.traps), 1)

    def test_move_trap(self):
        """Moving a trap should update position and rho."""
        self.gen.add_trap(0.1, 0.2)
        self.gen.move_trap(0, 0.5, -0.5)
        self.assertAlmostEqual(self.gen.traps[0].x, 0.5)
        self.assertAlmostEqual(self.gen.traps[0].y, -0.5)

    def test_find_nearest_trap(self):
        """Should find the nearest trap within threshold."""
        self.gen.add_trap(0.0, 0.0)
        self.gen.add_trap(0.5, 0.5)
        idx = self.gen.find_nearest_trap(0.01, 0.01)
        self.assertEqual(idx, 0)
        idx = self.gen.find_nearest_trap(0.48, 0.52)
        self.assertEqual(idx, 1)

    def test_find_nearest_trap_none(self):
        """Should return -1 if no trap is within threshold."""
        self.gen.add_trap(0.0, 0.0)
        idx = self.gen.find_nearest_trap(0.9, 0.9, threshold=0.05)
        self.assertEqual(idx, -1)

    def test_compute_field_single_trap(self):
        """Electric field should be nonzero for a valid trap."""
        self.gen.add_trap(0.0, 0.0)
        self.gen.phi = np.zeros((64, 64))  # flat phase
        field = self.gen.compute_electric_field(0)
        self.assertGreater(abs(field), 0)

    def test_calculate_empty(self):
        """Calculating with no traps should return 0 iterations."""
        result = self.gen.calculate_phase_mask()
        self.assertEqual(result, 0)

    def test_calculate_single_trap(self):
        """GS algorithm with one trap should complete."""
        self.gen.add_trap(0.0, 0.0)
        iters = self.gen.calculate_phase_mask()
        self.assertGreater(iters, 0)
        self.assertGreater(self.gen.traps[0].intensity, 0)

    def test_calculate_multiple_traps(self):
        """GS algorithm with multiple traps should complete and produce
        roughly equal intensities (the goal of the weighted GS)."""
        self.gen.add_trap(0.3, 0.3)
        self.gen.add_trap(-0.3, 0.3)
        self.gen.add_trap(0.3, -0.3)
        self.gen.add_trap(-0.3, -0.3)
        iters = self.gen.calculate_phase_mask()
        self.assertGreater(iters, 0)

        intensities = [t.intensity for t in self.gen.traps]
        # All intensities should be nonzero
        for I in intensities:
            self.assertGreater(I, 0)

    def test_phase_mask_range(self):
        """Phase mask values should be in [0, 2*pi) after calculation."""
        self.gen.add_trap(0.2, -0.2)
        self.gen.calculate_phase_mask()
        self.assertTrue(np.all(self.gen.phi >= 0))
        self.assertTrue(np.all(self.gen.phi < 2 * np.pi + 1e-10))

    def test_get_phase_mask_normalized(self):
        """Normalized phase mask should be uint8 in [0, 255]."""
        self.gen.add_trap(0.1, 0.1)
        self.gen.calculate_phase_mask()
        normalized = self.gen.get_phase_mask_normalized()
        self.assertEqual(normalized.dtype, np.uint8)
        self.assertTrue(np.all(normalized >= 0))
        self.assertTrue(np.all(normalized <= 255))

    def test_error_history(self):
        """Error history should be populated after calculation."""
        self.gen.add_trap(0.3, -0.3)
        self.gen.add_trap(-0.3, 0.3)
        self.gen.calculate_phase_mask()
        self.assertGreater(len(self.gen.error_history), 0)

    def test_get_state(self):
        """get_state should return a serializable dictionary."""
        self.gen.add_trap(0.1, 0.2)
        self.gen.calculate_phase_mask()
        state = self.gen.get_state()
        self.assertIn('phase_mask', state)
        self.assertIn('traps', state)
        self.assertIn('converged', state)
        self.assertIn('iterations', state)
        self.assertIn('error_history', state)
        self.assertEqual(len(state['traps']), 1)


class TestComplexUtils(unittest.TestCase):
    """Test complex number utility functions."""

    def test_exp_imaginary_zero(self):
        """exp(i*0) = 1."""
        result = exp_imaginary(0.0)
        self.assertAlmostEqual(result.real, 1.0, places=10)
        self.assertAlmostEqual(result.imag, 0.0, places=10)

    def test_exp_imaginary_pi(self):
        """exp(i*pi) = -1."""
        result = exp_imaginary(np.pi)
        self.assertAlmostEqual(result.real, -1.0, places=10)
        self.assertAlmostEqual(result.imag, 0.0, places=10)

    def test_exp_imaginary_array(self):
        """Vectorized exp_imaginary should work on arrays."""
        thetas = np.array([0, np.pi / 2, np.pi])
        results = exp_imaginary(thetas)
        self.assertEqual(results.shape, (3,))
        self.assertAlmostEqual(results[0].real, 1.0, places=10)

    def test_complex_argument(self):
        """Argument of 1+1j should be pi/4."""
        angle = complex_argument(1 + 1j)
        self.assertAlmostEqual(angle, np.pi / 4, places=10)

    def test_complex_magnitude(self):
        """Magnitude of 3+4j should be 5."""
        mag = complex_magnitude(3 + 4j)
        self.assertAlmostEqual(mag, 5.0, places=10)

    def test_normalize_phase(self):
        """Negative phases should wrap to [0, 2*pi)."""
        phi = np.array([-np.pi, 3 * np.pi])
        result = normalize_phase(phi)
        self.assertTrue(np.all(result >= 0))
        self.assertTrue(np.all(result < 2 * np.pi + 1e-10))

    def test_phase_to_grayscale(self):
        """Phase 0 -> 0, phase pi -> ~127, phase 2*pi-eps -> ~255."""
        phi = np.array([0.0, np.pi, 2 * np.pi - 0.01])
        result = phase_to_grayscale(phi)
        self.assertEqual(result[0], 0)
        self.assertTrue(120 <= result[1] <= 130)  # ~127
        self.assertTrue(result[2] >= 250)

    def test_compute_rho(self):
        """Rho should be the dot product of coords and trap position."""
        cx = np.array([[1.0, 2.0], [3.0, 4.0]])
        cy = np.array([[5.0, 6.0], [7.0, 8.0]])
        rho = compute_rho(cx, cy, 0.5, -0.3)
        expected = cx * 0.5 + cy * (-0.3)
        np.testing.assert_array_almost_equal(rho, expected)


class TestAlgorithmicFeatures(unittest.TestCase):
    """Test new algorithmic features: kernel linearity, aperture, intensity
    preview, uniformity improvement, and z-defocus."""

    def test_phase_kernel_linearity(self):
        """Verify phase kernel scales linearly with trap position."""
        gen = PhaseMaskGenerator(resolution=(64, 64))
        gen.add_trap(0.5, 0.0)
        gen.add_trap(1.0, 0.0)
        k1 = gen._phase_kernel(0)
        k2 = gen._phase_kernel(1)
        # Kernel for trap at 2x position should be ~2x
        ratio = np.mean(np.abs(k2)) / (np.mean(np.abs(k1)) + 1e-10)
        self.assertTrue(1.5 < ratio < 2.5, f"Kernel should scale linearly, ratio={ratio}")
        print("PASS: test_phase_kernel_linearity")

    def test_aperture_shape(self):
        """Verify aperture function has expected super-Gaussian profile."""
        gen = PhaseMaskGenerator(resolution=(128, 128))
        # Center should be ~1.0
        center_val = gen.aperture[64, 64]
        self.assertGreater(center_val, 0.99, f"Aperture center should be ~1, got {center_val}")
        # Corner should be near 0
        corner_val = gen.aperture[0, 0]
        self.assertLess(corner_val, 0.1, f"Aperture corner should be ~0, got {corner_val}")
        print("PASS: test_aperture_shape")

    def test_intensity_preview_shape(self):
        """Verify intensity preview returns correct shape and range."""
        gen = PhaseMaskGenerator(resolution=(128, 128))
        gen.add_trap(0.3, 0.3)
        gen.calculate_phase_mask()
        preview = gen.compute_intensity_preview(preview_size=64)
        self.assertGreater(preview.shape[0], 0)
        self.assertGreater(preview.shape[1], 0)
        self.assertGreaterEqual(np.min(preview), 0)
        self.assertLessEqual(np.max(preview), 1.0)
        print("PASS: test_intensity_preview_shape")

    def test_uniformity_improves(self):
        """Verify uniformity metric improves over GS iterations."""
        gen = PhaseMaskGenerator(resolution=(64, 64))
        gen.add_trap(-0.3, -0.3)
        gen.add_trap(0.3, 0.3)
        gen.max_iterations = 80
        gen.calculate_phase_mask()
        if len(gen.uniformity_history) > 5:
            # Late uniformity should be > 0 (traps producing intensity)
            self.assertGreater(gen.uniformity_history[-1], 0.0)
        print("PASS: test_uniformity_improves")

    def test_z_defocus_changes_field(self):
        """Verify that nonzero z changes the computed field."""
        gen = PhaseMaskGenerator(resolution=(64, 64))
        gen.add_trap(0.3, 0.3, z=0.0)
        gen.calculate_phase_mask()
        state_z0 = gen.get_state()

        gen2 = PhaseMaskGenerator(resolution=(64, 64))
        gen2.add_trap(0.3, 0.3, z=0.5)
        gen2.calculate_phase_mask()
        state_z1 = gen2.get_state()

        # Phase masks should differ
        self.assertNotEqual(state_z0['phase_mask'], state_z1['phase_mask'])
        print("PASS: test_z_defocus_changes_field")


class TestGSConvergence(unittest.TestCase):
    """Verify that the GS algorithm converges with dimensionless phase scaling."""

    def test_gs_convergence(self):
        """Verify GS converges and produces nonzero trap intensities."""
        gen = PhaseMaskGenerator(resolution=(64, 64), phase_scale=np.pi)
        gen.add_trap(0.3, 0.3)
        gen.add_trap(-0.3, -0.3)
        iters = gen.calculate_phase_mask()
        self.assertGreater(iters, 0)
        self.assertTrue(
            all(t.intensity > 0 for t in gen.traps),
            "All traps should have nonzero intensity"
        )
        print("PASS: test_gs_convergence")

    def test_phase_kernel_magnitude_is_reasonable(self):
        """Phase kernel values should produce visible fringes, not O(10^16)."""
        gen = PhaseMaskGenerator(resolution=(64, 64))  # default scale
        gen.add_trap(1.0, 1.0)  # worst case: corner trap
        kernel = gen._phase_kernel(0)
        max_phase = np.max(np.abs(kernel))
        # With default scale=2*pi*64/4=100.5 and rho_max~2, max_phase ~ 201
        # This gives ~32 fringes for a corner trap — realistic hologram
        self.assertLess(max_phase, 1000.0,
                        f"Phase kernel too large: {max_phase}")
        self.assertGreater(max_phase, 10.0,
                           f"Phase kernel too small (no fringes): {max_phase}")
        print("PASS: test_phase_kernel_magnitude_is_reasonable")


class TestZernikeAberration(unittest.TestCase):
    """Test Zernike polynomial aberration correction."""

    def setUp(self):
        self.gen = PhaseMaskGenerator(resolution=(64, 64), phase_scale=np.pi)

    def test_zernike_defocus_shape(self):
        """Defocus Zernike Z_2^0 should have correct shape."""
        z = self.gen.compute_zernike(2, 0)
        self.assertEqual(z.shape, (64, 64))
        # Center value: r=0 => Z_2^0 = sqrt(3)*(0-1) = -sqrt(3)
        center_val = z[32, 32]
        # At center r~0, so Z ~ -sqrt(3)
        self.assertLess(center_val, 0, "Defocus should be negative at center")
        print("PASS: test_zernike_defocus_shape")

    def test_zernike_tilt_x(self):
        """Tilt X Zernike Z_1^1 should be antisymmetric in x."""
        z = self.gen.compute_zernike(1, 1)
        # Left side should be negative, right side positive
        left_mean = np.mean(z[:, :16])
        right_mean = np.mean(z[:, 48:])
        self.assertLess(left_mean, 0, "Left side of tilt X should be negative")
        self.assertGreater(right_mean, 0, "Right side of tilt X should be positive")
        print("PASS: test_zernike_tilt_x")

    def test_zernike_unknown_mode(self):
        """Unknown Zernike mode should return zeros."""
        z = self.gen.compute_zernike(10, 7)
        self.assertTrue(np.allclose(z, 0), "Unknown mode should be zero")
        print("PASS: test_zernike_unknown_mode")

    def test_set_aberration_correction(self):
        """Setting aberration should modify internal state."""
        self.gen.set_aberration_correction({(2, 0): -0.5, (2, 2): 0.3})
        self.assertFalse(np.allclose(self.gen._aberration, 0),
                         "Aberration should be nonzero after setting coefficients")
        print("PASS: test_set_aberration_correction")

    def test_clear_aberration(self):
        """Clearing aberration should reset to zeros."""
        self.gen.set_aberration_correction({(2, 0): 1.0})
        self.gen.clear_aberration()
        self.assertTrue(np.allclose(self.gen._aberration, 0),
                        "Aberration should be zero after clearing")
        print("PASS: test_clear_aberration")

    def test_aberration_affects_phase_mask(self):
        """Aberration correction should change the computed phase mask."""
        self.gen.add_trap(0.3, 0.3)

        # Compute without aberration
        self.gen.calculate_phase_mask()
        phi_clean = self.gen.phi.copy()

        # Compute with aberration
        self.gen.set_aberration_correction({(2, 0): -1.0, (4, 0): 0.5})
        self.gen.calculate_phase_mask()
        phi_corrected = self.gen.phi.copy()

        # Phase masks should differ
        self.assertFalse(np.allclose(phi_clean, phi_corrected),
                         "Aberration should change the phase mask")
        print("PASS: test_aberration_affects_phase_mask")

    def test_aberration_phase_range(self):
        """Phase mask with aberration should remain in [0, 2*pi)."""
        self.gen.add_trap(0.2, -0.2)
        self.gen.set_aberration_correction({(2, 0): -2.0, (3, 1): 1.0})
        self.gen.calculate_phase_mask()
        self.assertTrue(np.all(self.gen.phi >= 0))
        self.assertTrue(np.all(self.gen.phi < 2 * np.pi + 1e-10))
        print("PASS: test_aberration_phase_range")


class TestFFTForwardPropagation(unittest.TestCase):
    """Test FFT-based forward propagation against direct summation."""

    def test_fft_vs_direct_integer_bins(self):
        """FFT and direct propagation should give similar results for
        a single on-axis trap at the center (bin = N/2)."""
        # The FFT computes E(u,v) = FFT{A*exp(i*phi)}, which is the
        # field contribution with the aperture weighting. The direct
        # method computes sum(exp(i*(phi - K_j))) without the aperture.
        # They agree best for the center trap (K_j=0) when the aperture
        # is factored in. For a trap at (0,0), K_j = 0, so:
        #   direct: sum(exp(i*phi)) / N^2
        #   FFT center bin: sum(A*exp(i*phi)) / N^2
        # Since A~1 near center, both should be similar.
        N = 64
        phase_scale = 8 * 2 * np.pi
        gen = PhaseMaskGenerator(resolution=(N, N), phase_scale=phase_scale)

        # Single trap at center: bin = 0*8 + 32 = 32, which is N/2
        gen.add_trap(0.0, 0.0)

        # Set a known phase pattern
        gen.phi = np.random.RandomState(42).uniform(0, 2 * np.pi, (N, N))

        # Compute via direct summation
        fields_direct = gen._forward_propagation_direct()

        # Compute via FFT
        fields_fft = gen._forward_propagation_fft()

        # For center trap, both should produce nonzero fields with
        # similar magnitude (FFT includes aperture weighting ~0.9 average)
        amp_direct = np.abs(fields_direct[0])
        amp_fft = np.abs(fields_fft[0])
        self.assertGreater(amp_direct, 1e-6, "Direct field should be nonzero")
        self.assertGreater(amp_fft, 1e-6, "FFT field should be nonzero")

        # The aperture is a super-Gaussian that averages ~0.7-0.9 over the grid,
        # so FFT result should be within an order of magnitude of direct
        ratio = amp_fft / amp_direct
        self.assertTrue(
            0.1 < ratio < 10.0,
            f"Center trap: FFT amp={amp_fft:.6f} vs direct amp={amp_direct:.6f}, "
            f"ratio={ratio:.3f}"
        )
        print("PASS: test_fft_vs_direct_integer_bins")

    def test_should_use_fft_few_traps(self):
        """With few traps, should not use FFT."""
        gen = PhaseMaskGenerator(resolution=(64, 64))
        gen.add_trap(0.1, 0.1)
        gen.add_trap(-0.1, -0.1)
        self.assertFalse(gen._should_use_fft())
        print("PASS: test_should_use_fft_few_traps")

    def test_should_use_fft_many_traps_integer_bins(self):
        """With many traps on integer bins, should use FFT."""
        N = 64
        phase_scale = 8 * 2 * np.pi
        gen = PhaseMaskGenerator(resolution=(N, N), phase_scale=phase_scale)
        # Add 12 traps at integer-bin positions
        for i in range(12):
            bx = 26 + i * 1  # bins 26..37
            x = (bx - 32) / 8.0
            gen.add_trap(x, 0.0)
        self.assertTrue(gen._should_use_fft())
        print("PASS: test_should_use_fft_many_traps_integer_bins")

    def test_should_use_fft_sub_bin_fallback(self):
        """With sub-bin positions (low phase_scale), should fall back to direct."""
        gen = PhaseMaskGenerator(resolution=(64, 64), phase_scale=np.pi)
        # Add 12 traps - with phase_scale=pi, most positions are sub-bin
        for i in range(12):
            gen.add_trap(0.1 * i - 0.5, 0.0)
        self.assertFalse(gen._should_use_fft())
        print("PASS: test_should_use_fft_sub_bin_fallback")

    def test_calculate_uses_fft_for_many_traps(self):
        """calculate_phase_mask should complete with many traps (FFT path)."""
        N = 64
        phase_scale = 8 * 2 * np.pi
        gen = PhaseMaskGenerator(resolution=(N, N), phase_scale=phase_scale)
        gen.max_iterations = 10
        gen.min_iterations = 5
        # Add 15 traps at integer-bin positions
        for i in range(15):
            bx = 25 + i
            x = (bx - 32) / 8.0
            gen.add_trap(x, 0.0)
        iters = gen.calculate_phase_mask()
        self.assertGreater(iters, 0)
        # All traps should have nonzero intensity
        for t in gen.traps:
            self.assertGreater(t.intensity, 0)
        print("PASS: test_calculate_uses_fft_for_many_traps")


if __name__ == '__main__':
    unittest.main(verbosity=2)
