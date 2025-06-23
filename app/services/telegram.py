import requests

TELEGRAM_API_URL = "https://api.telegram.org/bot{bot_token}/"

def get_user_profile(bot_token: str, telegram_id: str):
    """Récupère les informations utilisateur depuis Telegram."""
    url = TELEGRAM_API_URL.format(bot_token=bot_token) + f"getChat?chat_id={telegram_id}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch user profile: {response.json()}")
    return response.json()["result"]

def send_message(bot_token: str, chat_id: str, text: str):
    """Envoie un message à un utilisateur via Telegram."""
    url = TELEGRAM_API_URL.format(bot_token=bot_token) + "sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        raise Exception(f"Failed to send message: {response.json()}")
    return response.json()
