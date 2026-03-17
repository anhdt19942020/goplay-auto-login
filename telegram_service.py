import logging
import httpx

logger = logging.getLogger(__name__)

BOT_TOKEN = "5707304431:AAGfQQBQ3_ZLXCkXoBfw9GDLVwG0kxtoyeM"
CHAT_ID = "@goplay94"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


async def send_telegram(message: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(API_URL, json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
            })
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")


async def notify_topup(params: dict):
    success = params.get("success", False)
    emoji = "✅" if success else "❌"
    status = "THÀNH CÔNG" if success else "THẤT BẠI"

    lines = [
        f"{emoji} <b>Nạp thẻ GoPlay {status}</b>",
        f"Account: <code>{params.get('account', '?')}</code>",
        f"Game: <code>{params.get('game', '?')}</code>",
    ]

    detail = params.get("detail") or {}
    if detail.get("package"):
        lines.append(f"Gói: {detail['package']}")
    if detail.get("go_received") is not None:
        lines.append(f"GO nhận: {detail['go_received']}")
    if detail.get("balance") is not None:
        lines.append(f"Số dư: {detail['balance']}GO")

    if params.get("elapsed_seconds") is not None:
        lines.append(f"⏱ Thời gian: {params['elapsed_seconds']:.1f}s")

    if not success:
        lines.append(f"Lỗi: {params.get('error_code', '?')}")
        lines.append(f"Message: {params.get('message', '?')}")

    await send_telegram("\n".join(lines))


async def call_callback(url: str, payload: dict):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
            logger.info(f"Callback {url} → {resp.status_code}")
    except Exception as e:
        logger.error(f"Callback failed: {url} → {e}")
