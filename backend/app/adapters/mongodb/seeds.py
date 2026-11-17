
from pymongo import UpdateOne

from app.adapters.mongodb.database import database
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
