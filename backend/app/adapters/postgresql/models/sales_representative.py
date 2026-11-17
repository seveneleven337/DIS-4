from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgresql.models.base import Base


class SalesRepresentativeDB(Base):
    __tablename__ = "sales_representatives"

    sales_representative_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    sales_representative_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )