@echo off
title GoPlayAutoLogin
echo Starting GoPlay API...
cd /d "C:\Users\garena\goplay-auto-login"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
