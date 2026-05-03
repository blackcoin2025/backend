from fastapi import Depends, HTTPException, status
from app.models import User
from app.dependencies.auth import get_current_user

async def require_completed_welcome(
    user: User = Depends(get_current_user)
) -> User:
    if not user.has_completed_welcome_tasks:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous devez compléter les tâches de bienvenue"
        )
    return user