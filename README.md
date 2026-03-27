# GoPlay Auto TopUp

Hệ thống tự động nạp thẻ GoPlay.vn qua trình duyệt Chrome, cung cấp REST API để tích hợp.

## Kiến Trúc

```
┌──────────────┐     ┌────────────────┐     ┌────────────────────┐
│  Client API  │────▶│  FastAPI + Queue│────▶│  GoPlayService     │
│  (callback)  │◀────│  (main.py)     │     │  (DrissionPage)    │
└──────────────┘     └────────────────┘     └────────┬───────────┘
                                                     │
                                            ┌────────▼───────────┐
                                            │  Chrome Browser    │
                                            │  (Headless/GUI)    │
                                            └────────────────────┘
```

## Cấu Trúc File

| File | Mô tả |
|------|-------|
| `main.py` | FastAPI server, queue worker, API endpoints |
| `goplay_service.py` | Core service: login, navigate, Turnstile, topup |
| `enums.py` | Game codes, packages, error codes |
| `telegram_service.py` | Telegram notification & callback |
| `requirements.txt` | Python dependencies |

## API

### POST `/go-play/topup`

Nạp thẻ vào game. Request được xử lý bất đồng bộ qua queue.

**Request:**
```json
{
    "game": "CF",
    "account": "username",
    "password": "password",
    "package": "GO_100",
    "card_serial": "123456789",
    "card_code": "987654321",
    "url_callback": "https://example.com/callback"
}
```

**Games hỗ trợ:** `CF` (Crossfire), `DREAMY` (Dreamy), `VPT` (Võ Lâm)

**Response (queued):**
```json
{
    "success": true,
    "message": "Yêu cầu xử lý ngầm đã vào hàng đợi (vị trí thứ 1)",
    "detail": {
        "queue_position": 1,
        "url_callback": "https://example.com/callback"
    }
}
```

**Callback (khi xử lý xong):**
```json
{
    "success": true,
    "error_code": null,
    "message": "Nạp thẻ thành công",
    "detail": {
        "game": "CF",
        "package": "GO_100",
        "go_received": 100,
        "balance": 500
    }
}
```

### GET `/go-play/health`

Health check.

### GET `/go-play/queue-status`

Trạng thái queue hiện tại.

## Tối Ưu Hiệu Năng

### 1. Session Cookie Store

Lưu cookies đăng nhập mỗi account vào `sessions/{account}.json`. Khi account quay lại:
- **Có session saved** → inject cookies via CDP → skip login hoàn toàn (~17s saved)
- **Session expired** → tự động login fresh, save session mới
- **TTL:** 12 giờ

```
Flow: Request → Load session → Valid? → Skip login! 
                                  ↓ No
                           Fresh login → Save session
```

**Fallback 3 tầng:**
1. `_load_session()` — TTL check + `.userInfo` validation → fail → login fresh
2. `topup()` → navigate bị redirect → `SESSION_EXPIRED` → `force_fresh=True` login
3. `_login()` same account → `.userInfo` không hiện → clear + login fresh

### 2. Turnstile Optimization

- **Single strategy:** `renderEnableVerify` + iframe CDP click (~2-3s vs 46s cũ)
- **Cache invalidation:** Token là single-use, auto-reset widget khi bị reject
- **Auto-retry:** Cached token bị reject → invalidate → solve fresh → retry HTTP POST

### 3. Skip Navigation

Nếu browser đã ở đúng game page → skip `page.get()` (~5s saved).

### 4. HTTP-First Topup

- **Primary:** HTTP POST trực tiếp (nhanh hơn browser form)
- **Fallback:** Browser-native form nếu HTTP bị captcha reject

## Hiệu Năng Thực Tế

| Scenario | Thời gian |
|----------|-----------|
| Lần đầu (full login) | ~33-54s |
| Cùng account (skip login + navigate) | ~16s |
| Account quay lại (session restore) | ~22s |

## Triển Khai

### Local

```bash
pip install -r requirements.txt
python main.py
# Server chạy tại http://localhost:8000
```

### Server (Windows)

```bash
# SSH vào server
ssh garena@124.158.4.122

# Pull code mới & restart
cd C:\Users\garena\goplay-auto-login
git pull
taskkill /F /IM python.exe
powershell -Command "Start-Process python -ArgumentList main.py -WindowStyle Hidden"
```

### Docker

```bash
docker-compose up -d
```

## Cấu Hình

| Biến môi trường | Mặc định | Mô tả |
|-----------------|----------|-------|
| `GOPLAY_PROXY` | (none) | SOCKS5 proxy URL |
| `TELEGRAM_BOT_TOKEN` | (hardcoded) | Bot token cho notification |
| `TELEGRAM_CHAT_ID` | (hardcoded) | Chat ID nhận thông báo |

## Error Codes

| Code | Mô tả |
|------|-------|
| `WRONG_PASSWORD` | Sai mật khẩu |
| `ACCOUNT_LOCKED` | Tài khoản bị khóa |
| `ACCOUNT_NOT_FOUND` | Tài khoản không tồn tại |
| `ACCOUNT_NOT_REGISTERED` | Chưa đăng ký GoPlay |
| `LOGIN_TIMEOUT` | Đăng nhập quá thời gian |
| `CAPTCHA_REQUIRED` | Turnstile captcha thất bại |
| `PAYMENT_ERROR` | Lỗi thanh toán (thẻ sai, hết hạn...) |
| `INVALID_CARD_INFO` | Serial/mã thẻ không hợp lệ |
| `BROWSER_ERROR` | Lỗi trình duyệt Chrome |
| `UNKNOWN_ERROR` | Lỗi không xác định |

## Monitoring

- **Log file:** `app.log` (UTF-8, auto-rotate nên giám sát kích thước)
- **Debug HTML:** `debug/topup_error.html` (lưu khi có lỗi)
- **Telegram:** Thông báo kết quả mỗi lần nạp thẻ
- **Session files:** `sessions/*.json` (cookies cached)
