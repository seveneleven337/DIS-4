from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.adapters.postgresql.database import async_session_factory
from app.adapters.postgresql.models import (
    CustomerDB,
    OrderDB,
    ProductDB,
    PromotionDB,
    RecordLocationDB,
    ReturnDB,
    SalesRepresentativeDB,
    StoreDB,
    TransactionDB,
)
from app.loaders.seed_data import SeedRecord, build_seed_records


def _unique_models(
    records: list[SeedRecord],
    attribute: str,
    key_attribute: str,
) -> list[dict]:
    unique: dict[object, dict] = {}

    for record in records:
        model = getattr(record, attribute)

        if model is None:
            continue

        key = getattr(model, key_attribute)
        unique.setdefault(key, model.model_dump())

    return list(unique.values())


async def _insert_if_missing(
    session,
    model,
    values: list[dict],
) -> None:
    if not values:
        return

    statement = (
        pg_insert(model)
        .values(values)
        .on_conflict_do_nothing()
    )

    await session.execute(statement)


async def seed_postgresql() -> None:
    records = [
        record
        for record in build_seed_records()
        if record.storage_location in ("POSTGRESQL", "BOTH")
    ]

    customers = _unique_models(records, "customer", "customer_id")
    stores = _unique_models(records, "store", "store_id")
    representatives = _unique_models(
        records,
        "sales_representative",
        "sales_representative_id",
    )
    promotions = _unique_models(records, "promotion", "promotion_code")
    products = _unique_models(records, "product", "product_id")
    orders = _unique_models(records, "order", "order_id")
    transactions = _unique_models(
        records,
        "transaction",
        "transaction_id",
    )
    returns = _unique_models(records, "return_record", "order_id")

    locations = [
        {
            "order_id": record.order.order_id,
            "storage_location": record.storage_location,
            "version": 1,
        }
        for record in build_seed_records()
    ]

    async with async_session_factory() as session:
        async with session.begin():
            # Insert referenced entities before their dependent records.
            await _insert_if_missing(session, CustomerDB, customers)
            await _insert_if_missing(session, StoreDB, stores)
            await _insert_if_missing(
                session,
                SalesRepresentativeDB,
                representatives,
            )
            await _insert_if_missing(session, PromotionDB, promotions)
            await _insert_if_missing(session, ProductDB, products)

            # Insert orders before transactions and returns.
            await _insert_if_missing(session, OrderDB, orders)
            await _insert_if_missing(
                session,
                TransactionDB,
                transactions,
            )
            await _insert_if_missing(session, ReturnDB, returns)

            # Preserve explicit seed IDs while keeping future generated IDs safe.
            await session.execute(
                text(
                    """
                    SELECT setval(
                        pg_get_serial_sequence(
                            'sales_representatives',
                            'sales_representative_id'
                        ),
                        COALESCE(
                            MAX(sales_representative_id),
                            1
                        ),
                        MAX(sales_representative_id) IS NOT NULL
                    )
                    FROM sales_representatives
                    """
                )
            )

            # Track the storage location of every logical record.
            await _insert_if_missing(
                session,
                RecordLocationDB,
                locations,
            )