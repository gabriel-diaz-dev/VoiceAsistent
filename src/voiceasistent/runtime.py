"""Adaptadores de runtime: teclado global, portapapeles y bucle de eventos.

Todos los imports pesados (pynput, pyperclip, pyaudio) son perezosos para que
los tests unitarios corran sin esas dependencias instaladas.
"""

from __future__ import annotations

import logging
import queue
import time
from typing import Any

from .app import PushToTalkApp

logger = logging.getLogger("voiceasistent.runtime")


def canonical_key(key: Any) -> str | None:
    """Convierte un objeto de tecla de pynput en el nombre normalizado."""
    if key is None:
        return None
    try:
        char = key.char
        if char is not None:
            return char
    except AttributeError:
        pass
    try:
        return str(key.name)
    except AttributeError:
        return None


class PynputHotkeyListener:
    """Escucha global de teclado que encola eventos sin bloquear callbacks."""

    def __init__(self, runner: EventRunner) -> None:
        self._runner = runner
        self._listener = None

    def start(self) -> None:
        from pynput import keyboard  # carga perezosa

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()

    def _on_press(self, key: Any) -> None:
        self._runner.push_press(canonical_key(key))

    def _on_release(self, key: Any) -> None:
        self._runner.push_release(canonical_key(key))


class EventRunner:
    """Consume eventos de teclado y aplica el timeout de grabacion."""

    def __init__(self, app: PushToTalkApp, max_recording_seconds: float) -> None:
        self._app = app
        self._max_seconds = max_recording_seconds
        self._events: queue.Queue[tuple[str, str | None]] = queue.Queue()
        self._started_at: float | None = None

    def push_press(self, key: str | None) -> None:
        self._events.put(("press", key))

    def push_release(self, key: str | None) -> None:
        self._events.put(("release", key))

    def process_one(self, timeout: float = 0) -> bool:
        """Procesa un evento; devuelve False si no habia eventos disponibles."""
        try:
            kind, key = self._events.get(timeout=timeout)
        except queue.Empty:
            self._check_timeout()
            return False

        if kind == "press":
            action_was_start = not self._app.gate.is_holding
            self._app.on_key_press(key)
            if action_was_start and self._app.gate.is_holding:
                self._started_at = time.monotonic()
        else:
            result = self._app.on_key_release(key)
            if result is not None:
                self._started_at = None
        return True

    def run_forever(self) -> None:
        logger.info("Escuchando; mantén la tecla push-to-talk para dictar.")
        while True:
            self.process_one(timeout=0.1)

    def _check_timeout(self) -> None:
        if self._started_at is None or not self._app.gate.is_holding:
            return
        if time.monotonic() - self._started_at >= self._max_seconds:
            result = self._app.on_recording_timeout()
            if result is not None:
                self._started_at = None


class PyperclipClipboard:
    """Portapapeles del sistema a traves de pyperclip."""

    def copy(self, text: str) -> None:
        import pyperclip  # carga perezosa

        pyperclip.copy(text)

    def paste(self) -> str:
        import pyperclip  # carga perezosa

        return pyperclip.paste()


class PynputKeyboard:
    """Teclado simulado: Ctrl+V y tecleo de cadenas."""

    def hotkey_paste(self) -> None:
        from pynput.keyboard import Controller, Key  # carga perezosa

        controller = Controller()
        with controller.pressed(Key.ctrl):
            controller.press("v")
            controller.release("v")

    def type_text(self, text: str) -> None:
        from pynput.keyboard import Controller  # carga perezosa

        Controller().type(text)


class PyAudioMicrophones:
    """Enumera los dispositivos de entrada disponibles."""

    def list_input_devices(self) -> list[dict[str, Any]]:
        import pyaudio  # carga perezosa

        audio = pyaudio.PyAudio()
        devices: list[dict[str, Any]] = []
        try:
            for index in range(audio.get_device_count()):
                info = audio.get_device_info_by_index(index)
                if int(info.get("maxInputChannels", 0)) > 0:
                    devices.append(
                        {
                            "index": index,
                            "name": info.get("name", ""),
                            "default_sample_rate": info.get("defaultSampleRate"),
                        }
                    )
        finally:
            audio.terminate()
        return devices
