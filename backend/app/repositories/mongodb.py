import re

from pymongo.errors import DuplicateKeyError

from app.adapters.mongodb.mapper import (
    from_mongodb_document,
    to_mongodb_document,
)
from app.schemas.filters import RecordFilters
from app.schemas.record import RecordResponse


class MongoDBRepository:
    def __init__(self, database):
        self.collection = database["orders"]

    @staticmethod
    def _build_filter(filters: RecordFilters | None) -> dict:
        if filters is None:
            return {}

        query = {}

        exact_fields = {
            "order_id": "_id",
            "customer_id": "customer.customer_id",
            "product_id": "transaction.product.product_id",
            "store_id": "store.store_id",
            "sales_representative_id": (
                "sales_representative.sales_representative_id"
            ),
            "promotion_code": "promotion.promotion_code",
            "order_status": "order_status",
            "sales_channel": "sales_channel",
            "payment_method": "payment_method",
            "shipping_method": "shipping_method",
        }

        for filter_name, document_field in exact_fields.items():
            value = getattr(filters, filter_name)

            if value is not None:
                query[document_field] = value

        partial_fields = {
            "customer_name": "customer.customer_name",
            "customer_segment": "customer.customer_segment",
            "product_name": "transaction.product.product_name",
            "product_category": "transaction.product.product_category",
            "country": "store.country",
            "region": "store.region",
            "city": "store.city",
        }

        for filter_name, document_field in partial_fields.items():
            value = getattr(filters, filter_name)

            if value is not None:
                query[document_field] = {
                    "$regex": re.escape(value),
                    "$options": "i",
                }

        date_conditions = {}

        if filters.order_date_from is not None:
            date_conditions["$gte"] = (
                filters.order_date_from.isoformat()
            )

        if filters.order_date_to is not None:
            date_conditions["$lte"] = (
                filters.order_date_to.isoformat()
            )

        if date_conditions:
            query["order_date"] = date_conditions

        if filters.has_return is True:
            query["return"] = {"$exists": True}
        elif filters.has_return is False:
            query["return"] = {"$exists": False}

        return query

    async def get_by_order_id(self, order_id: str) -> dict | None:
        return await self.collection.find_one({"_id": order_id})

    async def get_documents_by_order_ids(
        self,
        order_ids: list[str],
    ) -> list[dict]:
        ordered_ids = sorted(set(order_ids))

        if not ordered_ids:
            return []

        cursor = (
            self.collection.find(
                {"_id": {"$in": ordered_ids}}
            )
            .sort("_id", 1)
        )

        documents = await cursor.to_list(length=len(ordered_ids))

        found_ids = {
            document["_id"]
            for document in documents
        }

        missing_ids = sorted(set(ordered_ids) - found_ids)

        if missing_ids:
            raise ValueError(
                "MongoDB documents not found for orders: "
                + ", ".join(missing_ids)
            )

        return documents

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: RecordFilters | None = None,
    ) -> list[dict]:
        query = self._build_filter(filters)

        cursor = (
            self.collection.find(query)
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
        filters: RecordFilters | None = None,
    ) -> list[RecordResponse]:
        documents = await self.get_all(
            limit=limit,
            offset=offset,
            filters=filters,
        )

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

    async def get_affected_order_ids(
        self,
        order_id: str,
        customer_id: str | None = None,
        store_id: str | None = None,
        sales_representative_id: int | None = None,
        product_id: str | None = None,
    ) -> list[str]:
        conditions = [
            {"_id": order_id},
        ]

        if customer_id is not None:
            conditions.append(
                {"customer.customer_id": customer_id}
            )

        if store_id is not None:
            conditions.append(
                {"store.store_id": store_id}
            )

        if sales_representative_id is not None:
            conditions.append(
                {
                    "sales_representative.sales_representative_id":
                    sales_representative_id
                }
            )

        if product_id is not None:
            conditions.append(
                {"transaction.product.product_id": product_id}
            )

        cursor = (
            self.collection.find(
                {"$or": conditions},
                projection={"_id": 1},
            )
            .sort("_id", 1)
        )

        documents = await cursor.to_list(length=None)

        return [document["_id"] for document in documents]

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

    async def delete_created(self, order_id: str) -> bool:
        result = await self.collection.delete_one(
            {"_id": order_id}
        )

        return result.deleted_count == 1

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
