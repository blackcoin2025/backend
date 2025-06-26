import hashlib
import hmac
import os
from app.schemas import TelegramAuthData

def verify_telegram_auth_data(data: TelegramAuthData) -> bool:
    """Vérifie la signature envoyée par Telegram pour s'assurer de l'authenticité."""
    auth_data = data.dict()
    received_hash = auth_data.pop("hash")  # Hash fourni par Telegram

    # Tri alphabétique des clés et création du string de vérification
    auth_data_sorted = sorted([f"{k}={v}" for k, v in auth_data.items()])
    data_check_string = "\n".join(auth_data_sorted)

    # Clé secrète dérivée du token du bot
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN est manquant dans le fichier .env")

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # Comparaison sécurisée
    return hmac.compare_digest(received_hash, calculated_hash)
