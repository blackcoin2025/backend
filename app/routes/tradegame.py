import random
import uuid
import asyncio
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models import User
from app.routers.auth import get_current_user
from app.services import balance_service

router = APIRouter(prefix="/tradegame", tags=["Trade Game"])

logos = ["bitcoin", "pi", "toncoin", "blackcoin"]

active_games = {}

MAX_GAIN = 10_000_000


# -------------------------
# Utils
# -------------------------

def generate_multiplier():
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


# -------------------------
# Start game
# -------------------------

@router.post("/play")
async def play_round(
    bet1: int = 0,
    bet2: int = 0,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):

    if bet1 < 0 or bet2 < 0:
        raise HTTPException(400, "Mise invalide")

    total_bet = bet1 + bet2

    if total_bet <= 0:
        raise HTTPException(400, "Aucune mise placée")

    balance = await balance_service.get_user_balance(db, current_user.id)

    if balance < total_bet:
        raise HTTPException(400, "Solde insuffisant")

    if bet1 > 0:
        await balance_service.debit_balance(db, current_user.id, bet1)

    if bet2 > 0:
        await balance_service.debit_balance(db, current_user.id, bet2)

    await db.commit()

    game_id = str(uuid.uuid4())

    multiplier_max = generate_multiplier()
    logo = choose_logo()

    active_games[game_id] = {
        "user_id": current_user.id,
        "logo": logo,
        "multiplier_max": multiplier_max,
        "bets": {},
        "finished": False
    }

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
        "game_id": game_id,
        "logo": logo
    }


# -------------------------
# Cashout
# -------------------------

@router.post("/cashout")
async def cashout(
    game_id: str,
    bet_key: str,
    cashout_multiplier: float,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):

    game = active_games.get(game_id)

    if not game:
        raise HTTPException(400, "Partie introuvable")

    if game["user_id"] != current_user.id:
        raise HTTPException(403, "Accès refusé")

    if game["finished"]:
        raise HTTPException(400, "Partie terminée")

    bet = game["bets"].get(bet_key)

    if not bet:
        raise HTTPException(400, "Mise invalide")

    if bet["cashed_out"]:
        raise HTTPException(400, "Déjà encaissé")

    max_mult = game["multiplier_max"]

    if cashout_multiplier > max_mult:

        bet["cashed_out"] = True
        bet["amount"] = 0

        return {
            "message": "Crash",
            "gain": 0
        }

    gain = int(bet["amount"] * cashout_multiplier)

    if gain > MAX_GAIN:
        gain = MAX_GAIN

    bet["cashed_out"] = True

    await balance_service.credit_balance(db, current_user.id, gain)

    await db.commit()

    return {
        "message": "Cashout réussi",
        "bet": bet_key,
        "multiplier": cashout_multiplier,
        "gain": gain
    }


# -------------------------
# Websocket progress
# -------------------------

@router.websocket("/ws/progress/{game_id}")
async def game_progress(websocket: WebSocket, game_id: str):

    await websocket.accept()

    game = active_games.get(game_id)

    if not game:
        await websocket.send_json({"error": "Partie introuvable"})
        await websocket.close()
        return

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
                step *= 2
            elif current >= 10:
                step *= 1.5

            current = round(current + step, 2)

            await websocket.send_json({
                "multiplier": current
            })

            sleep_time = max(
                0.02,
                0.1 - (current // 10) * 0.01 + random.uniform(-0.01, 0.01)
            )

            await asyncio.sleep(sleep_time)

        game["finished"] = True

        await websocket.send_json({
            "event": "crash",
            "final_multiplier": multiplier_max
        })

        await websocket.close()

    except WebSocketDisconnect:
        print(f"Client déconnecté du jeu {game_id}")