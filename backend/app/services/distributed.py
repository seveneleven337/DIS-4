from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.mongodb import MongoDBRepository
from app.repositories.postgresql import PostgreSQLRepository
from app.schemas.record import RecordResponse


RecordSource = Literal["ALL", "POSTGRESQL", "MONGODB"]


class DistributedRecordService:
    def __init__(self, session: AsyncSession, mongodb_database):
        self.postgresql_repository = PostgreSQLRepository(session)
        self.mongodb_repository = MongoDBRepository(mongodb_database)

    async def get_by_order_id(
        self,
        order_id: str,
    ) -> RecordResponse | None:
        metadata = await self.postgresql_repository.get_storage_location(
            order_id
        )

        if metadata is None:
            return None

        if metadata.storage_location in {"POSTGRESQL", "BOTH"}:
            record = await self.postgresql_repository.get_by_order_id(
                order_id
            )

            if record is None:
                raise RuntimeError(
                    f"Metadata exists for {order_id}, "
                    "but the PostgreSQL record is missing"
                )

            return record

        if metadata.storage_location == "MONGODB":
            record = await self.mongodb_repository.get_record_by_order_id(
                order_id=order_id,
                storage_location=metadata.storage_location,
                version=metadata.version,
            )

            if record is None:
                raise RuntimeError(
                    f"Metadata exists for {order_id}, "
                    "but the MongoDB document is missing"
                )

            return record

        raise ValueError(
            f"Unsupported storage location: {metadata.storage_location}"
        )

    async def get_all(
        self,
        source: RecordSource = "ALL",
        limit: int = 100,
        offset: int = 0,
    ) -> list[RecordResponse]:
        if source not in {"ALL", "POSTGRESQL", "MONGODB"}:
            raise ValueError(f"Unsupported record source: {source}")

        if limit < 1:
            raise ValueError("Limit must be greater than zero")

        if offset < 0:
            raise ValueError("Offset cannot be negative")

        metadata_records = (
            await self.postgresql_repository.get_all_storage_locations()
        )

        if source == "POSTGRESQL":
            metadata_records = [
                item
                for item in metadata_records
                if item.storage_location in {"POSTGRESQL", "BOTH"}
            ]

        elif source == "MONGODB":
            metadata_records = [
                item
                for item in metadata_records
                if item.storage_location in {"MONGODB", "BOTH"}
            ]

        records_by_id: dict[str, RecordResponse] = {}

        if source in {"ALL", "POSTGRESQL"}:
            postgres_records = await self.postgresql_repository.get_all(
                limit=len(metadata_records),
                offset=0,
            )

            records_by_id.update({
                record.order.order_id: record
                for record in postgres_records
            })

        if source in {"ALL", "MONGODB"}:
            storage_locations = {
                item.order_id: (
                    item.storage_location,
                    item.version,
                )
                for item in metadata_records
                if item.storage_location in {"MONGODB", "BOTH"}
            }

            mongo_records = await self.mongodb_repository.get_all_records(
                storage_locations=storage_locations,
                limit=len(metadata_records),
                offset=0,
            )

            for record in mongo_records:
                records_by_id.setdefault(
                    record.order.order_id,
                    record,
                )

        paginated_metadata = metadata_records[offset:offset + limit]

        records = []

        for metadata in paginated_metadata:
            record = records_by_id.get(metadata.order_id)

            if record is None:
                raise RuntimeError(
                    f"Metadata exists for {metadata.order_id}, "
                    "but the corresponding database record is missing"
                )

            records.append(record)

        return records
