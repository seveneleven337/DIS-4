import json

from app.adapters.mongodb.database import database
from app.adapters.postgresql.models import TransactionJournalDB
from app.repositories.mongodb import MongoDBRepository
from app.repositories.postgresql import PostgreSQLRepository
from app.repositories.transaction_journal import (
    TransactionJournalRepository,
)


class DistributedRecoveryService:
    """Recovers interrupted distributed CREATE operations."""

    def __init__(self):
        self.mongodb_repository = MongoDBRepository(database)
        self.transaction_journal = TransactionJournalRepository()

    async def _recover_create(
        self,
        session,
        operation: TransactionJournalDB,
    ) -> None:
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

            # PostgreSQL metadata is the commit marker. Finalize even if
            # the process stopped before updating the journal status.
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
                    if operation.operation_type != "CREATE":
                        operation.status = "FAILED"
                        operation.last_error = (
                            "Recovery for operation type "
                            f"{operation.operation_type} is not implemented."
                        )
                    else:
                        await self._recover_create(session, operation)

                    recovered_count += 1

        return recovered_count
