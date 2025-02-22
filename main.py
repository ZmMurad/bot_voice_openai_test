import asyncio
from aiogram import Bot, Dispatcher
from config import Settings
from openai import AsyncOpenAI
from context_middleware import ContextMiddleware
from main_router import router

settings = Settings()
bot = Bot(settings.BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
dp.update.middleware(ContextMiddleware(client, bot,settings))
dp.include_router(router)


async def create_assistant():
    assistant = await client.beta.assistants.create(
        name="Telegram Assistant",
        instructions="Ты полезный ассистент для Telegram бота",
        model="gpt-4o"
    )
    settings.ASSISTANT_ID = assistant.id


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await create_assistant()
    await dp.start_polling(bot)



if __name__ == "__main__":
    asyncio.run(main())
