from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgresql.models.base import Base


class TransactionJournalDB(Base):
    __tablename__ = "transaction_journal"

    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('CREATE', 'UPDATE', 'DELETE')",
            name="ck_transaction_journal_operation_type",
        ),
        CheckConstraint(
            "status IN ("
            "'PENDING', "
            "'DATABASE_COMMITTED', "
            "'COMMITTED', "
            "'COMPENSATING', "
            "'COMPENSATED', "
            "'FAILED'"
            ")",
            name="ck_transaction_journal_status",
        ),
        CheckConstraint(
            "attempts >= 0",
            name="ck_transaction_journal_attempts",
        ),
        Index(
            "ix_transaction_journal_status_created_at",
            "status",
            "created_at",
        ),
    )

    operation_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    operation_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    order_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )

    payload: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
