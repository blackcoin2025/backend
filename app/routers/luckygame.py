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

# Mémoire temporaire des parties (remplacer par DB pour production)
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
# Configuration des "niveaux" (tranches de parties)
# Chaque palier définit : min_mult, max_mult et nombre de cases gagnantes
# ----------------------
TIERS = {
    1: {  # parties 1..5
        "min_mult": 0.10,
        "max_mult": 1.60,
        "winners": 4  # 4 gagnantes (100%)
    },
    2: {  # parties 6..10
        "min_mult": 1.50,
        "max_mult": 3.80,
        "winners": 3  # 3 gagnantes, 1 perdante (≈75%)
    },
    3: {  # parties 11..15
        "min_mult": 1.90,
        "max_mult": 6.50,
        "winners": 3  # 3 gagnantes, 1 perdante (≈75%)
    },
    4: {  # parties 16..20
        "min_mult": 2.40,
        "max_mult": 20.00,
        "winners": 2  # 2 gagnantes, 2 perdantes (50%)
    },
    5: {  # parties 21..25+
        "min_mult": 7.50,
        "max_mult": 100.00,
        "winners": 1  # 1 gagnante, 3 perdantes (25%)
    },
}

# Sécurité pour éviter overflow/explosion
MAX_REWARD = 5_000_000

# ----------------------
# Helpers
# ----------------------
def map_level_to_tier(current_level: int) -> int:
    """Map current_level (1..n) to a tier 1..5 according to your ranges."""
    if 1 <= current_level <= 5:
        return 1
    if 6 <= current_level <= 10:
        return 2
    if 11 <= current_level <= 15:
        return 3
    if 16 <= current_level <= 20:
        return 4
    # 21+ -> tier 5
    return 5

def generate_unique_multiplier(existing: List[float], min_v: float, max_v: float) -> float:
    """Génère un multiplicateur (2 décimales) évitant autant que possible les doublons exacts."""
    for _ in range(12):
        m = round(random.uniform(min_v, max_v), 2)
        if m not in existing:
            return m
    # fallback : retourne une valeur random même si doublon
    return round(random.uniform(min_v, max_v), 2)

def generate_multipliers_for_tier(tier: int) -> List[float]:
    """
    Génère exactement 4 valeurs:
    - 'winners' multiplicateurs entre min_mult et max_mult (non nuls)
    - le reste sont 0 (perdantes)
    """
    cfg = TIERS[tier]
    winners_count = cfg["winners"]
    min_mult = cfg["min_mult"]
    max_mult = cfg["max_mult"]

    winners: List[float] = []
    for _ in range(winners_count):
        winners.append(generate_unique_multiplier(winners, min_mult, max_mult))

    losers = [0.0] * (4 - winners_count)
    result = winners + losers
    random.shuffle(result)
    return result

# ----------------------
# Routes
# ----------------------
@router.post("/start")
async def start_game(
    req: StartGameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    # Validation de la mise
    if req.bet <= 0:
        raise HTTPException(status_code=400, detail="Mise invalide")

    # Vérifier solde
    balance = await balance_service.get_user_balance(db, current_user.id)
    if balance < req.bet:
        raise HTTPException(status_code=400, detail="Solde insuffisant")

    # Débiter la mise
    await balance_service.debit_balance(db, current_user.id, req.bet)

    game_id = str(time.time_ns())
    game = {
        "user_id": current_user.id,
        "current_level": 1,
        "current_reward": float(req.bet),
        "active": True,
        "round_count": 1,  # nombre de tours joués (1 = première grille)
        "multipliers": generate_multipliers_for_tier(map_level_to_tier(1)),
    }
    games[game_id] = game

    return {
        "game_id": game_id,
        "current_level": game["current_level"],
        "current_reward": int(game["current_reward"]),
        "multipliers": game["multipliers"],
    }

@router.post("/play")
async def play_level(
    req: PlayRequest,
    current_user: User = Depends(get_current_user)
):
    game = games.get(req.game_id)
    if not game:
        raise HTTPException(status_code=400, detail="Partie non trouvée")
    if not game["active"]:
        raise HTTPException(status_code=400, detail="Partie terminée")

    if game["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé à cette partie")

    multipliers = game.get("multipliers")
    if not isinstance(multipliers, list) or len(multipliers) != 4:
        raise HTTPException(status_code=500, detail="Données de partie corrompues")

    if req.choice_index < 0 or req.choice_index >= 4:
        raise HTTPException(status_code=400, detail="Index de choix invalide")

    chosen = float(multipliers[req.choice_index])

    # Si perdant
    if chosen == 0.0:
        game["active"] = False
        game["current_reward"] = 0.0
        return {
            "result": "lose",
            "multipliers": multipliers,
            "reward": 0,
            "level": game["current_level"],
        }

    # Si gagnant : appliquer le multiplicateur
    new_reward = game["current_reward"] * chosen
    # Plafonner la récompense
    if new_reward > MAX_REWARD:
        new_reward = float(MAX_REWARD)

    game["current_reward"] = new_reward
    # Incrémente le current_level et le round_count
    game["current_level"] = game["current_level"] + 1
    game["round_count"] = game.get("round_count", 0) + 1

    # Déterminer le tier en fonction de current_level (tranches de 5)
    tier = map_level_to_tier(game["current_level"])
    next_multipliers = generate_multipliers_for_tier(tier)
    game["multipliers"] = next_multipliers

    return {
        "result": "continue",
        "chosen_multiplier": chosen,
        "multipliers": multipliers,
        "next_multipliers": next_multipliers,
        "reward": int(game["current_reward"]),
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

    # créditer le solde utilisateur
    await balance_service.credit_balance(db, current_user.id, reward)

    return {"reward": reward, "message": "Encaissement effectué ✅"}
