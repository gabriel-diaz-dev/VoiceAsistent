"""Unit tests para voiceasistent.app."""
import unittest

from voiceasistent.app import PushToTalkApp
from voiceasistent.hotkeys import HoldGate
from voiceasistent.output import OutputWriter


class FakeEngine:
    def __init__(self):
        self.started = 0
        self.stopped = 0
        self.shutdown_calls = 0
        self.text_value = "hola"
        self.detected_language = "es"

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1

    def text(self):
        return self.text_value

    def shutdown(self):
        self.shutdown_calls += 1


class FakeClipboard:
    def __init__(self):
        self.text = ""

    def copy(self, text):
        self.text = text

    def paste(self):
        return self.text


class FakeKeyboard:
    def __init__(self):
        self.paste_calls = 0

    def hotkey_paste(self):
        self.paste_calls += 1

    def type_text(self, text):
        pass


class PushToTalkAppTests(unittest.TestCase):
    def setUp(self):
        self.engine = FakeEngine()
        self.gate = HoldGate(("f9",))
        self.clipboard = FakeClipboard()
        self.writer = OutputWriter(self.clipboard, FakeKeyboard(), mode="paste")
        self.app = PushToTalkApp(
            engine=self.engine,
            gate=self.gate,
            output=self.writer,
            max_recording_seconds=30.0,
        )

    def test_press_starts_engine_once(self):
        self.app.on_key_press("f9")
        self.app.on_key_press("f9")
        self.assertEqual(self.engine.started, 1)

    def test_release_transcribes_and_delivers(self):
        self.app.on_key_press("f9")
        result = self.app.on_key_release("f9")
        self.assertEqual(self.engine.stopped, 1)
        self.assertEqual(result.status, "pasted")
        self.assertEqual(self.clipboard.text, "hola")

    def test_release_without_press_ignored(self):
        result = self.app.on_key_release("f9")
        self.assertIsNone(result)
        self.assertEqual(self.engine.stopped, 0)

    def test_timeout_stops_and_delivers(self):
        self.app.on_key_press("f9")
        result = self.app.on_recording_timeout()
        self.assertEqual(self.engine.stopped, 1)
        self.assertEqual(result.status, "pasted")

    def test_unknown_key_ignored(self):
        self.app.on_key_press("a")
        self.assertFalse(self.gate.is_holding)


if __name__ == "__main__":
    unittest.main()
