"""Logica pura de la tecla push-to-talk, sin dependencias de pynput."""

from __future__ import annotations

from .config import ALLOWED_HOTKEY_NAMES


def normalize_key(key: str | None) -> str | None:
    """Normaliza el nombre de una tecla a minusculas; None si no es soportada."""
    if key is None:
        return None
    name = key.strip().lower()
    if not name:
        return None
    if len(name) == 1 and name.isalnum():
        return name
    if name in ALLOWED_HOTKEY_NAMES:
        return name
    return None


class HoldGate:
    """Maquina de estados: espera a que todas las teclas requeridas esten pulsadas.

    Ignora la autorepeticion del sistema operativo y las teclas desconocidas.
    """

    def __init__(self, keys: tuple[str, ...]) -> None:
        self._required = tuple(normalize_key(key) for key in keys)
        if any(key is None for key in self._required):
            raise ValueError(f"Teclas no soportadas: {keys!r}")
        self._held: set[str] = set()

    @property
    def is_holding(self) -> bool:
        return self._required and self._held.issuperset(self._required)

    def press(self, key: str | None) -> str | None:
        """Registra una pulsacion; devuelve 'start' si comienza la grabacion."""
        normalized = normalize_key(key)
        if normalized is None or normalized not in self._required:
            return None
        if normalized in self._held:
            return None
        self._held.add(normalized)
        if self.is_holding:
            return "start"
        return None

    def release(self, key: str | None) -> str | None:
        """Registra una liberacion; devuelve 'stop' si termina la grabacion."""
        normalized = normalize_key(key)
        if normalized is None or normalized not in self._required:
            return None
        if normalized not in self._held:
            return None
        was_holding = self.is_holding
        self._held.discard(normalized)
        if was_holding:
            return "stop"
        return None
