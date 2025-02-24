from openai import AsyncOpenAI
from config import Settings


class OpenAIService:
    def __init__(self, assistant_id: str,api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.assistant_id = assistant_id

    async def process_message(self, text: str) -> str:
        try:
            # Создание треда и запуск обработки
            thread = await self.client.beta.threads.create()
            await self.client.beta.threads.messages.create(
                thread_id=thread.id,
                content=text,
                role="user"
            )

            run = await self.client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )

            if run.status == "completed":
                messages = await self.client.beta.threads.messages.list(thread.id)
                return messages.data[0].content[0].text.value
            else:
                return f"❌ Ошибка обработки: {run.status}"

        except Exception as e:
            return f"⛔️ OpenAI Error: {str(e)}"