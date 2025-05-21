# backend/test_email.py

from email_service import send_verification_email

if __name__ == "__main__":
    to = input("Entrez l'adresse email de destination : ")
    code = input("Entrez un code de test (ex: 123456) : ")

    success = send_verification_email(to, code)
    if success:
        print("✅ Email envoyé avec succès.")
    else:
        print("❌ Échec de l'envoi.")
