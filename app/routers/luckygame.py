import random
import time
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_async_session
from app.services import balance_service
from app.routers.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/luckygame", tags=["LuckyGame"])

# stockage temporaire des parties
games = {}

MAX_REWARD = 5_000_000


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
# Configuration des niveaux
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


def generate_unique_multiplier(existing: List[float], min_v: float, max_v: float) -> float:
    for _ in range(10):
        m = round(random.uniform(min_v, max_v), 2)
        if m not in existing:
            return m
    return round(random.uniform(min_v, max_v), 2)


def generate_multipliers_for_tier(tier: int) -> List[float]:
    cfg = TIERS[tier]

    winners = []
    for _ in range(cfg["winners"]):
        winners.append(
            generate_unique_multiplier(
                winners,
                cfg["min_mult"],
                cfg["max_mult"]
            )
        )

    losers = [0.0] * (4 - cfg["winners"])

    result = winners + losers
    random.shuffle(result)

    return result


# ----------------------
# Start game
# ----------------------

@router.post("/start")
async def start_game(
    req: StartGameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):

    if req.bet <= 0:
        raise HTTPException(400, "Mise invalide")

    balance = await balance_service.get_user_balance(db, current_user.id)

    if balance < req.bet:
        raise HTTPException(400, "Solde insuffisant")

    # débit
    await balance_service.debit_balance(db, current_user.id, req.bet)
    await db.commit()

    game_id = str(time.time_ns())

    games[game_id] = {
        "user_id": current_user.id,
        "current_level": 1,
        "current_reward": float(req.bet),
        "active": True,
        "multipliers": generate_multipliers_for_tier(1)
    }

    game = games[game_id]

    return {
        "game_id": game_id,
        "level": game["current_level"],
        "reward": int(game["current_reward"]),
        "multipliers": game["multipliers"]
    }


# ----------------------
# Play level
# ----------------------

@router.post("/play")
async def play_level(
    req: PlayRequest,
    current_user: User = Depends(get_current_user)
):

    game = games.get(req.game_id)

    if not game:
        raise HTTPException(400, "Partie introuvable")

    if not game["active"]:
        raise HTTPException(400, "Partie terminée")

    if game["user_id"] != current_user.id:
        raise HTTPException(403, "Accès refusé")

    if req.choice_index not in [0, 1, 2, 3]:
        raise HTTPException(400, "Choix invalide")

    multipliers = game["multipliers"]

    chosen = float(multipliers[req.choice_index])

    # perdant
    if chosen == 0.0:

        game["active"] = False
        game["current_reward"] = 0

        return {
            "result": "lose",
            "multipliers": multipliers,
            "reward": 0,
            "level": game["current_level"]
        }

    # gagnant
    reward = game["current_reward"] * chosen

    if reward > MAX_REWARD:
        reward = float(MAX_REWARD)

    game["current_reward"] = reward
    game["current_level"] += 1

    tier = map_level_to_tier(game["current_level"])

    next_multipliers = generate_multipliers_for_tier(tier)

    game["multipliers"] = next_multipliers

    return {
        "result": "continue",
        "chosen_multiplier": chosen,
        "multipliers": multipliers,
        "next_multipliers": next_multipliers,
        "reward": int(reward),
        "level": game["current_level"]
    }


# ----------------------
# Cashout
# ----------------------

@router.post("/cashout")
async def cashout(
    req: CashoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):

    game = games.get(req.game_id)

    if not game:
        raise HTTPException(400, "Partie introuvable")

    if not game["active"]:
        raise HTTPException(400, "Partie déjà terminée")

    if game["user_id"] != current_user.id:
        raise HTTPException(403, "Accès refusé")

    # bloquer immédiatement la partie
    game["active"] = False

    reward = int(game["current_reward"])

    if reward <= 0:
        raise HTTPException(400, "Récompense invalide")

    if reward > MAX_REWARD:
        reward = MAX_REWARD

    # crédit
    await balance_service.credit_balance(db, current_user.id, reward)

    await db.commit()

    return {
        "reward": reward,
        "message": "Encaissement effectué"
    }