from pymongo import ASCENDING

from app.adapters.mongodb.database import database


async def create_mongodb_schema() -> None:
    collection_names = await database.list_collection_names()

    if "orders" not in collection_names:
        await database.create_collection("orders")

    orders = database["orders"]

    await orders.create_index(
        [("transaction.transaction_id", ASCENDING)],
        unique=True,
        name="uq_orders_transaction_id",
    )

    await orders.create_index(
        [("customer.customer_id", ASCENDING)],
        name="ix_orders_customer_id",
    )

    await orders.create_index(
        [("store.store_id", ASCENDING)],
        name="ix_orders_store_id",
    )

    await orders.create_index(
        [("sales_representative.sales_representative_id", ASCENDING)],
        name="ix_orders_sales_representative_id",
    )

    await orders.create_index(
        [("transaction.product.product_id", ASCENDING)],
        name="ix_orders_product_id",
    )