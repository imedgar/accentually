"""
Comprehensive test suite for QuickAccent.
Verifies character mappings, Latvian diacritic positioning, Win32 structures,
and component initialization.
"""
import unittest
import sys
import os
import ctypes
from unittest.mock import patch, Mock

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_manager import ConfigManager
from core.key_injector import INPUT, KEYBDINPUT, EXTRA_INFO_MAGIC
from core.caret_detector import clamp_to_screen, get_work_area_for_point
from core.key_injector import inject_replacement, user32
from core.keyboard_hook import KeyboardManager, KBDLLHOOKSTRUCT, WM_KEYDOWN

class TestQuickAccent(unittest.TestCase):
    def setUp(self):
        self.cm = ConfigManager()
        self.cm.save = Mock(return_value=True)

    def test_latvian_characters_position_one(self):
        """Test that all 13 Latvian diacritic letters are in position #1."""
        self.cm.active_profile_name = "latvian_first"
        latvian_expected = {
            'a': ('ā', 'Ā'),
            'c': ('č', 'Č'),
            'e': ('ē', 'Ē'),
            'g': ('ģ', 'Ģ'),
            'i': ('ī', 'Ī'),
            'k': ('ķ', 'Ķ'),
            'l': ('ļ', 'Ļ'),
            'n': ('ņ', 'Ņ'),
            'o': ('ō', 'Ō'),
            'r': ('ŗ', 'Ŗ'),
            's': ('š', 'Š'),
            'u': ('ū', 'Ū'),
            'z': ('ž', 'Ž'),
        }

        for base_key, (expected_lower, expected_upper) in latvian_expected.items():
            lower_accents = self.cm.get_mappings_for_key(base_key, is_upper=False)
            upper_accents = self.cm.get_mappings_for_key(base_key, is_upper=True)

            self.assertTrue(len(lower_accents) > 0, f"Missing accents for '{base_key}'")
            self.assertEqual(lower_accents[0], expected_lower,
                             f"Key '{base_key}': Expected #1 to be '{expected_lower}', got '{lower_accents[0]}'")
            self.assertEqual(upper_accents[0], expected_upper,
                             f"Key '{base_key.upper()}': Expected #1 to be '{expected_upper}', got '{upper_accents[0]}'")

    def test_latvian_exclusive_profile(self):
        """Test that 'latvian_only' profile contains only the Latvian diacritics."""
        self.cm.active_profile_name = "latvian_only"
        self.assertEqual(self.cm.get_mappings_for_key('a'), ['ā'])
        self.assertEqual(self.cm.get_mappings_for_key('c'), ['č'])
        self.assertEqual(self.cm.get_mappings_for_key('e'), ['ē'])
        self.assertEqual(self.cm.get_mappings_for_key('s'), ['š'])
        self.assertEqual(self.cm.get_mappings_for_key('z'), ['ž'])

    def test_win32_input_structure_size_and_alignment(self):
        """Ensure Win64 binary structure size compatibility."""
        self.assertEqual(ctypes.sizeof(KEYBDINPUT), 24, "KEYBDINPUT must be 24 bytes on Win64")
        self.assertEqual(ctypes.sizeof(INPUT), 40, "INPUT structure must be 40 bytes on Win64")
        self.assertEqual(INPUT.ki.offset, 8, "Union inside INPUT must start at offset 8 on Win64")

    def test_caret_clamp_to_screen(self):
        """Ensure clamping keeps popup on screen."""
        work_left, work_top, work_right, work_bottom = get_work_area_for_point(100, 100)
        
        # Test negative coordinates
        clamped_x, clamped_y = clamp_to_screen(-100, -100, 200, 60)
        self.assertGreaterEqual(clamped_x, work_left)
        self.assertGreaterEqual(clamped_y, work_top)
        
        # Test coordinates beyond monitor
        clamped_x, clamped_y = clamp_to_screen(99999, 99999, 200, 60)
        self.assertLessEqual(clamped_x + 200, work_right)
        self.assertLessEqual(clamped_y + 60, work_bottom)

    def test_profiles_available(self):
        """Verify standard profiles exist in config."""
        profiles = self.cm.get_profiles()
        self.assertIn("latvian_first", profiles)
        self.assertIn("latvian_only", profiles)
        self.assertIn("international", profiles)
        self.assertIn("custom", profiles)

    def test_replacement_passes_input_array_to_sendinput(self):
        with patch('core.key_injector.ensure_desktop_access'), patch.object(user32, 'SendInput', return_value=4) as send:
            self.assertTrue(inject_replacement('ā'))
            events = send.call_args.args[1]
            self.assertEqual(events[0].ki.wVk, 8)
            self.assertEqual(events[2].ki.wScan, ord('ā'))

    def test_held_key_repeat_does_not_dismiss_popup(self):
        manager = KeyboardManager(None, Mock(pause_in_fullscreen=False), None)
        manager.is_popup_active = True
        manager.currently_held_vk = ord('A')
        event = KBDLLHOOKSTRUCT(vkCode=ord('A'))
        self.assertEqual(manager._hook_callback(0, WM_KEYDOWN, ctypes.addressof(event)), 1)
        self.assertTrue(manager.is_popup_active)

    def test_fullscreen_pause_passes_key_through(self):
        manager = KeyboardManager(None, Mock(pause_in_fullscreen=True), None)
        event = KBDLLHOOKSTRUCT(vkCode=ord('A'))
        with patch('core.keyboard_hook.is_foreground_fullscreen', return_value=True), \
             patch('core.keyboard_hook.user32.CallNextHookEx', return_value=0):
            self.assertEqual(manager._hook_callback(0, WM_KEYDOWN, ctypes.addressof(event)), 0)
        self.assertIsNone(manager.currently_held_vk)

if __name__ == '__main__':
    unittest.main()
