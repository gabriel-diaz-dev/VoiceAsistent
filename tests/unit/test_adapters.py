"""Tests de los adaptadores perezosos con modulos falsos inyectados."""
import sys
import types
import unittest
from unittest.mock import MagicMock

from voiceasistent.app import PushToTalkApp
from voiceasistent.backend import BackendDecision
from voiceasistent.config import AppConfig
from voiceasistent.engine import RealtimeSttEngine
from voiceasistent.hotkeys import HoldGate
from voiceasistent.output import OutputWriter
from voiceasistent.runtime import (
    EventRunner,
    PyAudioMicrophones,
    PynputHotkeyListener,
    PynputKeyboard,
    PyperclipClipboard,
)


def install_fake_module(name, attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


class RealtimeSttEngineTests(unittest.TestCase):
    def setUp(self):
        recorder = MagicMock()
        recorder.text.return_value = "hola"
        self.recorder = recorder
        install_fake_module(
            "RealtimeSTT",
            {"AudioToTextRecorder": MagicMock(return_value=recorder)},
        )

    def tearDown(self):
        sys.modules.pop("RealtimeSTT", None)

    def make_engine(self):
        return RealtimeSttEngine(
            AppConfig(hotkey="f9"),
            BackendDecision(device="cpu", compute_type="int8", cuda_attempted=False, notes=()),
        )

    def test_start_stop_delegate(self):
        engine = self.make_engine()
        engine.start()
        engine.stop()
        self.recorder.start.assert_called_once()
        self.recorder.stop.assert_called_once()

    def test_text_returns_and_captures_language(self):
        self.recorder.detected_language = "es"
        engine = self.make_engine()
        self.assertEqual(engine.text(), "hola")
        self.assertEqual(engine.detected_language, "es")

    def test_shutdown_delegates(self):
        engine = self.make_engine()
        engine.shutdown()
        self.recorder.shutdown.assert_called_once()


class RuntimeAdapterTests(unittest.TestCase):
    def tearDown(self):
        for name in ("pyperclip", "pynput", "pynput.keyboard", "pyaudio"):
            sys.modules.pop(name, None)

    def test_clipboard_adapter(self):
        pyperclip = install_fake_module("pyperclip", {"copy": MagicMock(), "paste": MagicMock()})
        adapter = PyperclipClipboard()
        adapter.copy("texto")
        adapter.paste()
        pyperclip.copy.assert_called_once_with("texto")
        pyperclip.paste.assert_called_once()

    def test_keyboard_adapter_paste(self):
        controller = MagicMock()
        key_module = MagicMock()
        key_module.Key.ctrl = "ctrl"
        pynput = types.ModuleType("pynput")
        pynput.keyboard = key_module
        key_module.Controller.return_value = controller
        sys.modules["pynput"] = pynput
        sys.modules["pynput.keyboard"] = key_module

        adapter = PynputKeyboard()
        adapter.hotkey_paste()
        controller.press.assert_any_call("v")
        controller.release.assert_any_call("v")

    def test_keyboard_adapter_type(self):
        controller = MagicMock()
        key_module = MagicMock()
        key_module.Controller.return_value = controller
        pynput = types.ModuleType("pynput")
        pynput.keyboard = key_module
        sys.modules["pynput"] = pynput
        sys.modules["pynput.keyboard"] = key_module

        adapter = PynputKeyboard()
        adapter.type_text("hola")
        controller.type.assert_called_once_with("hola")

    def test_microphone_listing(self):
        audio_instance = MagicMock()
        audio_instance.get_device_count.return_value = 1
        audio_instance.get_device_info_by_index.return_value = {
            "maxInputChannels": 2,
            "name": "Microfono",
            "defaultSampleRate": 16000,
        }
        pyaudio = install_fake_module(
            "pyaudio", {"PyAudio": MagicMock(return_value=audio_instance)}
        )

        devices = PyAudioMicrophones().list_input_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["name"], "Microfono")
        pyaudio.PyAudio.return_value.terminate.assert_called_once()

    def test_hotkey_listener_starts_and_stops(self):
        listener_instance = MagicMock()
        key_module = MagicMock()
        key_module.Listener.return_value = listener_instance
        pynput = types.ModuleType("pynput")
        pynput.keyboard = key_module
        sys.modules["pynput"] = pynput
        sys.modules["pynput.keyboard"] = key_module

        runner = EventRunner(
            PushToTalkApp(
                MagicMock(),
                HoldGate(("f9",)),
                OutputWriter(MagicMock(), MagicMock(), mode="paste"),
                max_recording_seconds=30.0,
            ),
            30.0,
        )
        listener = PynputHotkeyListener(runner)
        listener.start()
        key_module.Listener.assert_called_once()
        listener_instance.start.assert_called_once()
        listener.stop()
        listener_instance.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
