import os
import time
import logging

from DrissionPage import ChromiumOptions, ChromiumPage
from enums import CrossfirePackage, GameCode, GoPlayErrorCode, PaymentMethod

logger = logging.getLogger(__name__)


class GoPlayError(Exception):
    """Structured error with error code for API responses"""

    def __init__(self, code: GoPlayErrorCode, detail: str | None = None):
        self.code = code
        self.detail = detail or code.message
        super().__init__(self.detail)


class GoPlayService:
    """Browser automation service for GoPlay.vn top-up"""

    def __init__(self):
        workspace_dir = os.path.dirname(os.path.abspath(__file__))
        self.chrome_profile_dir = os.path.join(workspace_dir, 'chrome_profile_vlcm')
        os.makedirs(self.chrome_profile_dir, exist_ok=True)
        self.page = None

    def _create_browser(self):
        opts = ChromiumOptions()
        opts.set_user_data_path(self.chrome_profile_dir)
        opts.set_pref('credentials_enable_service', False)
        opts.set_pref('profile.password_manager_enabled', False)
        opts.set_pref('profile.password_manager_leak_detection', False)
        opts.set_pref('profile.default_content_setting_values.notifications', 2)
        opts.set_argument('--disable-notifications')
        opts.set_argument('--disable-features=PasswordLeakDetection,PasswordCheck')
        return ChromiumPage(opts)

    def _dump_debug(self, step_name: str):
        """Save HTML and screenshot for debugging"""
        try:
            workspace_dir = os.path.dirname(os.path.abspath(__file__))
            debug_dir = os.path.join(workspace_dir, 'debug')
            os.makedirs(debug_dir, exist_ok=True)

            html_file = os.path.join(debug_dir, f'{step_name}.html')
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(self.page.html)
            logger.info(f"Debug HTML saved: {html_file}")
        except Exception:
            pass

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
            # Dismiss popup
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
            # Check success
            if self.page.ele('#btn-header-shop', timeout=0.2):
                logger.info("Login OK")
                return
            # Check error popup
            error_code = self._check_login_popup()
            if error_code:
                raise GoPlayError(error_code)
            time.sleep(0.5)
        raise GoPlayError(GoPlayErrorCode.LOGIN_TIMEOUT)

    def _login(self, account: str, password: str):
        self.page.get('https://goplay.vn/')
        time.sleep(3)

        if self.page.ele('css:.userInfo', timeout=3):
            logger.info("Already logged in")
            return

        logger.info("Performing login...")
        self.page.ele('css:.btn-auth.box-login').click()
        time.sleep(1)

        self.page.ele('css:a.btn-auth.btn-login').click()
        self.page.wait.ele_displayed('css:.vtc-user-login')
        self.page.ele('css:.vtc-user-login').input(account)
        self.page.ele('#btn-submit-username').click()

        self.page.wait.ele_displayed('#password')
        self.page.ele('#password').input(password)
        self.page.ele('#btn-login-pass').click()

        self._wait_login_result()

    def _navigate_to_game(self, game: GameCode):
        self.page.ele('#btn-header-shop').click()
        time.sleep(3)

        link = self.page.ele(f'css:a[href*="/cua-hang/{game.value}"]', timeout=5)
        if link:
            link.click()
        else:
            self.page.get(f'https://goplay.vn/cua-hang/{game.value}')

        time.sleep(3)
        logger.info(f"Game page: {self.page.url}")

    def _select_package(self, package: CrossfirePackage):
        el = self.page.ele(package.selector, timeout=5)
        if not el:
            self._dump_debug('select_package_fail')
            raise GoPlayError(GoPlayErrorCode.PACKAGE_NOT_FOUND, f"Không tìm thấy gói: {package.pack_name}")

        el.click()
        logger.info(f"Selected: {package.pack_name}")

        # Wait for payment section to become visible
        self.page.wait.ele_displayed('css:[data-field="payment-method"]', timeout=5)
        logger.info("Payment section visible")

    def _select_payment(self, method: PaymentMethod):
        # Wait for payment item to be enabled (is-disabled class removed)
        selector = f'css:.payment-item[data-method="{method.value}"]:not(.is-disabled)'
        el = self.page.ele(selector, timeout=10)

        if not el:
            # Fallback: click even if disabled
            logger.warning("Payment item still disabled, trying click anyway")
            el = self.page.ele(method.selector, timeout=3)
            if not el:
                self._dump_debug('select_payment_fail')
                raise GoPlayError(GoPlayErrorCode.PAYMENT_NOT_FOUND, f"Không tìm thấy: {method.value}")

        el.click()
        time.sleep(1)
        logger.info(f"Payment: {method.name}")

    def _click_continue(self, game: GameCode):
        btn = self.page.ele(f'css:.btn-payment-game-{game.value}', timeout=5)
        if not btn:
            self._dump_debug('click_continue_fail')
            raise GoPlayError(GoPlayErrorCode.UNKNOWN_ERROR, "Không tìm thấy nút Tiếp tục")

        btn.click()
        time.sleep(3)
        logger.info("Clicked continue")

    def _fill_card_and_submit(self, card_serial: str, card_code: str):
        # Wait for popup to appear
        popup = self.page.ele('#goplayShopPopup', timeout=5)
        serial_input = self.page.ele('#card-serial', timeout=10)

        if not serial_input:
            self._dump_debug('card_popup_fail')
            raise GoPlayError(GoPlayErrorCode.UNKNOWN_ERROR, "Popup nhập thẻ không xuất hiện")

        serial_input.clear()
        serial_input.input(card_serial)

        code_input = self.page.ele('#card-code')
        code_input.clear()
        code_input.input(card_code)
        time.sleep(0.5)

        self.page.ele('#id-shop-popup-ok-btn').click()
        logger.info("Card submitted, waiting for result...")
        time.sleep(5)

        # Check for error in popup
        error_el = self.page.ele('#id-shop-popup-error', timeout=3)
        if error_el and error_el.text.strip():
            error_msg = error_el.text.strip()
            self._dump_debug('payment_error')
            raise GoPlayError(GoPlayErrorCode.PAYMENT_ERROR, error_msg)

        return True

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
            self.page = self._create_browser()

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
            return {
                "success": False,
                "error_code": e.code.value,
                "message": e.detail,
                "detail": None,
            }
        except Exception as e:
            logger.exception("Unexpected error")
            self._dump_debug('topup_error')
            return {
                "success": False,
                "error_code": GoPlayErrorCode.UNKNOWN_ERROR.value,
                "message": str(e),
                "detail": None,
            }
        finally:
            if self.page:
                try:
                    self.page.quit()
                except Exception:
                    pass
                self.page = None
