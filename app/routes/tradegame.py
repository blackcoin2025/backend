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
    # 80% des parties crashent tôt (petits gains ou pertes)
    if r < 0.8:
        return round(random.uniform(1.0, 5.0), 2)
    # 10% donnent des gains moyens
    elif r < 0.9:
        return round(random.uniform(5.0, 20.0), 2)
    # 7% donnent de gros gains
    elif r < 0.97:
        return round(random.uniform(20.0, 100.0), 2)
    # 3% jackpot rare
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
    total_bet = bet1 + bet2
    if total_bet <= 0:
        return {"error": "Aucune mise placée"}

    try:
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
        "bets": {
            "bet1": {"amount": bet1, "cashed_out": False},
            "bet2": {"amount": bet2, "cashed_out": False},
        }
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
        return {"error": "Trop tard, le logo a déjà crashé"}

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
            # Randomisation légère du step pour donner un sentiment d'incertitude
            step_variation = random.uniform(0.9, 1.1)
            step = base_step * step_variation

            # Accélération progressive à partir de x10, x20, x30...
            if current >= 30:
                step *= 2.5
            elif current >= 20:
                step *= 2.0
            elif current >= 10:
                step *= 1.5

            current = round(current + step, 2)
            await websocket.send_json({"multiplier": current})

            # Variation du temps de pause pour ajouter du suspense
            sleep_time = max(0.02, 0.1 - (current // 10) * 0.01 + random.uniform(-0.01, 0.01))
            await asyncio.sleep(sleep_time)

        # Crash final
        await websocket.send_json({"event": "crash", "final_multiplier": multiplier_max})
        await websocket.close()

    except WebSocketDisconnect:
        print(f"Client déconnecté du jeu {game_id}")
