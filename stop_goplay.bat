@echo off
:: Stop goplay-auto-login only — does NOT kill freefire or other services
wmic process where "commandline like '%%goplay-auto-login%%' and name='python.exe'" delete >nul 2>&1
wmic process where "commandline like '%%chrome_profile_vlcm%%' and name='chrome.exe'" delete >nul 2>&1
echo [stop_goplay] goplay-auto-login stopped.
