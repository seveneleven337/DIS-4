
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from app.core.config import settings


client = AsyncMongoClient(
    host=settings.mongo_host,
    port=settings.mongo_port,
    username=settings.mongo_username,
    password=settings.mongo_password.get_secret_value(),
    authSource="admin",
    serverSelectionTimeoutMS=5000,
)

database = client[settings.mongo_db]


async def check_mongodb_connection() -> bool:
    result = await client.admin.command("ping")
    return result.get("ok") == 1


async def close_mongodb_connection() -> None:
    await client.close()
