# utils/user.py
from typing import Dict
from models import User  # ton modèle SQLAlchemy

def serialize_user(user: User) -> Dict:
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone,
        "date_of_birth": str(user.date_of_birth) if user.date_of_birth else None,
        "wallet": user.wallet,
        "points": user.points,
        "level": user.level,
        "avatar_url": user.avatar_url,  # <--- ici ajouté
        "created_at": user.created_at.isoformat() if user.created_at else None
    }
