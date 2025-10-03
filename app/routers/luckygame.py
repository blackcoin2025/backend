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
    base_multipliers = [0, 0.2, 0.5, 1, 1.5, 2, 3, 5, 10, 25, 50, 100]
    probabilities =   [0.03, 0.07, 0.15, 0.20, 0.18, 0.12, 0.09, 0.07, 0.05, 0.025, 0.01, 0.005]

    # Effet "progression" → plus on monte en niveau, plus les grosses valeurs deviennent accessibles
    progression_boost = min(level * 0.01, 0.2)  # max +20% sur les fortes récompenses

    adjusted_probabilities = []
    for i, p in enumerate(probabilities):
        if base_multipliers[i] >= 5:  # Boost uniquement pour les gros gains
            adjusted_probabilities.append(p + progression_boost * p)
        else:
            adjusted_probabilities.append(p)

    # Normaliser
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
