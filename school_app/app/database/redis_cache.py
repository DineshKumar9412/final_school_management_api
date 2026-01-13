# database/redis_cache.py
import os
import json
import redis.asyncio as redis
from typing import Optional, Any

class RedisCache:
    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = None,
        password: str = None,
        decode_responses: bool = True
    ):
        self.host = host or os.getenv("REDIS_HOST", "127.0.0.1")
        self.port = port or int(os.getenv("REDIS_PORT", 6379))
        self.db = db or int(os.getenv("REDIS_DB", 0))
        self.password = password or os.getenv("REDIS_PASSWORD")
        self.decode_responses = decode_responses

        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,  
            decode_responses=self.decode_responses
        )

    async def get(self, key: str) -> Optional[Any]:
        data = await self.client.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data

    async def set(self, key: str, value: Any, expire: int = 60):
        if not isinstance(value, str):
            value = json.dumps(value)
        await self.client.set(key, value, ex=expire)

    async def delete(self, key: str):
        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.client.exists(key) > 0

    async def ping(self) -> bool:
        return await self.client.ping()
