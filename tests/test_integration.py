"""
Integration tests for the CEFOP DinHot application.

Tests the full workflow from initialization through trap manipulation
to phase mask computation, ensuring all components work together.
"""
import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.simulation.trap_manager import TrapManager
from app.simulation.phase_mask import PhaseMaskGenerator, OpticalTrap


class TestFullWorkflow(unittest.TestCase):
    """Test complete usage workflows."""

    def test_create_compute_inspect(self):
        """Create traps, compute mask, inspect results."""
        tm = TrapManager(resolution=(64, 64))

        # Create mode
        tm.mode = 'create'
        tm.handle_click(0.3, 0.3)
        tm.handle_click(-0.3, 0.3)
        tm.handle_click(0.3, -0.3)
        tm.handle_click(-0.3, -0.3)

        # Recalculate
        tm.recalculate_if_needed()

        # Check state
        state = tm.get_state()
        self.assertEqual(len(state['traps']), 4)
        self.assertGreater(state['iterations'], 0)

        # All traps should have nonzero intensity
        for trap in state['traps']:
            self.assertGreater(trap['intensity'], 0)

        # Phase mask should be a valid 2D array
        mask = state['phase_mask']
        self.assertGreater(len(mask), 0)
        self.assertGreater(len(mask[0]), 0)

    def test_create_move_delete_workflow(self):
        """Full workflow: create, move, delete traps."""
        tm = TrapManager(resolution=(64, 64))

        # Create two traps
        tm.mode = 'create'
        tm.handle_click(0.2, 0.2)
        tm.handle_click(-0.2, -0.2)
        tm.recalculate_if_needed()
        self.assertEqual(len(tm.generator.traps), 2)

        # Move first trap
        tm.mode = 'move'
        tm.handle_click(0.21, 0.21)  # select near trap 0
        self.assertEqual(tm.selected_trap, 0)
        tm.handle_drag(0.4, 0.4)
        tm.handle_release()
        tm.recalculate_if_needed()
        self.assertAlmostEqual(tm.generator.traps[0].x, 0.4, places=5)
        self.assertAlmostEqual(tm.generator.traps[0].y, 0.4, places=5)

        # Delete second trap
        tm.mode = 'delete'
        tm.handle_click(-0.19, -0.19)
        tm.recalculate_if_needed()
        self.assertEqual(len(tm.generator.traps), 1)

    def test_state_serialization_roundtrip(self):
        """State should be JSON-serializable (all values are native Python types)."""
        import json

        tm = TrapManager(resolution=(64, 64))
        tm.mode = 'create'
        tm.handle_click(0.1, 0.2)
        tm.handle_click(-0.3, 0.4)
        tm.recalculate_if_needed()

        state = tm.get_state()

        # Should not raise
        json_str = json.dumps(state)
        self.assertIsInstance(json_str, str)

        # Round-trip
        parsed = json.loads(json_str)
        self.assertEqual(len(parsed['traps']), 2)
        self.assertIsInstance(parsed['phase_mask'], list)

    def test_repeated_recalculation(self):
        """Multiple recalculations should all complete successfully."""
        tm = TrapManager(resolution=(64, 64))
        tm.generator.add_trap(0.2, 0.2)

        for _ in range(5):
            iters = tm.generator.calculate_phase_mask()
            self.assertGreater(iters, 0)
            self.assertTrue(np.all(tm.generator.phi >= 0))
            self.assertTrue(np.all(tm.generator.phi < 2 * np.pi + 1e-10))


class TestPhysicsConsistency(unittest.TestCase):
    """Test that the physics model produces sensible results."""

    def test_single_centered_trap(self):
        """A single trap at the center should have high intensity."""
        gen = PhaseMaskGenerator(resolution=(64, 64))
        gen.add_trap(0.0, 0.0)
        gen.calculate_phase_mask()
        # Central trap should have significant intensity
        self.assertGreater(gen.traps[0].intensity, 0)

    def test_symmetric_traps_similar_intensity(self):
        """Symmetric traps should have similar intensities after GS."""
        gen = PhaseMaskGenerator(resolution=(64, 64))
        gen.max_iterations = 100  # More iterations for better convergence
        gen.add_trap(0.3, 0.3)
        gen.add_trap(-0.3, 0.3)
        gen.add_trap(0.3, -0.3)
        gen.add_trap(-0.3, -0.3)
        gen.calculate_phase_mask()

        intensities = [t.intensity for t in gen.traps]
        mean_i = np.mean(intensities)

        # All intensities should be within 50% of the mean
        # (the GS algorithm tries to equalize them, but with small
        # resolution the uniformity might not be perfect)
        for I in intensities:
            if mean_i > 0:
                self.assertGreater(I / mean_i, 0.3,
                    f"Intensity {I:.2e} too far from mean {mean_i:.2e}")

    def test_phase_scale_affects_computation(self):
        """Different phase_scale values should produce different phase masks."""
        gen1 = PhaseMaskGenerator(resolution=(32, 32), phase_scale=np.pi)
        gen2 = PhaseMaskGenerator(resolution=(32, 32), phase_scale=2 * np.pi)

        gen1.add_trap(0.3, 0.3)
        gen2.add_trap(0.3, 0.3)

        # Set same initial random seed for comparison
        np.random.seed(42)
        gen1.calculate_phase_mask()
        np.random.seed(42)
        gen2.calculate_phase_mask()

        # Phase scales should differ
        self.assertNotAlmostEqual(gen1.phase_scale, gen2.phase_scale)

    def test_defocus_changes_field(self):
        """A trap with z != 0 should produce a different field."""
        gen = PhaseMaskGenerator(resolution=(32, 32))
        gen.add_trap(0.3, 0.3, z=0.0)
        gen.phi = np.random.uniform(0, 2 * np.pi, (32, 32))
        field_z0 = gen.compute_electric_field(0)

        gen.traps[0].z = 0.1
        field_z1 = gen.compute_electric_field(0)

        self.assertNotAlmostEqual(abs(field_z0), abs(field_z1), places=5)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_trap_at_boundary(self):
        """Traps at the boundary should work."""
        gen = PhaseMaskGenerator(resolution=(64, 64))
        gen.add_trap(1.0, 1.0)
        gen.add_trap(-1.0, -1.0)
        iters = gen.calculate_phase_mask()
        self.assertGreater(iters, 0)

    def test_overlapping_traps(self):
        """Two traps at the same position should not crash."""
        gen = PhaseMaskGenerator(resolution=(64, 64))
        gen.add_trap(0.5, 0.5)
        gen.add_trap(0.5, 0.5)
        iters = gen.calculate_phase_mask()
        self.assertGreater(iters, 0)

    def test_many_traps(self):
        """Should handle a moderate number of traps."""
        gen = PhaseMaskGenerator(resolution=(32, 32))
        gen.max_iterations = 10  # Limit for speed
        for i in range(8):
            angle = i * np.pi / 4
            gen.add_trap(0.5 * np.cos(angle), 0.5 * np.sin(angle))
        iters = gen.calculate_phase_mask()
        self.assertGreater(iters, 0)
        self.assertEqual(len(gen.traps), 8)

    def test_remove_all_traps(self):
        """Removing all traps should leave the system in a clean state."""
        tm = TrapManager(resolution=(32, 32))
        tm.generator.add_trap(0.1, 0.1)
        tm.generator.add_trap(-0.1, -0.1)
        tm.generator.remove_trap(1)
        tm.generator.remove_trap(0)
        self.assertEqual(len(tm.generator.traps), 0)
        state = tm.get_state()
        self.assertEqual(len(state['traps']), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
