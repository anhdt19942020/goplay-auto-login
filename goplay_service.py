import os
import re
import time
import logging

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

    def _handle_turnstile(self):
        """Click Cloudflare Turnstile checkbox if present."""
        import random
        try:
            response_input = self.page.ele('css:input[name="cf-turnstile-response"]', timeout=5)
            if not response_input:
                return

            val = response_input.attr('value')
            if val:
                logger.info(f"Turnstile already verified (token: {val[:20]}...)")
                return

            logger.info("Cloudflare Turnstile detected. Waiting for auto-verify...")

            # Wait 1s for auto-verify first (server rarely auto-verifies)
            for _ in range(2):
                try:
                    val = response_input.attr('value')
                    if val:
                        logger.info(f"Turnstile auto-verified (token: {val[:20]}...)")
                        return
                except Exception:
                    pass
                time.sleep(0.5)

            logger.info("Auto-verify failed, attempting click strategies...")

            def _click_turnstile():
                """Click Turnstile checkbox via iframe-relative coordinates + CDP.

                Turnstile renders the checkbox via CSS/canvas — no accessible DOM elements.
                We find the iframe element, scroll it into view, re-read its viewport rect
                AFTER scroll, then compute click coords relative to the iframe position.

                Cloudflare Turnstile widget spec (fixed by CF):
                  - iframe is always 300px wide × 65px tall
                  - checkbox circle center: ~40px from left edge, vertically centered
                  - Safe click zone: iframe.x + [28..45], iframe.y + [height/2 ± 5]
                """
                # Re-fetch every call — position may change between Turnstile 1 and 2
                iframe_el = self.page.ele('css:iframe[src*="challenges.cloudflare.com"]', timeout=5)
                if not iframe_el:
                    logger.info("Turnstile iframe not found")
                    return False

                try:
                    # Scroll iframe into viewport using JS (most reliable)
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

                    # Re-fetch AFTER scroll
                    iframe_el = self.page.ele('css:iframe[src*="challenges.cloudflare.com"]', timeout=3)
                    if not iframe_el:
                        return False

                    # Use viewport_location (not location!) — CDP needs viewport-relative coords
                    try:
                        vp_loc = iframe_el.rect.viewport_location  # (x, y) relative to viewport
                    except Exception:
                        vp_loc = iframe_el.rect.location  # fallback

                    size = iframe_el.rect.size

                    # Checkbox center: ~40px from left, vertically centered
                    click_x = int(vp_loc[0]) + random.randint(28, 45)
                    click_y = int(vp_loc[1] + size[1] / 2) + random.randint(-4, 4)

                    logger.info(
                        f"Turnstile iframe rect: viewport=({vp_loc[0]:.0f},{vp_loc[1]:.0f}) "
                        f"size={size[0]:.0f}x{size[1]:.0f} → click=({click_x},{click_y})"
                    )

                    # Sanity check: click must be within viewport
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

                    # CDP mouse events
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

            # First click attempt
            _click_turnstile()

            # Wait up to 30s total for verification
            for i in range(58):  # 29s after the initial 1s auto-verify wait = 30s total
                try:
                    val = response_input.attr('value')
                    if val:
                        logger.info(f"Turnstile verified (token: {val[:20]}...)")
                        return
                except Exception:
                    pass

                # Retry click every 5s with different strategy
                if i > 0 and i % 10 == 0:
                    elapsed = 3 + i * 0.5
                    logger.info(f"Turnstile not verified after {elapsed:.0f}s, retrying click...")
                    _click_turnstile()

                time.sleep(0.5)

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
    # Shopping flow
    # ------------------------------------------------------------------

    def _navigate_to_game(self, game: GameCode):
        self.page.get(f'https://goplay.vn/cua-hang/{game.value}')
        self.page.wait.ele_displayed('css:.goPlay-package', timeout=10)
        logger.info(f"Game page: {self.page.url}")

    def _select_package(self, package: CrossfirePackage):
        el = self.page.ele(package.selector, timeout=5)
        if not el:
            self._dump_debug('select_package_fail')
            raise GoPlayError(GoPlayErrorCode.PACKAGE_NOT_FOUND, f"Không tìm thấy gói: {package.pack_name}")

        self._click(el)
        logger.info(f"Selected: {package.pack_name}")

        self.page.wait.ele_displayed('css:[data-field="payment-method"]', timeout=5)
        logger.info("Payment section visible")

    def _select_payment(self, method: PaymentMethod):
        selector = f'css:.payment-item[data-method="{method.value}"]:not(.is-disabled)'
        el = self.page.ele(selector, timeout=5)

        if not el:
            logger.warning("Payment item still disabled, trying click anyway")
            el = self.page.ele(method.selector, timeout=3)
            if not el:
                self._dump_debug('select_payment_fail')
                raise GoPlayError(GoPlayErrorCode.PAYMENT_NOT_FOUND, f"Không tìm thấy: {method.value}")

        self._click(el)
        time.sleep(0.15)
        logger.info(f"Payment: {method.name}")

    def _click_continue(self, game: GameCode):
        btn = self.page.ele(f'css:.btn-payment-game-{game.value}', timeout=5)
        if not btn:
            self._dump_debug('click_continue_fail')
            raise GoPlayError(GoPlayErrorCode.UNKNOWN_ERROR, "Không tìm thấy nút Tiếp tục")

        self._click(btn)
        self.page.wait.ele_displayed('#goplayShopPopup', timeout=8)
        logger.info("Clicked continue")

    def _check_result_popup(self) -> dict | None:
        """Check if goplayPopup is visible, return parsed result or None"""
        try:
            popup = self.page.ele('#goplayPopup', timeout=0.2)
            if not popup:
                return None
            style = popup.attr('style') or ''
            if 'display: none' in style or 'display:none' in style:
                return None
            if 'display' not in style:
                return None

            title_el = self.page.ele('#goplayPopupTitle', timeout=0.2)
            msg_el = self.page.ele('#goplayPopupMsg', timeout=0.2)
            if not title_el or not msg_el:
                return None
            title = title_el.text.strip() if title_el.text else ''
            msg = msg_el.text.strip() if msg_el.text else ''
            if not title and not msg:
                return None

            img_el = self.page.ele('#goplayPopupImg', timeout=0.2)
            img_src = img_el.attr('src') if img_el else ''
            is_success = 'success' in (img_src or '') or 'thành công' in title.lower()

            ok_btn = self.page.ele('#goplayPopupOk', timeout=1)
            if ok_btn:
                self._click(ok_btn)
                time.sleep(0.15)

            return {'success': is_success, 'title': title, 'message': msg}
        except Exception:
            return None

    def _parse_topup_result(self, msg: str) -> dict:
        """Parse GO received and balance from popup message"""
        go_match = re.search(r'nhận được\s*(\d+)\s*GO', msg, re.IGNORECASE)
        balance_match = re.search(r'hiện tại[:\s]*(\d+)\s*GO', msg, re.IGNORECASE)
        return {
            'go_received': int(go_match.group(1)) if go_match else None,
            'balance': int(balance_match.group(1)) if balance_match else None,
        }

    def _fill_card_and_submit(self, card_serial: str, card_code: str):
        self._handle_turnstile()
        serial_input = self.page.ele('#card-serial', timeout=15)

        if not serial_input:
            self._dump_debug('card_popup_fail')
            raise GoPlayError(GoPlayErrorCode.UNKNOWN_ERROR, "Popup nhập thẻ không xuất hiện")

        serial_input.clear()
        serial_input.input(card_serial)

        code_input = self.page.ele('#card-code')
        code_input.clear()
        code_input.input(card_code)
        time.sleep(0.15)

        self._click(self.page.ele('#id-shop-popup-ok-btn'))
        logger.info("Card submitted, waiting for result...")

        for _ in range(60):  # max 30s
            error_el = self.page.ele('#id-shop-popup-error', timeout=0.2)
            if error_el and error_el.text.strip():
                self._dump_debug('payment_error')
                raise GoPlayError(GoPlayErrorCode.PAYMENT_ERROR, error_el.text.strip())

            result = self._check_result_popup()
            if result:
                if result['success']:
                    parsed = self._parse_topup_result(result['message'])
                    logger.info(f"Top-up success: {result['message']}")
                    return {
                        'success': True,
                        'title': result['title'],
                        'message': result['message'],
                        'go_received': parsed['go_received'],
                        'balance': parsed['balance'],
                    }
                else:
                    self._dump_debug('payment_error')
                    raise GoPlayError(GoPlayErrorCode.PAYMENT_ERROR, result['message'] or result['title'])

            time.sleep(0.5)

        self._dump_debug('card_submit_timeout')
        raise GoPlayError(GoPlayErrorCode.UNKNOWN_ERROR, "Không nhận được kết quả nạp thẻ sau 30s")

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
            self._navigate_to_game(game)
            self._select_package(package)
            self._handle_turnstile()
            self._select_payment(PaymentMethod.THE_VCOIN)
            self._handle_turnstile()
            self._click_continue(game)
            result = self._fill_card_and_submit(card_serial, card_code)

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
                },
            }
        except GoPlayError as e:
            logger.error(f"GoPlay error [{e.code.value}]: {e.detail}")
            self._dump_debug('topup_error')
            # Browser-level errors → kill browser to reset
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
