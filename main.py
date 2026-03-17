import asyncio
import logging
import time
from typing import Optional

from fastapi import FastAPI, APIRouter
from pydantic import BaseModel
from contextlib import asynccontextmanager

from enums import CrossfirePackage, GameCode, GoPlayErrorCode
from goplay_service import GoPlayService
from telegram_service import notify_topup, call_callback

import os

LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

MAX_QUEUE_SIZE = 5
TASK_TIMEOUT = 90


class TopUpTask:
    def __init__(self, game, account, password, package, card_serial, card_code, url_callback=None):
        self.game = game
        self.account = account
        self.password = password
        self.package = package
        self.card_serial = card_serial
        self.card_code = card_code
        self.url_callback = url_callback
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()
        self.created_at = time.time()


task_queue: asyncio.Queue[TopUpTask] = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
queue_stats = {"processing": False, "total_processed": 0, "total_rejected": 0}


async def queue_worker():
    service = GoPlayService()
    logger.info("Queue worker started")
    while True:
        task = await task_queue.get()
        if task.future.cancelled():
            task_queue.task_done()
            continue

        queue_stats["processing"] = True
        logger.info(f"Processing topup: {task.account} | queue remaining: {task_queue.qsize()}")
        try:
            result = await asyncio.to_thread(
                service.topup,
                game=task.game,
                account=task.account,
                password=task.password,
                package=task.package,
                card_serial=task.card_serial,
                card_code=task.card_code,
            )
            if not task.future.cancelled():
                task.future.set_result(result)
        except Exception as e:
            result = {
                "success": False,
                "error_code": GoPlayErrorCode.UNKNOWN_ERROR.value,
                "message": str(e),
                "detail": None,
            }
            if not task.future.cancelled():
                task.future.set_result(result)
        finally:
            queue_stats["processing"] = False
            queue_stats["total_processed"] += 1

            # Fire-and-forget: callback + telegram
            notify_payload = {**result, "account": task.account, "game": task.game.value}
            asyncio.create_task(notify_topup(notify_payload))
            if task.url_callback:
                asyncio.create_task(call_callback(task.url_callback, result))
            task_queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = asyncio.create_task(queue_worker())
    # Pre-warm: start Chrome browser so first request is faster
    def _prewarm():
        try:
            svc = GoPlayService()
            svc._ensure_browser()
            logger.info("Browser pre-warmed successfully")
        except Exception as e:
            logger.warning(f"Browser pre-warm failed (will retry on first request): {e}")
    asyncio.get_event_loop().run_in_executor(None, _prewarm)
    yield
    worker.cancel()


app = FastAPI(title="GoPlay Auto TopUp API", version="1.1.0", lifespan=lifespan)
router = APIRouter(prefix="/go-play")


class TopUpRequest(BaseModel):
    game: str
    account: str
    password: str
    package: str
    card_serial: str
    card_code: str
    url_callback: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "game": "CF",
                    "account": "username",
                    "password": "password",
                    "package": "GO_100",
                    "card_serial": "123456789",
                    "card_code": "987654321",
                }
            ]
        }
    }


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/games")
def list_games():
    games = [{"code": g.value, "name": g.name} for g in GameCode]
    packages = [
        {"key": p.name, "name": p.pack_name, "go": p.go, "price": p.price}
        for p in CrossfirePackage
    ]
    return {"games": games, "packages_crossfire": packages}


@router.get("/queue-status")
def get_queue_status():
    return {
        "queue_size": task_queue.qsize(),
        "max_queue_size": MAX_QUEUE_SIZE,
        "processing": queue_stats["processing"],
        "total_processed": queue_stats["total_processed"],
        "total_rejected": queue_stats["total_rejected"],
    }


@router.post("/topup")
async def topup(req: TopUpRequest):
    try:
        game = GameCode(req.game)
    except ValueError:
        valid = [g.value for g in GameCode]
        return {
            "success": False,
            "error_code": GoPlayErrorCode.INVALID_GAME.value,
            "message": f"{GoPlayErrorCode.INVALID_GAME.message}. Hợp lệ: {valid}",
            "detail": None,
        }

    try:
        package = CrossfirePackage[req.package]
    except KeyError:
        valid = [p.name for p in CrossfirePackage]
        return {
            "success": False,
            "error_code": GoPlayErrorCode.INVALID_PACKAGE.value,
            "message": f"{GoPlayErrorCode.INVALID_PACKAGE.message}. Hợp lệ: {valid}",
            "detail": None,
        }

    if task_queue.full():
        queue_stats["total_rejected"] += 1
        return {
            "success": False,
            "error_code": "QUEUE_FULL",
            "message": f"Server đang bận ({MAX_QUEUE_SIZE} request đang chờ). Vui lòng thử lại sau.",
            "detail": {"queue_size": task_queue.qsize()},
        }

    task = TopUpTask(game, req.account, req.password, package, req.card_serial, req.card_code, req.url_callback)
    await task_queue.put(task)
    position = task_queue.qsize()
    logger.info(f"Queued topup for {req.account} | position: {position}")

    if req.url_callback:
        return {
            "success": True,
            "error_code": None,
            "message": f"Yêu cầu xử lý ngầm đã vào hàng đợi (vị trí thứ {position}). Kết quả sẽ được gửi về callback.",
            "detail": {"queue_position": position, "url_callback": req.url_callback},
        }

    try:
        result = await asyncio.wait_for(task.future, timeout=TASK_TIMEOUT)
        return result
    except asyncio.TimeoutError:
        task.future.cancel()
        return {
            "success": False,
            "error_code": "QUEUE_TIMEOUT",
            "message": f"Request timeout sau {TASK_TIMEOUT}s. Vui lòng thử lại.",
            "detail": None,
        }


app.include_router(router)
