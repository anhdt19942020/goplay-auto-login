@echo off
setlocal enabledelayedexpansion

set "APP_NAME=GoPlayAPI"
set "WORK_DIR=%~dp0"
set "DAEMON_SCRIPT=%WORK_DIR%run_daemon.ps1"
set "PID_FILE=%WORK_DIR%goplay_api.pid"
set "REG_KEY=HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
set "REG_CMD=powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%DAEMON_SCRIPT%""

if "%1"=="" goto usage
if "%1"=="install" goto install
if "%1"=="uninstall" goto uninstall
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
if "%1"=="status" goto status
goto usage

:install
echo [%APP_NAME%] Installing auto-start registry key...
reg add "%REG_KEY%" /v "%APP_NAME%" /t REG_SZ /d "%REG_CMD%" /f
if %errorlevel%==0 (
    echo [OK] Auto-start registered. API will start when user logs in.
) else (
    echo [FAIL] Could not add registry key.
)
goto end

:uninstall
echo [%APP_NAME%] Removing auto-start registry key...
reg delete "%REG_KEY%" /v "%APP_NAME%" /f 2>nul
echo [OK] Auto-start removed.
call :do_stop
goto end

:start
echo [%APP_NAME%] Starting daemon...
:: Check if already running
if exist "%PID_FILE%" (
    for /f "tokens=1" %%p in (%PID_FILE%) do (
        tasklist /fi "PID eq %%p" 2>nul | findstr /i "powershell" >nul
        if !errorlevel!==0 (
            echo [WARN] Daemon already running (PID: %%p)
            goto end
        )
    )
    del "%PID_FILE%" 2>nul
)
:: Use schtasks to launch in interactive session (works from SSH too)
schtasks /create /tn "%APP_NAME%_Start" /tr "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File %DAEMON_SCRIPT%" /sc once /st 00:00 /f >nul 2>&1
schtasks /run /tn "%APP_NAME%_Start" >nul 2>&1
timeout /t 5 /nobreak >nul
schtasks /delete /tn "%APP_NAME%_Start" /f >nul 2>&1
if exist "%PID_FILE%" (
    for /f "tokens=1" %%p in (%PID_FILE%) do echo [OK] Daemon started (PID: %%p)
) else (
    echo [OK] Daemon starting...
)
goto end

:stop
call :do_stop
goto end

:do_stop
echo [%APP_NAME%] Stopping...
if not exist "%PID_FILE%" (
    echo [INFO] PID file not found. Trying to find process...
    goto kill_by_name
)
:: Kill all PIDs in the file (daemon + child)
for /f "tokens=*" %%p in (%PID_FILE%) do (
    taskkill /PID %%p /F 2>nul >nul
)
del "%PID_FILE%" 2>nul
echo [OK] Stopped.
goto :eof

:kill_by_name
:: Fallback: kill uvicorn python processes on port 8000
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "LISTEN" ^| findstr ":8000"') do (
    taskkill /PID %%p /F 2>nul >nul
    echo [OK] Killed process on port 8000 (PID: %%p)
)
goto :eof

:restart
call :do_stop
timeout /t 2 /nobreak >nul
goto start

:status
echo === %APP_NAME% Status ===
if exist "%PID_FILE%" (
    set "daemon_pid="
    set "child_pid="
    set "line=0"
    for /f "tokens=*" %%p in (%PID_FILE%) do (
        set /a line+=1
        if !line!==1 set "daemon_pid=%%p"
        if !line!==2 set "child_pid=%%p"
    )
    if defined daemon_pid (
        tasklist /fi "PID eq !daemon_pid!" 2>nul | findstr /i "powershell" >nul
        if !errorlevel!==0 (
            echo Daemon:  RUNNING (PID: !daemon_pid!)
        ) else (
            echo Daemon:  DEAD (stale PID: !daemon_pid!)
        )
    )
    if defined child_pid (
        tasklist /fi "PID eq !child_pid!" 2>nul | findstr /i "python" >nul
        if !errorlevel!==0 (
            echo Uvicorn: RUNNING (PID: !child_pid!)
        ) else (
            echo Uvicorn: DEAD (stale PID: !child_pid!)
        )
    )
) else (
    echo Daemon:  NOT RUNNING
)
:: Check port
netstat -ano | findstr "LISTEN" | findstr ":8000" >nul
if %errorlevel%==0 (
    echo Port:    8000 LISTENING
) else (
    echo Port:    8000 NOT LISTENING
)
goto end

:usage
echo.
echo  GoPlay API Service Manager
echo  ===========================
echo  Usage: %~nx0 {command}
echo.
echo  Commands:
echo    install   - Register auto-start on login
echo    uninstall - Remove auto-start + stop service
echo    start     - Start the API daemon
echo    stop      - Stop the API daemon
echo    restart   - Restart the API daemon
echo    status    - Show daemon status
echo.

:end
endlocal
