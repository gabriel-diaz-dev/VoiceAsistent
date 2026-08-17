# VoiceAsistent

Dictado por voz push-to-talk, local y privado. Mantén la tecla (`F9` por
defecto), habla, suéltala: el texto transcrito se pega en la ventana que tiene
el foco. Funciona en aplicaciones del host y dentro de una máquina virtual
cuando el hipervisor comparte el portapapeles del host al invitado.

- 100% offline: el audio y el texto no salen del equipo.
- Español e inglés con autodetección de idioma (modelo Whisper multilingüe).
- CUDA si hay GPU NVIDIA; si no, CPU con cuantización int8 automáticamente.
- Windows 11 como plataforma prioritaria; Linux X11 soportado.
- No guarda audio ni historial por defecto.

## Diagnóstico previo (recomendado)

Antes de instalar, ejecuta en Windows para conocer hardware y hipervisor:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\doctor_windows.ps1
```

Copia el JSON resultante para ajustar el modelo (base/small/medium) y el
backend (CUDA/CPU).

## Instalación en Windows

Requisitos: Python 3.11 o superior y un micrófono.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1 -WithSpeech
```

Permisos: en Configuración > Privacidad y seguridad > Micrófono, permite el
acceso de aplicaciones de escritorio.

## Instalación en Linux (X11)

```bash
bash scripts/install_linux.sh --with-speech
```

Wayland: la captura global de teclado y el pegado tienen soporte limitado;
usa una sesión X11 para el MVP.

## Uso

```powershell
.\.venv\Scripts\voiceasistent.exe run
.\.venv\Scripts\voiceasistent.exe mic          # listar micrófonos
.\.venv\Scripts\voiceasistent.exe config-init  # crear config.toml
```

Comandos principales: `run`, `mic`, `config-init`, `doctor`.

## Configuración (config.toml)

| Sección | Clave | Por defecto | Descripción |
|---|---|---|---|
| `hotkey` | `key` | `f9` | Tecla o combinación, ej. `ctrl+f9` |
| `speech` | `model` | `base` | `tiny`, `base`, `small`, `medium`, `large-v1/v2/v3` |
| `speech` | `language` | `auto` | Autodetección, o `es`/`en` |
| `speech` | `device` | `auto` | `auto` prueba CUDA y cae a CPU |
| `speech` | `cpu_compute_type` | `int8` | Precisión en CPU |
| `output` | `mode` | `paste` | `paste`, `type` o `clipboard` |
| `output` | `keep_clipboard` | `true` | Deja la transcripción en el portapapeles |
| `output` | `max_recording_seconds` | `60` | Cierre de seguridad |

## Pegado dentro de una máquina virtual

El texto se entrega a la ventana enfocada. Para que entre en la VM:

1. Enfoca la ventana de la VM.
2. VirtualBox: instala Guest Additions y activa *Dispositivos > Portapapeles
   compartido > Host a invitado* (o Bidireccional).
3. VMware: instala VMware Tools y activa la integración de portapapeles.
4. Si la aplicación dentro de la VM está elevada (UAC), Windows puede bloquear
   la inyección desde un proceso no elevado; ejecuta VoiceAsistent desde una
   terminal de administrador si lo necesitas.

## Desarrollo

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev,speech]"
PYTHONPATH=src python -m unittest discover -s tests -t .
```

## Privacidad

Sin guardado de audio ni historial; sin telemetría. Ollama (fase posterior)
solo usa `http://127.0.0.1:11434` por defecto y se desactiva ante fallos.

## Limitaciones conocidas

- Wayland: captura y pegado globales limitados.
- Ventanas elevadas: Windows puede bloquear la simulación de teclado.
- Modelos grandes (`medium`/`large`) requieren hardware suficiente; mide con
  el doctor antes de cambiarlos.
