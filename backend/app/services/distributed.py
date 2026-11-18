import json
from typing import Literal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.mongodb.mapper import (
    from_mongodb_document,
    to_mongodb_document,
)
from app.repositories.mongodb import MongoDBRepository
from app.repositories.postgresql import PostgreSQLRepository
from app.repositories.transaction_journal import TransactionJournalRepository
from app.schemas.filters import RecordFilters
from app.schemas.record import (
    RecordCreate,
    RecordResponse,
    RecordUpdate,
)


RecordSource = Literal["ALL", "POSTGRESQL", "MONGODB"]


class DistributedRecordService:
    def __init__(self, session: AsyncSession, mongodb_database):
        self.postgresql_repository = PostgreSQLRepository(session)
        self.mongodb_repository = MongoDBRepository(mongodb_database)
        self.transaction_journal = TransactionJournalRepository()

    @staticmethod
    def _validate_immutable_ids(
        existing: RecordResponse,
        record: RecordUpdate,
    ) -> None:
        immutable_ids = (
            (
                "Customer ID",
                existing.customer.customer_id,
                record.customer.customer_id,
            ),
            (
                "Store ID",
                existing.store.store_id,
                record.store.store_id,
            ),
            (
                "Sales representative ID",
                existing.sales_representative.sales_representative_id,
                record.sales_representative.sales_representative_id,
            ),
            (
                "Product ID",
                existing.product.product_id,
                record.product.product_id,
            ),
            (
                "Order ID",
                existing.order.order_id,
                record.order.order_id,
            ),
            (
                "Transaction ID",
                existing.transaction.transaction_id,
                record.transaction.transaction_id,
            ),
            (
                "Transaction Order ID",
                existing.transaction.order_id,
                record.transaction.order_id,
            ),
            (
                "Promotion code",
                (
                    existing.promotion.promotion_code
                    if existing.promotion is not None
                    else None
                ),
                (
                    record.promotion.promotion_code
                    if record.promotion is not None
                    else None
                ),
            ),
        )

        for label, old_value, new_value in immutable_ids:
            if old_value != new_value:
                raise ValueError(
                    f"{label} cannot be changed."
                )

        if record.return_record is not None:
            if (
                record.return_record.order_id
                != record.order.order_id
            ):
                raise ValueError(
                    "Return Order ID must match the target Order ID."
                )

            if (
                existing.return_record is not None
                and existing.return_record.order_id
                != record.return_record.order_id
            ):
                raise ValueError(
                    "Return Order ID cannot be changed."
                )

    @staticmethod
    def _get_changed_entities(
        existing: RecordResponse,
        record: RecordUpdate,
    ) -> dict:
        entity_names = (
            "customer",
            "store",
            "sales_representative",
            "product",
        )

        return {
            name: getattr(record, name)
            for name in entity_names
            if getattr(record, name) != getattr(existing, name)
        }

    async def create(self, record: RecordCreate) -> RecordResponse:
        response = RecordResponse.model_validate({
            **record.model_dump(),
            "version": 1,
        })

        order_id = response.order.order_id
        storage_location = response.storage_location
        operation_id = str(uuid4())

        initial_payload = json.dumps({
            "storage_location": storage_location,
            "operation_id": operation_id,
        })

        await self.transaction_journal.create_operation(
            operation_id=operation_id,
            operation_type="CREATE",
            order_id=order_id,
            payload=initial_payload,
        )

        mongo_created = False

        try:
            if storage_location == "POSTGRESQL":
                async with self.postgresql_repository.session.begin():
                    await self.postgresql_repository.create(response)
                    await self.transaction_journal.mark_database_committed(
                        self.postgresql_repository.session,
                        operation_id,
                    )

            elif storage_location == "MONGODB":
                await self.mongodb_repository.create(
                    response,
                    operation_id=operation_id,
                )
                mongo_created = True

                async with self.postgresql_repository.session.begin():
                    await self.postgresql_repository.create_storage_location(
                        order_id=order_id,
                        storage_location="MONGODB",
                        version=1,
                    )
                    await self.transaction_journal.mark_database_committed(
                        self.postgresql_repository.session,
                        operation_id,
                    )

            elif storage_location == "BOTH":
                async with self.postgresql_repository.session.begin():
                    await self.postgresql_repository.create(response)

                    await self.mongodb_repository.create(
                        response,
                        operation_id=operation_id,
                    )
                    mongo_created = True

                    await self.transaction_journal.mark_database_committed(
                        self.postgresql_repository.session,
                        operation_id,
                    )

            else:
                raise ValueError(
                    f"Unsupported storage location: {storage_location}"
                )

        except Exception as exc:
            try:
                await self.transaction_journal.transition(
                    operation_id,
                    "COMPENSATING",
                    error=str(exc),
                )
            except Exception as journal_error:
                raise RuntimeError(
                    f"Creation of {order_id} failed and its journal "
                    "could not enter COMPENSATING. Recovery is required."
                ) from journal_error

            if mongo_created:
                try:
                    compensated = await self.mongodb_repository.delete_created(
                        order_id,
                        operation_id,
                    )
                except Exception as compensation_error:
                    await self.transaction_journal.transition(
                        operation_id,
                        "FAILED",
                        error=str(compensation_error),
                    )
                    raise RuntimeError(
                        f"Creation of {order_id} failed and MongoDB "
                        "compensation also failed. Manual reconciliation "
                        "is required."
                    ) from compensation_error

                if not compensated:
                    await self.transaction_journal.transition(
                        operation_id,
                        "FAILED",
                        error="MongoDB creation compensation failed.",
                    )
                    raise RuntimeError(
                        f"Creation of {order_id} failed and its MongoDB "
                        "document could not be compensated. "
                        "Manual reconciliation is required."
                    ) from exc

            await self.transaction_journal.transition(
                operation_id,
                "COMPENSATED",
                error=str(exc),
            )
            raise

        # PostgreSQL has committed. A failure in this final transition
        # must not trigger compensation of an already committed operation.
        try:
            await self.transaction_journal.transition(
                operation_id,
                "COMMITTED",
            )
        except Exception:
            pass

        return response

    async def update(
        self,
        order_id: str,
        record: RecordUpdate,
    ) -> RecordResponse:
        if record.order.order_id != order_id:
            raise ValueError(
                "The URL Order ID must match the request Order ID."
            )

        snapshots: dict[str, dict] = {}
        modified_mongo_ids: list[str] = []

        try:
            async with self.postgresql_repository.session.begin():
                initial_metadata = (
                    await self.postgresql_repository.get_storage_location(
                        order_id
                    )
                )

                if initial_metadata is None:
                    raise ValueError(
                        f"Order '{order_id}' does not exist."
                    )

                storage_location = initial_metadata.storage_location

                if storage_location not in {
                    "POSTGRESQL",
                    "MONGODB",
                    "BOTH",
                }:
                    raise ValueError(
                        f"Unsupported storage location: {storage_location}"
                    )

                if storage_location in {"POSTGRESQL", "BOTH"}:
                    existing = (
                        await self.postgresql_repository.get_by_order_id(
                            order_id
                        )
                    )
                else:
                    existing = (
                        await self.mongodb_repository.get_record_by_order_id(
                            order_id=order_id,
                            storage_location=storage_location,
                            version=initial_metadata.version,
                        )
                    )

                if existing is None:
                    raise RuntimeError(
                        f"Metadata exists for {order_id}, "
                        "but the corresponding record is missing."
                    )

                if existing.version != initial_metadata.version:
                    raise RuntimeError(
                        f"Record version mismatch for {order_id}: "
                        f"metadata={initial_metadata.version}, "
                        f"record={existing.version}."
                    )

                self._validate_immutable_ids(existing, record)

                if record.expected_version != initial_metadata.version:
                    raise ValueError(
                        f"Version conflict for order '{order_id}': "
                        f"expected={record.expected_version}, "
                        f"actual={initial_metadata.version}."
                    )

                changed_entities = self._get_changed_entities(
                    existing,
                    record,
                )

                affected_arguments = {
                    "order_id": order_id,
                    "customer_id": (
                        record.customer.customer_id
                        if "customer" in changed_entities
                        else None
                    ),
                    "store_id": (
                        record.store.store_id
                        if "store" in changed_entities
                        else None
                    ),
                    "sales_representative_id": (
                        record.sales_representative.sales_representative_id
                        if "sales_representative" in changed_entities
                        else None
                    ),
                    "product_id": (
                        record.product.product_id
                        if "product" in changed_entities
                        else None
                    ),
                }

                postgres_affected_ids = set(
                    await self.postgresql_repository.get_affected_order_ids(
                        **affected_arguments
                    )
                )

                mongo_affected_ids = set(
                    await self.mongodb_repository.get_affected_order_ids(
                        **affected_arguments
                    )
                )

                affected_ids = sorted(
                    postgres_affected_ids
                    | mongo_affected_ids
                    | {order_id}
                )

                locked_locations = (
                    await self.postgresql_repository.lock_storage_locations(
                        affected_ids
                    )
                )

                metadata_by_id = {
                    item.order_id: item
                    for item in locked_locations
                }

                locked_target = metadata_by_id.get(order_id)

                if locked_target is None:
                    raise RuntimeError(
                        f"Storage metadata for '{order_id}' disappeared."
                    )

                if locked_target.storage_location != storage_location:
                    raise RuntimeError(
                        f"Storage location changed for '{order_id}'."
                    )

                if locked_target.version != record.expected_version:
                    raise ValueError(
                        f"Version conflict for order '{order_id}': "
                        f"expected={record.expected_version}, "
                        f"actual={locked_target.version}."
                    )

                expected_postgres_ids = {
                    item.order_id
                    for item in locked_locations
                    if item.storage_location in {"POSTGRESQL", "BOTH"}
                }

                expected_mongo_ids = {
                    item.order_id
                    for item in locked_locations
                    if item.storage_location in {"MONGODB", "BOTH"}
                }

                if postgres_affected_ids != expected_postgres_ids:
                    raise RuntimeError(
                        "PostgreSQL affected records do not match "
                        "the storage metadata."
                    )

                if mongo_affected_ids != expected_mongo_ids:
                    raise RuntimeError(
                        "MongoDB affected documents do not match "
                        "the storage metadata."
                    )

                expected_versions = {
                    item.order_id: item.version
                    for item in locked_locations
                }

                mongo_documents = (
                    await self.mongodb_repository.get_documents_by_order_ids(
                        sorted(expected_mongo_ids)
                    )
                )

                self.mongodb_repository.validate_document_versions(
                    documents=mongo_documents,
                    expected_versions={
                        order_id: expected_versions[order_id]
                        for order_id in expected_mongo_ids
                    },
                )

                documents_by_id = {
                    document["_id"]: document
                    for document in mongo_documents
                }

                for affected_id in sorted(expected_mongo_ids):
                    metadata = metadata_by_id[affected_id]
                    snapshot = documents_by_id[affected_id]

                    snapshots[affected_id] = snapshot

                    if affected_id == order_id:
                        updated_record = RecordResponse.model_validate({
                            **record.model_dump(
                                exclude={"expected_version"}
                            ),
                            "storage_location": storage_location,
                            "version": metadata.version,
                        })
                    else:
                        mongo_record = from_mongodb_document(
                            document=snapshot,
                            storage_location=metadata.storage_location,
                            version=metadata.version,
                        )

                        updated_record = mongo_record.model_copy(
                            update=changed_entities
                        )

                    updated_document = to_mongodb_document(
                        updated_record,
                        version=metadata.version,
                    )

                    await self.mongodb_repository.replace_document_with_version(
                        document=updated_document,
                        expected_version=metadata.version,
                    )

                    modified_mongo_ids.append(affected_id)

                await self.postgresql_repository.update_shared_entities(
                    record=record,
                    existing=existing,
                )

                if storage_location in {"POSTGRESQL", "BOTH"}:
                    await self.postgresql_repository.update_order_data(
                        record
                    )

                await self.postgresql_repository.increment_storage_versions(
                    expected_versions
                )

        except Exception as exc:
            compensation_errors = []

            for modified_id in reversed(modified_mongo_ids):
                snapshot = snapshots[modified_id]
                expected_current_version = (
                    snapshot["_version"] + 1
                )

                try:
                    await self.mongodb_repository.restore_document_with_version(
                        snapshot=snapshot,
                        expected_current_version=expected_current_version,
                    )
                except Exception as compensation_error:
                    compensation_errors.append(
                        f"{modified_id}: {compensation_error}"
                    )

            if compensation_errors:
                raise RuntimeError(
                    "Distributed update failed and MongoDB compensation "
                    "was incomplete. Manual reconciliation is required. "
                    + "; ".join(compensation_errors)
                ) from exc

            raise

        return RecordResponse.model_validate({
            **record.model_dump(exclude={"expected_version"}),
            "storage_location": storage_location,
            "version": record.expected_version + 1,
        })

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
        filters: RecordFilters | None = None,
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
                filters=filters,
            )

            records_by_id.update({
                record.order.order_id: record
                for record in postgres_records
            })

        if source in {"ALL", "MONGODB"}:
            mongo_storage_locations = {
                item.order_id: (
                    item.storage_location,
                    item.version,
                )
                for item in metadata_records
                if (
                    item.storage_location == "MONGODB"
                    if source == "ALL"
                    else item.storage_location in {"MONGODB", "BOTH"}
                )
            }

            mongo_records = await self.mongodb_repository.get_all_records(
                storage_locations=mongo_storage_locations,
                limit=len(metadata_records),
                offset=0,
                filters=filters,
            )

            for record in mongo_records:
                records_by_id.setdefault(
                    record.order.order_id,
                    record,
                )

        matched_metadata = [
            item
            for item in metadata_records
            if item.order_id in records_by_id
        ]

        paginated_metadata = matched_metadata[offset:offset + limit]

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

    async def delete(
        self,
        order_id: str,
        expected_version: int,
    ) -> bool:
        if (
            not isinstance(expected_version, int)
            or isinstance(expected_version, bool)
            or expected_version < 1
        ):
            raise ValueError("Expected version must be a positive integer.")

        mongo_snapshot = None
        mongo_deleted = False

        try:
            async with self.postgresql_repository.session.begin():
                location = (
                    await self.postgresql_repository.lock_storage_location(
                        order_id
                    )
                )

                if location is None:
                    raise ValueError(
                        f"Order '{order_id}' does not exist."
                    )

                if location.version != expected_version:
                    raise ValueError(
                        "Version conflict: the record has been modified."
                    )

                storage_location = location.storage_location

                if storage_location not in (
                    "POSTGRESQL",
                    "MONGODB",
                    "BOTH",
                ):
                    raise ValueError(
                        f"Unsupported storage location: {storage_location}"
                    )

                if storage_location in ("MONGODB", "BOTH"):
                    mongo_snapshot = (
                        await self.mongodb_repository.get_by_order_id(
                            order_id
                        )
                    )

                    if mongo_snapshot is None:
                        raise ValueError(
                            f"MongoDB document '{order_id}' does not exist."
                        )

                    mongo_version = mongo_snapshot.get("_version")

                    if mongo_version != expected_version:
                        raise ValueError(
                            f"MongoDB version mismatch for '{order_id}': "
                            f"expected={expected_version}, "
                            f"actual={mongo_version}."
                        )

                    await self.mongodb_repository.delete_with_version(
                        order_id=order_id,
                        expected_version=expected_version,
                    )
                    mongo_deleted = True

                if storage_location in ("POSTGRESQL", "BOTH"):
                    await self.postgresql_repository.delete(
                        order_id=order_id,
                        expected_version=expected_version,
                    )
                else:
                    await self.postgresql_repository.delete_storage_location(
                        order_id=order_id,
                        expected_version=expected_version,
                    )

            return True

        except Exception as exc:
            if mongo_deleted and mongo_snapshot is not None:
                try:
                    await self.mongodb_repository.restore_deleted_document(
                        mongo_snapshot
                    )
                except Exception as compensation_error:
                    raise RuntimeError(
                        f"Deletion of '{order_id}' failed and MongoDB "
                        "compensation also failed. Manual reconciliation "
                        "is required."
                    ) from compensation_error

            raise
