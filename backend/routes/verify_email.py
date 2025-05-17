from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.crud import verify_email_code

router = APIRouter()

@router.post("/verify-email")
async def verify_email(email: str, code: str, db: AsyncSession = Depends(get_db)):
    try:
        user = await verify_email_code(db, email, code)
        return {"message": "Email vérifié avec succès.", "user_id": user.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la vérification de l'email.")
