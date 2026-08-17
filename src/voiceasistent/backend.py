"""Seleccion del backend de transcripcion (CUDA con fallback a CPU int8)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import AppConfig

logger = logging.getLogger("voiceasistent.backend")


@dataclass(frozen=True)
class BackendDecision:
    """Decision final de dispositivo y precision con explicacion para el usuario."""

    device: str
    compute_type: str
    cuda_attempted: bool
    notes: tuple[str, ...]


def decide_backend(config: AppConfig, cuda_available: bool | None) -> BackendDecision:
    """Decide device/compute_type a partir de la configuracion y la disponibilidad de CUDA."""
    notes: list[str] = []

    if config.device == "cuda":
        notes.append(
            "Se solicito CUDA explicitamente"
            if cuda_available
            else "Se solicito CUDA pero no se detecto soporte; el arranque puede fallar."
        )
        return BackendDecision(
            device="cuda",
            compute_type=config.compute_type,
            cuda_attempted=True,
            notes=tuple(notes),
        )

    if config.device == "cpu":
        notes.append("Se solicito CPU explicitamente.")
        return BackendDecision(
            device="cpu",
            compute_type=config.cpu_compute_type,
            cuda_attempted=False,
            notes=tuple(notes),
        )

    if cuda_available:
        notes.append("CUDA disponible; se usa la GPU.")
        return BackendDecision(
            device="cuda",
            compute_type=config.compute_type,
            cuda_attempted=True,
            notes=tuple(notes),
        )

    notes.append("CUDA no disponible o no detectada; fallback a CPU int8.")
    return BackendDecision(
        device="cpu",
        compute_type=config.cpu_compute_type,
        cuda_attempted=bool(cuda_available),
        notes=tuple(notes),
    )


def detect_cuda() -> bool:
    """Prueba en tiempo de ejecucion si ctranslate2 puede usar CUDA.

    No lanza excepciones; devuelve False ante cualquier fallo de importacion
    o inicializacion del runtime.
    """
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception as exc:  # pragma: no cover - depende del entorno real
        logger.warning("CUDA no disponible: %s", exc)
        return False
