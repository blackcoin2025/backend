# 📦 Importations des modules nécessaires
from pydantic_settings import BaseSettings
from pydantic import EmailStr

# 🔧 Classe de configuration globale du projet
class Settings(BaseSettings):
    # ============================
    # 🔐 Identifiants administrateur
    # ============================
    ADMIN_EMAIL: EmailStr           # Email de l'admin pour la connexion
    ADMIN_PASSWORD: str            # Mot de passe de l'administrateur
    ADMIN_TELEGRAM: str            # Nom d'utilisateur Telegram de l'admin

    # ============================
    # 📧 Configuration Email
    # ============================
    EMAIL_FROM: EmailStr           # Adresse utilisée pour envoyer les mails
    EMAIL_PASSWORD: str            # Mot de passe d’application (Gmail)
    EMAIL_HOST: str                # Serveur SMTP (ex: smtp.gmail.com)
    EMAIL_PORT: int                # Port SMTP (587 pour TLS)
    EMAIL_HOST_USER: str           # Utilisateur SMTP (souvent identique à EMAIL_FROM)
    EMAIL_PASSWORD: str
    EMAIL_FROM_NAME: str           # Nom affiché lors de l’envoi des mails

    # ============================
    # 🛢️ Base de données
    # ============================
    DATABASE_URL: str              # URL de connexion ASYNC (FastAPI)
    DATABASE_URL_SYNC: str         # URL de connexion SYNC (pour Alembic)

    # ============================
    # 🌐 Frontend & Webhook
    # ============================
    FRONTEND_URL: str              # URL de ton frontend (pour CORS et redirections)
    WEBHOOK_URL: str               # URL publique pour recevoir les webhooks

    # ============================
    # 🤖 Telegram Bot
    # ============================
    TELEGRAM_BOT_TOKEN: str        # Jeton d’accès de ton bot Telegram

    # ============================
    # ⚙️ Paramètres supplémentaires
    # ============================
    DEBUG: bool                    # Active/désactive le mode debug

    # 🔍 Configuration du chargement du fichier .env
    class Config:
        env_file = ".env"


# 📦 Instance globale accessible dans tout le projet
settings = Settings()
