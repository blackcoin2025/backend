import asyncio
import sys, os
sys.path.append(os.path.dirname(__file__))

from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import Action, ActionCategory, DailyTask

BKC_TO_USDT = 2  # 1 BKC = 2 USDT

# =========================
# 📦 PACKS (CLÉS UNIQUEMENT)
# =========================
PACKS = [
    {"key": "discovery", "price": 4.44, "gain_percent": 1.2, "image": "/images/packs/pack1.png"},
    {"key": "growth", "price": 8.88, "gain_percent": 1.2, "image": "/images/packs/pack2.png"},
    {"key": "dynamic", "price": 17.75, "gain_percent": 1.2, "image": "/images/packs/pack3.png"},
    {"key": "premium", "price": 26.63, "gain_percent": 1.2, "image": "/images/packs/pack4.png"},
    {"key": "expert", "price": 44.38, "gain_percent": 1.2, "image": "/images/packs/pack5.png"},
    {"key": "supreme", "price": 57.695, "gain_percent": 1.2, "image": "/images/packs/pack6.png"},
    {"key": "prestige", "price": 88.76, "gain_percent": 1.2, "image": "/images/packs/pack7.png"},
    {"key": "elite", "price": 133.145, "gain_percent": 1.2, "image": "/images/packs/pack8.png"},
    {"key": "royal", "price": 177.525, "gain_percent": 1.2, "image": "/images/packs/pack9.png"},
    {"key": "ultimate", "price": 266.285, "gain_percent": 1.2, "image": "/images/packs/pack10.png"},
]

# =========================
# 📋 TASKS (CLÉS UNIQUEMENT)
# =========================
TASK_LINKS = [
    {"platform": "telegram", "key": "join_telegram", "video_url": "https://t.me/+2VYCu2Ygs0Q1YTk0"},
    {"platform": "facebook", "key": "like_facebook", "video_url": "https://www.facebook.com/share/1CjsWSj1P3/"},
    {"platform": "twitter", "key": "follow_twitter", "video_url": "https://x.com/BlackcoinON"},
    {"platform": "youtube", "key": "subscribe_youtube", "video_url": "https://www.youtube.com/@Blackcoinchaine"},
    {"platform": "tiktok", "key": "watch_tiktok", "video_url": "https://www.tiktok.com/@blackcoin_official"},
]

# =========================
# 🚀 SEED FUNCTION
# =========================
async def seed_packs():
    async with AsyncSessionLocal() as session:
        try:
            for p in PACKS:
                # 🔍 Vérifie si le pack existe déjà
                q = await session.execute(
                    select(Action).where(Action.name == p["key"])
                )
                existing = q.scalars().first()

                if existing:
                    print(f"⚠️  '{p['key']}' existe déjà — on passe.")
                    continue

                # 💰 Calcul prix
                price_bkc = p["price"]
                price_usdt = round(price_bkc * BKC_TO_USDT, 6)

                # 📦 Création pack (clé i18n)
                pack = Action(
                    name=p["key"],  # 🔥 clé i18n
                    category=ActionCategory.finance,
                    price_per_part=price_bkc,
                    price_usdt=price_usdt,
                    value_bkc=price_bkc,
                    image_url=p["image"],
                )

                session.add(pack)
                await session.flush()

                # 📋 Création des tâches
                tasks = [
                    DailyTask(
                        pack_id=pack.id,
                        platform=t["platform"],       # 🔥 clé
                        description=t["key"],         # 🔥 clé i18n
                        video_url=t["video_url"],
                        reward_share=(p["gain_percent"] / 100),
                    )
                    for t in TASK_LINKS
                ]

                session.add_all(tasks)

            await session.commit()
            print("✅ Tous les packs et tâches ont été insérés avec succès.")

        except Exception as e:
            await session.rollback()
            print(f"❌ Erreur lors de l’insertion : {e}")


# =========================
# ▶️ RUN
# =========================
if __name__ == "__main__":
    asyncio.run(seed_packs())