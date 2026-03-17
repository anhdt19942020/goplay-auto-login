from enum import Enum


class GoPlayErrorCode(str, Enum):
    """Error codes for GoPlay API responses"""

    # Login errors
    WRONG_PASSWORD = "WRONG_PASSWORD"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_NOT_FOUND = "ACCOUNT_NOT_FOUND"
    ACCOUNT_NOT_REGISTERED = "ACCOUNT_NOT_REGISTERED"
    LOGIN_TIMEOUT = "LOGIN_TIMEOUT"

    # Input validation
    INVALID_GAME = "INVALID_GAME"
    INVALID_PACKAGE = "INVALID_PACKAGE"

    # Shop errors
    PACKAGE_NOT_FOUND = "PACKAGE_NOT_FOUND"
    PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"
    PAYMENT_ERROR = "PAYMENT_ERROR"
    INVALID_CARD_INFO = "INVALID_CARD_INFO"

    # Infrastructure
    BROWSER_ERROR = "BROWSER_ERROR"

    # Generic
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

    @property
    def message(self) -> str:
        return _ERROR_MESSAGES.get(self, "Lỗi không xác định")

    @classmethod
    def from_popup_message(cls, popup_text: str) -> "GoPlayErrorCode":
        """Map GoPlay popup message text to error code"""
        normalized = popup_text.strip().lower()
        for text, code in _POPUP_TEXT_MAP.items():
            if text in normalized:
                return code
        return cls.UNKNOWN_ERROR


_ERROR_MESSAGES: dict[str, str] = {
    GoPlayErrorCode.WRONG_PASSWORD: "Sai mật khẩu",
    GoPlayErrorCode.ACCOUNT_LOCKED: "Tài khoản bị khóa",
    GoPlayErrorCode.ACCOUNT_NOT_FOUND: "Tài khoản không tồn tại",
    GoPlayErrorCode.ACCOUNT_NOT_REGISTERED: "Tài khoản chưa đăng ký GoPlay",
    GoPlayErrorCode.LOGIN_TIMEOUT: "Đăng nhập quá thời gian chờ",
    GoPlayErrorCode.INVALID_GAME: "Mã game không hợp lệ",
    GoPlayErrorCode.INVALID_PACKAGE: "Gói nạp không hợp lệ",
    GoPlayErrorCode.PACKAGE_NOT_FOUND: "Không tìm thấy gói nạp trên trang",
    GoPlayErrorCode.PAYMENT_NOT_FOUND: "Không tìm thấy phương thức thanh toán",
    GoPlayErrorCode.PAYMENT_ERROR: "Lỗi thanh toán",
    GoPlayErrorCode.INVALID_CARD_INFO: "Thông tin thẻ không hợp lệ",
    GoPlayErrorCode.BROWSER_ERROR: "Không thể khởi động trình duyệt",
    GoPlayErrorCode.UNKNOWN_ERROR: "Lỗi không xác định",
}

_POPUP_TEXT_MAP: dict[str, GoPlayErrorCode] = {
    "sai mật khẩu": GoPlayErrorCode.WRONG_PASSWORD,
    "wrong password": GoPlayErrorCode.WRONG_PASSWORD,
    "mật khẩu không đúng": GoPlayErrorCode.WRONG_PASSWORD,
    "tài khoản bị khóa": GoPlayErrorCode.ACCOUNT_LOCKED,
    "account locked": GoPlayErrorCode.ACCOUNT_LOCKED,
    "tài khoản không tồn tại": GoPlayErrorCode.ACCOUNT_NOT_FOUND,
    "account not found": GoPlayErrorCode.ACCOUNT_NOT_FOUND,
    "không tìm thấy tài khoản": GoPlayErrorCode.ACCOUNT_NOT_FOUND,
    "chưa được đăng ký": GoPlayErrorCode.ACCOUNT_NOT_REGISTERED,
}


class GameCode(str, Enum):
    CATS_AND_SOUP = "CNS"
    CROSSFIRE = "CF"
    DREAMY_CAFE = "DREAMY"
    VUA_PHAP_THUAT = "VPT"


class CrossfirePackage(Enum):
    """Crossfire GO packages (1 GO = 1,000đ)"""
    GO_20 = (1, "Nhận 20 GO", 20, 20_000, 0)
    GO_50 = (2, "Nhận 50 GO", 50, 50_000, 0)
    GO_100 = (3, "Nhận 100 GO", 100, 100_000, 0)
    GO_300 = (4, "Nhận 300 GO", 300, 300_000, 0)
    GO_1000 = (5, "Nhận 1,000 GO", 1_000, 1_000_000, 0)
    GO_2000 = (6, "Nhận 2,000 GO", 2_000, 2_000_000, 0)

    def __init__(self, pack_id, pack_name, go, price, pack_type):
        self.pack_id = pack_id
        self.pack_name = pack_name
        self.go = go
        self.price = price
        self.pack_type = pack_type

    @property
    def selector(self):
        return f'css:.goPlay-package[data-packid="{self.pack_id}"]'


class PaymentMethod(str, Enum):
    QR = "BANKTRANFER"
    THE_VCOIN = "CARD-VCOIN"
    ONEPAY = "EPAYMENT-ONEPAY"
    MOMO = "EPAYMENT-MOMO"
    VTC_PAY = "EPAYMENT-VTCPAY"

    @property
    def selector(self):
        return f'css:.payment-item[data-method="{self.value}"]'
