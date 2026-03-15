# Service Management — GoPlay API

Hệ thống quản lý daemon cho GoPlay Auto TopUp API trên Windows Server.

## Kiến Trúc

```
┌─────────────────────────────────────────────┐
│  Registry Run Key (auto-start khi login)    │
│  HKCU\...\Run\GoPlayAPI                     │
└──────────────────┬──────────────────────────┘
                   │ trigger
                   ▼
┌─────────────────────────────────────────────┐
│  run_daemon.ps1 (PowerShell Watchdog)       │
│  - Chạy ẩn (Hidden Window)                  │
│  - Loop: start → monitor → restart on crash │
│  - Ghi log: daemon.log                      │
│  - PID file: goplay_api.pid                 │
└──────────────────┬──────────────────────────┘
                   │ spawn
                   ▼
┌─────────────────────────────────────────────┐
│  uvicorn main:app --host 0.0.0.0 --port 8000│
│  FastAPI + Queue Worker                     │
│  - Ghi log: app.log                         │
└─────────────────────────────────────────────┘
```

## Files

| File | Mô tả |
|------|--------|
| `service_manager.bat` | Script quản lý chính (install/start/stop/restart/status) |
| `run_daemon.ps1` | PowerShell daemon với watchdog loop |
| `start_hidden.ps1` | Helper: khởi động daemon ẩn cửa sổ |
| `trigger_start.bat` | Helper: khởi động daemon qua SSH |
| `run_api.bat` | Chạy trực tiếp (không daemon, dùng để debug) |

## Sử Dụng

### Quản lý Service

```bat
service_manager.bat install    # Đăng ký auto-start khi user login
service_manager.bat start      # Khởi động daemon
service_manager.bat status     # Xem trạng thái daemon + uvicorn + port
service_manager.bat stop       # Dừng daemon + uvicorn
service_manager.bat restart    # Restart daemon
service_manager.bat uninstall  # Gỡ auto-start + dừng service
```

### Khởi động từ xa (SSH)

```bash
# Cách 1: Dùng trigger script
ssh garena@<IP> "C:\Users\garena\goplay-auto-login\trigger_start.bat"

# Cách 2: Dùng service_manager
ssh garena@<IP> "C:\Users\garena\goplay-auto-login\service_manager.bat start"

# Kiểm tra status
ssh garena@<IP> "C:\Users\garena\goplay-auto-login\service_manager.bat status"
```

### Debug (chạy trực tiếp, có console output)

```bat
run_api.bat
```

## Cơ Chế Hoạt Động

1. **Auto-start**: Registry Run key → khi user `garena` login Windows → daemon tự chạy
2. **Watchdog**: `run_daemon.ps1` chạy uvicorn trong vòng lặp → nếu crash → đợi 5s → restart
3. **PID tracking**: File `goplay_api.pid` lưu PID của daemon + uvicorn → dùng để stop/status
4. **Logging**: `daemon.log` (sự kiện daemon), `app.log` (API log)

## Lưu Ý

- **Yêu cầu user login**: Vì app dùng Chrome browser automation, cần user `garena` đã login Windows (RDP session).
- **Không dùng Windows Service**: Chrome cần desktop context (Session 0 không có GUI).
- **Port**: API chạy trên port `8000` (HTTP).
