Start-Process powershell -ArgumentList @(
    "-ExecutionPolicy", "Bypass",
    "-WindowStyle", "Hidden",
    "-File", "C:\Users\garena\goplay-auto-login\run_daemon.ps1"
) -WindowStyle Hidden
