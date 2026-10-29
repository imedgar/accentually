"""Regression checks for native/UIA caret positioning and delayed results."""
import json
import unittest
from unittest.mock import Mock, patch

from core.accessibility_caret import caret_from_range, find_caret
from core.caret_detector import get_accessible_caret_position, position_above_caret
from core.keyboard_hook import KeyboardManager


class CaretPositionTests(unittest.TestCase):
    def test_collapsed_range_uses_exact_caret_bounds(self):
        text_range = Mock()
        text_range.GetBoundingRectangles.return_value = (300, 400, 0, 20)
        self.assertEqual(caret_from_range(text_range), (300, 400, 20))
        text_range.Clone.assert_not_called()

    def test_wrapped_line_start_uses_following_character(self):
        text_range = Mock()
        text_range.GetBoundingRectangles.return_value = ()
        following = text_range.Clone.return_value
        following.MoveEndpointByUnit.return_value = 1
        following.GetBoundingRectangles.return_value = (100, 420, 9, 20)
        self.assertEqual(caret_from_range(text_range), (100, 420, 20))
        following.MoveEndpointByUnit.assert_called_once_with(1, 0, 1)

    def test_document_end_uses_previous_character_right_edge(self):
        text_range = Mock()
        text_range.GetBoundingRectangles.return_value = ()
        following = Mock()
        following.MoveEndpointByUnit.return_value = 0
        preceding = Mock()
        preceding.MoveEndpointByUnit.return_value = -1
        preceding.GetBoundingRectangles.return_value = (290, 400, 10, 20)
        text_range.Clone.side_effect = [following, preceding]
        self.assertEqual(caret_from_range(text_range), (300, 400, 20))

    def test_active_caret_pattern_is_preferred_to_selection(self):
        automation, uia = Mock(), Mock()
        element = automation.GetFocusedElement.return_value
        caret_range = Mock()
        caret_range.GetBoundingRectangles.return_value = (300, 400, 0, 20)
        element.GetCurrentPattern.return_value.QueryInterface.return_value.GetCaretRange.return_value = (True, caret_range)
        self.assertEqual(find_caret(automation, uia), (300, 400, 20))
        element.GetCurrentPattern.assert_called_once_with(uia.UIA_TextPattern2Id)

    def test_pattern_can_be_on_focused_elements_parent(self):
        automation, uia = Mock(), Mock()
        child = automation.GetFocusedElement.return_value
        child.GetCurrentPattern.side_effect = OSError('pattern not supported')
        parent = automation.ControlViewWalker.GetParentElement.return_value
        caret_range = Mock()
        caret_range.GetBoundingRectangles.return_value = (300, 400, 0, 20)
        parent.GetCurrentPattern.return_value.QueryInterface.return_value.GetCaretRange.return_value = (True, caret_range)
        self.assertEqual(find_caret(automation, uia), (300, 400, 20))

    def test_popup_stays_on_carets_monitor_at_monitor_boundary(self):
        with patch('core.caret_detector.get_work_area_for_point', return_value=(1920, 0, 3840, 1040)) as area:
            self.assertEqual(position_above_caret(1930, 500, 20, 300, 70), (1928, 420))
            area.assert_called_once_with(1930, 500)

    def test_popup_moves_below_caret_when_no_room_above(self):
        with patch('core.caret_detector.get_work_area_for_point', return_value=(-1920, 0, 0, 1040)):
            self.assertEqual(position_above_caret(-500, 20, 20, 300, 70), (-650, 50))

    def test_accessibility_result_rejected_after_window_switch(self):
        result = Mock(returncode=0, stdout=json.dumps([300, 400, 20]))
        with patch('core.caret_detector.subprocess.run', return_value=result), \
             patch('core.caret_detector.user32.GetForegroundWindow', return_value=222):
            self.assertIsNone(get_accessible_caret_position(111))

    def test_native_position_is_not_overwritten_by_async_probe(self):
        config = Mock(pause_in_fullscreen=False)
        config.get_mappings_for_key.return_value = ['a']
        overlay = Mock()
        overlay.show.return_value = True
        manager = KeyboardManager(None, config, overlay)
        manager.currently_held_vk = ord('A')
        with patch('core.keyboard_hook.threading.Thread') as thread:
            manager._show_overlay_on_ui_thread('a', False)
            thread.assert_not_called()

    def test_queued_accessibility_result_cannot_move_a_different_window(self):
        config = Mock(pause_in_fullscreen=False)
        config.get_mappings_for_key.return_value = ['a']
        overlay = Mock()
        overlay.show.return_value = False
        manager = KeyboardManager(None, config, overlay)
        manager.currently_held_vk = ord('A')
        with patch('core.keyboard_hook.user32.GetForegroundWindow', return_value=111), \
             patch('core.keyboard_hook.get_accessible_caret_position', return_value=(300, 400, 20)), \
             patch('core.keyboard_hook.threading.Thread') as thread:
            manager._show_overlay_on_ui_thread('a', False)
            overlay.on_select_callback = overlay.show.call_args.args[1]
            thread.call_args.kwargs['target']()
        action, args = manager._ui_queue.get_nowait()
        with patch('core.keyboard_hook.user32.GetForegroundWindow', return_value=222):
            action(*args)
        overlay.move_above_caret.assert_not_called()


if __name__ == '__main__':
    unittest.main()
