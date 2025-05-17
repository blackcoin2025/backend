import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
FILE_URL = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"

# Fonction pour récupérer les infos du username
async def verify_telegram_username(username: str):
    try:
        # Appeler la méthode /getChat pour vérifier le username
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/getChat", params={"chat_id": f"@{username}"})
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            return None

        chat = data["result"]
        user_id = chat.get("id")
        photo_url = None

        # Essayer de récupérer la photo de profil
        async with httpx.AsyncClient() as client:
            photo_response = await client.get(f"{BASE_URL}/getUserProfilePhotos", params={"user_id": user_id})
            if photo_response.status_code == 200 and photo_response.json().get("ok"):
                photos = photo_response.json()["result"]["photos"]
                if photos and len(photos) > 0:
                    # Prendre la dernière photo (ou la première disponible)
                    file_id = photos[0][0]["file_id"]
                    # Récupérer le chemin du fichier
                    file_info = await client.get(f"{BASE_URL}/getFile", params={"file_id": file_id})
                    if file_info.status_code == 200 and file_info.json().get("ok"):
                        file_path = file_info.json()["result"]["file_path"]
                        photo_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

        return {"id": user_id, "photo_url": photo_url}

    except Exception as e:
        print("Erreur lors de la vérification Telegram :", e)
        return None
