# 🔬 GoPlay API Recon Report

> **Date:** 2026-03-17
> **Branch:** `feature/api-bypass`
> **Status:** Phase 1A Complete — Static Analysis

---

## 1. Kiến trúc GoPlay

| Thông số | Giá trị |
|----------|---------|
| **Framework** | ASP.NET Core (Razor Pages / Page Handlers) |
| **CDN/WAF** | Cloudflare (Turnstile, KHÔNG phải full WAF challenge) |
| **Auth** | Cookie-based session (`goplay.vn` domain) |
| **CSRF** | `__RequestVerificationToken` (hidden input + header) |
| **Turnstile** | Explicit render mode, sitekey cố định |

---

## 2. Turnstile Configuration

```
Sitekey:  0x4AAAAAAAFIVsTrYE9E1noo
Script:   https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit
Mode:     Explicit (managed by TurnstileHelper JS class)
Widget:   Checkbox visible ở góc dưới phải trang login
```

### TurnstileHelper Class (từ `turnstile-helper.js`)
- `TurnstileHelper.renderEnableVerifyAsync()` — Render + wait for solve
- Token được inject vào field `captchaToken` trong JSON payload
- Token TTL: ~300 giây (Cloudflare standard)

---

## 3. Login API Flow

### Step 1: Check Username
```
POST https://goplay.vn/oauth/dang-nhap/tai-khoan?handler=CheckLogin

Headers:
  Content-Type: application/json
  RequestVerificationToken: <từ hidden input __RequestVerificationToken>

Body (JSON):
  {
    "inputUserName": "tên_đăng_nhập",
    "captchaToken": "cf-turnstile-response-token"
  }

Response: 
  → Success: redirect/show password form
  → Error: "Tài khoản không tồn tại"
```

### Step 2: Login with Password (cần recon thêm)
```
POST https://goplay.vn/oauth/dang-nhap/tai-khoan?handler=Login (dự đoán)

Headers:
  Content-Type: application/json
  RequestVerificationToken: <token mới>

Body (JSON):
  {
    "inputUserName": "...",
    "inputPassword": "...",
    "captchaToken": "cf-turnstile-response-token-mới"
  }

Response:
  → Success: Set-Cookie → session cookies
  → Error: "Sai mật khẩu"
```

---

## 4. Session & Security

### Cookies quan trọng (cần capture)
- Session cookie (ASP.NET Core: `.AspNetCore.Session` hoặc tương tự)
- Authentication cookie
- Cloudflare cookies (`cf_clearance`, `__cf_bm`)

### CSRF Protection
- `__RequestVerificationToken` — lấy từ hidden `<input>` trong HTML form
- Gửi kèm trong header `RequestVerificationToken` (không phải body!)
- Token thay đổi theo session → phải GET page trước, extract token, rồi POST

### localStorage Data
- `userData` — user info sau login
- `deviceId` — UUID v4 random (sinh lần đầu, reuse sau đó)

---

## 5. Topup API Flow (cần recon bằng CDP Network — Phase 1B)

**Dự đoán dựa trên browser automation hiện tại:**

```
Step 1: GET https://goplay.vn/cua-hang/{game_code}
  → Cần session cookies (đã login)
  → Response: HTML với danh sách packages

Step 2: POST (chọn package + payment method)
  → Endpoint: ??? (cần capture)
  → Turnstile: Có thể KHÔNG cần (chỉ UI interaction)

Step 3: POST (submit card serial + code)
  → Endpoint: ??? (cần capture)
  → Turnstile: CÓ THỂ cần (đã thấy _handle_turnstile ở code hiện tại)
```

---

## 6. Đánh giá khả thi (Cập nhật sau Recon)

| Yếu tố | Trước Recon | Sau Recon Phase 1A |
|---------|:-----------:|:------------------:|
| Turnstile solve (CapSolver) | ~90% | **~92%** ✅ Sitekey xác định |
| Reverse-engineer Login API | ~65% | **~85%** ✅ Đã biết endpoint + payload |
| CSRF token extraction | ??? | **~95%** ✅ Đơn giản: GET → parse HTML |
| TLS fingerprint bypass | ~80% | **~85%** (ASP.NET Core, ít strict) |
| Session cookies reuse | ~85% | **~90%** ✅ Cookie-based auth |
| Topup API bypass | ??? | **~60%** ⚠️ Cần recon Phase 1B |

### **Tổng khả thi Phương án C: ~80-85%** (tăng từ ~70-75%)

> **Lý do tăng:** GoPlay dùng ASP.NET Core Page Handlers với JSON API rõ ràng,
> CSRF protection đơn giản (hidden input), Turnstile sitekey cố định.
> Không có advanced anti-bot ngoài Turnstile.

---

## 7. Bước tiếp theo

- [ ] **Phase 1B:** Tạo CDP Network capture script → chạy full topup flow → capture ALL requests
- [ ] **Phase 2:** PoC HTTP Login — dùng `httpx` + CapSolver → login thành công
- [ ] **Phase 3:** PoC HTTP Topup — dùng session cookies → topup bằng HTTP
- [ ] **Phase 4:** Integration — tích hợp vào service chính

---

## 8. Tech Stack cho API Bypass

```
Python libraries cần thiết:
- httpx (async HTTP client)
- capsolver-python (Turnstile solver)  
- beautifulsoup4 (HTML parsing, extract CSRF token)
- curl_cffi (TLS fingerprint impersonation - nếu cần)
```
