import asyncio
import logging
from io import BytesIO

from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
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

@router.message(~F.voice & ~F.audio & ~F.photo & ~F.command)  # catch text messages that are not voice, audio, photo, or commands
async def answer_user_question(message: Message, state: FSMContext, client_ai: OpenAIService):
    user_input = message.text.strip()
    if not user_input:
        return

    # 1. Retrieve or create an OpenAI conversation thread for this user
    data = await state.get_data()  # FSM state data for this user (Chat + User in Aiogram)
    thread_id = data.get("thread_id")
    if thread_id is None:
        # No thread yet for this user: create a new thread and store it
        thread = await client_ai.client.beta.threads.create(
            # We could attach tool_resources here if needed, but since the assistant has it, it's not required
        )
        thread_id = thread.id
        await state.update_data(thread_id=thread_id)
    # If a thread exists, we will reuse it to maintain context across messages

    # 2. Send the user's message to the OpenAI thread
    await client_ai.client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_input
    )

    # 3. Run the assistant to get a response (using the pre-configured assistant with file_search)
    run = await client_ai.client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=client_ai.assistant_id   # use the existing assistant with file_search
    )

    # 4. Retrieve the assistant's answer from the thread messages
    if run.status == "completed":
        messages = await client_ai.client.beta.threads.messages.list(thread_id)
        # The latest assistant message should be included.
        # Assuming messages.data[0] is the assistant's reply (OpenAI Beta may return latest first):
        answer_text = messages.data[0].content[0].text.value
    else:
        answer_text = f"⚠️ Assistant run did not complete (status: {run.status})."

    # 5. Send the answer back to the user
    await message.answer(answer_text)