# GoPlay Auto TopUp API

API tự động nạp game trên GoPlay.vn thông qua thẻ VCOIN.

## Yêu cầu

- Python 3.10+
- Google Chrome (đã cài đặt)

## Cài đặt

```bash
pip install -r requirements.txt
```

## Chạy server

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Server chạy tại `http://localhost:8000`
Swagger docs: `http://localhost:8000/docs`

---

## API Endpoints

### 1. Health Check

```
GET /go-play/health
```

**Response:**
```json
{
  "status": "ok"
}
```

---

### 2. Danh sách Game & Gói nạp

```
GET /go-play/games
```

**Response:**
```json
{
  "games": [
    { "code": "CNS", "name": "CATS_AND_SOUP" },
    { "code": "CF", "name": "CROSSFIRE" },
    { "code": "DREAMY", "name": "DREAMY_CAFE" },
    { "code": "VPT", "name": "VUA_PHAP_THUAT" }
  ],
  "packages_crossfire": [
    { "key": "GO_20", "name": "Nhận 20 GO", "go": 20, "price": 20000 },
    { "key": "GO_50", "name": "Nhận 50 GO", "go": 50, "price": 50000 },
    { "key": "GO_100", "name": "Nhận 100 GO", "go": 100, "price": 100000 },
    { "key": "GO_300", "name": "Nhận 300 GO", "go": 300, "price": 300000 },
    { "key": "GO_1000", "name": "Nhận 1,000 GO", "go": 1000, "price": 1000000 },
    { "key": "GO_2000", "name": "Nhận 2,000 GO", "go": 2000, "price": 2000000 }
  ]
}
```

---

### 3. Nạp tiền

```
POST /go-play/topup
```

**Request Body:**

| Field | Type | Required | Mô tả |
|-------|------|----------|--------|
| `game` | string | ✅ | Mã game (`CF`, `CNS`, `DREAMY`, `VPT`) |
| `account` | string | ✅ | Tên đăng nhập GoPlay |
| `password` | string | ✅ | Mật khẩu |
| `package` | string | ✅ | Gói nạp (`GO_20`, `GO_50`, `GO_100`, `GO_300`, `GO_1000`, `GO_2000`) |
| `card_serial` | string | ✅ | Mã serial thẻ VCOIN |
| `card_code` | string | ✅ | Mã thẻ VCOIN |

**Request example:**
```json
{
  "game": "CF",
  "account": "your_username",
  "password": "your_password",
  "package": "GO_100",
  "card_serial": "123456789012",
  "card_code": "987654321098"
}
```

**Response thành công:**
```json
{
  "success": true,
  "error_code": null,
  "message": "Nạp thẻ thành công",
  "detail": {
    "game": "CF",
    "package": "Nhận 100 GO",
    "price": 100000,
    "go": 100
  }
}
```

**Response thất bại:**
```json
{
  "success": false,
  "error_code": "WRONG_PASSWORD",
  "message": "Sai mật khẩu",
  "detail": null
}
```

---

### Bảng mã lỗi (Error Codes)

| Error Code | Mô tả | Khi nào xảy ra |
|------------|--------|-----------------|
| `WRONG_PASSWORD` | Sai mật khẩu | Nhập sai password đăng nhập |
| `ACCOUNT_LOCKED` | Tài khoản bị khóa | Tài khoản bị ban hoặc lock |
| `ACCOUNT_NOT_FOUND` | Tài khoản không tồn tại | Username không tồn tại trên GoPlay |
| `LOGIN_TIMEOUT` | Đăng nhập quá thời gian chờ | Server GoPlay không phản hồi trong 15s |
| `INVALID_GAME` | Mã game không hợp lệ | Gửi game code không nằm trong danh sách |
| `INVALID_PACKAGE` | Gói nạp không hợp lệ | Gửi package key không nằm trong danh sách |
| `PACKAGE_NOT_FOUND` | Không tìm thấy gói nạp trên trang | Gói nạp không hiển thị trên trang game |
| `PAYMENT_NOT_FOUND` | Không tìm thấy phương thức thanh toán | Phương thức thanh toán không khả dụng |
| `PAYMENT_ERROR` | Lỗi thanh toán | Thẻ VCOIN không hợp lệ, hết hạn, v.v. |
| `UNKNOWN_ERROR` | Lỗi không xác định | Lỗi hệ thống hoặc lỗi chưa được phân loại |

---

## Bảng giá gói nạp Crossfire

| Key | Tên | GO | Giá (VNĐ) |
|-----|-----|----|-----------|
| `GO_20` | Nhận 20 GO | 20 | 20,000đ |
| `GO_50` | Nhận 50 GO | 50 | 50,000đ |
| `GO_100` | Nhận 100 GO | 100 | 100,000đ |
| `GO_300` | Nhận 300 GO | 300 | 300,000đ |
| `GO_1000` | Nhận 1,000 GO | 1,000 | 1,000,000đ |
| `GO_2000` | Nhận 2,000 GO | 2,000 | 2,000,000đ |

> **Quy đổi:** 1 GO = 1,000đ

---

## Phương thức thanh toán

Hiện tại API sử dụng **Thẻ VCOIN** (`CARD-VCOIN`) làm mặc định.

Các phương thức khác trên GoPlay (chưa hỗ trợ):
- Quét QR (`BANKTRANFER`)
- ONEPAY (`EPAYMENT-ONEPAY`)
- Momo (`EPAYMENT-MOMO`)
- VTC Pay (`EPAYMENT-VTCPAY`)

---

## Luồng xử lý

```
POST /go-play/topup
    │
    ├── 1. Mở Chrome (DrissionPage)
    ├── 2. Login GoPlay.vn (account/password)
    ├── 3. Vào trang game (/cua-hang/{game})
    ├── 4. Chọn gói nạp
    ├── 5. Chọn thanh toán Thẻ VCOIN
    ├── 6. Click "Tiếp tục"
    ├── 7. Nhập Mã serial + Mã thẻ
    ├── 8. Click "Xác nhận"
    └── 9. Trả kết quả success/error
```

> ⏱️ Mỗi request mất khoảng **15-30 giây** (do điều khiển browser thật).

---

## Lưu ý

- API sử dụng **Chrome thật** (không headless) để bypass Cloudflare Turnstile
- Chỉ xử lý **1 request tại 1 thời điểm**
- Chrome profile lưu tại `./chrome_profile_vlcm/` để giữ session
- Không lưu mật khẩu hoặc thông tin thẻ
