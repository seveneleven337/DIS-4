from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgresql.models.base import Base


class ProductDB(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )
    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    product_category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    product_subcategory: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )