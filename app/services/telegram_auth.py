import hashlib
import hmac
from app.schemas import TelegramAuthData
import os
from typing import Dict, Any

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def verify_telegram_auth_data(data: Dict[str, Any]) -> bool:
    """
    Vérifie les données d'authentification Telegram.
    Args:
        data: Dictionnaire contenant les données d'authentification
    Returns:
        bool: True si la vérification est réussie, False sinon
    """
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN manquant dans .env")

    # Vérification de la structure minimale requise
    if not all(key in data for key in ['auth_date', 'hash', 'id']):
        return False

    # 🔐 Clé secrète dérivée du token
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()

    # 🔁 Construction du check_string
    fields = {
        "auth_date": str(data['auth_date']),
        "id": str(data['id']),
    }

    # Ajout des champs optionnels
    optional_fields = ['first_name', 'last_name', 'username', 'photo_url']
    for field in optional_fields:
        if field in data and data[field]:
            fields[field] = data[field]

    check_string = "\n".join([f"{k}={v}" for k, v in sorted(fields.items())])

    # 🔒 Hash HMAC SHA256
    calculated_hash = hmac.new(
        secret_key, 
        check_string.encode(), 
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(calculated_hash, data['hash'])