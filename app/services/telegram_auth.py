import os
import hmac
import hashlib
from dotenv import load_dotenv

load_dotenv()

def verify_telegram_auth_data(auth_data: dict) -> bool:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN non trouvé")
        return False

    # Récupérer le hash envoyé par Telegram
    received_hash = auth_data.get("hash")
    if not received_hash:
        print("❌ Hash manquant dans la requête")
        return False

    # Enlever le hash du dictionnaire pour ne pas le signer
    auth_data_copy = {k: v for k, v in auth_data.items() if k != "hash"}

    # Trier les clés et construire le data_check_string
    data_check_string = '\n'.join(
        [f"{k}={auth_data_copy[k]}" for k in sorted(auth_data_copy)]
    )

    # Générer le secret key à partir du token
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # Calculer le hash avec HMAC
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # Debug prints
    print("🔐 BOT TOKEN ACTIF :", bot_token)
    print("🔎 Check string:", repr(data_check_string))
    print("✅ Calculated hash:", calculated_hash)
    print("📥 Provided hash:", received_hash)

    return calculated_hash == received_hash
