# Test API GoPlay TopUp

## Yêu cầu
- Server đang chạy: `python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`

---

## 1. Test Health Check

### cURL
```bash
curl http://localhost:8000/go-play/health
```

### PowerShell
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/go-play/health"
```

**Expected:** `{"status":"ok"}`

---

## 2. Test List Games

### cURL
```bash
curl http://localhost:8000/go-play/games
```

### PowerShell
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/go-play/games" | ConvertTo-Json -Depth 5
```

**Expected:** JSON chứa `games` (4 items) + `packages_crossfire` (6 items)

---

## 3. Test TopUp (Nạp thẻ)

### cURL
```bash
curl -X POST http://localhost:8000/go-play/topup \
  -H "Content-Type: application/json" \
  -d '{
    "game": "CF",
    "account": "your_username",
    "password": "your_password",
    "package": "GO_20",
    "card_serial": "123456789012",
    "card_code": "987654321098"
  }'
```

### PowerShell
```powershell
$body = @{
    game        = "CF"
    account     = "your_username"
    password    = "your_password"
    package     = "GO_20"
    card_serial = "123456789012"
    card_code   = "987654321098"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/go-play/topup" `
    -ContentType "application/json" `
    -Body $body
```

### Python (requests)
```python
import requests

resp = requests.post("http://localhost:8000/go-play/topup", json={
    "game": "CF",
    "account": "your_username",
    "password": "your_password",
    "package": "GO_20",
    "card_serial": "123456789012",
    "card_code": "987654321098",
})
print(resp.json())
```

---

## 4. Test Validation Errors

### Game không hợp lệ
```bash
curl -X POST http://localhost:8000/go-play/topup \
  -H "Content-Type: application/json" \
  -d '{"game":"INVALID","account":"x","password":"x","package":"GO_20","card_serial":"x","card_code":"x"}'
```
**Expected:**
```json
{"success": false, "message": "Invalid game. Valid: ['CNS', 'CF', 'DREAMY', 'VPT']"}
```

### Package không hợp lệ
```bash
curl -X POST http://localhost:8000/go-play/topup \
  -H "Content-Type: application/json" \
  -d '{"game":"CF","account":"x","password":"x","package":"INVALID","card_serial":"x","card_code":"x"}'
```
**Expected:**
```json
{"success": false, "message": "Invalid package. Valid: ['GO_20', 'GO_50', 'GO_100', 'GO_300', 'GO_1000', 'GO_2000']"}
```

---

## 5. Swagger UI (Interactive)

Mở trình duyệt:
```
http://localhost:8000/docs
```

Tại đây có thể test trực tiếp tất cả endpoints bằng giao diện web.

---

## Bảng tham chiếu nhanh

### Game Codes
| Code | Game |
|------|------|
| `CF` | Crossfire |
| `CNS` | Cats & Soup: Fluffy Town |
| `DREAMY` | Dreamy Cafe |
| `VPT` | Vua Pháp Thuật |

### Package Keys
| Key | GO | Giá |
|-----|-----|-----|
| `GO_20` | 20 | 20,000đ |
| `GO_50` | 50 | 50,000đ |
| `GO_100` | 100 | 100,000đ |
| `GO_300` | 300 | 300,000đ |
| `GO_1000` | 1,000 | 1,000,000đ |
| `GO_2000` | 2,000 | 2,000,000đ |
