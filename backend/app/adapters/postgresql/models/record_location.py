from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgresql.models.base import Base


class RecordLocationDB(Base):
    __tablename__ = "record_locations"

    __table_args__ = (
        CheckConstraint(
            "storage_location IN ('POSTGRESQL', 'MONGODB', 'BOTH')",
            name="ck_record_locations_storage_location",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_record_locations_version",
        ),
    )

    order_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    storage_location: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )