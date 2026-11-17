from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgresql.models.base import Base


class CustomerDB(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )
    customer_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    customer_gender: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    customer_segment: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )