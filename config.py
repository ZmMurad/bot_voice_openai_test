from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    OPENAI_API_KEY: str
    ASSISTANT_ID: str

    class Config:
        case_sensitive = True