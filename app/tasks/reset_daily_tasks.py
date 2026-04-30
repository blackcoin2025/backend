import asyncio
from datetime import datetime, timezone, timedelta, time
import pytz
from sqlalchemy import delete, update

from app.database import AsyncSessionLocal
from app.models import UserPack, UserDailyTask

# ✅ Redis SAFE
from app.core.cache import cache_delete, redis_client

BENIN_TZ = pytz.timezone("Africa/Porto-Novo")

RESET_LOCK_KEY = "daily_reset_lock"


# -----------------------------
# RESET TASKS
# -----------------------------
async def reset_all_daily_tasks():
    print("♻️ Réinitialisation des tâches quotidiennes...")

    # 🔥 REDIS LOCK (anti double reset)
    try:
        lock = await redis_client.set(
            RESET_LOCK_KEY,
            "1",
            ex=60,   # expire en 60 sec
            nx=True  # seulement si pas déjà existant
        )
    except Exception:
        lock = True  # fallback si Redis down

    if not lock:
        print("⏳ Reset déjà en cours (lock Redis)")
        return

    async with AsyncSessionLocal() as db:
        try:
            # 1️⃣ DELETE tasks
            await db.execute(delete(UserDailyTask))
            print("🧹 Table user_daily_tasks vidée.")

            # 2️⃣ RESET packs
            await db.execute(
                update(UserPack).values(
                    all_tasks_completed=False,
                    current_day=None,
                    last_claim_date=None,
                    total_earned=0,
                    pack_status="payé",
                    is_unlocked=False,
                    start_date=None
                )
            )
            print("🔁 Packs réinitialisés.")

            # 3️⃣ COMMIT
            await db.commit()

            # 🔥 CLEAN CACHE GLOBAL (important)
            try:
                await cache_delete("tasks")  # à améliorer plus tard
                await cache_delete("packs")
            except Exception:
                pass

            print("✅ Reset terminé avec succès.")

        except Exception as e:
            await db.rollback()
            print(f"[reset_all_daily_tasks] Erreur: {e}")


# -----------------------------
# SCHEDULER
# -----------------------------
async def start_daily_reset_task():
    print("🕒 Service reset quotidien démarré (00h Bénin).")

    while True:
        now_local = datetime.now(BENIN_TZ)

        tomorrow = now_local.date() + timedelta(days=1)
        next_reset_local = datetime.combine(tomorrow, time(0, 0))
        next_reset_local = BENIN_TZ.localize(next_reset_local)

        wait_seconds = (next_reset_local - now_local).total_seconds()

        print(
            f"⏳ Prochain reset à "
            f"{next_reset_local.strftime('%Y-%m-%d %H:%M:%S')} "
            f"(dans {wait_seconds/3600:.2f}h)"
        )

        await asyncio.sleep(wait_seconds)

        await reset_all_daily_tasks()


# -----------------------------
# TEST MANUEL
# -----------------------------
if __name__ == "__main__":
    print("⚡ Test reset immédiat")
    asyncio.run(reset_all_daily_tasks())