from datetime import date, time
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgresql.models.base import Base


class OrderDB(Base):
    __tablename__ = "orders"

    __table_args__ = (
        CheckConstraint(
            "delivery_days >= 0",
            name="ck_orders_delivery_days",
        ),
        CheckConstraint(
            "customer_rating >= 1 AND customer_rating <= 5",
            name="ck_orders_customer_rating",
        ),
    )

    order_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    customer_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("customers.customer_id"),
        nullable=False,
    )
    store_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("stores.store_id"),
        nullable=False,
    )
    sales_representative_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "sales_representatives.sales_representative_id"
        ),
        nullable=False,
    )
    promotion_code: Mapped[str | None] = mapped_column(
        String(100),
        ForeignKey("promotions.promotion_code"),
        nullable=True,
    )

    order_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    order_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    sales_channel: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    payment_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    order_status: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    shipping_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    delivery_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    customer_rating: Mapped[Decimal | None] = mapped_column(
        Numeric(2, 1),
        nullable=True,
    )