from enum import Enum


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
