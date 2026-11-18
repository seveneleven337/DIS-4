from bson import json_util

from app.adapters.mongodb.database import database
from app.adapters.postgresql.models import TransactionJournalDB
from app.repositories.mongodb import MongoDBRepository
from app.repositories.postgresql import PostgreSQLRepository
from app.repositories.transaction_journal import (
    TransactionJournalRepository,
)


class DistributedRecoveryService:
    """Recovers interrupted distributed CREATE and UPDATE operations."""

    def __init__(self):
        self.mongodb_repository = MongoDBRepository(database)
        self.transaction_journal = TransactionJournalRepository()

    async def _recover_create(
        self,
        session,
        operation: TransactionJournalDB,
    ) -> None:
        import json

        payload = json.loads(operation.payload)

        storage_location = payload.get("storage_location")
        operation_id = payload.get("operation_id")

        if storage_location not in {"POSTGRESQL", "MONGODB", "BOTH"}:
            operation.status = "FAILED"
            operation.last_error = (
                "Invalid storage_location in CREATE recovery payload."
            )
            return

        if operation_id != operation.operation_id:
            operation.status = "FAILED"
            operation.last_error = (
                "CREATE recovery operation ID does not match its journal ID."
            )
            return

        postgresql_repository = PostgreSQLRepository(session)

        metadata = await postgresql_repository.get_storage_location(
            operation.order_id
        )

        if metadata is not None:
            if metadata.storage_location != storage_location:
                operation.status = "FAILED"
                operation.last_error = (
                    "Storage location differs between journal and metadata."
                )
                return

            if storage_location in {"MONGODB", "BOTH"}:
                marker_cleared = (
                    await self.mongodb_repository.clear_creation_marker(
                        operation.order_id,
                        operation_id,
                    )
                )

                if not marker_cleared:
                    operation.status = "FAILED"
                    operation.last_error = (
                        "Committed CREATE has no matching MongoDB document "
                        "or its operation marker belongs to another operation."
                    )
                    return

            operation.status = "COMMITTED"
            operation.last_error = None
            return

        if operation.status == "DATABASE_COMMITTED":
            operation.status = "FAILED"
            operation.last_error = (
                "Journal says DATABASE_COMMITTED but PostgreSQL metadata "
                "is missing."
            )
            return

        if storage_location in {"MONGODB", "BOTH"}:
            document = await self.mongodb_repository.get_by_order_id(
                operation.order_id
            )

            if document is not None:
                if document.get("_operation_id") != operation_id:
                    operation.status = "FAILED"
                    operation.last_error = (
                        "Cannot compensate MongoDB document because its "
                        "operation marker is missing or belongs to another "
                        "operation."
                    )
                    return

                deleted = await self.mongodb_repository.delete_created(
                    operation.order_id,
                    operation_id,
                )

                if not deleted:
                    remaining = (
                        await self.mongodb_repository.get_by_order_id(
                            operation.order_id
                        )
                    )

                    if remaining is not None:
                        operation.status = "FAILED"
                        operation.last_error = (
                            "MongoDB CREATE compensation could not delete "
                            "the operation-owned document."
                        )
                        return

        operation.status = "COMPENSATED"
        operation.last_error = None

    async def _recover_update(
        self,
        session,
        operation: TransactionJournalDB,
    ) -> None:
        payload = json_util.loads(operation.payload)

        if payload.get("operation_id") != operation.operation_id:
            operation.status = "FAILED"
            operation.last_error = (
                "UPDATE recovery operation ID does not match its journal ID."
            )
            return

        affected_ids = payload.get("affected_ids")
        original_versions = payload.get("original_versions")
        storage_locations = payload.get("storage_locations")
        snapshots = payload.get("mongo_snapshots")

        if (
            not isinstance(affected_ids, list)
            or not affected_ids
            or not isinstance(original_versions, dict)
            or not isinstance(storage_locations, dict)
            or not isinstance(snapshots, list)
        ):
            operation.status = "FAILED"
            operation.last_error = "Invalid UPDATE recovery payload."
            return

        affected_ids = sorted(set(affected_ids))

        if (
            set(original_versions) != set(affected_ids)
            or set(storage_locations) != set(affected_ids)
        ):
            operation.status = "FAILED"
            operation.last_error = (
                "UPDATE recovery payload has inconsistent affected IDs."
            )
            return

        if operation.order_id not in affected_ids:
            operation.status = "FAILED"
            operation.last_error = (
                "UPDATE recovery payload does not include its target order."
            )
            return

        for item_id in affected_ids:
            version = original_versions.get(item_id)
            location = storage_locations.get(item_id)

            if (
                not isinstance(version, int)
                or isinstance(version, bool)
                or version < 1
                or location not in {"POSTGRESQL", "MONGODB", "BOTH"}
            ):
                operation.status = "FAILED"
                operation.last_error = (
                    f"Invalid original version or storage location for "
                    f"'{item_id}'."
                )
                return

        expected_mongo_ids = {
            item_id
            for item_id in affected_ids
            if storage_locations[item_id] in {"MONGODB", "BOTH"}
        }

        snapshots_by_id = {}

        for snapshot in snapshots:
            if not isinstance(snapshot, dict):
                operation.status = "FAILED"
                operation.last_error = (
                    "UPDATE recovery snapshot is not a document."
                )
                return

            snapshot_id = snapshot.get("_id")

            if (
                not isinstance(snapshot_id, str)
                or snapshot_id in snapshots_by_id
            ):
                operation.status = "FAILED"
                operation.last_error = (
                    "UPDATE recovery payload contains invalid or duplicate "
                    "MongoDB snapshots."
                )
                return

            snapshots_by_id[snapshot_id] = snapshot

        if set(snapshots_by_id) != expected_mongo_ids:
            operation.status = "FAILED"
            operation.last_error = (
                "UPDATE recovery snapshots do not match MongoDB storage "
                "metadata."
            )
            return

        for item_id, snapshot in snapshots_by_id.items():
            if snapshot.get("_version") != original_versions[item_id]:
                operation.status = "FAILED"
                operation.last_error = (
                    f"Snapshot version does not match original version "
                    f"for '{item_id}'."
                )
                return

        postgresql_repository = PostgreSQLRepository(session)

        try:
            locations = await postgresql_repository.lock_storage_locations(
                affected_ids
            )
        except Exception as exc:
            operation.status = "FAILED"
            operation.last_error = (
                f"Could not lock all UPDATE metadata rows: {exc}"
            )
            return

        metadata_by_id = {
            item.order_id: item
            for item in locations
        }

        if set(metadata_by_id) != set(affected_ids):
            operation.status = "FAILED"
            operation.last_error = (
                "UPDATE metadata rows do not match the journal affected IDs."
            )
            return

        old_state = True
        new_state = True

        for item_id in affected_ids:
            metadata = metadata_by_id[item_id]

            if metadata.storage_location != storage_locations[item_id]:
                operation.status = "FAILED"
                operation.last_error = (
                    f"Storage location changed for '{item_id}' during "
                    "UPDATE recovery."
                )
                return

            old_version = original_versions[item_id]

            if metadata.version != old_version:
                old_state = False

            if metadata.version != old_version + 1:
                new_state = False

        if old_state:
            if operation.status == "DATABASE_COMMITTED":
                operation.status = "FAILED"
                operation.last_error = (
                    "Journal says DATABASE_COMMITTED but all PostgreSQL "
                    "metadata versions are still unchanged."
                )
                return

            # PostgreSQL rolled back. Restore every Mongo document that
            # reached old_version + 1; leave untouched documents as-is.
            try:
                for item_id in sorted(expected_mongo_ids):
                    snapshot = snapshots_by_id[item_id]
                    current = (
                        await self.mongodb_repository.get_by_order_id(
                            item_id
                        )
                    )

                    if current is None:
                        raise RuntimeError(
                            f"MongoDB document '{item_id}' is missing."
                        )

                    old_version = original_versions[item_id]
                    current_version = current.get("_version")

                    if current_version == old_version:
                        continue

                    if current_version != old_version + 1:
                        raise RuntimeError(
                            f"Unexpected MongoDB version for '{item_id}': "
                            f"expected {old_version} or {old_version + 1}, "
                            f"found {current_version}."
                        )

                    await self.mongodb_repository.restore_document_with_version(
                        snapshot=snapshot,
                        expected_current_version=old_version + 1,
                    )

            except Exception as exc:
                operation.status = "FAILED"
                operation.last_error = (
                    f"UPDATE rollback recovery failed: {exc}"
                )
                return

            operation.status = "COMPENSATED"
            operation.last_error = None
            return

        if new_state:
            # PostgreSQL committed. MongoDB must also contain every new
            # version before the operation can be finalized.
            try:
                for item_id in sorted(expected_mongo_ids):
                    document = (
                        await self.mongodb_repository.get_by_order_id(
                            item_id
                        )
                    )

                    if document is None:
                        raise RuntimeError(
                            f"MongoDB document '{item_id}' is missing."
                        )

                    expected_version = original_versions[item_id] + 1

                    if document.get("_version") != expected_version:
                        raise RuntimeError(
                            f"MongoDB version mismatch for '{item_id}': "
                            f"expected={expected_version}, "
                            f"actual={document.get('_version')}."
                        )

            except Exception as exc:
                operation.status = "FAILED"
                operation.last_error = (
                    f"Post-commit MongoDB validation failed: {exc}"
                )
                return

            operation.status = "COMMITTED"
            operation.last_error = None
            return

        operation.status = "FAILED"
        operation.last_error = (
            "UPDATE recovery found mixed PostgreSQL metadata versions. "
            "No automatic compensation was attempted."
        )

    async def _recover_delete(
        self,
        session,
        operation: TransactionJournalDB,
    ) -> None:
        payload = json_util.loads(operation.payload)

        if payload.get("operation_id") != operation.operation_id:
            operation.status = "FAILED"
            operation.last_error = (
                "DELETE recovery operation ID does not match its journal ID."
            )
            return

        if payload.get("order_id") != operation.order_id:
            operation.status = "FAILED"
            operation.last_error = (
                "DELETE recovery order ID does not match its journal row."
            )
            return

        storage_location = payload.get("storage_location")
        original_version = payload.get("original_version")
        snapshot = payload.get("mongo_snapshot")

        if storage_location not in {"POSTGRESQL", "MONGODB", "BOTH"}:
            operation.status = "FAILED"
            operation.last_error = (
                "Invalid DELETE storage location in recovery payload."
            )
            return

        if (
            not isinstance(original_version, int)
            or isinstance(original_version, bool)
            or original_version < 1
        ):
            operation.status = "FAILED"
            operation.last_error = (
                "Invalid DELETE original version in recovery payload."
            )
            return

        requires_mongo = storage_location in {"MONGODB", "BOTH"}

        if requires_mongo:
            if (
                not isinstance(snapshot, dict)
                or snapshot.get("_id") != operation.order_id
                or snapshot.get("_version") != original_version
            ):
                operation.status = "FAILED"
                operation.last_error = (
                    "DELETE MongoDB snapshot is missing or inconsistent."
                )
                return
        elif snapshot is not None:
            operation.status = "FAILED"
            operation.last_error = (
                "PostgreSQL-only DELETE unexpectedly contains a MongoDB "
                "snapshot."
            )
            return

        postgresql_repository = PostgreSQLRepository(session)

        try:
            metadata = await postgresql_repository.lock_storage_location(
                operation.order_id
            )
        except Exception as exc:
            operation.status = "FAILED"
            operation.last_error = (
                f"Could not lock DELETE metadata: {exc}"
            )
            return

        if metadata is None:
            # Metadata is deleted in the same PostgreSQL transaction as
            # DATABASE_COMMITTED. Its absence is the commit marker.
            if operation.status != "DATABASE_COMMITTED":
                operation.status = "FAILED"
                operation.last_error = (
                    "DELETE metadata is absent but the journal does not "
                    "say DATABASE_COMMITTED."
                )
                return

            if requires_mongo:
                document = await self.mongodb_repository.get_by_order_id(
                    operation.order_id
                )

                if document is not None:
                    operation.status = "FAILED"
                    operation.last_error = (
                        "DELETE metadata is absent but a MongoDB document "
                        "still exists. Automatic deletion was skipped."
                    )
                    return

            operation.status = "COMMITTED"
            operation.last_error = None
            return

        # Metadata still exists: the PostgreSQL DELETE did not commit.
        if operation.status == "DATABASE_COMMITTED":
            operation.status = "FAILED"
            operation.last_error = (
                "Journal says DATABASE_COMMITTED but DELETE metadata "
                "still exists."
            )
            return

        if (
            metadata.storage_location != storage_location
            or metadata.version != original_version
        ):
            operation.status = "FAILED"
            operation.last_error = (
                "DELETE metadata differs from its original location or "
                "version. Automatic restoration was skipped."
            )
            return

        if requires_mongo:
            document = await self.mongodb_repository.get_by_order_id(
                operation.order_id
            )

            if document is None:
                try:
                    await self.mongodb_repository.restore_deleted_document(
                        snapshot
                    )
                except Exception as exc:
                    operation.status = "FAILED"
                    operation.last_error = (
                        f"DELETE snapshot restoration failed: {exc}"
                    )
                    return
            else:
                # Do not overwrite a document that may belong to another
                # operation or a concurrent insertion.
                if json_util.dumps(
                    document,
                    sort_keys=True,
                ) != json_util.dumps(
                    snapshot,
                    sort_keys=True,
                ):
                    operation.status = "FAILED"
                    operation.last_error = (
                        "MongoDB document exists but differs from the "
                        "DELETE snapshot. Automatic restoration was skipped."
                    )
                    return

        operation.status = "COMPENSATED"
        operation.last_error = None

    async def recover_pending_operations(
        self,
        batch_size: int = 10,
    ) -> int:
        """Recover all unfinished operations before the API accepts traffic."""
        recovered_count = 0

        while True:
            async with self.transaction_journal.claim_recovery_batch(
                limit=batch_size
            ) as (session, operations):
                if not operations:
                    break

                for operation in operations:
                    if operation.operation_type == "CREATE":
                        await self._recover_create(session, operation)
                    elif operation.operation_type == "UPDATE":
                        await self._recover_update(session, operation)
                    elif operation.operation_type == "DELETE":
                        await self._recover_delete(session, operation)
                    else:
                        operation.status = "FAILED"
                        operation.last_error = (
                            "Recovery for operation type "
                            f"{operation.operation_type} is not implemented."
                        )

                    recovered_count += 1

        return recovered_count
