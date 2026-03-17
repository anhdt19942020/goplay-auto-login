"""
GoPlay API Recon Script — Phase 1B
Captures ALL network requests during login + topup flow using CDP.

Usage:
  python recon_api.py --account USERNAME --password PASSWORD
  python recon_api.py --login-only --account USERNAME --password PASSWORD

Output:
  - Console log of all intercepted requests
  - recon_output.json — structured data for analysis
"""

import argparse
import json
import os
import time
import logging

from DrissionPage import ChromiumOptions, ChromiumPage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(WORKSPACE, "recon_output.json")


class NetworkCapture:
    """Capture network requests via CDP Network domain"""

    def __init__(self, page: ChromiumPage):
        self.page = page
        self.requests: list[dict] = []
        self._setup_listeners()

    def _setup_listeners(self):
        """Enable CDP network listeners"""
        self.page.run_cdp("Network.enable")
        logger.info("CDP Network monitoring enabled")

    def capture_snapshot(self, label: str = ""):
        """Take a snapshot of cookies and localStorage"""
        cookies = []
        try:
            cdp_cookies = self.page.run_cdp("Network.getAllCookies")
            cookies = cdp_cookies.get("cookies", [])
        except Exception as e:
            logger.warning(f"Could not get cookies: {e}")

        local_storage = {}
        try:
            local_storage = self.page.run_js("""
                const data = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    data[key] = localStorage.getItem(key);
                }
                return data;
            """)
        except Exception:
            pass

        return {
            "label": label,
            "url": self.page.url,
            "cookies": cookies,
            "localStorage": local_storage,
            "timestamp": time.time(),
        }

    def get_csrf_token(self) -> str | None:
        """Extract __RequestVerificationToken from page"""
        try:
            token_el = self.page.ele('css:input[name="__RequestVerificationToken"]', timeout=2)
            if token_el:
                return token_el.attr("value")
        except Exception:
            pass
        return None

    def get_turnstile_sitekey(self) -> str | None:
        """Extract Turnstile sitekey from page"""
        try:
            ts = self.page.ele('css:[data-sitekey]', timeout=2)
            if ts:
                return ts.attr("data-sitekey")
            # Also check cf-turnstile div
            ts = self.page.ele('css:.cf-turnstile', timeout=2)
            if ts:
                return ts.attr("data-sitekey")
        except Exception:
            pass
        # Fallback: search in JS
        try:
            return self.page.run_js("""
                const el = document.querySelector('[data-sitekey]');
                return el ? el.getAttribute('data-sitekey') : null;
            """)
        except Exception:
            return None

    def intercept_xhr_fetch(self) -> list[dict]:
        """Inject XHR/Fetch interceptor to capture request/response pairs"""
        self.page.run_js("""
            if (!window.__recon_requests) {
                window.__recon_requests = [];
                // Intercept fetch
                const origFetch = window.fetch;
                window.fetch = async function(...args) {
                    const [url, opts] = args;
                    const entry = {
                        type: 'fetch',
                        url: typeof url === 'string' ? url : url.url,
                        method: opts?.method || 'GET',
                        headers: opts?.headers || {},
                        body: opts?.body || null,
                        timestamp: Date.now(),
                    };
                    try {
                        const resp = await origFetch.apply(this, args);
                        const clone = resp.clone();
                        let respBody = null;
                        try { respBody = await clone.text(); } catch(e) {}
                        entry.status = resp.status;
                        entry.responseBody = respBody;
                        window.__recon_requests.push(entry);
                        return resp;
                    } catch(e) {
                        entry.error = e.toString();
                        window.__recon_requests.push(entry);
                        throw e;
                    }
                };
                // Intercept XMLHttpRequest
                const origOpen = XMLHttpRequest.prototype.open;
                const origSend = XMLHttpRequest.prototype.send;
                XMLHttpRequest.prototype.open = function(method, url, ...rest) {
                    this.__recon = { type: 'xhr', method, url, timestamp: Date.now() };
                    return origOpen.call(this, method, url, ...rest);
                };
                XMLHttpRequest.prototype.send = function(body) {
                    if (this.__recon) {
                        this.__recon.body = body;
                        this.addEventListener('load', function() {
                            this.__recon.status = this.status;
                            this.__recon.responseBody = this.responseText?.substring(0, 2000);
                            window.__recon_requests.push(this.__recon);
                        });
                    }
                    return origSend.call(this, body);
                };
            }
        """)
        logger.info("XHR/Fetch interceptor injected")

    def collect_intercepted(self) -> list[dict]:
        """Collect intercepted requests from JS"""
        try:
            data = self.page.run_js("return window.__recon_requests || [];")
            return data if data else []
        except Exception:
            return []


def create_browser() -> ChromiumPage:
    """Create a fresh Chrome instance for recon"""
    opts = ChromiumOptions()
    profile = os.path.join(WORKSPACE, "chrome_profile_recon")
    opts.set_user_data_path(profile)
    opts.set_local_port(9333)  # Different port from main service
    opts.set_argument("--disable-notifications")
    opts.set_argument("--disable-blink-features=AutomationControlled")
    opts.remove_argument("--enable-automation")
    opts.set_argument("--window-size=1280,720")

    for candidate in [
        os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LocalAppData", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]:
        if os.path.isfile(candidate):
            opts.set_browser_path(candidate)
            break

    return ChromiumPage(opts)


def recon_login(page: ChromiumPage, capture: NetworkCapture, account: str, password: str):
    """Perform login flow with network capture"""

    # Step 0: Navigate to login page
    logger.info("=" * 60)
    logger.info("STEP 0: Navigate to GoPlay login")
    logger.info("=" * 60)
    try:
        page.get("https://goplay.vn/oauth/dang-nhap/tai-khoan", timeout=30)
    except Exception as e:
        logger.error(f"Navigation failed: {e}")
        logger.info("Retrying...")
        page.get("https://goplay.vn/oauth/dang-nhap/tai-khoan", timeout=30)
    time.sleep(3)

    # Inject interceptor
    capture.intercept_xhr_fetch()

    # Capture initial state
    csrf = capture.get_csrf_token()
    sitekey = capture.get_turnstile_sitekey()
    snap_initial = capture.capture_snapshot("initial_login_page")

    logger.info(f"CSRF Token: {csrf[:30]}..." if csrf else "CSRF Token: NOT FOUND")
    logger.info(f"Turnstile Sitekey: {sitekey}" if sitekey else "Turnstile Sitekey: NOT FOUND")
    logger.info(f"Cookies count: {len(snap_initial['cookies'])}")

    # Step 1: Enter username and submit
    logger.info("=" * 60)
    logger.info("STEP 1: Submit username")
    logger.info("=" * 60)

    username_input = page.ele("css:.vtc-user-login", timeout=5)
    if username_input:
        username_input.input(account)
        logger.info(f"Username entered: {account}")
    else:
        logger.error("Username input not found!")
        return

    # Wait for Turnstile to auto-solve or user interaction
    logger.info("Waiting for Turnstile verification (may need manual click)...")
    time.sleep(5)  # Give Turnstile time

    # Check Turnstile response
    turnstile_token = None
    try:
        ts_input = page.ele('css:input[name="cf-turnstile-response"]', timeout=2)
        if ts_input:
            turnstile_token = ts_input.attr("value")
            if turnstile_token:
                logger.info(f"Turnstile Token: {turnstile_token[:30]}...")
            else:
                logger.warning("Turnstile token is empty — needs manual verification")
    except Exception:
        logger.warning("Could not find Turnstile response input")

    # Click submit username — try multiple selectors
    submit_btn = page.ele("#btn-submit-username", timeout=5)
    if not submit_btn:
        submit_btn = page.ele('css:button[type="submit"]', timeout=3)
    if not submit_btn:
        submit_btn = page.ele('text:Tiếp tục', timeout=3)
    if submit_btn:
        submit_btn.click()
        logger.info("Clicked submit username")
    else:
        logger.warning("Submit button not found!")

    time.sleep(3)

    # Collect intercepted requests after Step 1
    requests_step1 = capture.collect_intercepted()
    logger.info(f"Captured {len(requests_step1)} XHR/Fetch requests after Step 1:")
    for req in requests_step1:
        logger.info(f"  {req.get('method', '?')} {req.get('url', '?')} → {req.get('status', '?')}")
        if req.get("body"):
            logger.info(f"    Body: {str(req['body'])[:200]}")
        if req.get("responseBody"):
            logger.info(f"    Response: {str(req['responseBody'])[:200]}")

    snap_step1 = capture.capture_snapshot("after_username_submit")

    # Step 2: Enter password
    logger.info("=" * 60)
    logger.info("STEP 2: Submit password")
    logger.info("=" * 60)

    pwd_input = page.ele("#password", timeout=10)
    if pwd_input:
        pwd_input.input(password)
        logger.info("Password entered")

        # Capture new CSRF token (may change between steps)
        csrf2 = capture.get_csrf_token()
        logger.info(f"CSRF Token (Step 2): {csrf2[:30]}..." if csrf2 else "CSRF Token: same or NOT FOUND")

        time.sleep(3)  # Wait for Turnstile

        # Click login
        login_btn = page.ele("#btn-login-pass", timeout=5)
        if not login_btn:
            login_btn = page.ele('text:Đăng nhập', timeout=3)
        if login_btn:
            login_btn.click()
            logger.info("Clicked login button")
        time.sleep(5)

        # Collect intercepted requests after Step 2
        requests_step2 = capture.collect_intercepted()
        new_requests = requests_step2[len(requests_step1):]
        logger.info(f"Captured {len(new_requests)} NEW XHR/Fetch requests after Step 2:")
        for req in new_requests:
            logger.info(f"  {req.get('method', '?')} {req.get('url', '?')} → {req.get('status', '?')}")
            if req.get("body"):
                logger.info(f"    Body: {str(req['body'])[:200]}")
            if req.get("responseBody"):
                logger.info(f"    Response: {str(req['responseBody'])[:200]}")

        snap_step2 = capture.capture_snapshot("after_login")
    else:
        logger.error("Password input not found! Login Step 1 may have failed.")
        snap_step2 = None
        new_requests = []

    return {
        "login_flow": {
            "csrf_token_step1": csrf,
            "csrf_token_step2": csrf2 if pwd_input else None,
            "turnstile_sitekey": sitekey,
            "turnstile_token_sample": turnstile_token[:50] if turnstile_token else None,
            "snapshots": {
                "initial": snap_initial,
                "after_step1": snap_step1,
                "after_step2": snap_step2,
            },
            "intercepted_requests": requests_step1 + new_requests,
        }
    }


def recon_topup(page: ChromiumPage, capture: NetworkCapture, game_code: str = "CF"):
    """Capture topup flow network requests (requires logged-in session)"""

    logger.info("=" * 60)
    logger.info(f"STEP 3: Navigate to store — {game_code}")
    logger.info("=" * 60)

    try:
        page.get(f"https://goplay.vn/cua-hang/{game_code}", timeout=30)
    except Exception as e:
        logger.error(f"Store navigation failed: {e}")
    time.sleep(3)

    capture.intercept_xhr_fetch()

    snap_store = capture.capture_snapshot("store_page")
    csrf_store = capture.get_csrf_token()
    sitekey_store = capture.get_turnstile_sitekey()

    logger.info(f"Store URL: {page.url}")
    logger.info(f"CSRF Token (Store): {csrf_store[:30]}..." if csrf_store else "CSRF: NOT FOUND")
    logger.info(f"Turnstile Sitekey (Store): {sitekey_store}" if sitekey_store else "Turnstile: NOT FOUND on store")

    # Analyze store page structure
    packages = page.eles("css:.goPlay-package")
    logger.info(f"Found {len(packages)} packages on store page")
    for pkg in packages[:5]:
        pack_id = pkg.attr("data-packid")
        pack_name = pkg.text[:50] if pkg.text else "?"
        logger.info(f"  Package: id={pack_id} name={pack_name}")

    # Check for payment forms/scripts
    payment_forms = page.eles("css:form")
    logger.info(f"Found {len(payment_forms)} forms on store page")
    for form in payment_forms:
        action = form.attr("action") or "none"
        method = form.attr("method") or "?"
        logger.info(f"  Form: action={action} method={method}")

    # Look for topup-related JS endpoints in page source
    try:
        api_urls = page.run_js("""
            const scripts = document.querySelectorAll('script:not([src])');
            const urls = [];
            scripts.forEach(s => {
                const text = s.textContent;
                const re = new RegExp('[\'"]([/]api[/][^\'"]+|[/]cua-hang[/][^\'"]+|handler=[^\'"]+)[\'"]', 'g');
                let m;
                while ((m = re.exec(text)) !== null) urls.push(m[1]);
            });
            return urls;
        """)
        if api_urls:
            logger.info(f"Found {len(api_urls)} API-like URLs in inline scripts:")
            for url in api_urls:
                logger.info(f"  {url}")
    except Exception:
        pass

    # Check for goplayShopPopup and related endpoints
    try:
        shop_js = page.run_js("""
            const scripts = document.querySelectorAll('script:not([src])');
            const endpoints = [];
            scripts.forEach(s => {
                const text = s.textContent;
                if (text.includes('handler=') || text.includes('/api/') || text.includes('fetch(')) {
                    const handlerRe = new RegExp('handler=\\\\w+', 'g');
                    let m;
                    while ((m = handlerRe.exec(text)) !== null) endpoints.push(m[0]);
                    const fetchRe = new RegExp('fetch\\\\s*\\\\([\'"]([^\'"]+)[\'"]', 'g');
                    while ((m = fetchRe.exec(text)) !== null) endpoints.push(m[1]);
                }
            });
            return [...new Set(endpoints)];
        """)
        if shop_js:
            logger.info(f"Found {len(shop_js)} handler/fetch endpoints:")
            for ep in shop_js:
                logger.info(f"  {ep}")
    except Exception:
        pass

    return {
        "topup_flow": {
            "store_url": page.url,
            "csrf_token": csrf_store,
            "turnstile_sitekey": sitekey_store,
            "packages_count": len(packages),
            "forms_count": len(payment_forms),
            "snapshot": snap_store,
        }
    }


def main():
    parser = argparse.ArgumentParser(description="GoPlay API Recon Script")
    parser.add_argument("--account", required=True, help="GoPlay username")
    parser.add_argument("--password", required=True, help="GoPlay password")
    parser.add_argument("--login-only", action="store_true", help="Only recon login flow")
    parser.add_argument("--game", default="CF", help="Game code for store recon (default: CF)")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("GoPlay API Recon — Starting")
    logger.info("=" * 60)

    page = create_browser()
    capture = NetworkCapture(page)

    results = {}

    # Phase 1: Login recon
    login_data = recon_login(page, capture, args.account, args.password)
    if login_data:
        results.update(login_data)

    # Phase 2: Topup recon (only if logged in successfully)
    if not args.login_only:
        # Check if logged in
        if page.ele("css:.userInfo", timeout=3):
            logger.info("Login confirmed! Proceeding to store recon...")
            topup_data = recon_topup(page, capture, args.game)
            if topup_data:
                results.update(topup_data)
        else:
            logger.warning("Login may have failed — skipping store recon")
            logger.info(f"Current URL: {page.url}")

    # Save results
    # Clean non-serializable data
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean(i) for i in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        return str(obj)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(clean(results), f, indent=2, ensure_ascii=False)
    logger.info(f"Results saved to: {OUTPUT_FILE}")

    logger.info("=" * 60)
    logger.info("GoPlay API Recon — Complete")
    logger.info("=" * 60)

    # Keep browser open for 10s for manual inspection, then close
    logger.info("Browser will stay open for 10s for inspection...")
    time.sleep(10)
    page.quit()


if __name__ == "__main__":
    main()
