"""Interfaz de linea de comandos de VoiceAsistent."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .app import PushToTalkApp
from .backend import BackendDecision, decide_backend, detect_cuda
from .config import ConfigError, load_config, write_default_config
from .engine import RealtimeSttEngine
from .hotkeys import HoldGate
from .output import OutputWriter
from .runtime import (
    EventRunner,
    PyAudioMicrophones,
    PynputHotkeyListener,
    PynputKeyboard,
    PyperclipClipboard,
)

logger = logging.getLogger("voiceasistent")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voiceasistent",
        description="Dictado por voz push-to-talk con transcripcion local.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Inicia el asistente push-to-talk")
    run_parser.add_argument("--config", default="config.toml", help="Ruta del archivo TOML")
    run_parser.add_argument("--list-mics", action="store_true", help="Muestra microfonos y sale")

    subparsers.add_parser("mic", help="Lista los microfonos disponibles")
    subparsers.add_parser("config-init", help="Escribe config.toml con los valores por defecto")
    subparsers.add_parser("doctor", help="Indicaciones para ejecutar el diagnostico de Windows")
    return parser


def _create_engine_with_fallback(config, decision: BackendDecision) -> RealtimeSttEngine:
    try:
        return RealtimeSttEngine(config, decision)
    except Exception as exc:
        if decision.device != "cuda":
            raise
        logger.warning("CUDA fallo al inicializar (%s); usando CPU int8.", exc)
        cpu_decision = BackendDecision(
            device="cpu",
            compute_type=config.cpu_compute_type,
            cuda_attempted=True,
            notes=("Fallback tras fallo de inicializacion CUDA.",),
        )
        return RealtimeSttEngine(config, cpu_decision)


def cmd_run(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"Configuracion invalida: {exc}")
        return 2

    if args.list_mics:
        return _print_microphones()

    print(f"Modelo: {config.model} | idioma: {config.language} | tecla: {config.hotkey}")
    decision = decide_backend(config, cuda_available=detect_cuda())
    for note in decision.notes:
        print(f"- {note}")

    engine = _create_engine_with_fallback(config, decision)
    output = OutputWriter(
        PyperclipClipboard(),
        PynputKeyboard(),
        mode=config.output_mode,
        keep_clipboard=config.keep_clipboard,
        paste_delay_ms=config.paste_delay_ms,
    )
    app = PushToTalkApp(
        engine=engine,
        gate=HoldGate(config.hotkey_keys),
        output=output,
        max_recording_seconds=config.max_recording_seconds,
    )
    runner = EventRunner(app, config.max_recording_seconds)
    listener = PynputHotkeyListener(runner)

    print("Mantén la tecla push-to-talk, habla y suéltala. Ctrl+C para salir.")
    try:
        listener.start()
        runner.run_forever()
    except KeyboardInterrupt:
        print("\nSaliendo...")
    finally:
        listener.stop()
        app.shutdown()
    return 0


def _print_microphones() -> int:
    try:
        devices = PyAudioMicrophones().list_input_devices()
    except Exception as exc:
        print(f"No se pudieron listar los microfonos: {exc}")
        return 1
    if not devices:
        print("No se detectaron microfonos.")
        return 1
    for device in devices:
        print(f"[{device['index']}] {device['name']} ({device['default_sample_rate']} Hz)")
    return 0


def cmd_mic(_args: argparse.Namespace) -> int:
    return _print_microphones()


def cmd_config_init(_args: argparse.Namespace) -> int:
    target = Path("config.toml")
    if target.exists():
        print(f"{target} ya existe; no se sobrescribe.")
        return 1
    write_default_config(target)
    print(f"Configuracion de ejemplo escrita en {target}")
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    print("Ejecuta en el equipo Windows, desde PowerShell:")
    print("  powershell -ExecutionPolicy Bypass -File scripts\\doctor_windows.ps1")
    print("O si PowerShell 7 esta instalado:")
    print("  pwsh -File scripts/doctor_windows.ps1")
    print("Copia el bloque JSON resultante y pégalo en la conversacion.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    command = args.command or "run"
    if command == "run":
        return cmd_run(args)
    if command == "mic":
        return cmd_mic(args)
    if command == "config-init":
        return cmd_config_init(args)
    if command == "doctor":
        return cmd_doctor(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
