"""Unit tests para la CLI."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from voiceasistent import cli
from voiceasistent.config import AppConfig


class ParserTests(unittest.TestCase):
    def test_commands_exist(self):
        parser = cli.build_parser()
        args = parser.parse_args(["run", "--config", "custom.toml"])
        self.assertEqual(args.command, "run")
        self.assertEqual(args.config, "custom.toml")

    def test_default_command_is_run(self):
        parser = cli.build_parser()
        args = parser.parse_args([])
        self.assertIsNone(args.command)


class CommandTests(unittest.TestCase):
    def test_config_init_writes_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("voiceasistent.cli.Path") as path_class:
                path_class.return_value = Path(tmp) / "config.toml"
                result = cli.cmd_config_init(None)
            self.assertEqual(result, 0)
            self.assertTrue((Path(tmp) / "config.toml").exists())

    def test_config_init_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("voiceasistent.cli.Path") as path_class:
                path_class.return_value = Path(tmp) / "config.toml"
                (Path(tmp) / "config.toml").write_text("x", encoding="utf-8")
                result = cli.cmd_config_init(None)
            self.assertEqual(result, 1)

    @patch("voiceasistent.cli.PyAudioMicrophones")
    def test_mic_command_reports_failure(self, microphones):
        microphones.return_value.list_input_devices.side_effect = RuntimeError("sin audio")
        result = cli.cmd_mic(None)
        self.assertEqual(result, 1)

    @patch("voiceasistent.cli.PyAudioMicrophones")
    def test_mic_command_lists_devices(self, microphones):
        microphones.return_value.list_input_devices.return_value = [
            {"index": 0, "name": "Microfono", "default_sample_rate": 16000}
        ]
        result = cli.cmd_mic(None)
        self.assertEqual(result, 0)

    def test_doctor_prints_instructions(self):
        self.assertEqual(cli.cmd_doctor(None), 0)

    @patch("voiceasistent.cli.PynputHotkeyListener")
    @patch("voiceasistent.cli.EventRunner")
    @patch("voiceasistent.cli.RealtimeSttEngine")
    @patch("voiceasistent.cli.detect_cuda", return_value=False)
    @patch("voiceasistent.cli.load_config")
    def test_run_wires_flow_and_stops_cleanly(
        self, load_config, _detect_cuda, engine_class, runner_class, listener_class
    ):
        config = AppConfig(hotkey="f9")
        load_config.return_value = config
        runner = runner_class.return_value
        runner.run_forever.side_effect = KeyboardInterrupt
        engine = engine_class.return_value

        args = cli.build_parser().parse_args(["run"])
        with patch("builtins.print"):
            result = cli.cmd_run(args)

        self.assertEqual(result, 0)
        engine.shutdown.assert_called_once()
        listener_class.return_value.start.assert_called_once()
        listener_class.return_value.stop.assert_called_once()

    @patch("voiceasistent.cli.PyAudioMicrophones")
    def test_run_list_mics(self, microphones):
        microphones.return_value.list_input_devices.return_value = []
        args = cli.build_parser().parse_args(["run", "--list-mics"])
        with patch("builtins.print"):
            result = cli.cmd_run(args)
        self.assertEqual(result, 1)


class EngineFallbackTests(unittest.TestCase):
    def test_cuda_failure_falls_back_to_cpu(self):
        from voiceasistent.backend import BackendDecision

        with patch("voiceasistent.cli.RealtimeSttEngine") as engine_class:
            engine_class.side_effect = [RuntimeError("cuda"), object()]
            engine = cli._create_engine_with_fallback(
                AppConfig(hotkey="f9"),
                BackendDecision(
                    device="cuda",
                    compute_type="float16",
                    cuda_attempted=True,
                    notes=(),
                ),
            )
        self.assertIsNotNone(engine)
        self.assertEqual(engine_class.call_count, 2)
        self.assertEqual(engine_class.call_args_list[1][0][1].device, "cpu")

    def test_cpu_failure_propagates(self):
        from voiceasistent.backend import BackendDecision

        with patch("voiceasistent.cli.RealtimeSttEngine", side_effect=RuntimeError("cpu")):
            with self.assertRaises(RuntimeError):
                cli._create_engine_with_fallback(
                    AppConfig(hotkey="f9"),
                    BackendDecision(
                        device="cpu",
                        compute_type="int8",
                        cuda_attempted=False,
                        notes=(),
                    ),
                )


class MainDispatchTests(unittest.TestCase):
    @patch("voiceasistent.cli.cmd_config_init", return_value=0)
    def test_main_dispatches_config_init(self, cmd):
        self.assertEqual(cli.main(["config-init"]), 0)
        cmd.assert_called_once()

    @patch("voiceasistent.cli.cmd_doctor", return_value=0)
    def test_main_dispatches_doctor(self, cmd):
        self.assertEqual(cli.main(["doctor"]), 0)
        cmd.assert_called_once()


if __name__ == "__main__":
    unittest.main()
