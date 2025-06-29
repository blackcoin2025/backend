### ✅ app/services/telegram_auth.py

import hashlib
import hmac
import os
from app.schemas import TelegramAuthData

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def verify_telegram_auth_data(data: TelegramAuthData) -> bool:
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN manquant dans .env")

    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()

    fields = {
        "auth_date": str(data.auth_date),
        "first_name": data.first_name,
        "id": str(data.id),
    }

    if data.last_name:
        fields["last_name"] = data.last_name
    if data.username:
        fields["username"] = data.username
    if data.photo_url:
        fields["photo_url"] = data.photo_url

    check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))

    calculated_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return calculated_hash == data.hash