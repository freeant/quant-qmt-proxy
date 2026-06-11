#Requires -Version 5.1
<#
.SYNOPSIS
    Install or remove xtquant-proxy as a Windows service via NSSM.

.DESCRIPTION
    Registers python run.py as a Windows service with automatic restart on exit.
    Requires NSSM: https://nssm.cc/download

.EXAMPLE
    .\scripts\install-service.ps1 -Action Install
    .\scripts\install-service.ps1 -Action Install -BootstrapNssm
    .\scripts\install-service.ps1 -Action Uninstall
    .\scripts\install-service.ps1 -Action Status
#>
param(
    [ValidateSet("Install", "Uninstall", "Status", "Restart")]
    [string] $Action = "Install",
    [string] $ServiceName = "xtquant-proxy",
    [string] $ProjectRoot = "",
    [string] $NssmPath = "",
    [switch] $BootstrapNssm
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-ProjectRoot {
    param([string] $Root)
    if ($Root) {
        return (Resolve-Path $Root).Path
    }
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-LocalNssmPath {
    param([string] $Root)
    return (Join-Path $Root "tools\nssm\nssm.exe")
}

function Get-NssmDownloadCandidates {
    $is64 = [Environment]::Is64BitOperatingSystem
    $candidates = @(
        "https://nssm.cc/release/nssm-2.24.zip",
        "https://nssm.cc/ci/nssm-2.24-103-gdee49fc.zip"
    )
    if ($is64) {
        $candidates += @(
            "https://github.com/fawno/nssm.cc/releases/download/v2.24.1/nssm-v2.24.1-Win64.zip",
            "https://github.com/ONLYOFFICE/nssm/releases/download/v2.24.1/nssm_x64.zip"
        )
    } else {
        $candidates += @(
            "https://github.com/fawno/nssm.cc/releases/download/v2.24.1/nssm-v2.24.1-Win32.zip"
        )
    }
    return $candidates
}

function Find-NssmBinary {
    param([string] $SearchRoot)
    $preferredArch = if ([Environment]::Is64BitOperatingSystem) { "win64" } else { "win32" }
    $archMatch = Get-ChildItem -Path $SearchRoot -Recurse -Filter "nssm.exe" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match [regex]::Escape($preferredArch) } |
        Select-Object -First 1
    if ($archMatch) {
        return $archMatch.FullName
    }
    $any = Get-ChildItem -Path $SearchRoot -Recurse -Filter "nssm.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($any) {
        return $any.FullName
    }
    return $null
}

function Install-NssmLocal {
    param([string] $Root)

    $toolsDir = Join-Path $Root "tools\nssm"
    $nssmExe = Get-LocalNssmPath -Root $Root
    if (Test-Path $nssmExe) {
        return (Resolve-Path $nssmExe).Path
    }

    Write-Host "Downloading NSSM into $toolsDir ..."
    New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null
    $zipPath = Join-Path $toolsDir "nssm-download.zip"
    $extractRoot = Join-Path $toolsDir "_extract"
    if (Test-Path $extractRoot) {
        Remove-Item $extractRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null

    $downloaded = $false
    $errors = New-Object System.Collections.Generic.List[string]
    foreach ($zipUrl in (Get-NssmDownloadCandidates)) {
        try {
            Write-Host "Trying $zipUrl"
            Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
            Expand-Archive -Path $zipPath -DestinationPath $extractRoot -Force
            $downloaded = $true
            break
        } catch {
            $errors.Add("$zipUrl -> $($_.Exception.Message)") | Out-Null
            Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
            if (Test-Path $extractRoot) {
                Remove-Item $extractRoot -Recurse -Force -ErrorAction SilentlyContinue
                New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null
            }
        }
    }
    if (-not $downloaded) {
        throw ("Failed to download NSSM from all mirrors:`n" + ($errors -join "`n"))
    }

    $extracted = Find-NssmBinary -SearchRoot $extractRoot
    if (-not $extracted) {
        throw "NSSM binary not found in downloaded archive."
    }
    Copy-Item $extracted $nssmExe -Force
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
    Remove-Item $extractRoot -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "NSSM ready: $nssmExe"
    return (Resolve-Path $nssmExe).Path
}

function Resolve-NssmPath {
    param(
        [string] $ExplicitPath,
        [string] $Root,
        [bool] $AllowBootstrap
    )
    if ($ExplicitPath) {
        if (-not (Test-Path $ExplicitPath)) {
            throw "NSSM not found at: $ExplicitPath"
        }
        return (Resolve-Path $ExplicitPath).Path
    }
    $fromPath = Get-Command nssm -ErrorAction SilentlyContinue
    if ($fromPath) {
        return $fromPath.Source
    }
    $localNssm = Get-LocalNssmPath -Root $Root
    if (Test-Path $localNssm) {
        return (Resolve-Path $localNssm).Path
    }
    $common = @(
        "C:\nssm\nssm.exe",
        "C:\tools\nssm\nssm.exe",
        "$env:ProgramFiles\nssm\nssm.exe"
    )
    foreach ($candidate in $common) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }
    if ($AllowBootstrap) {
        return Install-NssmLocal -Root $Root
    }
    throw @"
NSSM not found. Use one of:
  1) .\scripts\install-service.ps1 -Action Install -BootstrapNssm
  2) Download from https://nssm.cc/download and pass -NssmPath 'C:\path\to\nssm.exe'
  3) Add nssm.exe to PATH
"@
}

function Test-Administrator {
    $principal = New-Object Security.Principal.WindowsPrincipal(
        [Security.Principal.WindowsIdentity]::GetCurrent()
    )
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-Nssm {
    param(
        [string] $Executable,
        [string[]] $Arguments
    )
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "NSSM failed ($LASTEXITCODE): nssm $($Arguments -join ' ')"
    }
}

function Get-ServicePython {
    param([string] $Root)
    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    return (Get-Command python).Source
}

$projectRoot = Resolve-ProjectRoot -Root $ProjectRoot
$pythonExe = Get-ServicePython -Root $projectRoot
$runPy = Join-Path $projectRoot "run.py"
$logsDir = Join-Path $projectRoot "logs"

if (-not (Test-Path $runPy)) {
    throw "run.py not found under $projectRoot"
}

if ($Action -eq "Status") {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $svc) {
        Write-Host "Service '$ServiceName' is not installed."
        exit 1
    }
    Write-Host "Service '$ServiceName' status: $($svc.Status)"
    exit 0
}

$allowBootstrap = $BootstrapNssm.IsPresent -or $Action -eq "Install"
$nssm = Resolve-NssmPath -ExplicitPath $NssmPath -Root $projectRoot -AllowBootstrap:$allowBootstrap

if ($Action -eq "Restart") {
    & $nssm restart $ServiceName
    Write-Host "Restarted service '$ServiceName'."
    exit 0
}

if ($Action -eq "Uninstall") {
    $existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existing) {
        if ($existing.Status -ne "Stopped") {
            & $nssm stop $ServiceName
            Start-Sleep -Seconds 2
        }
        & $nssm remove $ServiceName confirm
        Write-Host "Removed service '$ServiceName'."
    } else {
        Write-Host "Service '$ServiceName' is not installed."
    }
    exit 0
}

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    throw "Service '$ServiceName' already exists. Run -Action Uninstall first."
}

if (-not (Test-Administrator)) {
    throw "Administrator privileges are required. Open PowerShell as Administrator and rerun this script."
}

if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

Invoke-Nssm -Executable $nssm -Arguments @("install", $ServiceName, $pythonExe, $runPy)
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "AppDirectory", $projectRoot)
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "DisplayName", "xtquant-proxy")
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "Description", "QMT xtquant gRPC/REST proxy")
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "Start", "SERVICE_AUTO_START")
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "AppStdout", (Join-Path $logsDir "service.out.log"))
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "AppStderr", (Join-Path $logsDir "service.err.log"))
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "AppStdoutCreationDisposition", "4")
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "AppStderrCreationDisposition", "4")
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "AppRotateFiles", "1")
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "AppRotateOnline", "1")
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "AppRotateSeconds", "86400")
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "AppRotateBytes", "10485760")
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "AppExit", "Default", "Restart")
Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "AppRestartDelay", "5000")

$envFile = Join-Path $projectRoot ".env"
if (Test-Path $envFile) {
    $lines = Get-Content $envFile | Where-Object {
        $_ -and $_ -notmatch '^\s*#' -and $_ -match '='
    }
    if ($lines.Count -gt 0) {
        $envExtra = ($lines -join "`n")
        Invoke-Nssm -Executable $nssm -Arguments @("set", $ServiceName, "AppEnvironmentExtra", $envExtra)
        Write-Host "Loaded environment variables from .env"
    }
}

Invoke-Nssm -Executable $nssm -Arguments @("start", $ServiceName)
$installed = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $installed) {
    throw "Service '$ServiceName' was not created. Check NSSM output above."
}
Write-Host "Installed and started service '$ServiceName' (status: $($installed.Status))."
Write-Host "Python : $pythonExe"
Write-Host "Workdir: $projectRoot"
