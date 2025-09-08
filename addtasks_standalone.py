# app/services/addtasks_standalone.py
import asyncio
import random
import string
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models import Task  # assure-toi que le chemin est correct

# 🔹 Config de la base de données (à adapter)
DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_NQsxv1Cn0UuW@ep-spring-river-abgnr23v-pooler.eu-west-2.aws.neon.tech/neondb"

# Création de l'engine et de la session asynchrone
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

def generate_code(length: int = 4) -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

async def add_task(db: AsyncSession, title: str, link: str, reward_points: int = 100) -> Task:
    task = Task(
        title=title,
        link=link,
        reward_points=reward_points,
        validation_code=generate_code()
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

async def add_sample_tasks(db: AsyncSession):
    result = await db.execute(Task.__table__.select())
    existing_tasks = result.scalars().all()
    if existing_tasks:
        print("⚡ La table des tâches contient déjà des données.")
        return

    sample_tasks = [
        ("Telegram", "https://t.me/blackcoin202", 1000),
        ("Facebook", "https://www.facebook.com/share/1BxkwKdPZL/", 1000),
        ("Twitter", "https://x.com/BlackcoinON", 1000),
        ("YouTube", "https://www.youtube.com/@Blackcoinchaine", 1000),
        ("TikTok", "https://www.tiktok.com/@blackcoinsecurity", 1000),
    ]

    for title, link, points in sample_tasks:
        await add_task(db, title=title, link=link, reward_points=points)

    print("✅ Tâches par défaut ajoutées avec succès !")

async def main():
    async with async_session() as db:
        await add_sample_tasks(db)

if __name__ == "__main__":
    asyncio.run(main())
