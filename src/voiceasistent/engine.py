"""Adaptador del motor RealtimeSTT con carga perezosa y mapeo de configuracion."""

from __future__ import annotations

import logging
from typing import Any

from .backend import BackendDecision
from .config import AppConfig

logger = logging.getLogger("voiceasistent.engine")


def build_recorder_kwargs(config: AppConfig, decision: BackendDecision) -> dict[str, Any]:
    """Convierte configuracion y decision de backend en argumentos de AudioToTextRecorder."""
    kwargs: dict[str, Any] = {
        "model": config.model,
        "language": config.whisper_language,
        "device": decision.device,
        "compute_type": decision.compute_type,
        "enable_realtime_transcription": False,
        "spinner": False,
        "no_log_file": True,
        "print_transcription_time": True,
    }
    if config.input_device_index >= 0:
        kwargs["input_device_index"] = config.input_device_index
    return kwargs


class RealtimeSttEngine:
    """Envuelve AudioToTextRecorder con la API manual start/stop/text."""

    def __init__(self, config: AppConfig, decision: BackendDecision) -> None:
        from RealtimeSTT import AudioToTextRecorder  # carga perezosa

        kwargs = build_recorder_kwargs(config, decision)
        logger.info(
            "Inicializando motor: modelo=%s device=%s compute_type=%s",
            kwargs["model"],
            kwargs["device"],
            kwargs["compute_type"],
        )
        self._recorder = AudioToTextRecorder(**kwargs)
        self.detected_language: str | None = None

    def start(self) -> None:
        self._recorder.start()

    def stop(self) -> None:
        self._recorder.stop()

    def text(self) -> str:
        text = self._recorder.text()
        self.detected_language = getattr(self._recorder, "detected_language", None)
        return text

    def shutdown(self) -> None:
        self._recorder.shutdown()
