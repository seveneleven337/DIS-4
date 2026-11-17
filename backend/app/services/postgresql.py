
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.postgresql import PostgreSQLRepository
from app.schemas.record import RecordResponse


class PostgreSQLRecordService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = PostgreSQLRepository(session)

    async def get_by_order_id(
        self,
        order_id: str,
    ) -> RecordResponse | None:
        return await self.repository.get_by_order_id(order_id)

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RecordResponse]:
        return await self.repository.get_all(
            limit=limit,
            offset=offset,
        )

    async def create(
        self,
        record: RecordResponse,
    ) -> RecordResponse:
        async with self.session.begin():
            return await self.repository.create(record)

    async def update(
        self,
        record: RecordResponse,
    ) -> RecordResponse:
        async with self.session.begin():
            return await self.repository.update(record)

    async def delete(
        self,
        order_id: str,
        expected_version: int,
    ) -> bool:
        async with self.session.begin():
            return await self.repository.delete(
                order_id=order_id,
                expected_version=expected_version,
            )
