
from typing import Literal

from pydantic import BaseModel, ConfigDict

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
