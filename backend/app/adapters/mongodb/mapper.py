
from datetime import date, time
from decimal import Decimal

from bson.decimal128 import Decimal128

from app.loaders.seed_data import SeedRecord


def _convert_value(value):
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


def to_mongodb_document(record: SeedRecord) -> dict:
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
