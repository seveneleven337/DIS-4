from decimal import Decimal

from pydantic import Field

from app.models.base import LogicalModel


class Transaction(LogicalModel):
    transaction_id: str = Field(min_length=1, max_length=50)
    order_id: str = Field(min_length=1, max_length=50)
    product_id: str = Field(min_length=1, max_length=50)

    customer_age: int | None = Field(default=None, ge=0)

    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=Decimal("0"))

    discount_percentage: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        le=Decimal("100"),
    )

    sales_amount: Decimal = Field(ge=Decimal("0"))
    cost_amount: Decimal = Field(ge=Decimal("0"))
    profit: Decimal | None = None

    inventory_level: int | None = Field(default=None, ge=0)
