from aiogram.types import TelegramObject
from aiogram.dispatcher.middlewares.base import BaseMiddleware

class ContextMiddleware(BaseMiddleware):
    def __init__(self, client_ai, bot,settings,analytics):
        super().__init__()
        self.client_ai = client_ai
        self.bot = bot
        self.settings = settings
        self.analytics = analytics

    async def __call__(self, handler, event: TelegramObject, data: dict):
        data['client_ai']=self.client_ai
        data['bot']=self.bot
        data['settings']=self.settings
        data['analytics']=self.analytics
        return await handler(event, data)
