import asyncio
from dotenv import load_dotenv
from app.database import AsyncSessionLocal
from app.models import Action

load_dotenv()


async def seed_actions():
    async with AsyncSessionLocal() as session:
        packs = [
            {"name": "Pack Découverte", "category": "finance", "image_url": "/images/packs/pack1.png", "value_bkc": 4.44},
            {"name": "Pack Croissance", "category": "finance", "image_url": "/images/packs/pack2.png", "value_bkc": 8.88},
            {"name": "Pack Dynamique", "category": "finance", "image_url": "/images/packs/pack3.png", "value_bkc": 17.75},
            {"name": "Pack Premium", "category": "finance", "image_url": "/images/packs/pack4.png", "value_bkc": 26.63},
            {"name": "Pack Expert", "category": "finance", "image_url": "/images/packs/pack5.png", "value_bkc": 44.38},
            {"name": "Pack Suprême", "category": "finance", "image_url": "/images/packs/pack6.png", "value_bkc": 57.695},
            {"name": "Pack Prestige", "category": "finance", "image_url": "/images/packs/pack7.png", "value_bkc": 88.76},
            {"name": "Pack Élitaire", "category": "finance", "image_url": "/images/packs/pack8.png", "value_bkc": 133.145},
            {"name": "Pack Royal", "category": "finance", "image_url": "/images/packs/pack9.png", "value_bkc": 177.525},
            {"name": "Pack Ultime", "category": "finance", "image_url": "/images/packs/pack10.png", "value_bkc": 266.285},
        ]

        for pack in packs:
            existing_pack = await session.execute(
                Action.__table__.select().where(Action.name == pack["name"])
            )
            if not existing_pack.first():
                session.add(Action(**pack))

        await session.commit()
        print("✅ Packs financiers insérés avec succès !")


if __name__ == "__main__":
    asyncio.run(seed_actions())
