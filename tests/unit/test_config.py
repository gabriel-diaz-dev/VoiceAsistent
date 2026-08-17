"""Unit tests para voiceasistent.config."""
import tempfile
import unittest
from pathlib import Path

from voiceasistent.config import (
    AppConfig,
    ConfigError,
    load_config,
    parse_hotkey,
    write_default_config,
)


class ParseHotkeyTests(unittest.TestCase):
    def test_single_key_normalized_lowercase(self):
        self.assertEqual(parse_hotkey("F9"), ("f9",))

    def test_combo_preserves_order(self):
        self.assertEqual(parse_hotkey("ctrl+alt+space"), ("ctrl", "alt", "space"))

    def test_combo_with_spaces_is_accepted(self):
        self.assertEqual(parse_hotkey(" ctrl + f9 "), ("ctrl", "f9"))

    def test_function_keys_known(self):
        self.assertEqual(parse_hotkey("f12"), ("f12",))

    def test_unknown_function_key_rejected(self):
        with self.assertRaises(ConfigError):
            parse_hotkey("f99")

    def test_empty_rejected(self):
        with self.assertRaises(ConfigError):
            parse_hotkey("")

    def test_unknown_name_rejected(self):
        with self.assertRaises(ConfigError):
            parse_hotkey("hyper")

    def test_too_many_keys_rejected(self):
        with self.assertRaises(ConfigError):
            parse_hotkey("ctrl+alt+shift+x")


class LoadConfigTests(unittest.TestCase):
    def test_missing_file_returns_defaults(self):
        config = load_config(Path("/nonexistent/voiceasistent.toml"))
        self.assertEqual(config.hotkey, "f9")
        self.assertEqual(config.model, "base")
        self.assertEqual(config.language, "auto")
        self.assertEqual(config.device, "auto")

    def test_file_overrides_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                "[speech]\nmodel = \"small\"\nlanguage = \"es\"\n"
                "[hotkey]\nkey = \"ctrl+f9\"\n",
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertEqual(config.model, "small")
            self.assertEqual(config.language, "es")
            self.assertEqual(config.hotkey, "ctrl+f9")

    def test_invalid_model_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("[speech]\nmodel = \"huge\"\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_invalid_device_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("[speech]\ndevice = \"vulkan\"\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_invalid_output_mode_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("[output]\nmode = \"email\"\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_negative_max_recording_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("[output]\nmax_recording_seconds = -5\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)


class WriteDefaultConfigTests(unittest.TestCase):
    def test_round_trip_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            write_default_config(path)
            config = load_config(path)
            self.assertIsInstance(config, AppConfig)
            self.assertEqual(config.hotkey, "f9")
            self.assertEqual(config.model, "base")
            self.assertFalse(config.ollama_enabled)


if __name__ == "__main__":
    unittest.main()
