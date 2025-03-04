import asyncio
import logging
import subprocess
import sys

from aiogram import Bot, Dispatcher
from config import Settings
from context_middleware import ContextMiddleware
from main_router import router
from openai_client import OpenAIService



def run_migrations():
    logging.info("Running Alembic migrations...")
    ret = subprocess.run(["alembic", "upgrade", "head"])
    if ret.returncode != 0:
        logging.error("Alembic migration failed.")
        sys.exit(1)

async def main():
    settings = Settings()
    await settings.init_assistant()

    if not settings.ASSISTANT_ID or settings.ASSISTANT_ID == "":
        raise RuntimeError("Failed to create assistant")
    run_migrations()
    bot = Bot(settings.BOT_TOKEN)
    dp = Dispatcher()
    client = OpenAIService(settings.ASSISTANT_ID, settings.OPENAI_API_KEY)
    dp.update.middleware(ContextMiddleware(client, bot, settings))
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info('Bot starting')
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
