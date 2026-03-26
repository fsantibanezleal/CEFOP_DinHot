"""
Tests for the optical trap manager.

Validates trap creation, deletion, movement, and selection through the
TrapManager's event-handling interface, which mirrors the original C++
mouse event handlers.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.simulation.trap_manager import TrapManager


class TestTrapManagerInit(unittest.TestCase):
    """Test TrapManager initialization."""

    def test_default_init(self):
        """Default initialization should create a valid manager."""
        tm = TrapManager()
        self.assertEqual(tm.mode, 'create')
        self.assertEqual(tm.selected_trap, -1)
        self.assertFalse(tm.needs_recalculation)
        self.assertEqual(len(tm.generator.traps), 0)

    def test_custom_resolution(self):
        """Custom resolution should be passed to the generator."""
        tm = TrapManager(resolution=(128, 128))
        self.assertEqual(tm.generator.res_x, 128)
        self.assertEqual(tm.generator.res_y, 128)


class TestTrapManagerCreateMode(unittest.TestCase):
    """Test create mode interactions."""

    def setUp(self):
        self.tm = TrapManager(resolution=(64, 64))
        self.tm.mode = 'create'

    def test_click_creates_trap(self):
        """Clicking in create mode should add a trap."""
        result = self.tm.handle_click(0.3, -0.2)
        self.assertEqual(result, 'created')
        self.assertEqual(len(self.tm.generator.traps), 1)
        self.assertAlmostEqual(self.tm.generator.traps[0].x, 0.3)
        self.assertAlmostEqual(self.tm.generator.traps[0].y, -0.2)

    def test_click_marks_recalculation(self):
        """Creating a trap should mark recalculation needed."""
        self.tm.handle_click(0.0, 0.0)
        self.assertTrue(self.tm.needs_recalculation)

    def test_multiple_clicks(self):
        """Multiple clicks should create multiple traps."""
        self.tm.handle_click(0.1, 0.1)
        self.tm.handle_click(-0.2, 0.3)
        self.tm.handle_click(0.5, -0.5)
        self.assertEqual(len(self.tm.generator.traps), 3)


class TestTrapManagerDeleteMode(unittest.TestCase):
    """Test delete mode interactions."""

    def setUp(self):
        self.tm = TrapManager(resolution=(64, 64))
        # Pre-populate traps
        self.tm.generator.add_trap(0.0, 0.0)
        self.tm.generator.add_trap(0.5, 0.5)
        self.tm.mode = 'delete'

    def test_click_near_trap_deletes(self):
        """Clicking near a trap in delete mode should remove it."""
        result = self.tm.handle_click(0.01, 0.01)
        self.assertEqual(result, 'deleted')
        self.assertEqual(len(self.tm.generator.traps), 1)

    def test_click_far_from_trap_noop(self):
        """Clicking far from any trap should not delete."""
        result = self.tm.handle_click(0.9, 0.9)
        self.assertIsNone(result)
        self.assertEqual(len(self.tm.generator.traps), 2)

    def test_delete_marks_recalculation(self):
        """Deleting a trap should mark recalculation needed."""
        self.tm.handle_click(0.0, 0.0)
        self.assertTrue(self.tm.needs_recalculation)


class TestTrapManagerMoveMode(unittest.TestCase):
    """Test move mode interactions (select, drag, release)."""

    def setUp(self):
        self.tm = TrapManager(resolution=(64, 64))
        self.tm.generator.add_trap(0.0, 0.0)
        self.tm.generator.add_trap(0.5, 0.5)
        self.tm.mode = 'move'

    def test_click_selects_trap(self):
        """Clicking near a trap in move mode should select it."""
        result = self.tm.handle_click(0.01, 0.01)
        self.assertEqual(result, 'selected')
        self.assertEqual(self.tm.selected_trap, 0)

    def test_click_selects_nearest(self):
        """Should select the nearest trap."""
        result = self.tm.handle_click(0.48, 0.52)
        self.assertEqual(result, 'selected')
        self.assertEqual(self.tm.selected_trap, 1)

    def test_drag_moves_trap(self):
        """Dragging after selection should move the trap."""
        self.tm.handle_click(0.0, 0.0)  # select trap 0
        self.tm.handle_drag(0.3, 0.4)
        self.assertAlmostEqual(self.tm.generator.traps[0].x, 0.3)
        self.assertAlmostEqual(self.tm.generator.traps[0].y, 0.4)

    def test_drag_without_selection_noop(self):
        """Dragging without selection should not change anything."""
        self.tm.handle_drag(0.5, 0.5)
        self.assertAlmostEqual(self.tm.generator.traps[0].x, 0.0)

    def test_release_deselects(self):
        """Releasing should deselect the trap."""
        self.tm.handle_click(0.0, 0.0)
        self.tm.handle_release()
        self.assertEqual(self.tm.selected_trap, -1)

    def test_release_marks_recalculation(self):
        """Releasing should mark recalculation needed."""
        self.tm.handle_click(0.0, 0.0)
        self.tm.needs_recalculation = False  # reset
        self.tm.handle_release()
        self.assertTrue(self.tm.needs_recalculation)


class TestTrapManagerRecalculation(unittest.TestCase):
    """Test recalculation behavior."""

    def setUp(self):
        self.tm = TrapManager(resolution=(64, 64))

    def test_recalculate_when_needed(self):
        """recalculate_if_needed should compute when flag is set."""
        self.tm.generator.add_trap(0.2, 0.3)
        self.tm.needs_recalculation = True
        iters = self.tm.recalculate_if_needed()
        self.assertGreater(iters, 0)
        self.assertFalse(self.tm.needs_recalculation)

    def test_no_recalculate_when_not_needed(self):
        """recalculate_if_needed should skip when flag is False."""
        self.tm.needs_recalculation = False
        iters = self.tm.recalculate_if_needed()
        self.assertEqual(iters, 0)

    def test_full_create_and_recalculate(self):
        """Full workflow: create traps, recalculate, check state."""
        self.tm.mode = 'create'
        self.tm.handle_click(0.3, 0.3)
        self.tm.recalculate_if_needed()
        self.tm.handle_click(-0.3, -0.3)
        self.tm.recalculate_if_needed()

        state = self.tm.get_state()
        self.assertEqual(len(state['traps']), 2)
        self.assertIn('phase_mask', state)


class TestTrapManagerGetState(unittest.TestCase):
    """Test state serialization."""

    def test_empty_state(self):
        """Empty manager should return valid state."""
        tm = TrapManager(resolution=(64, 64))
        state = tm.get_state()
        self.assertIn('traps', state)
        self.assertIn('phase_mask', state)
        self.assertEqual(len(state['traps']), 0)

    def test_state_with_traps(self):
        """State should include trap data after creation."""
        tm = TrapManager(resolution=(64, 64))
        tm.generator.add_trap(0.1, 0.2)
        tm.generator.calculate_phase_mask()
        state = tm.get_state()
        self.assertEqual(len(state['traps']), 1)
        self.assertAlmostEqual(state['traps'][0]['x'], 0.1, places=5)
        self.assertAlmostEqual(state['traps'][0]['y'], 0.2, places=5)
        self.assertGreater(state['traps'][0]['intensity'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
