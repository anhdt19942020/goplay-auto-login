import logging

from fastapi import FastAPI, APIRouter
from pydantic import BaseModel

from enums import CrossfirePackage, GameCode
from goplay_service import GoPlayService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title="GoPlay Auto TopUp API", version="1.0.0")
router = APIRouter(prefix="/go-play")


class TopUpRequest(BaseModel):
    game: str
    account: str
    password: str
    package: str
    card_serial: str
    card_code: str

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
    """List available games and packages"""
    games = [{"code": g.value, "name": g.name} for g in GameCode]

    packages = [
        {
            "key": p.name,
            "name": p.pack_name,
            "go": p.go,
            "price": p.price,
        }
        for p in CrossfirePackage
    ]

    return {"games": games, "packages_crossfire": packages}


@router.post("/topup")
def topup(req: TopUpRequest):
    """Login and top-up game with VCOIN card"""
    try:
        game = GameCode(req.game)
    except ValueError:
        valid = [g.value for g in GameCode]
        return {"success": False, "message": f"Invalid game. Valid: {valid}"}

    try:
        package = CrossfirePackage[req.package]
    except KeyError:
        valid = [p.name for p in CrossfirePackage]
        return {"success": False, "message": f"Invalid package. Valid: {valid}"}

    service = GoPlayService()
    result = service.topup(
        game=game,
        account=req.account,
        password=req.password,
        package=package,
        card_serial=req.card_serial,
        card_code=req.card_code,
    )
    return result


app.include_router(router)
