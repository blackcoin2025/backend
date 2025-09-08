import os
import sys
import logging
import smtplib  # Import manquant ajouté
from typing import NoReturn

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_environment() -> bool:
    """Vérifie les variables d'environnement requises."""
    required_vars = {
        "EMAIL_HOST": "Serveur SMTP (ex: smtp.gmail.com)",
        "EMAIL_PORT": "Port SMTP (ex: 465 ou 587)",
        "EMAIL_USER": "Adresse email d'envoi",
        "EMAIL_PASSWORD": "Mot de passe/Token d'application"
    }
    
    missing = []
    for var, desc in required_vars.items():
        if not os.getenv(var):
            missing.append(f"{var} ({desc})")
    
    if missing:
        logger.error("Variables manquantes:\n- %s", "\n- ".join(missing))
        return False
    return True

def get_email_input() -> str:
    """Demande et valide l'email de test."""
    while True:
        email = input("Adresse e-mail destinataire à tester : ").strip()
        if "@" in email and "." in email.split("@")[-1]:
            return email
        print("Format d'email invalide, veuillez réessayer.")

def main() -> None:
    """Point d'entrée principal."""
    if not validate_environment():
        sys.exit(1)

    try:
        from app.services.VerifyEmail import send_verification_email
    except ImportError as err:
        logger.error("Erreur d'importation: %s", err)
        logger.info("Vérifiez que:")
        logger.info("1. Le module VerifyEmail existe dans app/services/")
        logger.info("2. Le fichier __init__.py est présent dans les dossiers app/ et app/services/")
        sys.exit(1)

    recipient = get_email_input()
    test_code = "999999"  # Code de test statique

    logger.info("Envoi du mail en cours...")
    try:
        # Solution pour le problème d'encodage
        os.environ["EMAIL_USER"] = os.getenv("EMAIL_USER").encode('ascii', 'ignore').decode('ascii')
        os.environ["EMAIL_PASSWORD"] = os.getenv("EMAIL_PASSWORD").encode('ascii', 'ignore').decode('ascii')
        
        send_verification_email(recipient, test_code)
        logger.info("✅ E-mail envoyé avec succès à %s", recipient)
    except smtplib.SMTPException as e:
        logger.error("Erreur SMTP: %s", str(e))
    except UnicodeEncodeError as e:
        logger.error("Problème d'encodage: %s", e)
        logger.info("Solution: Vérifiez que vos identifiants SMTP ne contiennent que des caractères ASCII")
    except Exception as e:
        logger.error("Erreur inattendue: %s", str(e))
    finally:
        logger.info("Test terminé")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Test annulé par l'utilisateur")
        sys.exit(0)