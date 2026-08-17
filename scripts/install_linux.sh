#!/usr/bin/env bash
set -euo pipefail

WITH_SPEECH=false
WITH_DEV=false
for arg in "$@"; do
    case "$arg" in
        --with-speech) WITH_SPEECH=true ;;
        --with-dev) WITH_DEV=true ;;
        *) echo "Uso: $0 [--with-speech] [--with-dev]" && exit 2 ;;
    esac
done

echo "== VoiceAsistent - instalador Linux =="
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 no encontrado. Instala python3 (3.11 o superior) antes de continuar."
    exit 1
fi

python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || {
    echo "Se requiere Python 3.11 o superior."
    exit 1
}

echo "Instalando dependencias del sistema (requiere sudo)..."
sudo apt-get update -y
sudo apt-get install -y python3-dev portaudio19-dev xclip

echo "Creando entorno virtual .venv..."
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip

echo "Instalando VoiceAsistent..."
.venv/bin/pip install -e .

if [ "$WITH_SPEECH" = true ]; then
    echo "Instalando motor de voz..."
    .venv/bin/pip install -e ".[speech]"
else
    echo "Motor de voz omitido. Instalalo despues con:"
    echo "  .venv/bin/pip install -e '.[speech]'"
fi

if [ "$WITH_DEV" = true ]; then
    .venv/bin/pip install -e ".[dev]"
fi

.venv/bin/voiceasistent config-init || true

echo ""
echo "Instalacion completada. Para iniciar (sesion X11):"
echo "  .venv/bin/voiceasistent run"
echo "Nota: bajo Wayland la captura global de teclado tiene soporte limitado."
