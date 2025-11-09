# app/routes/wallet.py
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.services.wallet_service import credit_wallet, debit_wallet, get_wallet_balance
from app.routers.auth import get_current_user

router = APIRouter(
    prefix="/wallet",
    tags=["Wallet"]
)


@router.post("/credit")
async def credit_user_wallet(
    amount: float = Body(..., embed=True, ge=0.01, description="Montant à créditer au wallet"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    💰 Créditer le wallet de l'utilisateur connecté.
    Crée un wallet si inexistant.
    """
    try:
        wallet = await credit_wallet(user, amount, db)
        return {
            "message": f"✅ {amount:.2f} $BKC ajoutés au wallet.",
            "user_id": user.id,
            "balance": wallet.amount
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/debit")
async def debit_user_wallet(
    amount: float = Body(..., embed=True, ge=0.01, description="Montant à débiter du wallet"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    💸 Débiter le wallet de l'utilisateur connecté (avec vérification du solde).
    """
    try:
        wallet = await debit_wallet(user, amount, db)
        return {
            "message": f"💸 {amount:.2f} $BKC retirés du wallet.",
            "user_id": user.id,
            "balance": wallet.amount
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def wallet_info(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    🔍 Récupère le solde actuel du wallet de l'utilisateur connecté.
    """
    balance = await get_wallet_balance(user, db)
    return {
        "user_id": user.id,
        "balance": balance
    }
