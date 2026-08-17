"""Configuracion tipada y validada para VoiceAsistent."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

ALLOWED_MODELS = {
    "tiny",
    "tiny.en",
    "base",
    "base.en",
    "small",
    "small.en",
    "medium",
    "medium.en",
    "large-v1",
    "large-v2",
    "large-v3",
}

ALLOWED_DEVICES = {"auto", "cuda", "cpu"}
ALLOWED_OUTPUT_MODES = {"paste", "type", "clipboard"}
ALLOWED_HOTKEY_NAMES = {
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
    "f6",
    "f7",
    "f8",
    "f9",
    "f10",
    "f11",
    "f12",
    "f13",
    "f14",
    "f15",
    "f16",
    "f17",
    "f18",
    "f19",
    "f20",
    "esc",
    "tab",
    "space",
    "enter",
    "backspace",
    "insert",
    "delete",
    "home",
    "end",
    "page_up",
    "page_down",
    "pause",
    "print_screen",
    "scroll_lock",
    "caps_lock",
    "num_lock",
    "menu",
    "ctrl",
    "alt",
    "shift",
    "cmd",
    "win",
    "alt_gr",
    "up",
    "down",
    "left",
    "right",
}

MAX_HOTKEY_KEYS = 3


class ConfigError(ValueError):
    """Error de configuracion con mensaje accionable para el usuario."""


@dataclass(frozen=True)
class AppConfig:
    """Configuracion efectiva del asistente."""

    hotkey: str
    hotkey_keys: tuple[str, ...] = ()
    model: str = "base"
    language: str = "auto"
    device: str = "auto"
    compute_type: str = "default"
    cpu_compute_type: str = "int8"
    beam_size: int = 1
    output_mode: str = "paste"
    keep_clipboard: bool = True
    paste_delay_ms: int = 100
    max_recording_seconds: float = 60.0
    input_device_index: int = -1
    ollama_enabled: bool = False
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = ""
    ollama_timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not self.hotkey_keys:
            object.__setattr__(self, "hotkey_keys", parse_hotkey(self.hotkey))

    @property
    def whisper_language(self) -> str:
        """Codigo de idioma para faster-whisper; 'auto' se traduce a autodeteccion."""
        return "" if self.language in ("", "auto") else self.language


def parse_hotkey(spec: str) -> tuple[str, ...]:
    """Convierte una cadena como 'ctrl+f9' en una tupla de teclas normalizadas."""
    parts = [part.strip().lower() for part in spec.split("+")]
    keys = [part for part in parts if part]
    if not keys:
        raise ConfigError("La tecla esta vacia; indica una tecla o combinacion.")
    if len(keys) > MAX_HOTKEY_KEYS:
        raise ConfigError(
            f"Se permiten {MAX_HOTKEY_KEYS} teclas como maximo; se recibieron {len(keys)}."
        )
    normalized: list[str] = []
    for key in keys:
        if len(key) == 1 and key.isalnum():
            normalized.append(key)
        elif key in ALLOWED_HOTKEY_NAMES:
            normalized.append(key)
        else:
            message = (
                f"Tecla desconocida: {key!r}. Usa letras, numeros, f1-f20 "
                "o nombres como ctrl, alt, shift."
            )
            raise ConfigError(message)
    return tuple(normalized)


def _require_choice(value: str, allowed: set[str], field: str) -> str:
    if value not in allowed:
        raise ConfigError(f"{field} invalido: {value!r}. Opciones: {', '.join(sorted(allowed))}.")
    return value


def _require_positive(value: float, field: str) -> float:
    if value < 0:
        raise ConfigError(f"{field} no puede ser negativo; se recibio {value}.")
    return value


def _build_config(data: dict[str, Any]) -> AppConfig:
    speech = data.get("speech", {})
    hotkey_section = data.get("hotkey", {})
    output = data.get("output", {})
    audio = data.get("audio", {})
    ollama = data.get("ollama", {})

    hotkey = str(hotkey_section.get("key", "f9"))
    hotkey_keys = parse_hotkey(hotkey)

    model = str(speech.get("model", "base"))
    _require_choice(model, ALLOWED_MODELS, "speech.model")

    device = str(speech.get("device", "auto"))
    _require_choice(device, ALLOWED_DEVICES, "speech.device")

    output_mode = str(output.get("mode", "paste"))
    _require_choice(output_mode, ALLOWED_OUTPUT_MODES, "output.mode")

    paste_delay_ms = int(output.get("paste_delay_ms", 100))
    _require_positive(paste_delay_ms, "output.paste_delay_ms")

    max_recording_seconds = float(output.get("max_recording_seconds", 60.0))
    _require_positive(max_recording_seconds, "output.max_recording_seconds")

    ollama_timeout_seconds = float(ollama.get("timeout_seconds", 10.0))
    _require_positive(ollama_timeout_seconds, "ollama.timeout_seconds")

    beam_size = int(speech.get("beam_size", 1))
    if beam_size < 1:
        raise ConfigError(f"speech.beam_size debe ser 1 o mayor; se recibio {beam_size}.")

    return AppConfig(
        hotkey=hotkey,
        hotkey_keys=hotkey_keys,
        model=model,
        language=str(speech.get("language", "auto")),
        device=device,
        compute_type=str(speech.get("compute_type", "default")),
        cpu_compute_type=str(speech.get("cpu_compute_type", "int8")),
        beam_size=beam_size,
        output_mode=output_mode,
        keep_clipboard=bool(output.get("keep_clipboard", True)),
        paste_delay_ms=paste_delay_ms,
        max_recording_seconds=max_recording_seconds,
        input_device_index=int(audio.get("input_device_index", -1)),
        ollama_enabled=bool(ollama.get("enabled", False)),
        ollama_url=str(ollama.get("url", "http://127.0.0.1:11434")),
        ollama_model=str(ollama.get("model", "")),
        ollama_timeout_seconds=ollama_timeout_seconds,
    )


def load_config(path: Path | str | None = None) -> AppConfig:
    """Carga la configuracion desde un TOML opcional; si falta, usa valores por defecto."""
    if path is None:
        path = Path("config.toml")
    config_path = Path(path)
    data: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
    return _build_config(data)


DEFAULT_CONFIG_TOML = """# VoiceAsistent - configuracion
[hotkey]
key = "f9"                  # tecla o combinacion, ej. "ctrl+f9", "f9", "alt+space"

[speech]
model = "base"              # tiny, base, small, medium, large-v1/v2/v3 (y variantes .en)
language = "auto"           # auto = autodeteccion; tambien "es", "en", ...
device = "auto"             # auto | cuda | cpu (auto prueba CUDA y cae a CPU)
compute_type = "default"    # precision para CUDA (default, float16, int8...)
cpu_compute_type = "int8"   # precision usada cuando se ejecuta en CPU
beam_size = 1               # 1 = mas rapido (recomendado en CPU); 5 = mas preciso

[audio]
input_device_index = -1     # -1 = microfono por defecto

[output]
mode = "paste"              # paste | type | clipboard
keep_clipboard = true       # deja la transcripcion en el portapapeles
paste_delay_ms = 100        # espera tras Ctrl+V antes de continuar
max_recording_seconds = 60  # cierre de seguridad si se suelta la tecla perdida

[ollama]
enabled = false             # fase opcional posterior
url = "http://127.0.0.1:11434"
model = ""
timeout_seconds = 10
"""


def write_default_config(path: Path | str) -> None:
    """Escribe una plantilla de configuracion TOML."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(DEFAULT_CONFIG_TOML, encoding="utf-8")


def with_overrides(config: AppConfig, **overrides: Any) -> AppConfig:
    """Devuelve una copia con campos reemplazados, sin mutar el original."""
    return replace(config, **overrides)
