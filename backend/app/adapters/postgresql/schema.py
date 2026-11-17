from app.adapters.postgresql.database import engine
from app.adapters.postgresql.models import Base


async def create_database_schema() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)