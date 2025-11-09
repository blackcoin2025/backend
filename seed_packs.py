import asyncio
import sys, os
sys.path.append(os.path.dirname(__file__))

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import Action, ActionCategory, DailyTask

PACKS = [
    {"name": "Pack Découverte", "price": 4.44, "gain_percent": 1.2, "image": "/images/packs/pack1.png"},
    {"name": "Pack Croissance", "price": 8.88, "gain_percent": 1.2, "image": "/images/packs/pack2.png"},
    {"name": "Pack Dynamique", "price": 17.75, "gain_percent": 1.2, "image": "/images/packs/pack3.png"},
    {"name": "Pack Premium", "price": 26.63, "gain_percent": 1.2, "image": "/images/packs/pack4.png"},
    {"name": "Pack Expert", "price": 44.38, "gain_percent": 1.2, "image": "/images/packs/pack5.png"},
    {"name": "Pack Suprême", "price": 57.695, "gain_percent": 1.2, "image": "/images/packs/pack6.png"},
    {"name": "Pack Prestige", "price": 88.76, "gain_percent": 1.2, "image": "/images/packs/pack7.png"},
    {"name": "Pack Élitaire", "price": 133.145, "gain_percent": 1.2, "image": "/images/packs/pack8.png"},
    {"name": "Pack Royal", "price": 177.525, "gain_percent": 1.2, "image": "/images/packs/pack9.png"},
    {"name": "Pack Ultime", "price": 266.285, "gain_percent": 1.2, "image": "/images/packs/pack10.png"},
]

TASK_LINKS = [
    {"platform": "Telegram", "description": "Rejoignez notre canal Telegram officiel.", "video_url": "https://t.me/+VXuf93TxzKxlMzE0"},
    {"platform": "Facebook", "description": "Partagez et aimez notre page Facebook.", "video_url": "https://www.facebook.com/share/1CjsWSj1P3/"},
    {"platform": "Twitter (X)", "description": "Suivez notre compte officiel sur X.", "video_url": "https://x.com/BlackcoinON"},
    {"platform": "YouTube", "description": "Abonnez-vous à notre chaîne YouTube officielle.", "video_url": "https://www.youtube.com/@Blackcoinchaine"},
    {"platform": "TikTok", "description": "Regardez et aimez nos vidéos TikTok.", "video_url": "https://www.tiktok.com/@blackcoinsecurity"},
]

async def seed_packs():
    async with AsyncSessionLocal() as session:
        try:
            for p in PACKS:
                q = await session.execute(select(Action).where(Action.name == p["name"]))
                existing = q.scalars().first()
                if existing:
                    print(f"⚠️  '{p['name']}' existe déjà — on passe.")
                    continue

                pack = Action(
                    name=p["name"],
                    category=ActionCategory.finance,
                    price_per_part=p["price"],
                    value_bkc=p["price"],
                    image_url=p["image"],
                )
                session.add(pack)
                await session.flush()  # flush pour récupérer l'id du pack

                # Ajouter toutes les tâches en mémoire avant le commit
                tasks = [
                    DailyTask(
                        pack_id=pack.id,
                        platform=t["platform"],
                        description=t["description"],
                        video_url=t["video_url"],
                        reward_share=(p["gain_percent"] / 100),
                    )
                    for t in TASK_LINKS
                ]
                session.add_all(tasks)

            await session.commit()  # commit unique pour tous les packs et toutes les tâches
            print("✅ Tous les packs et tâches ont été insérés avec succès.")

        except Exception as e:
            await session.rollback()
            print(f"❌ Erreur lors de l’insertion : {e}")

if __name__ == "__main__":
    asyncio.run(seed_packs())
