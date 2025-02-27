import asyncio
from io import BytesIO

from aiogram import Router, types, Bot
from aiogram.filters import Command
from openai import AsyncOpenAI
from aiogram import F

from models import save_to_db
from config import Settings
from database import AsyncSessionLocal
from openai_client import OpenAIService, validate_value
from utils import generate_unique_name, cleanup_files

router = Router()


@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 Отправьте голосовое сообщение для общения с AI")


@router.message(F.content_type.in_({'voice', 'audio'}))
async def handle_voice(message: types.Message, client_ai: OpenAIService, bot: Bot, settings: Settings):
    speech_path = f"speech_{generate_unique_name()}.mp3"
    audio_path = f"voice_{generate_unique_name()}.ogg"
    try:
        msg = await message.answer('Ваш запрос обрабатывается')
        file = await bot.get_file(message.voice.file_id)
        await bot.download_file(file.file_path, audio_path)
        with open(audio_path, "rb") as f:
            transcript = await client_ai.client.audio.transcriptions.create(
                file=f, model="whisper-1"
            )
        response_text = await client_ai.process_message(transcript.text)
        response = await client_ai.client.audio.speech.create(
            model="tts-1", voice="nova", input=response_text
        )
        response.stream_to_file(speech_path)
        with open(speech_path, "rb") as audio_file:
            await message.answer_voice(
                types.BufferedInputFile(
                    audio_file.read(),
                    filename="response.mp3"
                ),
                caption=response_text[:1000]
            )
        await msg.delete()
        cleanup_files(audio_path, speech_path)

    except Exception as e:
        await message.answer(f"🚨 Ошибка: {str(e)}")
        cleanup_files(audio_path, speech_path)


@router.message(Command("myvalue"))
async def ask_value(message: types.Message):
    """
    Хендлер, который просто просит пользователя ввести / сказать свою ценность.
    """
    await message.answer("Пожалуйста, опишите вашу ключевую ценность (короткой фразой или одним словом).")

@router.message(F.content_type == 'text')
async def handle_value(message: types.Message,client_ai:OpenAIService):
    print('Начали обработку')
    async with AsyncSessionLocal() as session:
        try:
            result = await client_ai.identify_value(message.text)
            if "error" in result:
                return await message.answer(f"Ошибка: {result['error']}")
            if "function_call" in result:
                args = result["function_call"]["arguments"]
                if validate_value(args["description"]):
                    await save_to_db(message.from_user.id, args, session)
                    await message.answer("✅ Ценность сохранена!")
                else:
                    await message.answer("🚫 Некорректное описание. Попробуйте снова.")
            else:
                await message.answer(result["response"])
        except Exception as e:
            await session.rollback()
            await message.answer(f"Ошибка: {str(e)}")