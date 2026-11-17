from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.mongodb.database import database
from app.adapters.postgresql.database import async_session_factory


async def get_postgresql_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


def get_mongodb_database():
    return database
