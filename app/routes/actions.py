# app/routes/actions.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_async_session
from app.models import Action, UserAction, User
from app.schemas import ActionBase, ActionSchema, UserActionBase, UserActionSchema
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/actions", tags=["Actions"])

# -----------------------
# Créer une nouvelle Action
# -----------------------
@router.post("/", response_model=ActionSchema)
async def create_action(
    payload: ActionBase,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    new_action = Action(
        name=payload.name,
        category=payload.category,
        type=payload.type,
        total_parts=payload.total_parts,
        price_per_part=payload.price_per_part
    )
    db.add(new_action)
    await db.commit()
    await db.refresh(new_action)
    return new_action

# -----------------------
# Lister toutes les actions
# -----------------------
@router.get("/", response_model=List[ActionSchema])
async def list_actions(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Action))
    return result.scalars().all()  # retourne [] si vide

# -----------------------
# Lister les actions par catégorie
# -----------------------
@router.get("/category/{category}", response_model=List[ActionSchema])
async def list_actions_by_category(category: str, db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Action).where(Action.category == category))
    actions = result.scalars().all()
    return actions  # retourne [] si aucune action

# -----------------------
# Acheter une action (UserAction)
# -----------------------
@router.post("/buy", response_model=UserActionSchema)
async def buy_action(
    payload: UserActionBase,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    # Vérifier que l'action existe
    action = await db.get(Action, payload.action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action introuvable")

    # Vérifier qu’il reste des parts disponibles
    result = await db.execute(select(UserAction).where(UserAction.action_id == payload.action_id))
    existing_parts = sum([ua.quantity for ua in result.scalars().all()])
    if existing_parts + payload.quantity > action.total_parts:
        raise HTTPException(status_code=400, detail="Pas assez de parts disponibles")

    # Vérifier montant
    total_amount = payload.quantity * action.price_per_part
    if total_amount != payload.amount:
        raise HTTPException(status_code=400, detail="Le montant ne correspond pas au prix par part")

    # Créer la participation
    user_action = UserAction(
        user_id=current_user.id,
        action_id=payload.action_id,
        quantity=payload.quantity,
        amount=total_amount
    )
    db.add(user_action)
    await db.commit()
    await db.refresh(user_action)
    return user_action

# -----------------------
# Récupérer les actions de l'utilisateur connecté
# -----------------------
@router.get("/me", response_model=List[UserActionSchema])
async def list_my_actions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(UserAction).where(UserAction.user_id == current_user.id))
    return result.scalars().all()  # retourne [] si aucune action
