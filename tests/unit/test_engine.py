"""Unit tests para voiceasistent.engine (sin importar RealtimeSTT)."""

import unittest

from voiceasistent.backend import BackendDecision
from voiceasistent.config import AppConfig
from voiceasistent.engine import build_recorder_kwargs


class BuildRecorderKwargsTests(unittest.TestCase):
    def setUp(self):
        self.config = AppConfig(hotkey="f9")

    def test_maps_model_device_and_compute(self):
        kwargs = build_recorder_kwargs(
            self.config,
            BackendDecision(device="cpu", compute_type="int8", cuda_attempted=False, notes=()),
        )
        self.assertEqual(kwargs["model"], "base")
        self.assertEqual(kwargs["device"], "cpu")
        self.assertEqual(kwargs["compute_type"], "int8")

    def test_auto_language_maps_to_empty(self):
        kwargs = build_recorder_kwargs(
            self.config,
            BackendDecision(device="cpu", compute_type="int8", cuda_attempted=False, notes=()),
        )
        self.assertEqual(kwargs["language"], "")

    def test_explicit_language_preserved(self):
        config = AppConfig(hotkey="f9", language="es")
        kwargs = build_recorder_kwargs(
            config,
            BackendDecision(device="cpu", compute_type="int8", cuda_attempted=False, notes=()),
        )
        self.assertEqual(kwargs["language"], "es")

    def test_beam_size_defaults_to_one(self):
        kwargs = build_recorder_kwargs(
            self.config,
            BackendDecision(device="cpu", compute_type="int8", cuda_attempted=False, notes=()),
        )
        self.assertEqual(kwargs["beam_size"], 1)

    def test_beam_size_from_config(self):
        config = AppConfig(hotkey="f9", beam_size=5)
        kwargs = build_recorder_kwargs(
            config,
            BackendDecision(device="cpu", compute_type="int8", cuda_attempted=False, notes=()),
        )
        self.assertEqual(kwargs["beam_size"], 5)

    def test_realtime_transcription_disabled(self):
        kwargs = build_recorder_kwargs(
            self.config,
            BackendDecision(device="cpu", compute_type="int8", cuda_attempted=False, notes=()),
        )
        self.assertFalse(kwargs["enable_realtime_transcription"])

    def test_default_input_device_omitted(self):
        kwargs = build_recorder_kwargs(
            self.config,
            BackendDecision(device="cpu", compute_type="int8", cuda_attempted=False, notes=()),
        )
        self.assertNotIn("input_device_index", kwargs)

    def test_explicit_input_device_included(self):
        config = AppConfig(hotkey="f9", input_device_index=2)
        kwargs = build_recorder_kwargs(
            config,
            BackendDecision(device="cpu", compute_type="int8", cuda_attempted=False, notes=()),
        )
        self.assertEqual(kwargs["input_device_index"], 2)


if __name__ == "__main__":
    unittest.main()
