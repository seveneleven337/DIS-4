from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.models import (
    Customer,
    Order,
    Product,
    Promotion,
    Return,
    SalesRepresentative,
    Store,
    Transaction,
)


StorageLocation = Literal["POSTGRESQL", "MONGODB", "BOTH"]


class RecordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer: Customer
    store: Store
    sales_representative: SalesRepresentative
    product: Product
    promotion: Promotion | None
    order: Order
    transaction: Transaction
    return_record: Return | None

    storage_location: StorageLocation

    @model_validator(mode="after")
    def validate_relationships(self):
        if self.order.customer_id != self.customer.customer_id:
            raise ValueError(
                "Order customer_id must match the Customer customer_id."
            )

        if self.order.store_id != self.store.store_id:
            raise ValueError(
                "Order store_id must match the Store store_id."
            )

        if (
            self.order.sales_representative_id
            != self.sales_representative.sales_representative_id
        ):
            raise ValueError(
                "Order sales_representative_id must match "
                "the SalesRepresentative ID."
            )

        if self.transaction.product_id != self.product.product_id:
            raise ValueError(
                "Transaction product_id must match the Product product_id."
            )

        if self.order.order_id != self.transaction.order_id:
            raise ValueError(
                "Order ID and Transaction order_id must match."
            )

        if self.promotion is None:
            if self.order.promotion_code is not None:
                raise ValueError(
                    "Order promotion_code must be null "
                    "when no Promotion is provided."
                )
        elif self.order.promotion_code != self.promotion.promotion_code:
            raise ValueError(
                "Order promotion_code must match the Promotion code."
            )

        if (
            self.return_record is not None
            and self.return_record.order_id != self.order.order_id
        ):
            raise ValueError(
                "Return order_id must match the Order ID."
            )

        return self


class RecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer: Customer
    store: Store
    sales_representative: SalesRepresentative
    product: Product
    promotion: Promotion | None
    order: Order
    transaction: Transaction
    return_record: Return | None

    storage_location: StorageLocation
    version: int
