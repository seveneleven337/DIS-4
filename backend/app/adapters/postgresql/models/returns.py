from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgresql.models.base import Base


class ReturnDB(Base):
    __tablename__ = "returns"

    order_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("orders.order_id"),
        primary_key=True,
    )
    return_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )