# seed_actions.py
import asyncio
from dotenv import load_dotenv
from app.database import AsyncSessionLocal  # ✅ correction ici
from app.models import Action

load_dotenv()

async def seed_actions():
    async with AsyncSessionLocal() as session:  # ✅ on utilise ton nom de session
        actions = [
            Action(
                name="Projet DeFi Alpha",
                category="finance",
                type="individuelle",
                total_parts=100,
                price_per_part=10.5
            ),
            Action(
                name="Investissement Immobilier Paris",
                category="immobilier",
                type="commune",
                total_parts=50,
                price_per_part=200.0
            ),
            Action(
                name="Startup Opportunité Web3",
                category="opportunite",
                type="individuelle",
                total_parts=75,
                price_per_part=15.0
            ),
        ]

        session.add_all(actions)
        await session.commit()
        print("✅ Actions insérées avec succès !")

if __name__ == "__main__":
    asyncio.run(seed_actions())
