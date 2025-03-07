import asyncio
import logging
from io import BytesIO

from aiogram import Router, types, Bot
from aiogram.filters import Command
from openai import AsyncOpenAI
from aiogram import F

from analytics import AnalyticsService
from openai_client import OpenAIService, validate_value, process_assistant_response
from utils import generate_unique_name, cleanup_files

router = Router()


@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 Отправьте голосовое сообщение для общения с AI")


@router.message(F.photo)
async def handle_photo(
        message: types.Message,
        client_ai: OpenAIService,
        analytics: AnalyticsService,
        bot: Bot
):
    try:
        file = await bot.get_file(message.photo[-1].file_id)
        image_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
        mood = await client_ai.analyze_mood(image_url)
        await message.answer(f"Ваше настроение: {mood}")

        analytics.track_event(
            user_id=message.from_user.id,
            event_type="photo_analyzed",
            event_props={"mood": mood}
        )

    except Exception as e:
        logging.error(f"Photo handling error: {e}")
        await message.answer("Ошибка обработки фото")

@router.message(F.content_type.in_({'voice', 'audio'}))
async def handle_voice(message: types.Message, client_ai: OpenAIService, bot: Bot,analytics):
    try:
        audio_path = f"voice_{generate_unique_name()}.ogg"
        file = await bot.get_file(message.voice.file_id)
        await bot.download_file(file.file_path, audio_path)

        with open(audio_path, "rb") as f:
            transcript = await client_ai.client.audio.transcriptions.create(
                file=f, model="whisper-1"
            )

        text,audio = await process_assistant_response(
            user_id=message.from_user.id,
            client_ai=client_ai,
            input_text=transcript.text,
            is_voice=True,
            bot=bot
        )
        if not audio:
            await message.answer(text)
        else:
            await message.answer_voice(audio,caption=text[:1000])

        analytics.track_event(
            user_id=message.from_user.id,
            event_type="voice_message",
            event_props={"length": len(text)}
        )

    except Exception as e:
        logging.error(f"Voice processing error: {str(e)}")
        await message.answer(f"🚨 Ошибка обработки аудио: {str(e)}")

    finally:
        cleanup_files(audio_path)
