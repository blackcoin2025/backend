import hashlib
import hmac
from typing import Dict, Any
import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN manquant dans .env")

def verify_telegram_auth_data(data: Dict[str, Any]) -> bool:
    """
    Vérifie la signature HMAC SHA256 fournie par Telegram.
    """
    provided_hash = data.get("hash")
    if not provided_hash:
        return False

    # Supprimer la clé 'hash' pour construire le check_string
    data_check = {k: str(v) for k, v in data.items() if k != "hash"}

    check_string = "\n".join(f"{k}={data_check[k]}" for k in sorted(data_check))

    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    calculated_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    # Debug
    print("Check string:", repr(check_string))
    print("Calculated hash:", calculated_hash)
    print("Provided hash:", provided_hash)

    return hmac.compare_digest(calculated_hash, provided_hash)
