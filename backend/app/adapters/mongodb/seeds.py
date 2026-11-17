from pymongo import UpdateOne
from sqlalchemy import select

from app.adapters.mongodb.database import database
from app.adapters.postgresql.database import async_session_factory
from app.adapters.postgresql.models.record_location import RecordLocationDB
from app.adapters.mongodb.mapper import to_mongodb_document
from app.loaders.seed_data import build_seed_records


async def seed_mongodb_records() -> int:
    records = [
        record
        for record in build_seed_records()
        if record.storage_location in ("MONGODB", "BOTH")
    ]

    if not records:
        return 0

    operations = [
        UpdateOne(
            {"_id": record.order.order_id},
            {
                "$setOnInsert": to_mongodb_document(record),
            },
            upsert=True,
        )
        for record in records
    ]

    result = await database["orders"].bulk_write(
        operations,
        ordered=False,
    )

    return result.upserted_count


async def synchronize_mongodb_versions() -> int:
    """Synchronize MongoDB document versions with PostgreSQL metadata."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(
                RecordLocationDB.order_id,
                RecordLocationDB.version,
            ).where(
                RecordLocationDB.storage_location.in_(
                    ("MONGODB", "BOTH")
                )
            )
        )

        locations = result.all()

    if not locations:
        return 0

    operations = [
        UpdateOne(
            {"_id": order_id},
            {"$set": {"_version": version}},
        )
        for order_id, version in locations
    ]

    result = await database["orders"].bulk_write(
        operations,
        ordered=False,
    )

    if result.matched_count != len(locations):
        raise RuntimeError(
            "MongoDB version synchronization failed: "
            f"expected {len(locations)} documents, "
            f"found {result.matched_count}."
        )

    return result.modified_count
