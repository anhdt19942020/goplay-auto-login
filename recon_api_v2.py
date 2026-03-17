"""
GoPlay API Recon v2 — Simplified & Robust
Uses DrissionPage to capture login + topup API flow.
Waits for manual Turnstile solve.

Usage:
  python recon_api_v2.py --account USERNAME --password PASSWORD
"""

import argparse
import json
import os
import time
import logging

from DrissionPage import ChromiumOptions, ChromiumPage

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recon.log")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recon_output.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

WORKSPACE = os.path.dirname(os.path.abspath(__file__))


def create_browser() -> ChromiumPage:
    opts = ChromiumOptions()
    opts.set_user_data_path(os.path.join(WORKSPACE, "chrome_recon"))
    opts.set_local_port(9444)
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


def inject_interceptor(page: ChromiumPage):
    """Inject XHR/Fetch interceptor"""
    page.run_js("""
        if (!window.__recon) {
            window.__recon = [];
            const origFetch = window.fetch;
            window.fetch = async function(...args) {
                const [url, opts] = args;
                const entry = {
                    type: 'fetch',
                    url: typeof url === 'string' ? url : url.url,
                    method: (opts && opts.method) || 'GET',
                    body: (opts && opts.body) || null,
                    ts: Date.now(),
                };
                try {
                    const r = await origFetch.apply(this, args);
                    const c = r.clone();
                    try { entry.resp = await c.text(); } catch(e) { entry.resp = null; }
                    entry.status = r.status;
                    window.__recon.push(entry);
                    return r;
                } catch(e) {
                    entry.error = e.toString();
                    window.__recon.push(entry);
                    throw e;
                }
            };
            const xOpen = XMLHttpRequest.prototype.open;
            const xSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.open = function(m, u, ...r) {
                this._r = {type:'xhr', method:m, url:u, ts:Date.now()};
                return xOpen.call(this, m, u, ...r);
            };
            XMLHttpRequest.prototype.send = function(b) {
                if (this._r) {
                    this._r.body = b;
                    this.addEventListener('load', function() {
                        this._r.status = this.status;
                        this._r.resp = (this.responseText || '').substring(0, 3000);
                        window.__recon.push(this._r);
                    });
                }
                return xSend.call(this, b);
            };
            console.log('[RECON] Interceptor active');
        }
    """)
    logger.info("Interceptor injected")


def collect_requests(page: ChromiumPage) -> list:
    try:
        return page.run_js("return window.__recon || [];") or []
    except Exception:
        return []


def get_csrf(page: ChromiumPage) -> str | None:
    try:
        el = page.ele('css:input[name="__RequestVerificationToken"]', timeout=3)
        return el.attr("value") if el else None
    except Exception:
        return None


def get_cookies(page: ChromiumPage) -> list:
    try:
        return page.run_cdp("Network.getAllCookies").get("cookies", [])
    except Exception:
        return []


def wait_for_turnstile(page: ChromiumPage, timeout: int = 60) -> str | None:
    """Wait for Turnstile to be solved (manual or auto)"""
    logger.info(f"Waiting up to {timeout}s for Turnstile solve...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            token = page.run_js("""
                const inputs = document.querySelectorAll('input[name="cf-turnstile-response"]');
                for (const inp of inputs) {
                    if (inp.value && inp.value.length > 10) return inp.value;
                }
                // Also check via Turnstile callback
                if (window.turnstile) {
                    const widgets = document.querySelectorAll('.cf-turnstile iframe');
                    // Check response
                }
                return null;
            """)
            if token:
                logger.info(f"Turnstile SOLVED! Token: {token[:40]}...")
                return token
        except Exception:
            pass
        time.sleep(2)
    logger.warning("Turnstile NOT solved within timeout")
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--game", default="CF")
    args = parser.parse_args()

    results = {"login": {}, "topup": {}, "requests": [], "cookies": []}

    logger.info("=" * 60)
    logger.info("GoPlay API Recon v2")
    logger.info("=" * 60)

    # Kill lingering Chrome on port 9444
    page = create_browser()
    page.run_cdp("Network.enable")

    # ─── STEP 1: Navigate to login ───
    logger.info("STEP 1: Navigate to login page")
    try:
        page.get("https://goplay.vn/oauth/dang-nhap/tai-khoan", timeout=30)
    except Exception as e:
        logger.error(f"Navigation failed: {e}, retrying...")
        time.sleep(3)
        page.get("https://goplay.vn/oauth/dang-nhap/tai-khoan", timeout=30)

    time.sleep(3)

    # Handle "Chọn tài khoản" page (appears if session exists)
    use_other = page.ele("text:Sử dụng tài khoản khác", timeout=3)
    if use_other:
        logger.info("Found 'Sử dụng tài khoản khác' — clicking...")
        use_other.click()
        time.sleep(2)
    else:
        logger.info("Direct login form (no account picker)")

    inject_interceptor(page)

    csrf1 = get_csrf(page)
    logger.info(f"CSRF Token: {csrf1[:40]}..." if csrf1 else "CSRF: NOT FOUND")

    # Find Turnstile sitekey
    sitekey = page.run_js("""
        const el = document.querySelector('.cf-turnstile') || document.querySelector('[data-sitekey]');
        return el ? (el.getAttribute('data-sitekey') || 'found-no-key') : 'not-found';
    """)
    logger.info(f"Turnstile sitekey: {sitekey}")
    results["login"]["sitekey"] = sitekey
    results["login"]["csrf_step1"] = csrf1

    # ─── STEP 2: Enter username ───
    logger.info("STEP 2: Enter username")
    inp = page.ele("css:input.vtc-user-login", timeout=5)
    if not inp:
        inp = page.ele("css:input[placeholder]", timeout=5)
    if inp:
        inp.input(args.account)
        logger.info(f"Username: {args.account}")
    else:
        logger.error("Username input NOT FOUND!")
        return

    # Wait for Turnstile
    ts_token1 = wait_for_turnstile(page, timeout=60)
    results["login"]["turnstile_token_step1"] = ts_token1[:50] if ts_token1 else None

    # Click continue
    btn = page.ele("text:Tiếp tục", timeout=5) or page.ele("#btn-submit-username", timeout=3)
    if btn:
        btn.click()
        logger.info("Clicked 'Tiếp tục'")
    else:
        logger.error("Continue button not found!")

    time.sleep(3)

    # Capture Step 1 requests
    reqs1 = collect_requests(page)
    logger.info(f"Captured {len(reqs1)} requests after username submit:")
    for r in reqs1:
        logger.info(f"  {r.get('method')} {r.get('url')} -> {r.get('status')}")
        if r.get("body"):
            logger.info(f"    BODY: {str(r['body'])[:300]}")
        if r.get("resp"):
            logger.info(f"    RESP: {str(r['resp'])[:300]}")

    # ─── STEP 3: Enter password ───
    logger.info("STEP 3: Enter password")
    csrf2 = get_csrf(page)
    results["login"]["csrf_step2"] = csrf2
    logger.info(f"CSRF Token (step 2): {csrf2[:40]}..." if csrf2 else "CSRF2: NOT FOUND")

    pwd = page.ele("#password", timeout=15)
    if not pwd:
        pwd = page.ele('css:input[type="password"]', timeout=10)
    if pwd:
        pwd.input(args.password)
        logger.info("Password entered")

        # Wait for Turnstile again
        ts_token2 = wait_for_turnstile(page, timeout=60)
        results["login"]["turnstile_token_step2"] = ts_token2[:50] if ts_token2 else None

        # Click login
        btn2 = page.ele("#btn-login-pass", timeout=5) or page.ele("text:Đăng nhập", timeout=3)
        if btn2:
            btn2.click()
            logger.info("Clicked 'Đăng nhập'")

        time.sleep(5)

        # Capture Step 2 requests
        reqs2 = collect_requests(page)
        new_reqs = reqs2[len(reqs1):]
        logger.info(f"Captured {len(new_reqs)} NEW requests after login:")
        for r in new_reqs:
            logger.info(f"  {r.get('method')} {r.get('url')} -> {r.get('status')}")
            if r.get("body"):
                logger.info(f"    BODY: {str(r['body'])[:300]}")
            if r.get("resp"):
                logger.info(f"    RESP: {str(r['resp'])[:300]}")
    else:
        logger.error("Password field NOT FOUND — Step 1 may have failed")
        new_reqs = []
        reqs2 = reqs1

    # Check login success
    logger.info(f"Current URL after login: {page.url}")
    cookies_after_login = get_cookies(page)
    logger.info(f"Cookies after login: {len(cookies_after_login)}")
    for c in cookies_after_login:
        if "goplay" in c.get("domain", "") or "vtc" in c.get("domain", ""):
            logger.info(f"  Cookie: {c['name']} = {str(c.get('value',''))[:50]}... domain={c['domain']}")

    results["cookies"] = [
        {"name": c["name"], "domain": c.get("domain", ""), "value": str(c.get("value", ""))[:50]}
        for c in cookies_after_login
        if "goplay" in c.get("domain", "") or "vtc" in c.get("domain", "")
    ]

    # ─── STEP 4: Navigate to store ───
    logged_in = "oauth" not in page.url.lower() and "dang-nhap" not in page.url.lower()
    if logged_in:
        logger.info("=" * 60)
        logger.info(f"STEP 4: Navigate to store — {args.game}")
        logger.info("=" * 60)

        try:
            page.get(f"https://goplay.vn/cua-hang/{args.game}", timeout=30)
        except Exception:
            pass
        time.sleep(3)

        inject_interceptor(page)
        csrf_store = get_csrf(page)
        sitekey_store = page.run_js("""
            const el = document.querySelector('.cf-turnstile') || document.querySelector('[data-sitekey]');
            return el ? (el.getAttribute('data-sitekey') || 'found-no-key') : 'not-found';
        """)

        logger.info(f"Store URL: {page.url}")
        logger.info(f"Store CSRF: {csrf_store[:40]}..." if csrf_store else "Store CSRF: NOT FOUND")
        logger.info(f"Store Turnstile: {sitekey_store}")

        results["topup"]["url"] = page.url
        results["topup"]["csrf"] = csrf_store
        results["topup"]["turnstile"] = sitekey_store

        # Get all packages
        pkgs = page.eles("css:.goPlay-package")
        logger.info(f"Packages found: {len(pkgs)}")
        pkg_list = []
        for p in pkgs:
            info = {
                "packid": p.attr("data-packid"),
                "text": (p.text or "")[:80],
            }
            pkg_list.append(info)
            logger.info(f"  pkg #{info['packid']}: {info['text']}")
        results["topup"]["packages"] = pkg_list

        # Find ALL script src URLs
        scripts = page.run_js("""
            return Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
        """) or []
        logger.info(f"Script URLs on store page: {len(scripts)}")
        for s in scripts:
            if "goplay" in s.lower() or "shop" in s.lower() or "site" in s.lower():
                logger.info(f"  {s}")
        results["topup"]["scripts"] = [s for s in scripts if "goplay" in s.lower() or "shop" in s.lower() or "site" in s.lower()]

        # Try to find button handlers in page JS
        handlers = page.run_js("""
            const inline = Array.from(document.querySelectorAll('script:not([src])')).map(s => s.textContent).join('\\n');
            const found = [];
            // Find handler= patterns
            const hm = inline.match(/handler=\\w+/g);
            if (hm) found.push(...hm);
            // Find URL patterns
            const um = inline.match(/['"][/](api|cua-hang)[^'"]+['"]/g);
            if (um) found.push(...um);
            // Find ajax/fetch calls
            const fm = inline.match(/(fetch|ajax|post|get)\\s*\\(['"]/gi);
            if (fm) found.push(...fm);
            return [...new Set(found)];
        """) or []
        logger.info(f"JS handlers/endpoints: {len(handlers)}")
        for h in handlers:
            logger.info(f"  {h}")
        results["topup"]["handlers"] = handlers

        # Check for payment-related forms
        forms = page.eles("css:form")
        form_infos = []
        for f in forms:
            info = {"action": f.attr("action") or "", "method": f.attr("method") or "", "id": f.attr("id") or ""}
            form_infos.append(info)
            if info["action"]:
                logger.info(f"  Form: action={info['action']} method={info['method']}")
        results["topup"]["forms"] = form_infos

    else:
        logger.warning(f"Login failed — current URL: {page.url}")
        results["login"]["success"] = False

    # Save all intercepted requests
    all_reqs = collect_requests(page)
    results["requests"] = [
        {
            "type": r.get("type"),
            "method": r.get("method"),
            "url": r.get("url"),
            "status": r.get("status"),
            "body": str(r.get("body", ""))[:500] if r.get("body") else None,
            "resp": str(r.get("resp", ""))[:500] if r.get("resp") else None,
        }
        for r in all_reqs
    ]

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Output saved: {OUTPUT_FILE}")

    logger.info("=" * 60)
    logger.info("Recon Complete!")
    logger.info("=" * 60)

    time.sleep(10)
    page.quit()


if __name__ == "__main__":
    main()
