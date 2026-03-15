# GoPlay API Daemon - PowerShell Watchdog
# Runs uvicorn in a loop, auto-restarts on crash.

$workDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $workDir "goplay_api.pid"
$logFile = Join-Path $workDir "daemon.log"
$restartDelay = 5

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts $msg" | Out-File -Append -Encoding utf8 $logFile
}

# Save daemon PID
$PID | Out-File -Encoding ascii $pidFile
Write-Log "Daemon started (PID: $PID)"

$global:childProc = $null

# Cleanup on exit
Register-EngineEvent PowerShell.Exiting -Action {
    if ($global:childProc -and !$global:childProc.HasExited) {
        $global:childProc.Kill()
    }
    if (Test-Path $pidFile) { Remove-Item $pidFile -Force }
}

while ($true) {
    Write-Log "Starting uvicorn..."

    $global:childProc = Start-Process -FilePath "python" `
        -ArgumentList "-m uvicorn main:app --host 0.0.0.0 --port 8000" `
        -WorkingDirectory $workDir `
        -PassThru -NoNewWindow

    # Update PID file with child process ID
    "$PID`n$($global:childProc.Id)" | Out-File -Encoding ascii $pidFile

    $global:childProc.WaitForExit()
    $exitCode = $global:childProc.ExitCode

    Write-Log "Uvicorn stopped (exit: $exitCode). Restarting in ${restartDelay}s..."
    Start-Sleep -Seconds $restartDelay
}
