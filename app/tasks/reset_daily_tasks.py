# app/tasks/reset_daily_tasks.py
import asyncio
from datetime import datetime, timedelta, time
import pytz
from sqlalchemy import delete, update
from app.database import AsyncSessionLocal
from app.models import UserPack, UserDailyTask


BENIN_TZ = pytz.timezone("Africa/Porto-Novo")


async def reset_all_daily_tasks():
    print("♻️ Réinitialisation des tâches quotidiennes...")
    async with AsyncSessionLocal() as db:
        try:
            # 1️⃣ Supprimer toutes les tâches journalières
            await db.execute(delete(UserDailyTask))
            print("🧹 Table user_daily_tasks vidée.")

            # 2️⃣ Réinitialiser les statuts des packs utilisateurs
            await db.execute(
                update(UserPack)
                .values(
                    all_tasks_completed=False,
                    current_day=None,
                    last_claim_date=None,
                    total_earned=0,
                    pack_status="payé",
                    is_unlocked=False
                )
            )
            print("🔁 Colonnes user_pack réinitialisées.")

            # 3️⃣ Commit des changements
            await db.commit()
            print("✅ Reset terminé avec succès.")

        except Exception as e:
            await db.rollback()
            print(f"[reset_all_daily_tasks] Erreur: {e}")


async def start_daily_reset_task():
    """
    Boucle planifiée qui exécute le reset chaque jour à 00h00 (heure locale du Bénin)
    """
    print("🕒 Démarrage du service de réinitialisation quotidienne (00h00 heure locale du Bénin).")

    while True:
        now_local = datetime.now(BENIN_TZ)

        # Calcul du prochain minuit (00:00) heure locale
        tomorrow = now_local.date() + timedelta(days=1)
        next_reset_local = datetime.combine(tomorrow, time(0, 0))
        next_reset_local = BENIN_TZ.localize(next_reset_local)

        # Temps d’attente en secondes avant la prochaine exécution
        wait_seconds = (next_reset_local - now_local).total_seconds()

        print(
            f"⏳ Prochain reset prévu à {next_reset_local.strftime('%Y-%m-%d %H:%M:%S %Z')} "
            f"(dans {wait_seconds / 3600:.2f} heures)"
        )

        # Attente jusqu’à minuit local
        await asyncio.sleep(wait_seconds)

        # Exécution du reset
        await reset_all_daily_tasks()
