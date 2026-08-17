# VoiceAsistent

## Objetivo

Aplicacion local de dictado por voz para Windows 11. El usuario mantiene una
tecla, habla, suelta la tecla y el texto transcrito se pega en la ventana que
tiene el foco. La misma salida debe poder entrar en una maquina virtual cuando
el hipervisor permite portapapeles del host al invitado.

## Alcance aprobado

- MVP: dictado y pegado; no incluye asistente conversacional, TTS ni ejecucion
  de comandos.
- Plataforma prioritaria: Windows 11.
- Validacion posterior: VirtualBox y VMware en el host Windows.
- Linux: segunda etapa, con soporte esperado para sesiones X11. Wayland queda
  documentado como limitacion hasta elegir una integracion especifica.
- Push-to-talk: mantener `F9`; la tecla sera configurable.
- Idiomas: espanol e ingles con modelo Whisper multilingue y autodeteccion.
- Perfil inicial: Whisper `base`; se podra cambiar a `small` o `medium` tras
  medir el hardware real.
- Backend: intentar `faster-whisper` con CUDA cuando sea viable y usar CPU
  `int8` como fallback. Vulkan no forma parte de esta ruta.
- Salida: pegar usando el portapapeles y conservar la transcripcion en el
  portapapeles. Si el pegado falla, intentar tecleo simulado.
- Ollama: fase opcional posterior, desactivada por defecto, con timeout y
  fallback al texto original.
- Privacidad: no guardar audio ni historial por defecto; no enviar texto a
  servicios remotos desde el MVP.
- Distribucion inicial: codigo Python dentro de un entorno virtual. El `.exe`
  de Windows queda para una fase posterior, despues de validar el flujo.

## Fases

### Fase 0 - Diagnostico y contrato

- Ejecutar `scripts/doctor_windows.ps1` en cada computador Windows.
- Recoger version de Windows, Python, CPU, RAM, GPU, NVIDIA/CUDA, microfonos,
  VirtualBox, VMware y Hyper-V.
- Confirmar el hipervisor y el sistema invitado antes de la prueba de VM.
- No incluir rutas con credenciales, tokens, contenido del portapapeles ni
  archivos personales en el diagnostico.

### Fase 1 - Base del proyecto

- Crear paquete Python con `pyproject.toml` y configuracion TOML validada.
- Fijar Python 3.11+ y dependencias con rangos reproducibles.
- Agregar CLI para ejecutar, comprobar dependencias, listar microfonos y
  mostrar la configuracion efectiva sin secretos.
- Añadir instaladores PowerShell y Bash con prerequisitos visibles.

### Fase 2 - Captura push-to-talk

- Usar `pynput` para escuchar `F9` globalmente.
- Mantener los callbacks de teclado ligeros; enviar eventos a una cola.
- Ignorar autorepeticion, impedir grabaciones simultaneas y cerrar ante una
  liberacion perdida o una duracion maxima configurada.
- Usar la API manual de RealtimeSTT: `start()`, `stop()` y `text()`.
- Mantener prebuffer y VAD configurables para no cortar la primera palabra.

### Fase 3 - Transcripcion

- Usar `RealtimeSTT[faster-whisper]` con modelo multilingue.
- Mapear `language = "auto"` a autodeteccion y conservar el idioma detectado
  para diagnostico y para la futura fase Ollama.
- En `device = "auto"`, probar CUDA de forma controlada y caer a CPU `int8`.
- No ocultar errores de CUDA: registrar el motivo y el backend elegido.
- Desactivar transcripcion realtime en el MVP para no cargar dos modelos.

### Fase 4 - Salida en aplicaciones y VM

- Copiar el resultado al portapapeles y enviar `Ctrl+V` a la ventana enfocada.
- Mantener el resultado en el portapapeles cuando el pegado termine.
- Si el portapapeles falla, intentar tecleo simulado y reportar caracteres no
  soportados de forma clara.
- No enviar `Enter` automaticamente.
- Validar primero Notepad y un editor de texto del host.
- Validar despues VirtualBox y VMware. VirtualBox necesita Guest Additions y
  Shared Clipboard en modo Host to Guest o Bidirectional; VMware necesita la
  integracion de VMware Tools y el portapapeles habilitado.
- Documentar que una VM elevada o una aplicacion elevada puede bloquear la
  inyeccion de teclado desde un proceso no elevado.

### Fase 5 - Pruebas

- Tests unitarios sin microfono, GPU ni descarga de modelos para configuracion,
  parser de tecla, maquina de estados, seleccion de backend y salida.
- Tests de integracion con recorder, clipboard y teclado falsos.
- Cobertura minima del 80% sobre el codigo propio.
- Smoke test real en Windows: microfono, F9, Notepad y fallback.
- Smoke test de VM por hipervisor, con evidencia de configuracion y resultado.
- Prueba opcional en Linux X11 y diagnostico de la limitacion Wayland.

### Fase 6 - Ollama opcional

- Mantenerlo desactivado por defecto.
- Usar solo `http://127.0.0.1:11434` por defecto.
- Aplicar prompt estricto: corregir sin inventar, conservar idioma y devolver
  solo el texto.
- Usar timeout, validar respuesta y volver al texto Whisper si Ollama no esta
  disponible o devuelve una respuesta vacia.
- Medir la latencia adicional antes de recomendarlo para dictado frecuente.

### Fase 7 - Distribucion y mantenimiento

- Documentar instalacion, permisos, modelos, diagnostico y desinstalacion.
- Empaquetar `.exe` solo despues de estabilizar el codigo Python.
- Mantener el modelo fuera del ejecutable para evitar binarios enormes y
  permitir cambiar de perfil.
- Revisar dependencias, licencias y cambios de RealtimeSTT antes de actualizar.

## Criterios de aceptacion del MVP

1. En Windows 11, mantener F9 durante una frase produce una transcripcion sin
   necesidad de pulsar otra tecla.
2. El texto se pega en Notepad y queda disponible en el portapapeles.
3. Si el pegado falla, el programa intenta teclear y muestra el resultado.
4. El modelo usa autodeteccion para frases en espanol e ingles.
5. Un host sin CUDA puede usar CPU `int8` sin cambiar codigo.
6. El programa no guarda audio ni texto salvo que el usuario lo habilite de
   forma explicita.
7. Una VM con la integracion de portapapeles habilitada recibe el texto cuando
   su ventana esta enfocada.
8. Una falla de microfono, modelo, CUDA, portapapeles u Ollama produce un
   mensaje accionable y no termina en un error silencioso.

## Pendientes no bloqueantes

- Hipervisor exacto y sistema invitado: se validan en los smoke tests.
- Wayland: requiere una ruta de captura y pegado especifica.
- Ejecutable Windows: se aborda despues del MVP Python.

## Hardware confirmado

- Dell Latitude 5480, Windows 10 Home 19045, 15.86 GB RAM, i7-7600U (2C/4T),
  sin GPU dedicada (Intel HD 620), Python 3.13, microfonos Realtek OK.
- Consecuencia: backend definitivo CPU `int8`, modelo `base`, `beam_size = 1`.
- CUDA queda descartado en este equipo; el modo `auto` lo detecta y no cambia
  nada de configuracion.
