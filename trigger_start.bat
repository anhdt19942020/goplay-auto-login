@echo off
cd /d "C:\Users\garena\goplay-auto-login"
schtasks /create /tn "GoPlayDaemonStart" /tr "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\Users\garena\goplay-auto-login\run_daemon.ps1" /sc once /st 00:00 /f
schtasks /run /tn "GoPlayDaemonStart"
timeout /t 3 /nobreak >nul
schtasks /delete /tn "GoPlayDaemonStart" /f
echo Done.
