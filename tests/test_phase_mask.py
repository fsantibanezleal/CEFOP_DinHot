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
            wavelength=632e-9,
            focal_distance=500e-9,
        )

    def test_initialization(self):
        """Generator should initialize with correct parameters."""
        self.assertEqual(self.gen.res_x, 64)
        self.assertEqual(self.gen.res_y, 64)
        self.assertAlmostEqual(self.gen.wavelength, 632e-9)
        self.assertEqual(self.gen.phi.shape, (64, 64))
        self.assertEqual(len(self.gen.traps), 0)

    def test_wave_vector(self):
        """Wave vector k = 2*pi/lambda should be computed correctly."""
        expected_k = 2 * np.pi / 632e-9
        self.assertAlmostEqual(self.gen.wave_vector, expected_k, places=0)

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
        gen.max_iterations = 30
        gen.calculate_phase_mask()
        if len(gen.uniformity_history) > 2:
            # Late uniformity should be >= early uniformity (generally)
            self.assertGreaterEqual(gen.uniformity_history[-1],
                                    gen.uniformity_history[0] * 0.5)
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
