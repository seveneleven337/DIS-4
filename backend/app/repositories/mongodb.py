from pymongo.errors import DuplicateKeyError

from app.adapters.mongodb.mapper import (
    from_mongodb_document,
    to_mongodb_document,
)
from app.schemas.record import RecordResponse


class MongoDBRepository:
    def __init__(self, database):
        self.collection = database["orders"]

    async def get_by_order_id(self, order_id: str) -> dict | None:
        return await self.collection.find_one({"_id": order_id})

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        cursor = (
            self.collection.find({})
            .sort("_id", 1)
            .skip(offset)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def get_record_by_order_id(
        self,
        order_id: str,
        storage_location: str,
        version: int,
    ) -> RecordResponse | None:
        document = await self.get_by_order_id(order_id)

        if document is None:
            return None

        return from_mongodb_document(
            document=document,
            storage_location=storage_location,
            version=version,
        )

    async def get_all_records(
        self,
        storage_locations: dict[str, tuple[str, int]],
        limit: int = 100,
        offset: int = 0,
    ) -> list[RecordResponse]:
        documents = await self.get_all(limit=limit, offset=offset)

        records = []

        for document in documents:
            order_id = document["_id"]
            metadata = storage_locations.get(order_id)

            if metadata is None:
                continue

            storage_location, version = metadata

            records.append(
                from_mongodb_document(
                    document=document,
                    storage_location=storage_location,
                    version=version,
                )
            )

        return records

    async def create(self, record: RecordResponse) -> dict:
        if record.storage_location not in {"MONGODB", "BOTH"}:
            raise ValueError(
                "Record storage location must be MONGODB or BOTH"
            )

        document = to_mongodb_document(record)

        try:
            await self.collection.insert_one(document)
        except DuplicateKeyError as exc:
            raise ValueError(
                f"Record {record.order.order_id} already exists"
            ) from exc

        return document

    async def update(
        self,
        record: RecordResponse,
        expected_version: int,
    ) -> dict:
        if record.storage_location not in {"MONGODB", "BOTH"}:
            raise ValueError(
                "Record storage location must be MONGODB or BOTH"
            )

        if record.version != expected_version:
            raise ValueError("Record version does not match expected version")

        document = to_mongodb_document(record)

        existing = await self.collection.find_one(
            {"_id": record.order.order_id}
        )

        if existing is None:
            raise ValueError(
                f"Record {record.order.order_id} does not exist"
            )

        result = await self.collection.replace_one(
            {"_id": record.order.order_id},
            document,
        )

        if result.modified_count != 1:
            raise ValueError(
                f"Could not update record {record.order.order_id}"
            )

        return document

    async def delete(
        self,
        order_id: str,
        storage_location: str,
        expected_version: int,
        current_version: int,
    ) -> bool:
        if storage_location not in {"MONGODB", "BOTH"}:
            raise ValueError(
                "Record storage location must be MONGODB or BOTH"
            )

        if expected_version != current_version:
            raise ValueError("Record version does not match expected version")

        result = await self.collection.delete_one({"_id": order_id})

        if result.deleted_count != 1:
            raise ValueError(f"Record {order_id} does not exist")

        return True
