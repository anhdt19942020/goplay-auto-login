@echo off
cd /d C:\Users\garena\goplay-auto-login
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 >nul
python -m uvicorn main:app --host 0.0.0.0 --port 8000
