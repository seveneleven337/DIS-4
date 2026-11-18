from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgresql.database import async_session_factory
from app.adapters.postgresql.models import TransactionJournalDB


class TransactionJournalRepository:
    """Persists distributed-operation state independently of CRUD sessions."""

    ALLOWED_TRANSITIONS = {
        "PENDING": {
            "DATABASE_COMMITTED",
            "COMPENSATING",
            "FAILED",
        },
        "DATABASE_COMMITTED": {
            "COMMITTED",
            "FAILED",
        },
        "COMPENSATING": {
            "COMPENSATED",
            "FAILED",
        },
        "COMMITTED": set(),
        "COMPENSATED": set(),
        "FAILED": set(),
    }

    async def create_operation(
        self,
        operation_id: str,
        operation_type: str,
        order_id: str,
        payload: str,
    ) -> None:
        """Durably register an operation before modifying either database."""
        async with async_session_factory() as session:
            async with session.begin():
                session.add(
                    TransactionJournalDB(
                        operation_id=operation_id,
                        operation_type=operation_type,
                        order_id=order_id,
                        status="PENDING",
                        payload=payload,
                    )
                )

    async def update_payload(
        self,
        operation_id: str,
        payload: str,
    ) -> None:
        """Persist recovery data before the first MongoDB write."""
        async with async_session_factory() as session:
            async with session.begin():
                statement = (
                    select(TransactionJournalDB)
                    .where(
                        TransactionJournalDB.operation_id == operation_id
                    )
                    .with_for_update()
                )

                operation = await session.scalar(statement)

                if operation is None:
                    raise ValueError(
                        f"Journal operation not found: {operation_id}"
                    )

                if operation.status != "PENDING":
                    raise ValueError(
                        "Recovery payload can only be updated "
                        "while the operation is PENDING."
                    )

                operation.payload = payload

    async def transition(
        self,
        operation_id: str,
        new_status: str,
        error: str | None = None,
    ) -> None:
        """Change an operation state while enforcing valid transitions."""
        async with async_session_factory() as session:
            async with session.begin():
                statement = (
                    select(TransactionJournalDB)
                    .where(
                        TransactionJournalDB.operation_id == operation_id
                    )
                    .with_for_update()
                )

                operation = await session.scalar(statement)

                if operation is None:
                    raise ValueError(
                        f"Journal operation not found: {operation_id}"
                    )

                allowed = self.ALLOWED_TRANSITIONS.get(
                    operation.status
                )

                if allowed is None or new_status not in allowed:
                    raise ValueError(
                        f"Invalid journal transition: "
                        f"{operation.status} -> {new_status}"
                    )

                operation.status = new_status
                operation.last_error = error

    async def mark_database_committed(
        self,
        session: AsyncSession,
        operation_id: str,
    ) -> None:
        """
        Mark the operation inside the CRUD PostgreSQL transaction.

        The journal state and the PostgreSQL data changes therefore commit
        or roll back together.
        """
        statement = (
            select(TransactionJournalDB)
            .where(
                TransactionJournalDB.operation_id == operation_id
            )
            .with_for_update()
        )

        operation = await session.scalar(statement)

        if operation is None:
            raise ValueError(
                f"Journal operation not found: {operation_id}"
            )

        if operation.status != "PENDING":
            raise ValueError(
                "Only PENDING operations can become "
                "DATABASE_COMMITTED."
            )

        operation.status = "DATABASE_COMMITTED"
        operation.last_error = None

    @asynccontextmanager
    async def claim_recovery_batch(
        self,
        limit: int = 10,
    ) -> AsyncIterator[list[TransactionJournalDB]]:
        """
        Lock a batch of unfinished operations for one recovery worker.

        Row locks remain held until the caller finishes processing the
        batch and the transaction commits.
        """
        if limit < 1:
            raise ValueError("Recovery batch limit must be positive.")

        async with async_session_factory() as session:
            async with session.begin():
                statement = (
                    select(TransactionJournalDB)
                    .where(
                        TransactionJournalDB.status.in_(
                            [
                                "PENDING",
                                "DATABASE_COMMITTED",
                                "COMPENSATING",
                            ]
                        )
                    )
                    .order_by(
                        TransactionJournalDB.created_at,
                        TransactionJournalDB.operation_id,
                    )
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )

                result = await session.scalars(statement)
                operations = list(result.all())

                for operation in operations:
                    operation.attempts += 1

                yield operations
