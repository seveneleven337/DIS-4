from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator


class RecordFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str | None = None

    customer_id: str | None = None
    customer_name: str | None = None
    customer_segment: str | None = None

    product_id: str | None = None
    product_name: str | None = None
    product_category: str | None = None

    store_id: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None

    sales_representative_id: int | None = None

    promotion_code: str | None = None

    order_status: str | None = None
    sales_channel: str | None = None
    payment_method: str | None = None
    shipping_method: str | None = None

    order_date_from: date | None = None
    order_date_to: date | None = None

    has_return: bool | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if (
            self.order_date_from is not None
            and self.order_date_to is not None
            and self.order_date_from > self.order_date_to
        ):
            raise ValueError(
                "order_date_from cannot be later than order_date_to"
            )

        return self
