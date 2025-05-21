import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Blackcoin Support")


def send_verification_email(to_email: str, code: str) -> bool:
    if not all([EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD]):
        print("❌ Les variables d'environnement email sont mal configurées.")
        return False

    if not to_email or not code:
        print("❌ Email ou code manquant.")
        return False

    subject = "🔐 Vérifiez votre adresse email - Blackcoin"

    html_body = f"""
    <html>
    <body style="background-color: #121212; color: #FFFFFF; font-family: Arial, sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background-color: #1E1E1E; border-radius: 8px; overflow: hidden; border: 1px solid #333;">
            <div style="padding: 20px; text-align: center; border-bottom: 1px solid #333;">
                <h2 style="color: #FFD700;">Bienvenue chez Blackcoin 🚀</h2>
            </div>
            <div style="padding: 20px;">
                <p>Bonjour,</p>
                <p>Merci de vous être inscrit à Blackcoin.</p>
                <p>Veuillez utiliser le code ci-dessous pour vérifier votre adresse email :</p>
                <div style="background-color: #2C2C2C; color: #FFD700; font-size: 24px; font-weight: bold; padding: 15px; text-align: center; border-radius: 6px; margin: 20px 0;">
                    {code}
                </div>
                <p style="font-size: 14px; color: #CCCCCC;">
                    Ce code est valide pour une durée limitée. Ne le partagez avec personne.
                </p>
                <p>Si vous n'avez pas demandé ce code, vous pouvez ignorer cet email.</p>
                <p style="margin-top: 30px;">À bientôt,<br>L’équipe <span style="color: #FFD700;">Blackcoin</span> 💰</p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_HOST_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        part_html = MIMEText(html_body, "html")
        msg.attach(part_html)

        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        server.sendmail(EMAIL_HOST_USER, to_email, msg.as_string())
        server.quit()

        print(f"✅ Email de vérification envoyé à {to_email}")
        return True

    except Exception as e:
        print(f"❌ Échec de l'envoi : {e}")
        return False
