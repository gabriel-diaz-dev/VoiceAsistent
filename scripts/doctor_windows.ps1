[CmdletBinding()]
param(
    [switch]$Json
)

$ErrorActionPreference = "SilentlyContinue"

function Get-CommandInfo {
    param([string]$Name)

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        return [ordered]@{
            available = $false
            path = $null
            version = $null
        }
    }

    $version = $null
    try {
        $version = (& $Name --version 2>&1 | Select-Object -First 1).ToString().Trim()
    } catch {
        $version = $null
    }

    return [ordered]@{
        available = $true
        path = $command.Source
        version = $version
    }
}

function Get-ToolVersion {
    param([string]$Path)

    $version = $null
    try {
        $fileVersion = (Get-Item -LiteralPath $Path).VersionInfo.ProductVersion
        if (-not [string]::IsNullOrWhiteSpace($fileVersion)) {
            return $fileVersion.Trim()
        }
    } catch {
    }

    try {
        $version = (& $Path --version 2>&1 | Select-Object -First 1).ToString().Trim()
    } catch {
        $version = $null
    }

    return $version
}

function Resolve-Tool {
    param(
        [string]$Name,
        [string[]]$KnownPaths
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return [ordered]@{
            available = $true
            path = $command.Source
            version = Get-ToolVersion -Path $command.Source
            source = "path"
        }
    }

    foreach ($candidate in $KnownPaths) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return [ordered]@{
                available = $true
                path = $candidate
                version = Get-ToolVersion -Path $candidate
                source = "known_path"
            }
        }
    }

    return [ordered]@{
        available = $false
        path = $null
        version = $null
        source = $null
    }
}

function Get-PythonInfo {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $python) {
        return [ordered]@{
            available = $false
            path = $null
            version = $null
            architecture = $null
        }
    }

    $version = (& python --version 2>&1 | Select-Object -First 1).ToString().Trim()
    $architecture = $null
    try {
        $architecture = (& python -c "import platform; print(platform.architecture()[0])" 2>&1 | Select-Object -First 1).ToString().Trim()
    } catch {
        $architecture = $null
    }

    return [ordered]@{
        available = $true
        path = $python.Source
        version = $version
        architecture = $architecture
        py_launcher = Resolve-Tool "py.exe" @("$env:windir\py.exe")
    }
}

function Get-GpuInfo {
    $controllers = @(
        Get-CimInstance Win32_VideoController |
            Select-Object Name, DriverVersion, AdapterRAM
    )

    $nvidiaTool = Resolve-Tool "nvidia-smi.exe" @(
        "C:\Windows\System32\nvidia-smi.exe",
        "C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"
    )
    $nvidia = @()
    if ($nvidiaTool.available) {
        $nvidia = @(& $nvidiaTool.path --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>&1)
    }

    return [ordered]@{
        video_controllers = $controllers
        nvidia_smi = [ordered]@{
            available = $nvidiaTool.available
            path = $nvidiaTool.path
            gpus = $nvidia
        }
    }
}

function Get-AudioInfo {
    $devices = @(
        Get-CimInstance Win32_SoundDevice |
            Select-Object Name, Manufacturer, Status, PNPDeviceID
    )

    return ,$devices
}

function Get-CaptureEndpoints {
    $captureRoot = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture"
    $friendlyNameProperty = "{a45c254e-df1c-4efd-8020-67d146a850e0},2"
    $items = @()

    Get-ChildItem -LiteralPath $captureRoot -ErrorAction SilentlyContinue | ForEach-Object {
        $propertiesPath = Join-Path $_.PSPath "Properties"
        $properties = Get-ItemProperty -LiteralPath $propertiesPath -ErrorAction SilentlyContinue
        $name = $null
        if ($null -ne $properties) {
            $property = $properties.PSObject.Properties |
                Where-Object { $_.Name -eq $friendlyNameProperty } |
                Select-Object -First 1
            if ($null -ne $property) {
                $name = $property.Value
            }
        }

        $items += [ordered]@{
            name = $name
            mmdevice_id = $_.PSChildName
        }
    }

    return ,$items
}

function Get-VirtualizationInfo {
    $hyperV = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All
    $hyperVState = $null
    if ($null -ne $hyperV) {
        $hyperVState = $hyperV.State.ToString()
    }

    return [ordered]@{
        virtualbox = Resolve-Tool "VBoxManage.exe" @(
            "$env:ProgramFiles\Oracle\VirtualBox\VBoxManage.exe"
        )
        vmware = Resolve-Tool "vmrun.exe" @(
            "${env:ProgramFiles(x86)}\VMware\VMware Workstation\vmrun.exe",
            "$env:ProgramFiles\VMware\VMware Workstation\vmrun.exe"
        )
        hyper_v_feature = $hyperVState
        notes = @(
            "El portapapeles de la VM se debe revisar en la configuracion del hipervisor.",
            "VirtualBox normalmente requiere Guest Additions y Shared Clipboard habilitado.",
            "VMware normalmente requiere VMware Tools y la integracion de portapapeles habilitada."
        )
    }
}

$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
$processor = Get-CimInstance Win32_Processor | Select-Object -First 1

$report = [ordered]@{
    report = "VoiceAsistent Windows doctor"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    machine = [ordered]@{
        computer_name = $env:COMPUTERNAME
        manufacturer = $computer.Manufacturer
        model = $computer.Model
        windows_caption = $os.Caption
        windows_version = $os.Version
        windows_build = $os.BuildNumber
        architecture = $os.OSArchitecture
        powershell = $PSVersionTable.PSVersion.ToString()
        ram_gb = if ($computer.TotalPhysicalMemory) { [math]::Round($computer.TotalPhysicalMemory / 1GB, 2) } else { $null }
    }
    cpu = [ordered]@{
        name = $processor.Name
        cores = $processor.NumberOfCores
        logical_processors = $processor.NumberOfLogicalProcessors
        max_clock_mhz = $processor.MaxClockSpeed
    }
    python = Get-PythonInfo
    gpu = Get-GpuInfo
    audio = [ordered]@{
        sound_devices = Get-AudioInfo
        capture_endpoints = Get-CaptureEndpoints
    }
    virtualization = Get-VirtualizationInfo
    runtime_checks = [ordered]@{
        git = Get-CommandInfo "git.exe"
        ollama = Resolve-Tool "ollama.exe" @(
            "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
            "$env:ProgramFiles\Ollama\ollama.exe"
        )
        clipboard_hint = "No se lee ni se incluye el contenido actual del portapapeles."
    }
}

if ($Json) {
    $report | ConvertTo-Json -Depth 8
    exit 0
}

Write-Output "=== VoiceAsistent Windows doctor ==="
Write-Output "Copia todo este bloque y pegalo en la conversacion."
Write-Output ""
$report | ConvertTo-Json -Depth 8
Write-Output ""
Write-Output "=== Fin del diagnostico ==="
