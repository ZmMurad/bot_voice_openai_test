from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

def create_storage(redis_url: str):
    redis = Redis.from_url(redis_url)
    return RedisStorage(redis=redis)