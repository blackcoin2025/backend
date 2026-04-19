import asyncio
import logging
from app.tasks.reset_daily_tasks import start_daily_reset_task

logging.basicConfig(level=logging.INFO)

async def main():
    logging.info("🚀 Reset worker lancé")
    await start_daily_reset_task()

if __name__ == "__main__":
    asyncio.run(main())