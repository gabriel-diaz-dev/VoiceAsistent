"""Salida del texto transcrito hacia la ventana enfocada, con fallback de tecleo."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger("voiceasistent.output")


class ClipboardPort(Protocol):
    def copy(self, text: str) -> None: ...

    def paste(self) -> str: ...


class KeyboardPort(Protocol):
    def hotkey_paste(self) -> None: ...

    def type_text(self, text: str) -> None: ...


@dataclass(frozen=True)
class OutputResult:
    """Resultado de una entrega de texto para diagnostico y pruebas."""

    status: str
    message: str = ""
    unsupported_chars: list[str] = field(default_factory=list)


class OutputWriter:
    """Copia al portapapeles y pega, con politica conservadora.

    `mode` puede ser:
    - "paste": copiar y enviar Ctrl+V; si el portapapeles falla, teclear.
    - "type": teclear directamente, sin portapapeles.
    - "clipboard": solo copiar, sin pegar ni teclear.
    """

    def __init__(
        self,
        clipboard: ClipboardPort,
        keyboard: KeyboardPort,
        mode: str = "paste",
        keep_clipboard: bool = True,
        paste_delay_ms: int = 100,
    ) -> None:
        self._clipboard = clipboard
        self._keyboard = keyboard
        self._mode = mode
        self._keep_clipboard = keep_clipboard
        self._paste_delay_ms = paste_delay_ms

    def deliver(self, text: str) -> OutputResult:
        if not text.strip():
            return OutputResult(status="skipped", message="Texto vacio; nada que entregar.")

        if self._mode == "type":
            return self._type(text)

        try:
            self._clipboard.copy(text)
        except Exception as exc:
            logger.warning("Portapapeles no disponible (%s); intentando tecleo.", exc)
            return self._type(text)

        if self._mode == "clipboard":
            return OutputResult(status="copied", message="Copiado al portapapeles.")

        try:
            self._keyboard.hotkey_paste()
        except Exception as exc:
            logger.warning("Ctrl+V fallo (%s); intentando tecleo.", exc)
            return self._type(text)

        if self._paste_delay_ms > 0:
            time.sleep(self._paste_delay_ms / 1000)

        return OutputResult(
            status="pasted",
            message="Pegado en la ventana enfocada; el portapapeles conserva la transcripcion.",
        )

    def _type(self, text: str) -> OutputResult:
        unsupported: list[str] = []
        try:
            self._keyboard.type_text(text)
        except ValueError as exc:
            logger.warning("Caracteres no soportados por el teclado simulado: %s", exc)
            unsupported.append(str(exc))
        except Exception as exc:
            logger.error("Tecleo simulado fallo: %s", exc)
            return OutputResult(
                status="failed",
                message=f"No se pudo entregar el texto: {exc}",
            )
        return OutputResult(
            status="typed",
            message="Texto tecleado en la ventana enfocada.",
            unsupported_chars=unsupported,
        )
