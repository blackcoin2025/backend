import random
import uuid
import asyncio
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.models import User
from app.routers.auth import get_current_user
from app.services import balance_service

router = APIRouter(prefix="/tradegame", tags=["Trade Game"])

# Logos disponibles
logos = ["bitcoin", "pi", "toncoin", "blackcoin"]

# Stockage temporaire des parties actives (id_partie → infos)
active_games = {}


# -------- Utils --------
def generate_multiplier():
    """
    Génère un multiplicateur aléatoire totalisant les gains et pertes
    pour créer une expérience psychologiquement plus réaliste.
    """
    r = random.random()
    if r < 0.8:
        return round(random.uniform(1.0, 5.0), 2)
    elif r < 0.9:
        return round(random.uniform(5.0, 20.0), 2)
    elif r < 0.97:
        return round(random.uniform(20.0, 100.0), 2)
    else:
        return round(random.uniform(100.0, 500.0), 2)


def choose_logo():
    return random.choice(logos)


# -------- Routes --------
@router.post("/play")
async def play_round(
    bet1: int = 0,
    bet2: int = 0,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    total_bet = (bet1 if bet1 > 0 else 0) + (bet2 if bet2 > 0 else 0)

    if total_bet <= 0:
        return {"error": "Aucune mise placée"}

    try:
        # Débit uniquement les mises supérieures à 0
        if bet1 > 0:
            await balance_service.debit_balance(db, current_user.id, bet1)
        if bet2 > 0:
            await balance_service.debit_balance(db, current_user.id, bet2)
    except ValueError as e:
        return {"error": str(e)}

    logo = choose_logo()
    multiplier_max = generate_multiplier()
    game_id = str(uuid.uuid4())

    active_games[game_id] = {
        "user_id": current_user.id,
        "logo": logo,
        "multiplier_max": multiplier_max,
        "bets": {}
    }

    # On enregistre seulement les mises actives
    if bet1 > 0:
        active_games[game_id]["bets"]["bet1"] = {
            "amount": bet1,
            "cashed_out": False
        }
    if bet2 > 0:
        active_games[game_id]["bets"]["bet2"] = {
            "amount": bet2,
            "cashed_out": False
        }

    return {
        "message": "Partie lancée",
        "game_id": game_id,
        "logo": logo,
        "max_multiplier": multiplier_max
    }


@router.post("/cashout")
async def cashout(
    game_id: str,
    bet_key: str,
    cashout_multiplier: float,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    if game_id not in active_games:
        return {"error": "Partie introuvable ou expirée"}

    game = active_games[game_id]

    if game["user_id"] != current_user.id:
        return {"error": "Non autorisé"}

    bet = game["bets"].get(bet_key)
    if not bet or bet["amount"] <= 0:
        return {"error": "Pas de mise valide sur ce champ"}

    if bet["cashed_out"]:
        return {"error": "Déjà encaissé"}

    if cashout_multiplier > game["multiplier_max"]:
        # La mise a crashé
        bet["cashed_out"] = True
        bet["amount"] = 0
        return {"message": "Trop tard, la mise a crashé", "gain": 0}

    # Encaisser la mise
    gain = int(bet["amount"] * cashout_multiplier)
    bet["cashed_out"] = True

    await balance_service.credit_balance(db, current_user.id, gain)

    return {
        "message": "Cashout réussi",
        "bet": bet_key,
        "cashout_multiplier": cashout_multiplier,
        "gain": gain
    }


@router.websocket("/ws/progress/{game_id}")
async def game_progress(websocket: WebSocket, game_id: str):
    await websocket.accept()

    if game_id not in active_games:
        await websocket.send_json({"error": "Partie introuvable"})
        await websocket.close()
        return

    game = active_games[game_id]
    multiplier_max = game["multiplier_max"]

    try:
        current = 1.0
        base_step = 0.05
        while current < multiplier_max:
            step_variation = random.uniform(0.9, 1.1)
            step = base_step * step_variation

            if current >= 30:
                step *= 2.5
            elif current >= 20:
                step *= 2.0
            elif current >= 10:
                step *= 1.5

            current = round(current + step, 2)
            await websocket.send_json({"multiplier": current})

            sleep_time = max(0.02, 0.1 - (current // 10) * 0.01 + random.uniform(-0.01, 0.01))
            await asyncio.sleep(sleep_time)

        # Crash final
        await websocket.send_json({"event": "crash", "final_multiplier": multiplier_max})
        await websocket.close()

    except WebSocketDisconnect:
        print(f"Client déconnecté du jeu {game_id}")
