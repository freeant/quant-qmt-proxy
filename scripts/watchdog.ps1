#Requires -Version 5.1
<#
.SYNOPSIS
    Watch xtquant-proxy liveness and restart on crash or heartbeat stall.

.DESCRIPTION
    Polls GET /health/live. Restarts the Windows service (NSSM) or the run.py
    process when probes fail repeatedly or heartbeat_age_seconds exceeds threshold.

    Do NOT use /health/ready for restart decisions; QMT disconnect returns 503
    but the proxy process may still be healthy.

.EXAMPLE
    .\scripts\watchdog.ps1
    .\scripts\watchdog.ps1 -ServiceName xtquant-proxy -IntervalSeconds 30
#>
param(
    [string] $HealthUrl = "http://127.0.0.1:8000/health/live",
    [int] $IntervalSeconds = 30,
    [int] $FailureThreshold = 3,
    [int] $RequestTimeoutSeconds = 5,
    [double] $HeartbeatMaxAgeSeconds = 60,
    [string] $ServiceName = "xtquant-proxy",
    [string] $ProjectRoot = "",
    [string] $LogFile = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function Resolve-ProjectRoot {
    param([string] $Root)
    if ($Root) {
        return (Resolve-Path $Root).Path
    }
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Write-WatchdogLog {
    param([string] $Message)
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    if ($script:LogPath) {
        Add-Content -Path $script:LogPath -Value $line
    }
}

function Test-ServiceInstalled {
    param([string] $Name)
    return [bool](Get-Service -Name $Name -ErrorAction SilentlyContinue)
}

function Resolve-NssmExecutable {
    param([string] $Root)
    $fromPath = Get-Command nssm -ErrorAction SilentlyContinue
    if ($fromPath) {
        return $fromPath.Source
    }
    $localNssm = Join-Path $Root "tools\nssm\nssm.exe"
    if (Test-Path $localNssm) {
        return (Resolve-Path $localNssm).Path
    }
    return $null
}

function Restart-ProxyService {
    param(
        [string] $Name,
        [string] $Root
    )
    $nssmExe = Resolve-NssmExecutable -Root $Root
    if ($nssmExe) {
        & $nssmExe restart $Name
        Write-WatchdogLog "Restarted Windows service via NSSM: $Name"
        return
    }
    Restart-Service -Name $Name -Force
    Write-WatchdogLog "Restarted Windows service: $Name"
}

function Stop-ProxyProcess {
    param([string] $Root)
    $pythonPath = Join-Path $Root "run.py"
    $processes = Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -like "*$pythonPath*"
        }
    foreach ($proc in $processes) {
        Write-WatchdogLog "Stopping process pid=$($proc.ProcessId)"
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Start-ProxyProcess {
    param([string] $Root)
    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
    $pythonExe = if (Test-Path $venvPython) { $venvPython } else { (Get-Command python).Source }
    $runPy = Join-Path $Root "run.py"
    Start-Process -FilePath $pythonExe -ArgumentList $runPy -WorkingDirectory $Root -WindowStyle Hidden
    Write-WatchdogLog "Started proxy process: $pythonExe $runPy"
}

function Restart-Proxy {
    param(
        [string] $Service,
        [string] $Root
    )
    if (Test-ServiceInstalled -Name $Service) {
        try {
            Restart-ProxyService -Name $Service -Root $Root
            return
        } catch {
            Write-WatchdogLog "Service restart failed: $($_.Exception.Message)"
        }
    }
    Stop-ProxyProcess -Root $Root
    Start-Sleep -Seconds 2
    Start-ProxyProcess -Root $Root
}

function Invoke-LivenessProbe {
    param(
        [string] $Url,
        [int] $TimeoutSeconds
    )
    $response = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec $TimeoutSeconds -UseBasicParsing
    if ($response.StatusCode -ne 200) {
        return @{
            Ok = $false
            Reason = "HTTP $($response.StatusCode)"
        }
    }
    $payload = $response.Content | ConvertFrom-Json
    if (-not $payload.success) {
        return @{
            Ok = $false
            Reason = "success=false"
        }
    }
    $data = $payload.data
    if (-not $data) {
        return @{
            Ok = $false
            Reason = "missing data"
        }
    }
    $heartbeatAge = [double]$data.heartbeat_age_seconds
    if ($heartbeatAge -gt $HeartbeatMaxAgeSeconds) {
        return @{
            Ok = $false
            Reason = "heartbeat_age_seconds=$heartbeatAge (> $HeartbeatMaxAgeSeconds)"
        }
    }
    return @{
        Ok = $true
        Reason = "pid=$($data.pid) uptime=$($data.uptime_seconds)s heartbeat_age=$heartbeatAge"
    }
}

$projectRoot = Resolve-ProjectRoot -Root $ProjectRoot
$script:LogPath = if ($LogFile) { $LogFile } else { Join-Path $projectRoot "logs\watchdog.log" }
$logDir = Split-Path $script:LogPath -Parent
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$consecutiveFailures = 0
Write-WatchdogLog "Watchdog started. url=$HealthUrl interval=${IntervalSeconds}s threshold=$FailureThreshold heartbeat_max_age=${HeartbeatMaxAgeSeconds}s"

while ($true) {
    try {
        $result = Invoke-LivenessProbe -Url $HealthUrl -TimeoutSeconds $RequestTimeoutSeconds
        if ($result.Ok) {
            if ($consecutiveFailures -gt 0) {
                Write-WatchdogLog "Recovered after $consecutiveFailures failure(s). $($result.Reason)"
            }
            $consecutiveFailures = 0
        } else {
            $consecutiveFailures += 1
            Write-WatchdogLog "Probe failed ($consecutiveFailures/$FailureThreshold): $($result.Reason)"
            if ($consecutiveFailures -ge $FailureThreshold) {
                Write-WatchdogLog "Restarting proxy due to repeated liveness failures."
                Restart-Proxy -Service $ServiceName -Root $projectRoot
                $consecutiveFailures = 0
                Start-Sleep -Seconds 15
            }
        }
    } catch {
        $consecutiveFailures += 1
        Write-WatchdogLog "Probe exception ($consecutiveFailures/$FailureThreshold): $($_.Exception.Message)"
        if ($consecutiveFailures -ge $FailureThreshold) {
            Write-WatchdogLog "Restarting proxy due to repeated probe exceptions."
            Restart-Proxy -Service $ServiceName -Root $projectRoot
            $consecutiveFailures = 0
            Start-Sleep -Seconds 15
        }
    }
    Start-Sleep -Seconds $IntervalSeconds
}
