import hashlib
import hmac

# 🔐 Ton token Telegram ici (trouvé dans @BotFather)
BOT_TOKEN = "7707610354:AAHWjy0QjaQkrppOPyMQm8vWhGayzXV9oAA"  # ⬅️ remplace par ton vrai token

# ✅ Données simulées
fields = {
    "id": "123456789",
    "first_name": "Jean",
    "last_name": "Dupont",
    "username": "jeandupont",
    "photo_url": "https://t.me/i/userpic/320/photo.jpg",
    "auth_date": "1719400000"
}

# 🔁 Construction du check_string (dans l'ordre)
check_string = "\n".join([f"{k}={fields[k]}" for k in sorted(fields.keys())])
print("check_string =\n", check_string)

# 🔒 Calcul du hash sécurisé
secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
hash_hex = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

print("\nhash =", hash_hex)


