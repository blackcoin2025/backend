# app/services/telegram_auth.py

import hashlib
import hmac
import os
from app.schemas import TelegramAuthData

def verify_telegram_auth_data(data: TelegramAuthData) -> bool:
    auth_data = data.dict()
    received_hash = auth_data.pop("hash")
    auth_data_sorted = sorted([f"{k}={v}" for k, v in auth_data.items()])
    data_check_string = "\n".join(auth_data_sorted)

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key.encode(), data_check_string.encode(), hashlib.sha256).hexdigest()

    return hmac.compare_digest(received_hash, calculated_hash)
