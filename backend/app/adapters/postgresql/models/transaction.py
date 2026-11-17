from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgresql.models.base import Base


class TransactionDB(Base):
    __tablename__ = "transactions"

    __table_args__ = (
        UniqueConstraint(
            "order_id",
            name="uq_transactions_order_id",
        ),
        CheckConstraint(
            "customer_age >= 0",
            name="ck_transactions_customer_age",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_transactions_quantity",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_transactions_unit_price",
        ),
        CheckConstraint(
            "discount_percentage >= 0 "
            "AND discount_percentage <= 100",
            name="ck_transactions_discount_percentage",
        ),
        CheckConstraint(
            "sales_amount >= 0",
            name="ck_transactions_sales_amount",
        ),
        CheckConstraint(
            "cost_amount >= 0",
            name="ck_transactions_cost_amount",
        ),
        CheckConstraint(
            "inventory_level >= 0",
            name="ck_transactions_inventory_level",
        ),
    )

    transaction_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    order_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("orders.order_id"),
        nullable=False,
    )
    product_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("products.product_id"),
        nullable=False,
    )

    customer_age: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )

    sales_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    cost_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    profit: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    inventory_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )