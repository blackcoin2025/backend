import hashlib
import hmac
from typing import Dict, Any
import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
print("TELEGRAM_BOT_TOKEN from env:", BOT_TOKEN)

def verify_telegram_auth_data(data: Dict[str, Any]) -> bool:
    """
    Vérifie la validité des données d'authentification Telegram via le hash HMAC SHA256.
    Args:
        data: Dictionnaire contenant les données Telegram reçues
    Returns:
        bool: True si signature valide, False sinon
    """
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN manquant dans .env")

    required_keys = ['auth_date', 'hash', 'id']
    if not all(k in data for k in required_keys):
        return False

    if not data.get('hash'):
        return False

    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()

    # Construire la chaîne check_string triée par clé (clé=valeur, séparées par \n)
    fields = {
        "auth_date": str(data['auth_date']),
        "id": str(data['id']),
    }
    optional_fields = ['first_name', 'last_name', 'username', 'photo_url']
    for field in optional_fields:
        if field in data and data[field]:
            fields[field] = data[field]

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))

    calculated_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    # Logs pour débogage
    print("Check string:", repr(check_string))
    print("Calculated hash:", calculated_hash)
    print("Provided hash:", data['hash'])
    print("🔐 BOT TOKEN ACTIF :", os.environ.get("TELEGRAM_BOT_TOKEN"))

    return hmac.compare_digest(calculated_hash, data['hash'])
