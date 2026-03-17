# GoPlay API Recon Report

> **Phase 1 + 2 Complete** | Branch: `feature/api-bypass`

## Architecture

GoPlay uses **ASP.NET Core Razor Pages** with Page Handlers.  
All API calls go through a single pattern:

```
POST <current_page_url>?handler=<HandlerName>
Headers:
  Content-Type: application/json
  X-Requested-With: XMLHttpRequest
  RequestVerificationToken: <csrf_token>
Body: JSON
```

## Login API (2 steps, requires Turnstile)

### Step 1: CheckLogin (username)
```
POST /oauth/dang-nhap/tai-khoan?handler=CheckLogin
Body: { "username": "<user>", "captchaToken": "<turnstile_token>" }
```

### Step 2: Login (password)
```
POST /oauth/dang-nhap/tai-khoan?handler=Login  
Body: { "password": "<pass>", "captchaToken": "<turnstile_token>" }
```

**Turnstile sitekey:** `0x4AAAAAAAFIVsTrYE9E1noo`

## Card Topup API (NO Turnstile on server!)

```
POST /cua-hang/<GAME>?handler=Card
Headers: CSRF + Session Cookies
Body: {
  "method": "CARD-VCOIN",
  "serial": "123456789012",
  "code": "123456789012",
  "captchaToken": ""
}
Response: { "success": true, "data": { "totalBalance": 12345 } }
```

## Buy Pack Flow (2-step)

### Step 1: CreateOrder
```
POST /cua-hang/<GAME>?handler=CreateOrder
Body: { "method": "GOGATE", "amount": 20000, "goCoin": 20, "packId": 1, "characterId": "<id>" }
Response: { "success": true, "data": { "shopId": "xxx" } }
```

### Step 2: ConfirmOrder
```
POST /cua-hang/<GAME>?handler=ConfirmOrder
Body: { "shopId": "<from_create>", "method": "GOGATE" }
Response: { "success": true, "data": { "totalBalance": 12345 } }
```

## Security Summary

| Mechanism | Login | Topup/Store |
|-----------|:-----:|:-----------:|
| Turnstile | ✅ Required (2x) | ❌ NOT required |
| CSRF Token | ✅ Required | ✅ Required |
| Session Cookies | — | ✅ Required |
| WAF/Rate Limit | ❌ None | ❌ None |

## Key Cookies

- `goPlayOauth.SharedCookie` — main auth (domain: `.goplay.vn`)
- `GoPlayWeb.SharedCookie` — web session
- `.AspNetCore.Antiforgery.*` — CSRF cookies

## JS Files (source of truth)

- `goplay.shop.popup.js` → `CallPageHandlerApi()` — core HTTP caller
- `goplay.shop.cardcontroller.js` → `handler=Card` (card topup)
- `goplay.shop.app.js` → `CreateOrder` + `ConfirmOrder`
- `goplay.shop.js` → package selection + payment routing

## Feasibility: ~90%

- Login via CapSolver + HTTP: ~93%
- Card Topup via HTTP (no Turnstile): ~92%
- Session reuse: ~95%
