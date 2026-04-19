import json
import uuid
import random
import secrets
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_async_session
from app.services import balance_service
from app.routers.auth import get_current_user
from app.models import User

# 🔥 IMPORT CENTRALISÉ (IMPORTANT)
from app.core.cache import redis_client

GAME_TTL = 300
MAX_REWARD = 5_000_000

router = APIRouter(prefix="/luckygame", tags=["LuckyGame"])


# ----------------------
# Models
# ----------------------

class StartGameRequest(BaseModel):
    bet: int


class PlayRequest(BaseModel):
    game_id: str
    choice_index: int


class CashoutRequest(BaseModel):
    game_id: str


# ----------------------
# Config niveaux
# ----------------------

TIERS = {
    1: {"min_mult": 0.10, "max_mult": 1.60, "winners": 4},
    2: {"min_mult": 1.50, "max_mult": 3.80, "winners": 3},
    3: {"min_mult": 1.90, "max_mult": 6.50, "winners": 3},
    4: {"min_mult": 2.40, "max_mult": 20.00, "winners": 2},
    5: {"min_mult": 7.50, "max_mult": 100.00, "winners": 1},
}


# ----------------------
# Helpers
# ----------------------

def generate_game_id():
    return str(uuid.uuid4())


def map_level_to_tier(level: int) -> int:
    if level <= 5:
        return 1
    if level <= 10:
        return 2
    if level <= 15:
        return 3
    if level <= 20:
        return 4
    return 5


def secure_random(min_v: float, max_v: float) -> float:
    return round(min_v + (max_v - min_v) * secrets.randbelow(10000) / 10000, 2)


def generate_unique_multiplier(existing: List[float], min_v: float, max_v: float) -> float:
    for _ in range(10):
        m = secure_random(min_v, max_v)
        if m not in existing:
            return m
    return secure_random(min_v, max_v)


def generate_multipliers_for_tier(tier: int) -> List[float]:
    cfg = TIERS[tier]

    winners = [
        generate_unique_multiplier([], cfg["min_mult"], cfg["max_mult"])
        for _ in range(cfg["winners"])
    ]

    losers = [0.0] * (4 - cfg["winners"])
    result = winners + losers
    random.shuffle(result)

    return result


# ----------------------
# Start
# ----------------------

@router.post("/start")
async def start_game(
    req: StartGameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    if not redis_client:
        raise HTTPException(500, "Redis indisponible")

    if req.bet <= 0:
        raise HTTPException(400, "Mise invalide")

    balance = await balance_service.get_user_balance(db, current_user.id)

    if balance < req.bet:
        raise HTTPException(400, "Solde insuffisant")

    await balance_service.debit_balance(db, current_user.id, req.bet)
    await db.commit()

    game_id = generate_game_id()

    game_data = {
        "user_id": current_user.id,
        "level": 1,
        "reward": float(req.bet),
        "active": True,
        "multipliers": generate_multipliers_for_tier(1)
    }

    await redis_client.setex(f"game:{game_id}", GAME_TTL, json.dumps(game_data))

    return {
        "game_id": game_id,
        "level": 1,
        "reward": req.bet,
        "multipliers": game_data["multipliers"]
    }


# ----------------------
# Play
# ----------------------

@router.post("/play")
async def play_level(
    req: PlayRequest,
    current_user: User = Depends(get_current_user)
):
    if not redis_client:
        raise HTTPException(500, "Redis indisponible")

    key = f"game:{req.game_id}"
    lock_key = f"lock:{req.game_id}"

    if not await redis_client.set(lock_key, "1", ex=5, nx=True):
        raise HTTPException(429, "Action en cours")

    try:
        data = await redis_client.get(key)

        if not data:
            raise HTTPException(400, "Partie introuvable")

        game = json.loads(data)

        if not game["active"]:
            raise HTTPException(400, "Partie terminée")

        if game["user_id"] != current_user.id:
            raise HTTPException(403, "Accès refusé")

        if req.choice_index not in [0, 1, 2, 3]:
            raise HTTPException(400, "Choix invalide")

        multipliers = game["multipliers"]
        chosen = float(multipliers[req.choice_index])

        # ❌ LOSE
        if chosen == 0.0:
            game["active"] = False
            game["reward"] = 0

            await redis_client.setex(key, GAME_TTL, json.dumps(game))

            return {
                "result": "lose",
                "multipliers": multipliers,
                "reward": 0,
                "level": game["level"]
            }

        # ✅ WIN
        reward = min(game["reward"] * chosen, MAX_REWARD)

        game["reward"] = reward
        game["level"] += 1

        tier = map_level_to_tier(game["level"])
        next_multipliers = generate_multipliers_for_tier(tier)

        game["multipliers"] = next_multipliers

        await redis_client.setex(key, GAME_TTL, json.dumps(game))

        return {
            "result": "continue",
            "chosen_multiplier": chosen,
            "multipliers": multipliers,
            "next_multipliers": next_multipliers,
            "reward": int(reward),
            "level": game["level"]
        }

    finally:
        await redis_client.delete(lock_key)


# ----------------------
# Cashout
# ----------------------

@router.post("/cashout")
async def cashout(
    req: CashoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    if not redis_client:
        raise HTTPException(500, "Redis indisponible")

    key = f"game:{req.game_id}"
    lock_key = f"lock:{req.game_id}"

    if not await redis_client.set(lock_key, "1", ex=5, nx=True):
        raise HTTPException(429, "Action en cours")

    try:
        data = await redis_client.get(key)

        if not data:
            raise HTTPException(400, "Partie introuvable")

        game = json.loads(data)

        if not game["active"]:
            raise HTTPException(400, "Déjà terminé")

        if game["user_id"] != current_user.id:
            raise HTTPException(403, "Accès refusé")

        reward = int(min(game["reward"], MAX_REWARD))

        if reward <= 0:
            raise HTTPException(400, "Récompense invalide")

        await balance_service.credit_balance(db, current_user.id, reward)
        await db.commit()

        await redis_client.delete(key)

        return {
            "reward": reward,
            "message": "Encaissement effectué"
        }

    finally:
        await redis_client.delete(lock_key)