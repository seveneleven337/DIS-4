from dataclasses import dataclass
from datetime import date, time, timedelta
from decimal import Decimal
from typing import Literal

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


@dataclass(frozen=True)
class SeedRecord:
    storage_location: StorageLocation
    customer: Customer
    store: Store
    sales_representative: SalesRepresentative
    product: Product
    promotion: Promotion | None
    order: Order
    transaction: Transaction
    return_record: Return | None


def build_seed_records() -> list[SeedRecord]:
    records: list[SeedRecord] = []

    genders = ["Female", "Male", "Other"]
    segments = ["Consumer", "Corporate", "Home Office"]
    categories = ["Electronics", "Home", "Sports", "Books", "Clothing"]
    subcategories = [
        "Accessories",
        "Furniture",
        "Equipment",
        "Literature",
        "Apparel",
    ]

    for index in range(1, 31):
        customer_number = ((index - 1) % 10) + 1
        store_number = ((index - 1) % 5) + 1
        representative_number = ((index - 1) % 5) + 1
        product_number = ((index - 1) % 10) + 1

        customer = Customer(
            customer_id=f"CUST-{customer_number:03d}",
            customer_name=f"Test Customer {customer_number:03d}",
            customer_gender=genders[(customer_number - 1) % len(genders)],
            customer_segment=segments[
                (customer_number - 1) % len(segments)
            ],
        )

        store = Store(
            store_id=f"STORE-{store_number:03d}",
            store_name=f"Test Store {store_number:03d}",
            country="Finland",
            region="Uusimaa",
            city="Helsinki",
        )

        representative = SalesRepresentative(
            sales_representative_id=representative_number,
            sales_representative_name=(
                f"Test Representative {representative_number:03d}"
            ),
        )

        product = Product(
            product_id=f"PROD-{product_number:03d}",
            product_name=f"Test Product {product_number:03d}",
            product_category=categories[
                (product_number - 1) % len(categories)
            ],
            product_subcategory=subcategories[
                (product_number - 1) % len(subcategories)
            ],
        )

        promotion = None

        if index % 3 != 0:
            promotion_number = ((index - 1) % 4) + 1
            promotion = Promotion(
                promotion_code=f"PROMO-{promotion_number:03d}",
            )

        order_id = f"ORD-{index:03d}"

        order = Order(
            order_id=order_id,
            customer_id=customer.customer_id,
            store_id=store.store_id,
            sales_representative_id=representative.sales_representative_id,
            promotion_code=(
                promotion.promotion_code if promotion else None
            ),
            order_date=date(2026, 1, 1) + timedelta(days=index - 1),
            order_time=time(
                hour=9 + (index % 8),
                minute=(index * 7) % 60,
            ),
            sales_channel="Online" if index % 2 else "In-store",
            payment_method="Card" if index % 2 else "Cash",
            order_status="Completed",
            shipping_method="Standard",
            delivery_days=None if index % 7 == 0 else index % 6,
            customer_rating=(
                None
                if index % 4 == 0
                else Decimal(str((index % 5) + 1))
            ),
        )

        transaction = Transaction(
            transaction_id=f"TX-{index:03d}",
            order_id=order_id,
            product_id=product.product_id,
            customer_age=20 + (index % 40),
            quantity=1 + (index % 4),
            unit_price=Decimal(f"{20 + index}.00"),
            discount_percentage=(
                Decimal("10.00") if index % 2 == 0 else Decimal("0.00")
            ),
            sales_amount=Decimal(f"{50 + index}.00"),
            cost_amount=Decimal(f"{30 + index}.00"),
            profit=(
                None
                if index % 7 == 0
                else Decimal(f"{12 + index}.00")
            ),
            inventory_level=(
                None if index % 6 == 0 else 100 + index
            ),
        )

        return_record = None

        if index % 5 == 0:
            return_record = Return(
                order_id=order_id,
                return_reason="Test return reason",
            )

        if index <= 10:
            storage_location: StorageLocation = "POSTGRESQL"
        elif index <= 20:
            storage_location = "MONGODB"
        else:
            storage_location = "BOTH"

        records.append(
            SeedRecord(
                storage_location=storage_location,
                customer=customer,
                store=store,
                sales_representative=representative,
                product=product,
                promotion=promotion,
                order=order,
                transaction=transaction,
                return_record=return_record,
            )
        )

    return records