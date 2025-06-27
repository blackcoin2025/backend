import hashlib
import hmac
from app.schemas import TelegramAuthData
import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Assure-toi que .env contient cette variable


def verify_telegram_auth_data(data: TelegramAuthData) -> bool:
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN manquant dans .env")

    # 🔐 Clé secrète dérivée du token
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()

    # 🔁 Construction du check_string
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

    check_string = "\n".join([f"{k}={fields[k]}" for k in sorted(fields.keys())])

    # 🔒 Hash HMAC SHA256
    calculated_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    return calculated_hash == data.hash
