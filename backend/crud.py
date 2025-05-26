import secrets
from sqlalchemy.future import select
from backend.models import User, EmailVerificationCode
from backend.schemas import UserCreate
from backend.email_service import send_verification_email
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import datetime

CODE_LENGTH = 6

def generate_code():
    return secrets.token_hex(3)[:CODE_LENGTH]  # Ex: "a1b2c3"

async def create_user(db: AsyncSession, user_data: UserCreate):
    query = select(User).where(
        (User.email == user_data.email) |
        (User.telegram_username == user_data.telegram_username)
    )
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        if existing_user.is_verified:
            raise ValueError("Email ou nom d'utilisateur Telegram déjà utilisé.")
        else:
            code = generate_code()
            if existing_user.email_verification:
                existing_user.email_verification.code = code
                existing_user.email_verification.created_at = datetime.utcnow()
            else:
                verification = EmailVerificationCode(
                    user_id=existing_user.id,
                    code=code
                )
                db.add(verification)
            await db.commit()
            await db.refresh(existing_user)
            send_verification_email(existing_user.email, code)
            return existing_user

    new_user = User(
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        birth_date=user_data.date_of_birth,
        phone=user_data.phone,
        telegram_username=user_data.telegram_username,
        telegram_id=None,
        telegram_photo=None,
        password_hash=user_data.password,  # 🔐 À hasher correctement
        is_verified=False
    )

    try:
        db.add(new_user)
        await db.flush()

        code = generate_code()
        verification = EmailVerificationCode(
            user_id=new_user.id,
            code=code
        )
        db.add(verification)

        await db.commit()
        await db.refresh(new_user)

        send_verification_email(new_user.email, code)
        return new_user

    except IntegrityError:
        await db.rollback()
        raise ValueError("Erreur lors de la création du compte.")
    except Exception as e:
        await db.rollback()
        raise RuntimeError(f"Erreur inattendue : {str(e)}")

# 🔽 Ajout des fonctions manquantes

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def get_user_by_telegram_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.telegram_username == username))
    return result.scalars().first()
