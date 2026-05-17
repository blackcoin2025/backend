import asyncio
import sys, os
sys.path.append(os.path.dirname(__file__))

from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import Action, ActionCategory, DailyTask

LTN_TO_USDT = 2  # 1 LTN = 2 USDT

# =========================
# 📦 PACKS
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
# 📋 TASKS
# =========================
TASK_LINKS = [
    {
        "platform": "telegram",
        "key": "join_telegram",
        "video_url": "https://t.me/ltn_network"
    },
    {
        "platform": "facebook",
        "key": "like_facebook",
        "video_url": "https://www.facebook.com/share/1DMkFcwA2B/"
    },
    {
        "platform": "twitter",
        "key": "follow_twitter",
        "video_url": "https://x.com/Liton_network"
    },
    {
        "platform": "youtube",
        "key": "subscribe_youtube",
        "video_url": "https://youtube.com/@liton_network?si=xWWgWzHPPWmQZtML"
    },
    {
        "platform": "tiktok",
        "key": "watch_tiktok",
        "video_url": "https://www.tiktok.com/@liton_network"
    },
    {
        "platform": "instagram",
        "key": "follow_instagram",
        "video_url": "https://www.instagram.com/liton_network?igsh=cDc4OXF5eXM5Y2Nj"
    },
]

# =========================
# 🚀 SEED FUNCTION
# =========================
async def seed_packs():
    async with AsyncSessionLocal() as session:
        try:
            for p in PACKS:

                q = await session.execute(
                    select(Action).where(Action.name == p["key"])
                )

                existing = q.scalars().first()

                if existing:
                    print(f"⚠️ '{p['key']}' existe déjà — on passe.")
                    continue

                price_LTN = p["price"]
                price_usdt = round(price_LTN * LTN_TO_USDT, 6)

                pack = Action(
                    name=p["key"],
                    category=ActionCategory.finance,
                    price_per_part=price_LTN,
                    price_usdt=price_usdt,
                    value_LTN=price_LTN,
                    image_url=p["image"],
                )

                session.add(pack)
                await session.flush()

                tasks = [
                    DailyTask(
                        pack_id=pack.id,
                        platform=t["platform"],
                        description=t["key"],
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