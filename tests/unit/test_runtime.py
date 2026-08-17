"""Unit tests para voiceasistent.runtime (bucle de eventos y teclas canonicas)."""

import unittest
from unittest.mock import patch

from voiceasistent.app import PushToTalkApp
from voiceasistent.hotkeys import HoldGate
from voiceasistent.output import OutputWriter
from voiceasistent.runtime import EventRunner, canonical_key


class FakeEngine:
    def __init__(self):
        self.started = 0
        self.stopped = 0
        self.detected_language = None

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1

    def text(self):
        return "texto"

    def shutdown(self):
        pass


class FakeClipboard:
    def copy(self, text):
        pass

    def paste(self):
        return ""


class FakeKeyboard:
    def hotkey_paste(self):
        pass

    def type_text(self, text):
        pass


def build_runner(max_seconds=10.0):
    engine = FakeEngine()
    app = PushToTalkApp(
        engine=engine,
        gate=HoldGate(("f9",)),
        output=OutputWriter(FakeClipboard(), FakeKeyboard(), mode="paste"),
        max_recording_seconds=max_seconds,
    )
    return EventRunner(app, max_seconds), engine


class CanonicalKeyTests(unittest.TestCase):
    def test_name_falls_back_to_lower_name(self):
        key = type("Key", (), {"name": "f9", "char": None})()
        self.assertEqual(canonical_key(key), "f9")

    def test_char_preferred(self):
        key = type("Key", (), {"char": "a", "name": None})()
        self.assertEqual(canonical_key(key), "a")

    def test_none_key(self):
        self.assertIsNone(canonical_key(None))

    def test_unknown_object(self):
        self.assertIsNone(canonical_key(object()))


class EventRunnerTests(unittest.TestCase):
    def test_press_starts_engine(self):
        runner, engine = build_runner()
        runner.push_press("f9")
        runner.process_one(timeout=0)
        self.assertEqual(engine.started, 1)

    def test_release_stops_and_delivers(self):
        runner, engine = build_runner()
        runner.push_press("f9")
        runner.process_one(timeout=0)
        runner.push_release("f9")
        runner.process_one(timeout=0)
        self.assertEqual(engine.stopped, 1)

    def test_no_events_returns_false(self):
        runner, _ = build_runner()
        self.assertFalse(runner.process_one(timeout=0))

    @patch("voiceasistent.runtime.time.monotonic", side_effect=[100.0, 115.0])
    def test_timeout_stops_recording(self, _clock):
        runner, engine = build_runner(max_seconds=10.0)
        runner.push_press("f9")
        runner.process_one(timeout=0)
        self.assertFalse(runner.process_one(timeout=0))
        self.assertEqual(engine.stopped, 1)


if __name__ == "__main__":
    unittest.main()
