import asyncio
import logging
from io import BytesIO

from aiogram import Router, types, Bot
from aiogram.filters import Command
from openai import AsyncOpenAI
from aiogram import F

from models import save_to_db
from config import Settings
from database import AsyncSessionLocal
from openai_client import OpenAIService, validate_value, process_assistant_response
from utils import generate_unique_name, cleanup_files

router = Router()


@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 Отправьте голосовое сообщение для общения с AI")


@router.message(F.content_type.in_({'voice', 'audio'}))
async def handle_voice(message: types.Message, client_ai: OpenAIService, bot: Bot):
    try:
        audio_path = f"voice_{generate_unique_name()}.ogg"
        file = await bot.get_file(message.voice.file_id)
        await bot.download_file(file.file_path, audio_path)

        with open(audio_path, "rb") as f:
            transcript = await client_ai.client.audio.transcriptions.create(
                file=f, model="whisper-1"
            )

        await process_assistant_response(
            message=message,
            client_ai=client_ai,
            input_text=transcript.text,
            is_voice=True,
            bot=bot
        )

    except Exception as e:
        logging.error(f"Voice processing error: {str(e)}")
        await message.answer(f"🚨 Ошибка обработки аудио: {str(e)}")

    finally:
        cleanup_files(audio_path)
