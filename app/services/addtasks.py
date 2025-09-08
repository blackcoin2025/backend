# app/services/addtasks.py
import random
import string
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Task

def generate_code(length: int = 4) -> str:
    """Génère un code aléatoire de validation (4 lettres/chiffres)."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


async def add_task(db: AsyncSession, title: str, link: str, reward_points: int = 100) -> Task:
    """
    Ajoute une nouvelle tâche (ex: vidéo YouTube, TikTok, etc.)
    """
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
    """
    Ajoute des tâches par défaut si la table est vide.
    """
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
