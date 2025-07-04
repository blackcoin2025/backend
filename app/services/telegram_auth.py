import os
import hmac
import hashlib
from dotenv import load_dotenv

load_dotenv()

def verify_telegram_auth_data(payload: dict) -> bool:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN non trouvé")
        return False

    # ➜ Aplatir les données depuis le payload brut
    auth_data = payload.get("user", {}).copy()
    auth_data["auth_date"] = payload.get("auth_date")
    received_hash = payload.get("hash")

    if not received_hash:
        print("❌ Hash manquant")
        return False

    # Supprimer le hash du dict pour éviter de l’inclure dans le calcul
    auth_data_copy = {k: v for k, v in auth_data.items() if k != "hash"}

    # Créer la check string triée
    data_check_string = "\n".join(
        f"{k}={auth_data_copy[k]}" for k in sorted(auth_data_copy)
    )

    # Hash HMAC
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # Logs pour debug
    print("🔐 BOT TOKEN ACTIF :", bot_token)
    print("🔎 Check string:", repr(data_check_string))
    print("✅ Calculated hash:", calculated_hash)
    print("📥 Provided hash:", received_hash)

    return calculated_hash == received_hash
