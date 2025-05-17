import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_HOST_USER)

def send_verification_email(to_email: str, code: str):
    subject = "Code de vérification - BlackCoin"
    body = f"""
    Bonjour,

    Merci de vous être inscrit sur BlackCoin !
    Voici votre code de vérification : {code}

    Ce code est valable pendant 10 minutes.

    L'équipe BlackCoin
    """

    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print("Erreur lors de l'envoi de l'email:", e)
        return False
