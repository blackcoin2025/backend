# app/services/addtasks_standalone.py
import asyncio
import random
import string
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models import Task  # ✅ Assure-toi que ce chemin est correct

# 🔹 Config de la base de données (à adapter à ton environnement)
DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_NQsxv1Cn0UuW@ep-spring-river-abgnr23v-pooler.eu-west-2.aws.neon.tech/neondb"

# Création de l'engine et de la session asynchrone
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

def generate_code(length: int = 6) -> str:
    """Génère un code de validation aléatoire."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

async def add_task(
    db: AsyncSession,
    title: str,
    link: str,
    reward_points: int = 100,
    logo: str | None = None
) -> Task:
    """Ajoute une nouvelle tâche dans la base."""
    task = Task(
        title=title,
        link=link,
        reward_points=reward_points,
        validation_code=generate_code(),
        logo=logo
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

async def add_sample_tasks(db: AsyncSession):
    """Ajoute des tâches par défaut si la table est vide."""
    result = await db.execute(Task.__table__.select())
    existing_tasks = result.scalars().all()
    if existing_tasks:
        print("⚡ La table des tâches contient déjà des données.")
        return

    # ✅ Ici on fournit aussi le nom du logo
    sample_tasks = [
        ("Telegram", "https://t.me/+2VYCu2Ygs0Q1YTk0", 1000, "telegram.png"),
        ("Facebook", "https://www.facebook.com/share/1BxkwKdPZL/", 1000, "facebook.png"),
        ("Twitter", "https://x.com/BlackcoinON", 1000, "twitter.png"),
        ("YouTube", "https://www.youtube.com/@Blackcoinchaine", 1000, "youtube.png"),
        ("TikTok", "https://www.tiktok.com/@blackcoin_official", 1000, "tiktok.png"),
    ]

    for title, link, points, logo in sample_tasks:
        await add_task(db, title=title, link=link, reward_points=points, logo=logo)

    print("✅ Tâches par défaut ajoutées avec succès !")

async def main():
    async with async_session() as db:
        await add_sample_tasks(db)

if __name__ == "__main__":
    asyncio.run(main())
