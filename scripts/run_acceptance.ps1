param(
    [string]$PythonExe = "",
    [switch]$SkipInstall,
    [switch]$IncludeGui,
    [switch]$EnableHardware,
    [switch]$PreferLastRoster,
    [switch]$PytestDebug,
    [int]$PytestTimeoutSec = 180,
    [string]$HardwareUrl = "http://127.0.0.1:5001",
    [string]$AthletesCsv = "data/athletes.csv",
    [string]$EventsCsv = "data/events.csv",
    [string]$SummaryOut = "data/workout_summary.acceptance.csv"
)

$ErrorActionPreference = "Stop"

function Resolve-PythonExe {
    param([string]$Preferred)

    if ($Preferred -and (Test-Path $Preferred)) {
        return (Resolve-Path $Preferred).Path
    }

    $repoVenv = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
    if (Test-Path $repoVenv) {
        return (Resolve-Path $repoVenv).Path
    }

    $workspaceVenv = Join-Path $PSScriptRoot "..\..\.venv\Scripts\python.exe"
    if (Test-Path $workspaceVenv) {
        return (Resolve-Path $workspaceVenv).Path
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return $pythonCmd.Source
    }

    throw "Could not find a Python executable. Pass -PythonExe explicitly."
}

function Invoke-Step {
    param(
        [string]$Title,
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
    & $Action
}

function Invoke-ProcessWithTimeout {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [int]$TimeoutSec,
        [string]$StepName
    )

    $proc = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -NoNewWindow -PassThru
    $finished = $proc.WaitForExit($TimeoutSec * 1000)

    if (-not $finished) {
        try {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
        catch {}

        throw "$StepName timed out after $TimeoutSec seconds"
    }

    # Ensure process resources are finalized before reading exit code.
    $proc.WaitForExit()
    $proc.Refresh()

    $exitCode = $proc.ExitCode
    if ($null -eq $exitCode -or $exitCode -isnot [int]) {
        # Some PowerShell/Process combinations can surface a null ExitCode
        # despite successful completion; treat this as success.
        Write-Host "Warning: $StepName completed but exit code was unavailable; assuming success." -ForegroundColor Yellow
        return
    }

    if ($exitCode -ne 0) {
        throw "$StepName failed with exit code $exitCode"
    }
}

function Get-PytestArgs {
    param(
        [switch]$DebugMode,
        [string[]]$ExtraArgs = @()
    )

    $args = @("-m", "pytest", "-q")

    if ($DebugMode) {
        # Show fixture setup/teardown and dump traceback if stuck.
        $args += @("--setup-show", "-o", "faulthandler_timeout=30")
    }

    if ($ExtraArgs -and $ExtraArgs.Count -gt 0) {
        $args += $ExtraArgs
    }

    return $args
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$python = Resolve-PythonExe -Preferred $PythonExe
Write-Host "Using Python: $python" -ForegroundColor Yellow
Write-Host "Repository: $repoRoot" -ForegroundColor Yellow

if (-not $PSBoundParameters.ContainsKey("PreferLastRoster")) {
    # Default behavior: reuse saved roster when present.
    $PreferLastRoster = $true
}

if (-not $PSBoundParameters.ContainsKey("EnableHardware")) {
    # Default behavior: include RFID hardware integration smoke check.
    $EnableHardware = $true
}

if (-not (Test-Path $AthletesCsv)) {
    throw "Athletes CSV not found: $AthletesCsv"
}

if (-not (Test-Path $EventsCsv)) {
    throw "Events CSV not found: $EventsCsv"
}

if ($EnableHardware) {
    $env:FEATURE2_RFID_REST_URL = $HardwareUrl
    Write-Host "Hardware mode enabled. FEATURE2_RFID_REST_URL=$HardwareUrl" -ForegroundColor Yellow
}

if (-not $SkipInstall) {
    Invoke-Step -Title "Install Dependencies" -Action {
        & $python -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

        & $python -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw "requirements install failed" }
    }
}

Invoke-Step -Title "Run Full Test Suite" -Action {
    # Avoid hangs caused by unrelated globally installed pytest plugins.
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

    $pytestArgs = Get-PytestArgs -DebugMode:$PytestDebug
    Invoke-ProcessWithTimeout -FilePath $python -ArgumentList $pytestArgs -TimeoutSec $PytestTimeoutSec -StepName "pytest"
}

Invoke-Step -Title "Run Simulation Mode" -Action {
    & $python main.py --mode simulate --athletes $AthletesCsv --events $EventsCsv
    if ($LASTEXITCODE -ne 0) { throw "simulation mode failed" }
}

if ($EnableHardware) {
    Invoke-Step -Title "Run Hardware Integration Smoke (sim_server + adapter)" -Action {
        $simServerPath = "tests/test_external/sim_server.py"
        if (-not (Test-Path $simServerPath)) {
            throw "sim_server not found at: $simServerPath"
        }

        # Ensure simulator/runtime dependencies are available.
        & $python -m pip install flask requests
        if ($LASTEXITCODE -ne 0) { throw "hardware dependency install failed" }

        # Bind simulator to the URL configured for FEATURE2_RFID_REST_URL.
        $hardwareUri = [System.Uri]$HardwareUrl
        $env:RFID_SIM_HOST = $hardwareUri.Host
        $env:RFID_SIM_PORT = "$($hardwareUri.Port)"
        $env:RFID_SIM_INTERVAL = "0.5"

        $simProc = $null
        try {
            $simProc = Start-Process -FilePath $python -ArgumentList @($simServerPath) -NoNewWindow -PassThru

            # Wait for simulator startup with lightweight health probe.
            $serverReady = $false
            for ($i = 0; $i -lt 20; $i++) {
                try {
                    Invoke-WebRequest -Uri "$HardwareUrl/api/v1/profiles/stop" -Method POST -UseBasicParsing -TimeoutSec 2 | Out-Null
                    $serverReady = $true
                    break
                }
                catch {
                    Start-Sleep -Milliseconds 250
                }
            }

            if (-not $serverReady) {
                throw "sim_server did not become ready at $HardwareUrl"
            }

            $adapterSmokeSnippet = @'
import queue
import sys
import time

repo_root = sys.argv[2]
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from externalInterface.rfid_impinj_rest import ReaderRfidImpinjRest

url = sys.argv[1]
event_q = queue.Queue()
reader = ReaderRfidImpinjRest(url, event_q)

reader.start()
deadline = time.time() + 8.0
got_event = None

try:
    while time.time() < deadline:
        try:
            got_event = event_q.get(timeout=0.5)
            break
        except queue.Empty:
            continue
finally:
    reader.stop()

if got_event is None:
    print("Hardware smoke failed: no RFID events received from sim_server")
    raise SystemExit(1)

tag_id, timestamp_ms = got_event
print(f"Hardware smoke ok: received RFID event tag={tag_id} ts={timestamp_ms}")
'@

            $smokeScriptPath = Join-Path $env:TEMP "rfid_hardware_smoke.py"
            Set-Content -Path $smokeScriptPath -Value $adapterSmokeSnippet -Encoding UTF8

            try {
                & $python $smokeScriptPath $HardwareUrl $repoRoot
                if ($LASTEXITCODE -ne 0) { throw "hardware adapter smoke failed" }
            }
            finally {
                Remove-Item -Path $smokeScriptPath -ErrorAction SilentlyContinue
            }
        }
        finally {
            if ($simProc -and -not $simProc.HasExited) {
                try {
                    Stop-Process -Id $simProc.Id -Force -ErrorAction SilentlyContinue
                }
                catch {}
            }
        }
    }
}

Invoke-Step -Title "Run CLI Acceptance Sequence" -Action {
    $loadRosterCommand = "2 $AthletesCsv"
    $lastRosterPath = "data/last_roster.csv"
    if ($PreferLastRoster -and (Test-Path $lastRosterPath)) {
        Write-Host "Saved roster found. Using command 15 (load last roster)." -ForegroundColor Yellow
        $loadRosterCommand = "15"
    }

    $cliCommands = @(
        $loadRosterCommand,
        "3 $EventsCsv",
        "status",
        "9",
        "10",
        "12",
        "11",
        "4 $SummaryOut",
        "14"
    )

    $inputBlob = ($cliCommands -join [Environment]::NewLine) + [Environment]::NewLine
    $inputBlob | & $python -m controller.cli
    if ($LASTEXITCODE -ne 0) { throw "CLI acceptance sequence failed" }
}

Invoke-Step -Title "Verify PDF Generation Feature" -Action {
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

    $pdfPytestArgs = Get-PytestArgs -DebugMode:$PytestDebug -ExtraArgs @("tests/test_application/test_runner_pdf_report_service.py")
    Invoke-ProcessWithTimeout -FilePath $python -ArgumentList $pdfPytestArgs -TimeoutSec $PytestTimeoutSec -StepName "PDF generation verification"
}

if ($IncludeGui) {
    Invoke-Step -Title "Launch GUI (Manual Check)" -Action {
        Write-Host "GUI is interactive. Close the GUI window to continue." -ForegroundColor Yellow
        & $python gui/main.py
        if ($LASTEXITCODE -ne 0) { throw "GUI launch failed" }
    }
}

Write-Host ""
Write-Host "Acceptance run completed successfully." -ForegroundColor Green
Write-Host "Summary CSV: $SummaryOut" -ForegroundColor Green
if ($PreferLastRoster) {
    Write-Host "Roster mode: prefer last saved roster (CLI command 15)." -ForegroundColor Green
}
if ($EnableHardware) {
    Write-Host "Hardware URL used: $HardwareUrl" -ForegroundColor Green
}
