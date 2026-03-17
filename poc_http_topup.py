"""
GoPlay PoC — HTTP Card Topup
Proves that card topup can be done via HTTP after browser login.

Usage:
  python poc_http_topup.py --account USER --password PASS --serial SERIAL --code CODE [--game CF]

Flow:
  1. Browser login (DrissionPage) → extract session cookies
  2. HTTP GET store page → extract CSRF token
  3. HTTP POST ?handler=Card → verify topup via pure HTTP
"""

import argparse
import json
import logging
import os
import re
import sys
import time

import httpx
from DrissionPage import ChromiumOptions, ChromiumPage

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(WORKSPACE, "poc_topup.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# STEP 1: Browser Login
# ═══════════════════════════════════════════

def create_browser() -> ChromiumPage:
    opts = ChromiumOptions()
    opts.set_user_data_path(os.path.join(WORKSPACE, "chrome_poc"))
    opts.set_local_port(9555)
    opts.set_argument("--disable-notifications")
    opts.set_argument("--disable-blink-features=AutomationControlled")
    opts.remove_argument("--enable-automation")
    opts.set_argument("--window-size=1280,800")

    for path in [
        os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LocalAppData", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]:
        if os.path.isfile(path):
            opts.set_browser_path(path)
            break

    return ChromiumPage(opts)


def wait_turnstile(page: ChromiumPage, timeout: int = 60) -> str | None:
    logger.info(f"  Waiting Turnstile (up to {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            token = page.run_js("""
                const inp = document.querySelector('input[name="cf-turnstile-response"]');
                return (inp && inp.value && inp.value.length > 10) ? inp.value : null;
            """)
            if token:
                logger.info(f"  Turnstile SOLVED: {token[:30]}...")
                return token
        except Exception:
            pass
        time.sleep(2)
    logger.warning("  Turnstile timeout!")
    return None


def browser_login(page: ChromiumPage, account: str, password: str) -> dict:
    """Login via browser, returns cookies dict"""
    logger.info("=" * 50)
    logger.info("STEP 1: Browser Login")
    logger.info("=" * 50)

    page.get("https://goplay.vn/oauth/dang-nhap/tai-khoan", timeout=30)
    time.sleep(3)

    # Handle account picker
    use_other = page.ele("text:Sử dụng tài khoản khác", timeout=3)
    if use_other:
        logger.info("  Account picker detected → clicking 'Sử dụng tài khoản khác'")
        use_other.click()
        time.sleep(2)

    # Enter username
    inp = page.ele("css:input.vtc-user-login", timeout=5)
    if not inp:
        inp = page.ele('css:input[placeholder="Nhập tên đăng nhập"]', timeout=3)
    if inp:
        inp.input(account)
        logger.info(f"  Username: {account}")
    else:
        raise RuntimeError("Username input not found!")

    # Wait Turnstile
    wait_turnstile(page, timeout=60)

    # Click continue
    btn = page.ele("text:Tiếp tục", timeout=5) or page.ele("#btn-submit-username", timeout=3)
    if btn:
        btn.click()
        logger.info("  Clicked 'Tiếp tục'")
    time.sleep(3)

    # Enter password
    pwd = page.ele("#password", timeout=15) or page.ele('css:input[type="password"]', timeout=10)
    if pwd:
        pwd.input(password)
        logger.info("  Password entered")
    else:
        raise RuntimeError("Password field not found — Step 1 may have failed")

    # Wait Turnstile again
    wait_turnstile(page, timeout=60)

    # Click login
    btn2 = page.ele("#btn-login-pass", timeout=5) or page.ele("text:Đăng nhập", timeout=3)
    if btn2:
        btn2.click()
        logger.info("  Clicked 'Đăng nhập'")
    time.sleep(5)

    # Verify login
    if "oauth" in page.url.lower() and "dang-nhap" in page.url.lower():
        raise RuntimeError(f"Login failed! Still on: {page.url}")

    logger.info(f"  ✅ Login OK — URL: {page.url}")

    # Extract ALL cookies via CDP
    cdp_cookies = page.run_cdp("Network.getAllCookies").get("cookies", [])
    cookies = {}
    for c in cdp_cookies:
        if "goplay" in c.get("domain", ""):
            cookies[c["name"]] = c["value"]
            logger.info(f"  Cookie: {c['name']} = {str(c['value'])[:40]}...")

    logger.info(f"  Total GoPlay cookies: {len(cookies)}")
    return cookies


# ═══════════════════════════════════════════
# STEP 2: HTTP — Extract CSRF from Store Page
# ═══════════════════════════════════════════

def extract_csrf_and_turnstile(page: ChromiumPage, game: str) -> tuple[str, str, str]:
    """Navigate browser to store, extract CSRF + Turnstile token.
    Returns (csrf_token, turnstile_token, page_url)."""
    logger.info("=" * 50)
    logger.info(f"STEP 2: Browser GET store page — /cua-hang/{game}")
    logger.info("=" * 50)

    page.get(f"https://goplay.vn/cua-hang/{game}", timeout=30)
    time.sleep(3)
    page_url = page.url
    logger.info(f"  URL: {page_url}")

    # Extract CSRF token from DOM
    csrf_el = page.ele('css:input[name="__RequestVerificationToken"]', timeout=5)
    csrf_token = csrf_el.attr("value") if csrf_el else None
    if not csrf_token:
        raise RuntimeError("CSRF token not found on store page!")
    logger.info(f"  ✅ CSRF: {csrf_token[:40]}...")

    # Extract Turnstile token — trigger render and wait
    logger.info("  Waiting for Turnstile on store page...")
    turnstile_token = wait_turnstile(page, timeout=30)

    # If no auto-solve, try triggering TurnstileHelper.renderEnableVerify
    if not turnstile_token:
        logger.info("  Trying TurnstileHelper.renderEnableVerify()...")
        try:
            page.run_js("""
                if (typeof TurnstileHelper !== 'undefined' && typeof TurnstileHelper.renderEnableVerify === 'function') {
                    TurnstileHelper.renderEnableVerify(function(token) {
                        window.__poc_turnstile = token;
                    }, { timeoutMs: 30000 });
                }
            """)
            # Wait for callback
            for _ in range(15):
                time.sleep(2)
                tt = page.run_js("return window.__poc_turnstile || null;")
                if tt:
                    turnstile_token = tt
                    break
        except Exception as e:
            logger.warning(f"  TurnstileHelper call failed: {e}")

    if turnstile_token:
        logger.info(f"  ✅ Turnstile: {turnstile_token[:40]}...")
    else:
        logger.warning("  ⚠️ No Turnstile token obtained — will try empty")
        turnstile_token = ""

    return csrf_token, turnstile_token, page_url


# ═══════════════════════════════════════════
# STEP 3: HTTP POST — Card Topup
# ═══════════════════════════════════════════

def http_card_topup(
    client: httpx.Client,
    page_url: str,
    csrf_token: str,
    serial: str,
    code: str,
    method: str = "CARD-VCOIN",
    captcha_token: str = "",
) -> dict:
    """POST ?handler=Card to topup via HTTP"""
    logger.info("=" * 50)
    logger.info("STEP 3: HTTP POST — Card Topup")
    logger.info("=" * 50)

    # Build handler URL
    if "?" in page_url:
        api_url = page_url + "&handler=Card"
    else:
        api_url = page_url + "?handler=Card"

    payload = {
        "method": method,
        "serial": serial,
        "code": code,
        "captchaToken": captcha_token,
    }

    headers = {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "RequestVerificationToken": csrf_token,
        "Accept": "application/json",
        "Origin": "https://goplay.vn",
        "Referer": page_url,
    }

    logger.info(f"  URL: {api_url}")
    logger.info(f"  Method: {method}")
    logger.info(f"  Serial: {serial[:4]}****{serial[-4:]}" if len(serial) > 8 else f"  Serial: {serial}")
    logger.info(f"  Code: {code[:4]}****{code[-4:]}" if len(code) > 8 else f"  Code: {code}")

    resp = client.post(api_url, json=payload, headers=headers)

    logger.info(f"  Status: {resp.status_code}")
    logger.info(f"  Content-Type: {resp.headers.get('content-type', 'N/A')}")

    # Parse response
    result = {"status_code": resp.status_code, "raw": resp.text[:500]}

    try:
        data = resp.json()
        result["json"] = data
        logger.info(f"  Response JSON: {json.dumps(data, ensure_ascii=False)[:300]}")

        if data.get("success"):
            logger.info("  🎉 TOPUP SUCCESS!")
            logger.info(f"  Message: {data.get('message', 'N/A')}")
            if data.get("data", {}).get("totalBalance"):
                logger.info(f"  Balance: {data['data']['totalBalance']:,} GO")
        else:
            logger.warning(f"  ❌ TOPUP FAILED: {data.get('message', 'Unknown error')}")
            logger.warning(f"  Code: {data.get('code', 'N/A')}")
    except Exception:
        logger.warning(f"  Non-JSON response: {resp.text[:200]}")

    return result


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="GoPlay PoC — HTTP Card Topup")
    parser.add_argument("--account", required=True, help="GoPlay username")
    parser.add_argument("--password", required=True, help="GoPlay password")
    parser.add_argument("--serial", required=True, help="Card serial number")
    parser.add_argument("--code", required=True, help="Card code")
    parser.add_argument("--game", default="CF", help="Game code (default: CF)")
    parser.add_argument("--method", default="CARD-VCOIN", help="Payment method (default: CARD-VCOIN)")
    parser.add_argument("--dry-run", action="store_true", help="Skip actual topup POST")
    args = parser.parse_args()

    logger.info("╔══════════════════════════════════════╗")
    logger.info("║  GoPlay PoC — HTTP Card Topup        ║")
    logger.info("╚══════════════════════════════════════╝")

    page = None
    try:
        # STEP 1: Browser Login
        page = create_browser()
        cookies = browser_login(page, args.account, args.password)

        if not cookies:
            logger.error("No cookies extracted!")
            sys.exit(1)

        # Create HTTP client with extracted cookies
        client = httpx.Client(
            cookies=cookies,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            },
            timeout=30,
            follow_redirects=True,
        )

        # STEP 2: Navigate browser to store + extract CSRF + Turnstile
        csrf_token, turnstile_token, page_url = extract_csrf_and_turnstile(page, args.game)

        # Also grab fresh cookies from browser after store page
        store_cdp_cookies = page.run_cdp("Network.getAllCookies").get("cookies", [])
        for c in store_cdp_cookies:
            if "goplay" in c.get("domain", ""):
                client.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))

        # STEP 3: HTTP POST — Card Topup
        if args.dry_run:
            logger.info("=" * 50)
            logger.info("DRY RUN — skipping actual topup POST")
            logger.info("=" * 50)
            logger.info(f"  Would POST to: {page_url}?handler=Card")
            logger.info(f"  Turnstile: {'YES' if turnstile_token else 'NO'}")
            logger.info(f"  Payload: serial={args.serial}, code={args.code}, method={args.method}")
            logger.info("  ✅ Dry run complete — all prerequisites verified!")
            result = {"dry_run": True, "csrf": csrf_token[:20], "turnstile": bool(turnstile_token), "cookies_count": len(cookies)}
        else:
            result = http_card_topup(
                client, page_url, csrf_token,
                serial=args.serial, code=args.code, method=args.method,
                captcha_token=turnstile_token,
            )

        # Save result
        output_file = os.path.join(WORKSPACE, "poc_result.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Result saved: {output_file}")

        client.close()

    except Exception as e:
        logger.error(f"FATAL: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if page:
            try:
                time.sleep(3)
                page.quit()
            except Exception:
                pass

    logger.info("=" * 50)
    logger.info("PoC Complete!")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
