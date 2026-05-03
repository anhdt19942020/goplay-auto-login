# CLAUDE.md

Guidance for Claude Code when working with this repository.

---

## What this is

GoPlay.vn auto top-up service. Customers POST `game` + `account` + `password` + `card_serial` + `card_code`; backend uses Chrome automation (DrissionPage) to log in to goplay.vn and complete card recharge. Result returned via Telegram + optional webhook callback.

**Production runs on VPS `124.158.4.122:8000`.** Same VPS as `nap-ho-free-fire` (port 8001) — do NOT use blanket `Stop-Process -Name python,chrome` as it kills both services.

---

## Architecture

```
POST /go-play/topup
  → validate game + package → enqueue task (asyncio.Queue, MAX_QUEUE_SIZE=5)
        ↓
single queue_worker
  → GoPlayService.topup (DrissionPage Chrome)
        1. _ensure_browser — launch or reuse Chrome (chrome_profile_vlcm/)
        2. login: goplay.vn → username/password form
        3. navigate to game shop → select package
        4. fill card_serial + card_code → submit
        5. confirm result popup
        ↓
Telegram notify + webhook fire-and-forget
```

### Key files

- **`main.py`** — FastAPI. Endpoints: `POST /go-play/topup`, `GET /go-play/health`, `GET /go-play/games`, `GET /go-play/queue-status`. Single queue worker. Browser pre-warmed at startup via `lifespan`.
- **`goplay_service.py`** — `GoPlayService`: `topup()`, `_ensure_browser()`, login/navigate/payment flow. Chrome profile at `chrome_profile_vlcm/` relative to project dir.
- **`enums.py`** — `GameCode` (CF, DREAMY, VPT), package enums, `GoPlayErrorCode`.
- **`telegram_service.py`** — Telegram notification + callback.
- **`run_daemon.ps1`** — PowerShell watchdog: starts uvicorn, auto-restarts on crash, saves PIDs to `goplay_api.pid`.

### Supported games

| Code | Game |
|------|------|
| `CF` | CrossFire (Đột Kích) |
| `DREAMY` | Dreamy |
| `VPT` | VPT |

---

## Production deployment

VPS: `garena@124.158.4.122` (Windows). Project at `C:\Users\garena\goplay-auto-login\`. Daemon managed by `run_daemon.ps1` (PowerShell watchdog).

Chrome profile dir: `C:\Users\garena\goplay-auto-login\chrome_profile_vlcm\`

### Stop goplay (without killing freefire)

```bat
C:\Users\garena\goplay-auto-login\stop_goplay.bat
```

`stop_goplay.bat` kills only:
- Python processes with `goplay-auto-login` in command line
- Chrome processes with `chrome_profile_vlcm` in command line

### Restart procedure

```bash
# 1. Kill goplay only (does NOT kill freefire or other services)
ssh garena@124.158.4.122 "C:\\Users\\garena\\goplay-auto-login\\stop_goplay.bat"
# 2. Start daemon (runs in current SSH session — or use scheduled task if RDP needed)
ssh garena@124.158.4.122 "powershell -File C:\\Users\\garena\\goplay-auto-login\\run_daemon.ps1"
# 3. Verify
curl http://124.158.4.122:8000/go-play/health
```

### Deploy code

```bash
git push origin main
ssh garena@124.158.4.122 "cd C:\Users\garena\goplay-auto-login && git pull --ff-only origin main"
# then restart per above
```

### Test a topup

```bash
curl -X POST http://124.158.4.122:8000/go-play/topup \
  -H "Content-Type: application/json" \
  -d '{"game":"CF","account":"username","password":"pw","card_serial":"123","card_code":"456"}'
```

---

## Error codes

- `WRONG_PASSWORD` / `ACCOUNT_LOCKED` / `ACCOUNT_NOT_FOUND` — login failure, terminal
- `INVALID_CARD_INFO` — wrong card serial/code, terminal
- `CAPTCHA_REQUIRED` — Turnstile captcha not auto-solved
- `PAYMENT_ERROR` / `PACKAGE_NOT_FOUND` — shop navigation failure
- `LOGIN_TIMEOUT` — browser hung during login
- `BROWSER_ERROR` — Chrome failed to launch
- `UNKNOWN_ERROR` — uncaught exception

---

## Co-existing with nap-ho-free-fire

Both services run on the same VPS:
- goplay → port **8000**, Chrome profile `chrome_profile_vlcm/`
- freefire → port **8001**, Chrome profiles `profiles/{account}/`

**Never** use `Stop-Process -Name python,chrome -Force` — it kills both. Always use the service-specific stop scripts (`stop_goplay.bat` / `stop_srv.bat`).
