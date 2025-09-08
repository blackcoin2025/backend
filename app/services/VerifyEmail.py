import os
import smtplib
import random
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from passlib.context import CryptContext
from app.models import PendingUser
from app.schemas import RegisterRequest

# Contexte pour le hachage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Variables d'environnement SMTP et admin
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

# Paramètres de sécurité
CODE_EXPIRATION_MINUTES = 15
SPAM_DELAY_SECONDS = 60


# ✅ Génère un code à 6 chiffres
def generate_code():
    return str(random.randint(100000, 999999))


# ✅ Vérifie si un utilisateur existe déjà (par email ou username)
async def user_exists(session: AsyncSession, email: str, username: str):
    username = username.strip().lower()
    result = await session.execute(
        select(PendingUser).filter(
            (PendingUser.email == email) | (PendingUser.username == username)
        )
    )
    return result.scalars().first()


# ✅ Envoie un e-mail HTML contenant le code de validation
def send_verification_email(to_email: str, code: str):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    msg["Subject"] = "Code de vérification - BlackCoin ✅"

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <p>Bonjour 👋,</p>
        <p>
          Merci de vous être inscrit sur <strong>BlackCoin</strong>.<br />
          Pour confirmer votre adresse e-mail, veuillez entrer le code ci-dessous :
        </p>
        <div style="font-size: 24px; font-weight: bold; background-color: #f4f4f4; 
                    padding: 10px 20px; border: 2px dashed #007bff; text-align: center; 
                    color: #007bff; width: fit-content; margin: 20px auto;">
          🔐 {code}
        </div>
        <p>
          Ce code est valable <strong>{CODE_EXPIRATION_MINUTES} minutes</strong>.<br />
          <strong style="color: red;">⚠️ Ne partagez jamais ce code.</strong>
        </p>
        <hr style="margin: 20px 0;" />
        <p style="font-size: 0.95em; color: #555;">
          Besoin d’aide ? Contactez-nous à 
          <a href="mailto:{ADMIN_EMAIL}" style="color: #007bff;">{ADMIN_EMAIL}</a>.
        </p>
        <p style="margin-top: 30px; font-weight: bold;">— L’équipe BlackCoin</p>
      </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"❌ Erreur d'envoi email : {e}")
        raise


# ✅ Enregistre temporairement l'utilisateur et envoie le code
async def process_registration(form: RegisterRequest, session: AsyncSession):
    now = datetime.utcnow()
    email = form.email.strip().lower()
    username = form.username.strip().lower()

    # Vérifie si l'utilisateur existe déjà
    existing = await user_exists(session, email, username)
    if existing and existing.is_verified:
        return {"status": "existing_user", "detail": "Compte déjà vérifié."}

    # Vérifie les tentatives fréquentes (anti-spam)
    if existing and (now - existing.created_at).total_seconds() < SPAM_DELAY_SECONDS:
        return {"status": "too_soon", "detail": "Trop de tentatives. Attendez 1 minute."}

    # Génère un nouveau code
    code = generate_code()
    hashed_password = pwd_context.hash(form.password)

    if existing:
        # Mise à jour de l'entrée existante non vérifiée
        existing.first_name = form.first_name
        existing.last_name = form.last_name
        existing.birth_date = form.birth_date
        existing.phone = form.phone
        existing.username = username
        existing.password_hash = hashed_password
        existing.verification_code = code
        existing.code_expires_at = now + timedelta(minutes=CODE_EXPIRATION_MINUTES)
        existing.created_at = now
    else:
        # Création d’un nouvel utilisateur temporaire
        new_pending = PendingUser(
            email=email,
            first_name=form.first_name,
            last_name=form.last_name,
            birth_date=form.birth_date,
            phone=form.phone,
            username=username,
            password_hash=hashed_password,
            verification_code=code,
            code_expires_at=now + timedelta(minutes=CODE_EXPIRATION_MINUTES),
            is_verified=False,
            created_at=now
        )
        session.add(new_pending)

    await session.commit()

    # Envoie le mail dans un thread non-bloquant
    await run_in_threadpool(send_verification_email, email, code)

    return {
        "status": "verification_sent",
        "detail": "Code envoyé par e-mail.",
        "emailToVerify": email
    }
