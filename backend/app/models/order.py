from datetime import date, time
from decimal import Decimal

from pydantic import Field

from app.models.base import LogicalModel


class Order(LogicalModel):
    order_id: str = Field(min_length=1, max_length=50)

    customer_id: str = Field(min_length=1, max_length=50)
    store_id: str = Field(min_length=1, max_length=50)
    sales_representative_id: int = Field(gt=0)

    promotion_code: str | None = Field(default=None, max_length=100)

    order_date: date
    order_time: time

    sales_channel: str = Field(min_length=1, max_length=100)
    payment_method: str = Field(min_length=1, max_length=100)
    order_status: str = Field(min_length=1, max_length=100)
    shipping_method: str = Field(min_length=1, max_length=100)

    delivery_days: int | None = Field(default=None, ge=0)
    customer_rating: Decimal | None = Field(
        default=None,
        ge=Decimal("1"),
        le=Decimal("5"),
    )
