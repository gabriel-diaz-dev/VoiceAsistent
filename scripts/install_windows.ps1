[CmdletBinding()]
param(
    [switch]$WithSpeech,
    [switch]$WithDev
)

$ErrorActionPreference = "Stop"

Write-Host "== VoiceAsistent - instalador Windows =="

$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $python) {
    Write-Host "No se encontro Python. Instala Python 3.11 o superior desde https://www.python.org/downloads/"
    Write-Host "Marca la casilla 'Add python.exe to PATH' durante la instalacion."
    exit 1
}

$version = (& python --version 2>&1).ToString()
Write-Host "Python detectado: $version"
Write-Host "Nota: para usar el microfono, activa en Configuracion > Privacidad > Microfono el acceso de aplicaciones de escritorio."

Write-Host "Creando entorno virtual .venv..."
python -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip

Write-Host "Instalando VoiceAsistent..."
& ".\.venv\Scripts\pip.exe" install -e .

if ($WithSpeech) {
    Write-Host "Instalando motor de voz (descarga dependencias adicionales)..."
    & ".\.venv\Scripts\pip.exe" install -e ".[speech]"
} else {
    Write-Host "Se omitio el motor de voz. Ejecutalo aparte con:"
    Write-Host "  .\.venv\Scripts\pip.exe install -e `".[speech]`""
}

if ($WithDev) {
    & ".\.venv\Scripts\pip.exe" install -e ".[dev]"
}

& ".\.venv\Scripts\voiceasistent.exe" config-init
if (-not (Test-Path "config.toml")) {
    Write-Host "Se creara config.toml en la primera ejecucion."
}

Write-Host ""
Write-Host "Instalacion completada. Para iniciar:"
Write-Host "  .\.venv\Scripts\voiceasistent.exe run"
Write-Host "Para listar microfonos:"
Write-Host "  .\.venv\Scripts\voiceasistent.exe mic"
