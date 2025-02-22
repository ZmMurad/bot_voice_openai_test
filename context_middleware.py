from aiogram.types import TelegramObject
from aiogram.dispatcher.middlewares.base import BaseMiddleware

class ContextMiddleware(BaseMiddleware):
    def __init__(self, client_ai, bot,settings):
        super().__init__()
        self.client_ai = client_ai
        self.bot = bot
        self.settings = settings

    async def __call__(self, handler, event: TelegramObject, data: dict):
        data['client_ai']=self.client_ai
        data['bot']=self.bot
        data['settings']=self.settings
        return await handler(event, data)
