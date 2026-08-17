"""Unit tests para voiceasistent.backend."""
import unittest

from voiceasistent.backend import decide_backend
from voiceasistent.config import AppConfig


def make_config(**overrides):
    values = {
        "hotkey": "f9",
        "model": "base",
        "language": "auto",
        "device": "auto",
        "compute_type": "default",
        "cpu_compute_type": "int8",
        "output_mode": "paste",
        "keep_clipboard": True,
        "paste_delay_ms": 100,
        "max_recording_seconds": 60.0,
        "input_device_index": -1,
        "ollama_enabled": False,
        "ollama_url": "http://127.0.0.1:11434",
        "ollama_model": "",
        "ollama_timeout_seconds": 10.0,
    }
    values.update(overrides)
    return AppConfig(**values)


class DecideBackendTests(unittest.TestCase):
    def test_auto_with_cuda_selects_cuda(self):
        decision = decide_backend(make_config(), cuda_available=True)
        self.assertEqual(decision.device, "cuda")
        self.assertTrue(decision.cuda_attempted)
        self.assertEqual(decision.compute_type, "default")

    def test_auto_without_cuda_falls_back_to_cpu_int8(self):
        decision = decide_backend(make_config(), cuda_available=False)
        self.assertEqual(decision.device, "cpu")
        self.assertEqual(decision.compute_type, "int8")
        self.assertTrue(any("fallback" in note.lower() for note in decision.notes))

    def test_auto_with_unknown_cuda_treats_as_cpu(self):
        decision = decide_backend(make_config(), cuda_available=None)
        self.assertEqual(decision.device, "cpu")

    def test_explicit_cpu_respected(self):
        decision = decide_backend(make_config(device="cpu"), cuda_available=True)
        self.assertEqual(decision.device, "cpu")
        self.assertFalse(decision.cuda_attempted)

    def test_explicit_cuda_without_support_warns(self):
        decision = decide_backend(make_config(device="cuda"), cuda_available=False)
        self.assertEqual(decision.device, "cuda")
        self.assertTrue(decision.cuda_attempted)
        self.assertTrue(any("no" in note.lower() for note in decision.notes))


if __name__ == "__main__":
    unittest.main()
