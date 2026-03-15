import os
import re
import time
import logging

from DrissionPage import ChromiumOptions, ChromiumPage
from DrissionPage.errors import BrowserConnectError
from enums import CrossfirePackage, GameCode, GoPlayErrorCode, PaymentMethod

logger = logging.getLogger(__name__)

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
        opts.set_pref('credentials_enable_service', False)
        opts.set_pref('profile.password_manager_enabled', False)
        opts.set_pref('profile.password_manager_leak_detection', False)
        opts.set_pref('profile.default_content_setting_values.notifications', 2)
        opts.set_argument('--disable-notifications')
        opts.set_argument('--disable-features=PasswordLeakDetection,PasswordCheck')

        if os.environ.get('DOCKER_ENV'):
            opts.set_argument('--no-sandbox')
            opts.set_argument('--disable-dev-shm-usage')
            opts.set_argument('--disable-gpu')
        try:
            return ChromiumPage(opts)
        except BrowserConnectError as e:
            raise GoPlayError(
                GoPlayErrorCode.BROWSER_ERROR,
                f"Không thể kết nối Chrome port 9222. Hãy tắt Chrome cũ và thử lại. ({e})",
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

    def _dump_debug(self, step_name: str):
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
    # Cloudflare Turnstile
    # ------------------------------------------------------------------

    def _handle_turnstile(self):
        """Click Cloudflare Turnstile checkbox if present."""
        try:
            iframe = self.page.ele('css:iframe[src*="challenges.cloudflare.com"]', timeout=2)
            if not iframe:
                logger.debug("No Turnstile iframe found, skipping")
                return

            logger.info("Cloudflare Turnstile detected, clicking checkbox...")
            checkbox = iframe.ele('tag:body', timeout=3)
            if checkbox:
                iframe.ele('tag:body').click()
                time.sleep(2)

            # Wait for Turnstile to complete verification
            for _ in range(10):  # max 5s
                try:
                    response_input = self.page.ele('css:input[name="cf-turnstile-response"]', timeout=0.3)
                    if response_input and response_input.attr('value'):
                        logger.info("Turnstile verified successfully")
                        return
                except Exception:
                    pass
                time.sleep(0.5)

            logger.warning("Turnstile may not be verified, proceeding anyway")
        except Exception as e:
            logger.debug(f"Turnstile handling skipped: {e}")

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
                ok_btn.click()
                time.sleep(0.3)
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
        self.page.wait.ele_displayed('css:.btn-auth.box-login', timeout=8)

        # Double-check: maybe already logged in (cookie from profile)
        if self.page.ele('css:.userInfo', timeout=1):
            logger.info("Already logged in (from profile), logging out for new account...")
            self._logout()

        logger.info(f"Logging in as {account}...")
        self.page.ele('css:.btn-auth.box-login').click()
        self.page.wait.ele_displayed('css:a.btn-auth.btn-login', timeout=3)

        self.page.ele('css:a.btn-auth.btn-login').click()
        self.page.wait.ele_displayed('css:.vtc-user-login')
        self.page.ele('css:.vtc-user-login').input(account)
        self.page.ele('#btn-submit-username').click()

        for _ in range(20):  # max 10s
            if self.page.ele('#password', timeout=0.3):
                break
            error_el = self.page.ele('css:.input-error .text-danger', timeout=0.2)
            if error_el and error_el.text.strip():
                raise GoPlayError(GoPlayErrorCode.ACCOUNT_NOT_REGISTERED, error_el.text.strip())
        else:
            raise GoPlayError(GoPlayErrorCode.LOGIN_TIMEOUT, "Không thể chuyển sang bước nhập mật khẩu")

        self.page.ele('#password').input(password)
        self._handle_turnstile()
        self.page.ele('#btn-login-pass').click()

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

        el.click()
        logger.info(f"Selected: {package.pack_name}")

        self.page.wait.ele_displayed('css:[data-field="payment-method"]', timeout=5)
        logger.info("Payment section visible")

    def _select_payment(self, method: PaymentMethod):
        selector = f'css:.payment-item[data-method="{method.value}"]:not(.is-disabled)'
        el = self.page.ele(selector, timeout=10)

        if not el:
            logger.warning("Payment item still disabled, trying click anyway")
            el = self.page.ele(method.selector, timeout=3)
            if not el:
                self._dump_debug('select_payment_fail')
                raise GoPlayError(GoPlayErrorCode.PAYMENT_NOT_FOUND, f"Không tìm thấy: {method.value}")

        el.click()
        time.sleep(0.3)
        logger.info(f"Payment: {method.name}")

    def _click_continue(self, game: GameCode):
        btn = self.page.ele(f'css:.btn-payment-game-{game.value}', timeout=5)
        if not btn:
            self._dump_debug('click_continue_fail')
            raise GoPlayError(GoPlayErrorCode.UNKNOWN_ERROR, "Không tìm thấy nút Tiếp tục")

        btn.click()
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
                ok_btn.click()
                time.sleep(0.3)

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
        serial_input = self.page.ele('#card-serial', timeout=10)

        if not serial_input:
            self._dump_debug('card_popup_fail')
            raise GoPlayError(GoPlayErrorCode.UNKNOWN_ERROR, "Popup nhập thẻ không xuất hiện")

        serial_input.clear()
        serial_input.input(card_serial)

        code_input = self.page.ele('#card-code')
        code_input.clear()
        code_input.input(card_code)
        time.sleep(0.3)

        self.page.ele('#id-shop-popup-ok-btn').click()
        logger.info("Card submitted, waiting for result...")

        for _ in range(24):  # max 12s
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
        raise GoPlayError(GoPlayErrorCode.UNKNOWN_ERROR, "Không nhận được kết quả nạp thẻ sau 12s")

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
            self._select_payment(PaymentMethod.THE_VCOIN)
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
                "message": str(e),
                "detail": None,
            }
