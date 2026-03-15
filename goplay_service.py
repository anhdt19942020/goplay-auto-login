import os
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
    # Login / Logout
    # ------------------------------------------------------------------

    def _check_login_popup(self) -> GoPlayErrorCode | None:
        """Check if GoPlay error popup is visible, return error code or None"""
        try:
            popup_msg = self.page.ele('#goplayPopupMsg', timeout=0.3)
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
        for _ in range(max_checks):
            if self.page.ele('#btn-header-shop', timeout=0.2):
                logger.info("Login OK")
                return
            error_code = self._check_login_popup()
            if error_code:
                raise GoPlayError(error_code)
            time.sleep(0.5)
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

        self.page.wait.ele_displayed('#password')
        self.page.ele('#password').input(password)
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

        for _ in range(20):  # max 10s
            error_el = self.page.ele('#id-shop-popup-error', timeout=0.3)
            if error_el and error_el.text.strip():
                self._dump_debug('payment_error')
                raise GoPlayError(GoPlayErrorCode.PAYMENT_ERROR, error_el.text.strip())
            popup = self.page.ele('#goplayShopPopup', timeout=0.2)
            if not popup or 'display: none' in (popup.attr('style') or ''):
                return True
            time.sleep(0.5)

        return True

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
            self._fill_card_and_submit(card_serial, card_code)

            return {
                "success": True,
                "error_code": None,
                "message": "Nạp thẻ thành công",
                "detail": {
                    "game": game.value,
                    "package": package.pack_name,
                    "price": package.price,
                    "go": package.go,
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
