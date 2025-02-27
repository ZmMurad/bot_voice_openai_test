import logging

import os
from openai import AsyncOpenAI
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    OPENAI_API_KEY: str
    ASSISTANT_ID: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str

    class Config:
        case_sensitive = True
        env_file = ".env"

    async def init_assistant(self):
        """Создает ассистента при первом запуске"""
        print(self.ASSISTANT_ID, type(self.ASSISTANT_ID))
        if not self.ASSISTANT_ID or len(self.ASSISTANT_ID) < 3:
            print('Create ASSISTANT_ID')
            client = AsyncOpenAI(api_key=self.OPENAI_API_KEY)
            assistant = await client.beta.assistants.create(
                name="AutoCreated Assistant",
                instructions="You are a helpful assistant",
                model="gpt-4-1106-preview"
            )
            self.ASSISTANT_ID = assistant.id
            if os.path.exists(".env"):
                with open(".env", "a") as f:
                    f.write(f"\nASSISTANT_ID={assistant.id}")

            print(f"🆕 Created new Assistant ID: {assistant.id}")
