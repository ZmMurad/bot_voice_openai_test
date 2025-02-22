import asyncio
from io import BytesIO

from aiogram import Router, types, Bot
from aiogram.filters import Command
from openai import AsyncOpenAI
from aiogram import F

from config import Settings

router = Router()

@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 Отправьте голосовое сообщение для общения с AI")


@router.message(F.content_type.in_({'voice','audio'}))
async def handle_voice(message: types.Message,client_ai:AsyncOpenAI,bot:Bot,settings:Settings):
    try:
        msg = await message.answer('Ваш запрос обрабатывается')
        file = await bot.get_file(message.voice.file_id)
        audio_data = await bot.download_file(file.file_path)

        voice_to_text_data = await client_ai.audio.transcriptions.create(
            file= ('voice.ogg',audio_data.read()),model='whisper-1'
        )

        thread = await client_ai.beta.threads.create()
        await client_ai.beta.threads.messages.create(
            thread_id=thread.id,
            content=voice_to_text_data.text,
            role = 'user'
        )
        run = await client_ai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=settings.ASSISTANT_ID
        )

        while run.status not in ['completed','failed']:
            await asyncio.sleep(1)
            run = await client_ai.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        messages = await client_ai.beta.threads.messages.list(thread.id)
        reponse = messages.data[0].content[0].text.value

        speech = await client_ai.audio.speech.create(
            model='tts-1',
            voice='alloy',
            input=reponse
        )
        speech_data = speech.read()

        audio_buffer = BytesIO(speech_data)
        await message.answer_voice(
            types.BufferedInputFile(
                audio_buffer.getvalue(),
                filename='response.ogg'
            ),
        )
        await msg.delete()
    except Exception as e:
        await message.answer(f"Ошибка при генерации: {str(e)}")
