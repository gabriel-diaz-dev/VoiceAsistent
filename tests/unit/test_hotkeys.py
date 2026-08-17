"""Unit tests para voiceasistent.hotkeys."""
import unittest

from voiceasistent.hotkeys import HoldGate, normalize_key


class NormalizeKeyTests(unittest.TestCase):
    def test_upper_function_key(self):
        self.assertEqual(normalize_key("F9"), "f9")

    def test_known_names_kept(self):
        for name in ("ctrl", "alt", "shift", "space", "esc", "tab", "enter"):
            self.assertEqual(normalize_key(name), name)

    def test_unknown_returns_none(self):
        self.assertIsNone(normalize_key("hyper"))
        self.assertIsNone(normalize_key("f99"))


class HoldGateSingleKeyTests(unittest.TestCase):
    def setUp(self):
        self.gate = HoldGate(("f9",))

    def test_press_starts_hold(self):
        self.assertEqual(self.gate.press("f9"), "start")
        self.assertTrue(self.gate.is_holding)

    def test_autorepeat_ignored(self):
        self.gate.press("f9")
        self.assertIsNone(self.gate.press("f9"))
        self.assertTrue(self.gate.is_holding)

    def test_release_stops_hold(self):
        self.gate.press("f9")
        self.assertEqual(self.gate.release("f9"), "stop")
        self.assertFalse(self.gate.is_holding)

    def test_double_release_ignored(self):
        self.gate.press("f9")
        self.gate.release("f9")
        self.assertIsNone(self.gate.release("f9"))

    def test_unknown_key_ignored(self):
        self.assertIsNone(self.gate.press("a"))
        self.assertIsNone(self.gate.release("a"))


class HoldGateComboTests(unittest.TestCase):
    def setUp(self):
        self.gate = HoldGate(("ctrl", "f9"))

    def test_start_only_when_all_held(self):
        self.assertIsNone(self.gate.press("ctrl"))
        self.assertEqual(self.gate.press("f9"), "start")
        self.assertTrue(self.gate.is_holding)

    def test_stop_when_any_released(self):
        self.gate.press("ctrl")
        self.gate.press("f9")
        self.assertEqual(self.gate.release("f9"), "stop")
        self.assertFalse(self.gate.is_holding)

    def test_release_before_full_hold_is_ignored(self):
        self.gate.press("ctrl")
        self.assertIsNone(self.gate.release("ctrl"))


if __name__ == "__main__":
    unittest.main()
