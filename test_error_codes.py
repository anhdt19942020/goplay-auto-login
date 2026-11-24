"""Regression check: PAYMENT_ERROR is reserved for a card GoPlay rejected.

The caller moves on to another card when it sees PAYMENT_ERROR, so a server-side
message must never map to it. Messages are verbatim from production logs.
Run: python test_error_codes.py
"""
from enums import GoPlayErrorCode as Code
from goplay_service import GoPlayService

classify = lambda msg: GoPlayService._classify_topup_error(None, msg)

CASES = {
    "Thẻ đã được sử dụng hoặc không tồn tại": Code.PAYMENT_ERROR,
    "Thông tin serial hoặc mã thẻ không đúng định dạng.": Code.PAYMENT_ERROR,
    "Hệ thống đang bận. Vui lòng thử lại sau 15 phút": Code.UNKNOWN_ERROR,
    "Hệ thống lỗi khi xử lý mã thẻ không hợp lệ": Code.UNKNOWN_ERROR,
    "Xác thực captcha không thành công. Vui lòng thử lại": Code.CAPTCHA_REQUIRED,
    "Một thông báo chưa từng thấy": Code.UNKNOWN_ERROR,
    "": Code.UNKNOWN_ERROR,
}

if __name__ == "__main__":
    for message, expected in CASES.items():
        actual = classify(message)
        assert actual == expected, f"{message!r}: expected {expected.value}, got {actual.value}"
    print(f"OK {len(CASES)} cases")
