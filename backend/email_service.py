# backend/email_service.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST")  # ex : smtp.gmail.com
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Blackcoin Support")

def send_verification_email(to_email: str, code: str):
    subject = "🔐 Vérifiez votre adresse email - Blackcoin"

    body = f"""
Bonjour,

Bienvenue dans l'univers de **Blackcoin** 🚀

Pour finaliser la création de votre compte, veuillez entrer le code de vérification ci-dessous dans l'application :

➡️ Code de vérification : **{code}**

Ce code est temporaire et ne doit pas être partagé. Il est valide pour une durée limitée.

Si vous n'êtes pas à l'origine de cette inscription, veuillez ignorer cet email.

À très bientôt sur Blackcoin ✨

L’équipe Blackcoin 💰
"""

    msg = MIMEMultipart()
    msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_HOST_USER}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        server.sendmail(EMAIL_HOST_USER, to_email, msg.as_string())
        server.quit()
        print(f"✅ Email de vérification envoyé à {to_email}")
        return True
    except Exception as e:
        print(f"❌ Échec de l'envoi de l'email à {to_email}: {e}")
        return False
