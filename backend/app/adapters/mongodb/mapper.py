from datetime import date, time
from decimal import Decimal

from bson.decimal128 import Decimal128

from app.loaders.seed_data import SeedRecord
from app.schemas.record import RecordResponse


def _convert_value(value):
    """Convert Python values into MongoDB-compatible values."""
    if isinstance(value, Decimal):
        return Decimal128(value)

    if isinstance(value, (date, time)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _convert_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_convert_value(item) for item in value]

    return value


def _restore_value(value):
    """Convert MongoDB values back into Python values."""
    if isinstance(value, Decimal128):
        return value.to_decimal()

    if isinstance(value, dict):
        return {
            key: _restore_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_restore_value(item) for item in value]

    return value


def to_mongodb_document(
    record: SeedRecord | RecordResponse,
    version: int | None = None,
) -> dict:
    """Convert a logical record into a MongoDB document."""
    if version is None:
        version = getattr(record, "version", 1)

    order = record.order.model_dump(
        mode="python",
        exclude={
            "order_id",
            "customer_id",
            "store_id",
            "sales_representative_id",
            "promotion_code",
        },
    )

    transaction = record.transaction.model_dump(
        mode="python",
        exclude={
            "order_id",
            "product_id",
        },
    )

    document = {
        "_id": record.order.order_id,
        "_version": version,
        "customer": record.customer.model_dump(mode="python"),
        "store": record.store.model_dump(mode="python"),
        "sales_representative": (
            record.sales_representative.model_dump(mode="python")
        ),
        **order,
        "transaction": {
            **transaction,
            "product": record.product.model_dump(mode="python"),
        },
    }

    if record.promotion is not None:
        document["promotion"] = (
            record.promotion.model_dump(mode="python")
        )

    if record.return_record is not None:
        document["return"] = (
            record.return_record.model_dump(mode="python")
        )

    return _convert_value(document)


def from_mongodb_document(
    document: dict,
    storage_location: str,
    version: int,
) -> RecordResponse:
    """Convert a MongoDB document into the shared logical model."""
    document = _restore_value(document)

    order_id = document["_id"]

    customer = document["customer"]
    store = document["store"]
    representative = document["sales_representative"]

    transaction_document = document["transaction"]
    product = transaction_document["product"]

    promotion = document.get("promotion")

    order = {
        key: value
        for key, value in document.items()
        if key not in {
            "_id",
            "_version",
            "customer",
            "store",
            "sales_representative",
            "transaction",
            "promotion",
            "return",
        }
    }

    order.update({
        "order_id": order_id,
        "customer_id": customer["customer_id"],
        "store_id": store["store_id"],
        "sales_representative_id": (
            representative["sales_representative_id"]
        ),
        "promotion_code": (
            promotion["promotion_code"]
            if promotion is not None
            else None
        ),
    })

    transaction = {
        key: value
        for key, value in transaction_document.items()
        if key != "product"
    }

    transaction.update({
        "order_id": order_id,
        "product_id": product["product_id"],
    })

    record_data = {
        "customer": customer,
        "store": store,
        "sales_representative": representative,
        "product": product,
        "promotion": promotion,
        "order": order,
        "transaction": transaction,
        "return_record": document.get("return"),
        "storage_location": storage_location,
        "version": version,
    }

    return RecordResponse.model_validate(record_data)
