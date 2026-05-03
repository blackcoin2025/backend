from datetime import datetime, timezone, timedelta
from app.models import PendingUser
from app.services.VerifyEmail import generate_code

async def resend_register_code(db, pending_user):
    now = datetime.now(timezone.utc)

    # cooldown 60 sec
    if pending_user.created_at and (now - pending_user.created_at).total_seconds() < 60:
        raise Exception("cooldown")

    new_code = generate_code()

    pending_user.verification_code = new_code
    pending_user.code_expires_at = now + timedelta(minutes=5)
    pending_user.created_at = now

    await db.commit()

    return new_code


async def reset_login_code(db, user):
    now = datetime.now(timezone.utc)

    new_code = generate_code()

    user.reset_code = new_code
    user.reset_code_expires_at = now + timedelta(minutes=5)

    await db.commit()

    return new_code