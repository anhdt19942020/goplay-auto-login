import os
import time
import logging

from DrissionPage import ChromiumOptions, ChromiumPage
from enums import CrossfirePackage, GameCode, PaymentMethod

logger = logging.getLogger(__name__)


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

    def _login(self, account: str, password: str):
        self.page.get('https://goplay.vn/')
        time.sleep(3)

        # Already logged in?
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

        self.page.wait.ele_displayed('#btn-header-shop', timeout=15)
        logger.info("Login OK")

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
            raise Exception(f"Package not found: {package.pack_name}")
        el.click()
        time.sleep(1)
        logger.info(f"Selected: {package.pack_name}")

    def _select_payment(self, method: PaymentMethod):
        el = self.page.ele(method.selector, timeout=5)
        if not el:
            raise Exception(f"Payment not found: {method.value}")
        el.click()
        time.sleep(1)
        logger.info(f"Payment: {method.name}")

    def _click_continue(self, game: GameCode):
        btn = self.page.ele(f'css:.btn-payment-game-{game.value}', timeout=5)
        if not btn:
            raise Exception("Continue button not found")
        btn.click()
        time.sleep(2)
        logger.info("Clicked continue")

    def _fill_card_and_submit(self, card_serial: str, card_code: str):
        # Wait for popup
        self.page.wait.ele_displayed('#card-serial', timeout=10)

        self.page.ele('#card-serial').input(card_serial)
        self.page.ele('#card-code').input(card_code)
        time.sleep(0.5)

        self.page.ele('#id-shop-popup-ok-btn').click()
        logger.info("Card submitted, waiting for result...")
        time.sleep(5)

        # Check for error
        error_el = self.page.ele('#id-shop-popup-error', timeout=3)
        if error_el and error_el.text.strip():
            raise Exception(f"Payment error: {error_el.text.strip()}")

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
                "message": "Nạp thẻ thành công",
                "detail": {
                    "game": game.value,
                    "package": package.pack_name,
                    "price": package.price,
                    "go": package.go,
                },
            }
        except Exception as e:
            logger.exception("Topup failed")
            return {
                "success": False,
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
