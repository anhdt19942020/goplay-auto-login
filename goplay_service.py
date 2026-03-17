import os
import re
import time
import logging

import httpx
from DrissionPage import ChromiumOptions, ChromiumPage
from DrissionPage.errors import BrowserConnectError
from enums import CrossfirePackage, GameCode, GoPlayErrorCode, PaymentMethod

logger = logging.getLogger(__name__)

# DrissionPage error messages are in Chinese → translate to Vietnamese
_CN_TO_VI = {
    '浏览器连接失败': 'Không thể kết nối trình duyệt',
    '该元素没有位置和大小': 'Phần tử không có vị trí hoặc kích thước (trang chưa load xong)',
    '没有找到元素': 'Không tìm thấy phần tử trên trang',
    '元素未加载成功': 'Phần tử chưa tải xong',
    '未连接浏览器': 'Chưa kết nối trình duyệt',
    '页面已关闭': 'Trang đã bị đóng',
    '连接超时': 'Kết nối bị timeout',
    '等待元素超时': 'Chờ phần tử bị timeout',
    '代理': 'proxy',
}


def _translate_error(msg: str) -> str:
    """Translate common DrissionPage Chinese errors to Vietnamese"""
    result = str(msg)
    for cn, vi in _CN_TO_VI.items():
        if cn in result:
            result = vi
            break
    return result

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))


class GoPlayError(Exception):
    """Structured error with error code for API responses"""

    def __init__(self, code: GoPlayErrorCode, detail: str | None = None):
        self.code = code
        self.detail = detail or code.message
        super().__init__(self.detail)


class GoPlayService:
    """Browser automation service for GoPlay.vn top-up

    Uses a persistent Chrome browser across requests.
    Tracks the current logged-in account and only re-logs
    when the account changes.
    """

    _page: ChromiumPage | None = None
    _current_account: str | None = None
    _chrome_profile_dir = os.path.join(WORKSPACE_DIR, 'chrome_profile_vlcm')

    def __init__(self):
        os.makedirs(self._chrome_profile_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Browser lifecycle
    # ------------------------------------------------------------------

    def _ensure_browser(self):
        """Reuse existing browser or create a new one if dead/missing."""
        if self._is_browser_alive():
            return
        logger.info("Starting new Chrome instance...")
        GoPlayService._page = self._create_browser()
        GoPlayService._current_account = None
        # Stealth: remove webdriver detection flags
        try:
            self.page.run_js('''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}};
            ''')
        except Exception:
            pass

    def _is_browser_alive(self) -> bool:
        if GoPlayService._page is None:
            return False
        try:
            _ = GoPlayService._page.title
            return True
        except Exception:
            logger.warning("Browser is dead, will restart")
            GoPlayService._page = None
            GoPlayService._current_account = None
            return False

    def _create_browser(self) -> ChromiumPage:
        opts = ChromiumOptions()
        opts.set_user_data_path(self._chrome_profile_dir)
        opts.set_local_port(9222)
        opts.set_argument('--disable-notifications')
        opts.set_argument('--disable-features=PasswordLeakDetection,PasswordCheck,PasswordManagerOnboarding')
        opts.set_argument('--disable-save-password-bubble')
        opts.set_argument('--disable-blink-features=AutomationControlled')
        opts.remove_argument('--enable-automation')
        opts.set_argument('--window-size=1280,720')

        # Disable all password manager dialogs (Change Password, Save Password, etc.)
        opts.set_pref('credentials_enable_service', False)
        opts.set_pref('profile.password_manager_enabled', False)
        opts.set_pref('profile.password_manager_leak_detection', False)
        opts.set_pref('password_manager.password_checkup.enabled', False)

        # Option 2: Route Chrome through residential proxy if configured
        # Set env var GOPLAY_PROXY=socks5://127.0.0.1:9091 to enable
        proxy = os.environ.get('GOPLAY_PROXY', '').strip()
        if proxy:
            opts.set_argument(f'--proxy-server={proxy}')
            logger.info(f"Proxy enabled: {proxy}")
        else:
            logger.info("Proxy: none (direct connection)")

        # Auto-detect Chrome path on Windows
        import shutil
        if not shutil.which(opts.browser_path or 'chrome'):
            for candidate in [
                os.path.join(os.environ.get('ProgramFiles', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
                os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
                os.path.join(os.environ.get('LocalAppData', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            ]:
                if os.path.isfile(candidate):
                    opts.set_browser_path(candidate)
                    logger.info(f"Chrome found at: {candidate}")
                    break

        try:
            return ChromiumPage(opts)
        except BrowserConnectError as e:
            raise GoPlayError(
                GoPlayErrorCode.BROWSER_ERROR,
                f"Không thể kết nối Chrome. ({_translate_error(e)})",
            )

    def _kill_browser(self):
        """Force-quit browser and reset state (used on fatal errors)."""
        if GoPlayService._page:
            try:
                GoPlayService._page.quit()
            except Exception:
                pass
        GoPlayService._page = None
        GoPlayService._current_account = None

    @property
    def page(self) -> ChromiumPage:
        return GoPlayService._page

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def _click(self, el):
        """Click element — fallback to JS click if normal click fails"""
        try:
            el.click()
        except Exception:
            logger.debug("Normal click failed, using JS click")
            el.click(by_js=True)

    def _dump_debug(self, step_name: str):
        import traceback
        logger.error(f"Debug dump at step '{step_name}': {traceback.format_exc()}")
        try:
            debug_dir = os.path.join(WORKSPACE_DIR, 'debug')
            os.makedirs(debug_dir, exist_ok=True)
            html_file = os.path.join(debug_dir, f'{step_name}.html')
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(self.page.html)
            logger.info(f"Debug HTML saved: {html_file}")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Chrome dialog dismissal
    # ------------------------------------------------------------------

    def _dismiss_chrome_dialogs(self):
        """Dismiss Chrome built-in dialogs (Change Password, Save Password, etc.)"""
        try:
            # Google Password Manager "Change your password" popup
            ok_btn = self.page.ele('xpath://div[contains(text(),"Change your password")]/ancestor::div//button[contains(text(),"OK") or contains(text(),"Close")]', timeout=1)
            if ok_btn:
                ok_btn.click()
                logger.info("Dismissed 'Change your password' dialog")
                time.sleep(0.2)
                return True
        except Exception:
            pass

        try:
            # Any dialog with OK/Close button from Chrome UI
            for sel in [
                'css:button[jsname="LgbsSe"]',  # Google Material button
                'xpath://button[text()="OK"]',
                'xpath://button[text()="Close"]',
                'css:.password-check-ok-button',
            ]:
                btn = self.page.ele(sel, timeout=0.3)
                if btn and btn.is_displayed():
                    btn.click()
                    logger.info(f"Dismissed Chrome dialog via {sel}")
                    time.sleep(0.15)
                    return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Cloudflare Turnstile
    # ------------------------------------------------------------------

    def _handle_turnstile(self, detect_timeout: int = 5):
        """Click Cloudflare Turnstile checkbox if present."""
        import random
        try:
            response_input = self.page.ele('css:input[name="cf-turnstile-response"]', timeout=detect_timeout)
            if not response_input:
                return

            val = response_input.attr('value')
            if val:
                logger.info(f"Turnstile already verified (token: {val[:20]}...)")
                return

            logger.info("Cloudflare Turnstile detected, clicking immediately...")

            def _click_turnstile():
                """Click Turnstile checkbox via iframe-relative coordinates + CDP."""
                iframe_el = self.page.ele('css:iframe[src*="challenges.cloudflare.com"]', timeout=5)
                if not iframe_el:
                    logger.info("Turnstile iframe not found")
                    return False

                try:
                    try:
                        self.page.run_js(
                            'document.querySelector(\'iframe[src*="challenges.cloudflare.com"]\').scrollIntoView({block:"center"})'
                        )
                        time.sleep(0.5)
                    except Exception:
                        try:
                            iframe_el.scroll.to_see()
                            time.sleep(0.4)
                        except Exception:
                            pass

                    iframe_el = self.page.ele('css:iframe[src*="challenges.cloudflare.com"]', timeout=3)
                    if not iframe_el:
                        return False

                    try:
                        vp_loc = iframe_el.rect.viewport_location
                    except Exception:
                        vp_loc = iframe_el.rect.location

                    size = iframe_el.rect.size
                    click_x = int(vp_loc[0]) + random.randint(28, 45)
                    click_y = int(vp_loc[1] + size[1] / 2) + random.randint(-4, 4)

                    logger.info(
                        f"Turnstile iframe rect: viewport=({vp_loc[0]:.0f},{vp_loc[1]:.0f}) "
                        f"size={size[0]:.0f}x{size[1]:.0f} → click=({click_x},{click_y})"
                    )

                    if click_y < 0 or click_y > 900:
                        logger.warning(f"Click y={click_y} outside viewport, scrolling again...")
                        self.page.run_js(
                            'document.querySelector(\'iframe[src*="challenges.cloudflare.com"]\').scrollIntoView({block:"center"})'
                        )
                        time.sleep(0.5)
                        iframe_el = self.page.ele('css:iframe[src*="challenges.cloudflare.com"]', timeout=3)
                        if not iframe_el:
                            return False
                        try:
                            vp_loc = iframe_el.rect.viewport_location
                        except Exception:
                            vp_loc = iframe_el.rect.location
                        size = iframe_el.rect.size
                        click_x = int(vp_loc[0]) + random.randint(28, 45)
                        click_y = int(vp_loc[1] + size[1] / 2) + random.randint(-4, 4)
                        logger.info(f"After re-scroll: viewport=({vp_loc[0]:.0f},{vp_loc[1]:.0f}) → click=({click_x},{click_y})")

                    self.page.run_cdp('Input.dispatchMouseEvent',
                                      type='mouseMoved', x=click_x, y=click_y,
                                      button='none', modifiers=0)
                    time.sleep(random.uniform(0.08, 0.18))
                    self.page.run_cdp('Input.dispatchMouseEvent',
                                      type='mousePressed', x=click_x, y=click_y,
                                      button='left', clickCount=1, modifiers=0)
                    time.sleep(random.uniform(0.06, 0.14))
                    self.page.run_cdp('Input.dispatchMouseEvent',
                                      type='mouseReleased', x=click_x, y=click_y,
                                      button='left', clickCount=1, modifiers=0)
                    return True

                except Exception as e:
                    logger.warning(f"Turnstile click error: {e}")
                    return False

            # Small delay for iframe to render position, then click
            time.sleep(0.3)
            _click_turnstile()

            # Wait up to 30s for verification (poll every 0.2s for fast detection)
            for i in range(150):  # 150 × 0.2s = 30s
                try:
                    val = response_input.attr('value')
                    if val:
                        logger.info(f"Turnstile verified (token: {val[:20]}...)")
                        return
                except Exception:
                    pass

                # Retry click every 3s
                if i > 0 and i % 15 == 0:
                    elapsed = i * 0.2
                    logger.info(f"Turnstile not verified after {elapsed:.0f}s, retrying click...")
                    _click_turnstile()

                time.sleep(0.2)

            logger.warning("Turnstile NOT verified after 30s")
        except Exception as e:
            logger.warning(f"Turnstile handling error: {e}")

    # ------------------------------------------------------------------
    # Login / Logout
    # ------------------------------------------------------------------

    def _check_login_popup(self) -> GoPlayErrorCode | None:
        """Check if GoPlay error popup is visible, return error code or None"""
        try:
            popup = self.page.ele('#goplayPopup', timeout=0.2)
            if not popup:
                return None
            style = popup.attr('style') or ''
            if 'display: none' in style or 'display:none' in style:
                return None
            if 'display' not in style:
                return None

            popup_msg = self.page.ele('#goplayPopupMsg', timeout=0.2)
            if not popup_msg:
                return None
            text = popup_msg.text.strip() if popup_msg.text else ''
            if not text:
                return None
            code = GoPlayErrorCode.from_popup_message(text)
            logger.warning(f"Popup error detected: '{text}' → {code.value}")
            ok_btn = self.page.ele('#goplayPopupOk', timeout=1)
            if ok_btn:
                self._click(ok_btn)
                time.sleep(0.15)
            return code
        except Exception:
            return None

    def _wait_login_result(self, timeout: int = 15):
        """Polling loop: wait for login success OR error popup"""
        max_checks = int(timeout / 0.5)
        for i in range(max_checks):
            if self.page.ele('#btn-header-shop', timeout=0.2):
                logger.info("Login OK")
                return
            error_code = self._check_login_popup()
            if error_code:
                raise GoPlayError(error_code)
            if i % 5 == 4:
                logger.debug(f"Waiting for login result... ({(i+1)*0.5:.0f}s)")
            time.sleep(0.5)
        self._dump_debug('login_timeout')
        raise GoPlayError(GoPlayErrorCode.LOGIN_TIMEOUT)

    def _logout(self):
        """Logout by clearing cookies and reloading."""
        logger.info(f"Logging out (was: {GoPlayService._current_account})...")
        try:
            self.page.set.cookies.clear()
            self.page.get('https://goplay.vn/')
            self.page.wait.ele_displayed('css:.btn-auth.box-login', timeout=5)
        except Exception:
            pass
        GoPlayService._current_account = None

    def _login(self, account: str, password: str):
        # Already logged in with the same account → skip
        if GoPlayService._current_account == account:
            if self.page.ele('css:.userInfo', timeout=1):
                logger.info(f"Already logged in as {account}, skipping login")
                return
            # Session expired, need to re-login
            logger.info("Session expired, re-logging in...")
            GoPlayService._current_account = None

        # Different account → logout first
        if GoPlayService._current_account is not None:
            self._logout()

        self.page.get('https://goplay.vn/')
        self.page.wait.ele_displayed('css:.btn-auth.box-login', timeout=5)

        # Double-check: maybe already logged in (cookie from profile)
        if self.page.ele('css:.userInfo', timeout=1):
            logger.info("Already logged in (from profile), logging out for new account...")
            self._logout()

        logger.info(f"Logging in as {account}...")
        self._click(self.page.ele('css:.btn-auth.box-login'))
        self.page.wait.ele_displayed('css:a.btn-auth.btn-login', timeout=2)

        self._click(self.page.ele('css:a.btn-auth.btn-login'))
        self.page.wait.ele_displayed('css:.vtc-user-login')
        self.page.ele('css:.vtc-user-login').input(account)
        self._handle_turnstile()
        self._click(self.page.ele('#btn-submit-username'))

        for _ in range(60):  # max 30s (server Turnstile may take longer)
            if self.page.ele('#password', timeout=0.3):
                break
            error_el = self.page.ele('css:.input-error .text-danger', timeout=0.2)
            if error_el and error_el.text.strip():
                raise GoPlayError(GoPlayErrorCode.ACCOUNT_NOT_REGISTERED, error_el.text.strip())
        else:
            raise GoPlayError(GoPlayErrorCode.LOGIN_TIMEOUT, "Không thể chuyển sang bước nhập mật khẩu")

        self.page.ele('#password').input(password)
        self._handle_turnstile()
        self._click(self.page.ele('#btn-login-pass'))

        # Dismiss Chrome Password Manager dialogs if they appear
        time.sleep(0.3)
        self._dismiss_chrome_dialogs()

        self._wait_login_result()
        GoPlayService._current_account = account

    # ------------------------------------------------------------------
    # Shopping flow (Hybrid: browser for navigation + HTTP for topup)
    # ------------------------------------------------------------------

    def _navigate_to_game(self, game: GameCode):
        self.page.get(f'https://goplay.vn/cua-hang/{game.value}')
        self.page.wait.ele_displayed('css:.goPlay-package', timeout=10)
        if 'oauth/dang-nhap' in self.page.url or 'signin' in self.page.url:
            logger.warning("Session expired (redirected to login page), will re-login")
            GoPlayService._current_account = None
            raise GoPlayError(GoPlayErrorCode.LOGIN_TIMEOUT, "SESSION_EXPIRED")
        logger.info(f"Game page: {self.page.url}")

    def _extract_cookies_for_http(self) -> dict:
        """Extract all GoPlay cookies from browser via CDP for httpx."""
        cdp_cookies = self.page.run_cdp("Network.getAllCookies").get("cookies", [])
        cookies = {}
        for c in cdp_cookies:
            if "goplay" in c.get("domain", ""):
                cookies[c["name"]] = c["value"]
        logger.info(f"Extracted {len(cookies)} cookies for HTTP client")
        return cookies

    def _get_store_csrf_token(self) -> str:
        """Extract CSRF token from current store page DOM."""
        csrf_el = self.page.ele('css:input[name="__RequestVerificationToken"]', timeout=5)
        if not csrf_el:
            raise GoPlayError(GoPlayErrorCode.UNKNOWN_ERROR, "CSRF token not found on store page")
        token = csrf_el.attr("value")
        if not token:
            raise GoPlayError(GoPlayErrorCode.UNKNOWN_ERROR, "CSRF token is empty")
        logger.info(f"CSRF token: {token[:30]}...")
        return token

    def _get_store_turnstile_token(self) -> str:
        """Trigger Turnstile on store page and wait for token."""
        # Try auto-detected token first (sometimes already solved)
        try:
            inp = self.page.ele('css:input[name="cf-turnstile-response"]', timeout=2)
            if inp:
                val = inp.attr('value')
                if val and len(val) > 10:
                    logger.info(f"Turnstile already solved: {val[:30]}...")
                    return val
        except Exception:
            pass

        # Trigger TurnstileHelper.renderEnableVerify() via JS
        logger.info("Triggering TurnstileHelper.renderEnableVerify()...")
        try:
            self.page.run_js("""
                if (typeof TurnstileHelper !== 'undefined' && typeof TurnstileHelper.renderEnableVerify === 'function') {
                    TurnstileHelper.renderEnableVerify(function(token) {
                        window.__topup_turnstile = token;
                    }, { timeoutMs: 30000 });
                }
            """)
        except Exception as e:
            logger.warning(f"TurnstileHelper call failed: {e}")

        # Poll for the token
        for i in range(20):  # 20 × 2s = 40s max
            time.sleep(2)
            try:
                token = self.page.run_js("return window.__topup_turnstile || null;")
                if token:
                    logger.info(f"Turnstile solved: {token[:30]}...")
                    return token
            except Exception:
                pass
            # Also check the input field
            try:
                inp = self.page.ele('css:input[name="cf-turnstile-response"]', timeout=0.3)
                if inp:
                    val = inp.attr('value')
                    if val and len(val) > 10:
                        logger.info(f"Turnstile solved (input): {val[:30]}...")
                        return val
            except Exception:
                pass

        logger.warning("Turnstile token not obtained after 40s, proceeding with empty")
        return ""

    def _http_card_topup(self, game: GameCode, card_serial: str, card_code: str, method: str = "CARD-VCOIN") -> dict:
        """Submit card topup via HTTP POST instead of browser clicks."""
        # Validate card info
        errors = []
        if not (8 <= len(card_serial) <= 32):
            errors.append(f"Serial không hợp lệ (8-32 ký tự, hiện {len(card_serial)})")
        if not (8 <= len(card_code) <= 32):
            errors.append(f"Mã thẻ không hợp lệ (8-32 ký tự, hiện {len(card_code)})")
        if errors:
            raise GoPlayError(GoPlayErrorCode.INVALID_CARD_INFO, "; ".join(errors))

        # Extract prerequisites from browser
        cookies = self._extract_cookies_for_http()
        csrf_token = self._get_store_csrf_token()
        turnstile_token = self._get_store_turnstile_token()

        # Build URL and payload
        page_url = self.page.url
        api_url = page_url + ("&" if "?" in page_url else "?") + "handler=Card"

        payload = {
            "method": method,
            "serial": card_serial,
            "code": card_code,
            "captchaToken": turnstile_token,
        }

        headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "RequestVerificationToken": csrf_token,
            "Accept": "application/json",
            "Origin": "https://goplay.vn",
            "Referer": page_url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

        logger.info(f"HTTP POST {api_url}")
        logger.info(f"  serial={card_serial[:4]}****{card_serial[-4:]}" if len(card_serial) > 8 else f"  serial={card_serial}")

        try:
            with httpx.Client(cookies=cookies, timeout=30, follow_redirects=True) as client:
                resp = client.post(api_url, json=payload, headers=headers)
        except httpx.TimeoutException:
            raise GoPlayError(GoPlayErrorCode.UNKNOWN_ERROR, "HTTP topup request timeout (30s)")
        except httpx.HTTPError as e:
            raise GoPlayError(GoPlayErrorCode.UNKNOWN_ERROR, f"HTTP error: {e}")

        logger.info(f"  HTTP {resp.status_code} | Content-Type: {resp.headers.get('content-type', 'N/A')}")

        if resp.status_code != 200:
            raise GoPlayError(GoPlayErrorCode.PAYMENT_ERROR, f"HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            data = resp.json()
        except Exception:
            raise GoPlayError(GoPlayErrorCode.UNKNOWN_ERROR, f"Non-JSON response: {resp.text[:200]}")

        if data.get("success"):
            msg = data.get("message", "Nạp thẻ thành công")
            topup_data = data.get("data", {})
            go_received = topup_data.get("Topup")
            balance = topup_data.get("totalBalance")
            # Also try parsing from message
            if not go_received:
                go_match = re.search(r'nhận được\s*(\d+)\s*GO', msg, re.IGNORECASE)
                go_received = int(go_match.group(1)) if go_match else None
            logger.info(f"🎉 Topup OK: {msg} | +{go_received} GO | Balance: {balance}")
            return {
                'success': True,
                'message': msg,
                'go_received': go_received,
                'balance': balance,
                'log_id': topup_data.get('logId'),
            }
        else:
            error_msg = data.get("message", "Lỗi không xác định")
            logger.warning(f"❌ Topup failed: {error_msg}")
            raise GoPlayError(GoPlayErrorCode.PAYMENT_ERROR, error_msg)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def topup(
        self,
        game: GameCode,
        account: str,
        password: str,
        package: CrossfirePackage,
        card_serial: str,
        card_code: str,
    ) -> dict:
        try:
            self._ensure_browser()

            self._login(account, password)

            try:
                self._navigate_to_game(game)
            except GoPlayError as nav_err:
                if 'SESSION_EXPIRED' in str(nav_err.detail):
                    logger.info("Re-logging in after session expiry...")
                    self._login(account, password)
                    self._navigate_to_game(game)
                else:
                    raise

            # HTTP card topup (replaces browser click flow)
            result = self._http_card_topup(game, card_serial, card_code)

            return {
                "success": True,
                "error_code": None,
                "message": result.get('message', 'Nạp thẻ thành công'),
                "detail": {
                    "game": game.value,
                    "package": package.pack_name,
                    "price": package.price,
                    "go": package.go,
                    "go_received": result.get('go_received'),
                    "balance": result.get('balance'),
                    "log_id": result.get('log_id'),
                },
            }
        except GoPlayError as e:
            logger.error(f"GoPlay error [{e.code.value}]: {e.detail}")
            self._dump_debug('topup_error')
            if e.code == GoPlayErrorCode.BROWSER_ERROR:
                self._kill_browser()
            return {
                "success": False,
                "error_code": e.code.value,
                "message": e.detail,
                "detail": None,
            }
        except Exception as e:
            logger.exception("Unexpected error")
            self._dump_debug('topup_error')
            self._kill_browser()
            return {
                "success": False,
                "error_code": GoPlayErrorCode.UNKNOWN_ERROR.value,
                "message": _translate_error(e),
                "detail": None,
            }
