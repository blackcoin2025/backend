import random
import time
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.services import balance_service
from app.routers.auth import get_current_user
from app.models import User
from pydantic import BaseModel

router = APIRouter(prefix="/luckygame", tags=["LuckyGame"])

# ⚠️ Mémoire temporaire des parties (à remplacer par une table DB si persistance nécessaire)
games = {}

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
# Utils
# ----------------------
def generate_multipliers(level: int):
    base_multipliers = [0, 0.3, 0.5, 1, 1.5, 2, 3, 5, 10, 50, 100, 1000]
    probabilities = [0.3, 0.25, 0.15, 0.1, 0.07, 0.05, 0.03, 0.02, 0.015, 0.008, 0.005, 0.002]

    difficulty_factor = 1 + (level // 5) * 0.5
    adjusted_probabilities = [max(p / difficulty_factor, 0.0001) for p in probabilities]

    total = sum(adjusted_probabilities)
    adjusted_probabilities = [p / total for p in adjusted_probabilities]

    def pick():
        r = random.random()
        cumulative = 0
        for m, p in zip(base_multipliers, adjusted_probabilities):
            cumulative += p
            if r <= cumulative:
                return m
        return base_multipliers[-1]

    multipliers = [pick() for _ in range(4)]
    random.shuffle(multipliers)
    return multipliers

# ----------------------
# Routes
# ----------------------
@router.post("/start")
async def start_game(
    req: StartGameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    # Vérifier solde utilisateur
    balance = await balance_service.get_user_balance(db, current_user.id)
    if balance < req.bet:
        raise HTTPException(status_code=400, detail="Solde insuffisant")

    # Débiter la mise
    await balance_service.debit_balance(db, current_user.id, req.bet)

    # Initialiser la partie
    game_id = str(time.time_ns())
    multipliers = generate_multipliers(1)

    games[game_id] = {
        "user_id": current_user.id,
        "current_level": 1,
        "current_reward": req.bet,
        "active": True,
        "multipliers": multipliers
    }

    return {
        "game_id": game_id,
        "current_level": 1,
        "current_reward": req.bet,
        "multipliers": multipliers
    }


@router.post("/play")
async def play_level(
    req: PlayRequest,
    current_user: User = Depends(get_current_user)
):
    game = games.get(req.game_id)
    if not game or not game["active"]:
        raise HTTPException(status_code=400, detail="Partie non trouvée ou terminée")

    # 🔒 Vérification que l'utilisateur correspond
    if game["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé à cette partie")

    multipliers = game["multipliers"]
    if req.choice_index < 0 or req.choice_index >= len(multipliers):
        raise HTTPException(status_code=400, detail="Index de choix invalide")

    chosen = multipliers[req.choice_index]

    if chosen == 0:
        game["active"] = False
        return {
            "result": "lose",
            "multipliers": multipliers,
            "reward": 0,
            "level": game["current_level"]
        }

    game["current_reward"] *= chosen
    game["current_level"] += 1

    next_multipliers = generate_multipliers(game["current_level"])
    game["multipliers"] = next_multipliers

    return {
        "result": "continue",
        "chosen_multiplier": chosen,
        "multipliers": multipliers,
        "next_multipliers": next_multipliers,
        "reward": game["current_reward"],
        "level": game["current_level"],
    }


@router.post("/cashout")
async def cashout(
    req: CashoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    game = games.get(req.game_id)
    if not game or not game["active"]:
        raise HTTPException(status_code=400, detail="Partie non trouvée ou déjà terminée")

    if game["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé à cette partie")

    game["active"] = False
    reward = int(game["current_reward"])

    await balance_service.credit_balance(db, current_user.id, reward)

    return {"reward": reward, "message": "Encaissement effectué ✅"}
