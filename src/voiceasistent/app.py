"""Orquestacion del flujo push-to-talk: tecla -> grabacion -> transcripcion -> salida."""

from __future__ import annotations

import logging
from typing import Protocol

from .hotkeys import HoldGate
from .output import OutputResult, OutputWriter

logger = logging.getLogger("voiceasistent.app")


class EnginePort(Protocol):
    """Contrato del motor de transcripcion; permite falsos en pruebas."""

    detected_language: str | None

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def text(self) -> str: ...

    def shutdown(self) -> None: ...


class PushToTalkApp:
    """Conecta la maquina de estados de teclas con el motor y la salida."""

    def __init__(
        self,
        engine: EnginePort,
        gate: HoldGate,
        output: OutputWriter,
        max_recording_seconds: float,
    ) -> None:
        self._engine = engine
        self.gate = gate
        self._output = output
        self._max_recording_seconds = max_recording_seconds

    @property
    def is_holding(self) -> bool:
        return self.gate.is_holding

    def on_key_press(self, key: str | None) -> None:
        action = self.gate.press(key)
        if action == "start":
            logger.info("Grabacion iniciada con la tecla push-to-talk.")
            self._engine.start()

    def on_key_release(self, key: str | None) -> OutputResult | None:
        action = self.gate.release(key)
        if action != "stop":
            return None
        logger.info("Grabacion detenida; transcribiendo.")
        self._engine.stop()
        return self._finish()

    def on_recording_timeout(self) -> OutputResult | None:
        if not self.gate.is_holding:
            return None
        logger.warning("Tiempo maximo de grabacion alcanzado; transcribiendo.")
        self.gate.release(self.gate._required[0])
        self._engine.stop()
        return self._finish()

    def _finish(self) -> OutputResult:
        text = self._engine.text()
        result = self._output.deliver(text)
        logger.info(
            "Transcripcion entregada (idioma detectado: %s): %r",
            getattr(self._engine, "detected_language", None),
            result.status,
        )
        return result

    def shutdown(self) -> None:
        self._engine.shutdown()
