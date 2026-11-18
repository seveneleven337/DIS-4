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

    @staticmethod
    def validate_document_versions(
        documents: list[dict],
        expected_versions: dict[str, int],
    ) -> None:
        document_versions = {}

        for document in documents:
            order_id = document.get("_id")
            version = document.get("_version")

            if not isinstance(order_id, str):
                raise ValueError(
                    "MongoDB document has an invalid order ID."
                )

            if order_id in document_versions:
                raise ValueError(
                    f"Duplicate MongoDB document for order '{order_id}'."
                )

            if (
                not isinstance(version, int)
                or isinstance(version, bool)
                or version < 1
            ):
                raise ValueError(
                    f"MongoDB document '{order_id}' has an invalid _version."
                )

            document_versions[order_id] = version

        expected_ids = set(expected_versions)
        actual_ids = set(document_versions)

        missing_ids = sorted(expected_ids - actual_ids)
        unexpected_ids = sorted(actual_ids - expected_ids)

        if missing_ids or unexpected_ids:
            details = []

            if missing_ids:
                details.append(
                    "Missing MongoDB documents: "
                    + ", ".join(missing_ids)
                )

            if unexpected_ids:
                details.append(
                    "Unexpected MongoDB documents: "
                    + ", ".join(unexpected_ids)
                )

            raise ValueError("; ".join(details))

        for order_id in sorted(expected_ids):
            expected_version = expected_versions[order_id]
            actual_version = document_versions[order_id]

            if (
                not isinstance(expected_version, int)
                or isinstance(expected_version, bool)
                or expected_version < 1
            ):
                raise ValueError(
                    f"PostgreSQL metadata for order '{order_id}' "
                    "has an invalid version."
                )

            if actual_version != expected_version:
                raise ValueError(
                    f"Version mismatch for order '{order_id}': "
                    f"PostgreSQL={expected_version}, "
                    f"MongoDB={actual_version}."
                )

    async def replace_document_with_version(
        self,
        document: dict,
        expected_version: int,
    ) -> dict:
        order_id = document.get("_id")

        if not isinstance(order_id, str):
            raise ValueError("MongoDB document has an invalid order ID.")

        if (
            not isinstance(expected_version, int)
            or isinstance(expected_version, bool)
            or expected_version < 1
        ):
            raise ValueError(
                "Expected MongoDB version must be a positive integer."
            )

        replacement = dict(document)
        replacement["_version"] = expected_version + 1

        result = await self.collection.replace_one(
            {
                "_id": order_id,
                "_version": expected_version,
            },
            replacement,
        )

        if result.matched_count != 1:
            current = await self.collection.find_one(
                {"_id": order_id},
                projection={"_version": 1},
            )

            if current is None:
                raise ValueError(
                    f"MongoDB document '{order_id}' does not exist."
                )

            current_version = current.get("_version")

            raise ValueError(
                f"MongoDB version conflict for order '{order_id}': "
                f"expected={expected_version}, "
                f"actual={current_version}."
            )

        return replacement

    async def restore_document_with_version(
        self,
        snapshot: dict,
        expected_current_version: int,
    ) -> dict:
        order_id = snapshot.get("_id")
        snapshot_version = snapshot.get("_version")

        if not isinstance(order_id, str):
            raise ValueError(
                "MongoDB snapshot has an invalid order ID."
            )

        if (
            not isinstance(snapshot_version, int)
            or isinstance(snapshot_version, bool)
            or snapshot_version < 1
        ):
            raise ValueError(
                f"MongoDB snapshot '{order_id}' has an invalid _version."
            )

        if (
            not isinstance(expected_current_version, int)
            or isinstance(expected_current_version, bool)
            or expected_current_version < 1
        ):
            raise ValueError(
                "Expected current MongoDB version must be a positive integer."
            )

        if expected_current_version != snapshot_version + 1:
            raise ValueError(
                f"Invalid compensation versions for order '{order_id}': "
                f"snapshot={snapshot_version}, "
                f"expected_current={expected_current_version}."
            )

        original_document = dict(snapshot)

        result = await self.collection.replace_one(
            {
                "_id": order_id,
                "_version": expected_current_version,
            },
            original_document,
        )

        if result.matched_count != 1:
            current = await self.collection.find_one(
                {"_id": order_id},
                projection={"_version": 1},
            )

            if current is None:
                raise ValueError(
                    f"Cannot compensate order '{order_id}': "
                    "MongoDB document does not exist."
                )

            current_version = current.get("_version")

            raise ValueError(
                f"MongoDB compensation conflict for order '{order_id}': "
                f"expected_current={expected_current_version}, "
                f"actual={current_version}."
            )

        return original_document

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

    async def delete_with_version(
        self,
        order_id: str,
        expected_version: int,
    ) -> bool:
        result = await self.collection.delete_one(
            {
                "_id": order_id,
                "_version": expected_version,
            }
        )

        if result.deleted_count != 1:
            current = await self.collection.find_one(
                {"_id": order_id},
                projection={"_version": 1},
            )

            if current is None:
                raise ValueError(
                    f"MongoDB document '{order_id}' does not exist."
                )

            raise ValueError(
                f"MongoDB version conflict for order '{order_id}': "
                f"expected={expected_version}, "
                f"actual={current.get('_version')}."
            )

        return True

    async def restore_deleted_document(
        self,
        snapshot: dict,
    ) -> bool:
        order_id = snapshot.get("_id")
        version = snapshot.get("_version")

        if not isinstance(order_id, str):
            raise ValueError("MongoDB snapshot has an invalid order ID.")

        if (
            not isinstance(version, int)
            or isinstance(version, bool)
            or version < 1
        ):
            raise ValueError(
                f"MongoDB snapshot '{order_id}' has an invalid version."
            )

        await self.collection.insert_one(dict(snapshot))
        return True
