from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgresql.models.base import Base


class PromotionDB(Base):
    __tablename__ = "promotions"

    promotion_code: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )