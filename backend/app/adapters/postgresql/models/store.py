from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgresql.models.base import Base


class StoreDB(Base):
    __tablename__ = "stores"

    store_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )
    store_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    region: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )