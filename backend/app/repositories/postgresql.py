
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.schemas.record import RecordResponse


class PostgreSQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _build_query(self):
        return (
            select(
                CustomerDB,
                StoreDB,
                SalesRepresentativeDB,
                PromotionDB,
                OrderDB,
                TransactionDB,
                ProductDB,
                ReturnDB,
                RecordLocationDB,
            )
            .select_from(OrderDB)
            .join(
                CustomerDB,
                OrderDB.customer_id == CustomerDB.customer_id,
            )
            .join(
                StoreDB,
                OrderDB.store_id == StoreDB.store_id,
            )
            .join(
                SalesRepresentativeDB,
                OrderDB.sales_representative_id
                == SalesRepresentativeDB.sales_representative_id,
            )
            .outerjoin(
                PromotionDB,
                OrderDB.promotion_code == PromotionDB.promotion_code,
            )
            .join(
                TransactionDB,
                OrderDB.order_id == TransactionDB.order_id,
            )
            .join(
                ProductDB,
                TransactionDB.product_id == ProductDB.product_id,
            )
            .outerjoin(
                ReturnDB,
                OrderDB.order_id == ReturnDB.order_id,
            )
            .join(
                RecordLocationDB,
                OrderDB.order_id == RecordLocationDB.order_id,
            )
            .where(
                RecordLocationDB.storage_location.in_(
                    ["POSTGRESQL", "BOTH"]
                )
            )
        )

    def _to_response(self, row) -> RecordResponse:
        (
            customer,
            store,
            representative,
            promotion,
            order,
            transaction,
            product,
            return_record,
            location,
        ) = row

        return RecordResponse(
            customer=Customer.model_validate(
                customer,
                from_attributes=True,
            ),
            store=Store.model_validate(
                store,
                from_attributes=True,
            ),
            sales_representative=SalesRepresentative.model_validate(
                representative,
                from_attributes=True,
            ),
            product=Product.model_validate(
                product,
                from_attributes=True,
            ),
            promotion=(
                Promotion.model_validate(
                    promotion,
                    from_attributes=True,
                )
                if promotion is not None
                else None
            ),
            order=Order.model_validate(
                order,
                from_attributes=True,
            ),
            transaction=Transaction.model_validate(
                transaction,
                from_attributes=True,
            ),
            return_record=(
                Return.model_validate(
                    return_record,
                    from_attributes=True,
                )
                if return_record is not None
                else None
            ),
            storage_location=location.storage_location,
            version=location.version,
        )

    async def get_by_order_id(
        self,
        order_id: str,
    ) -> RecordResponse | None:
        statement = self._build_query().where(
            OrderDB.order_id == order_id
        )

        result = await self.session.execute(statement)
        row = result.one_or_none()

        if row is None:
            return None

        return self._to_response(row)

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RecordResponse]:
        statement = (
            self._build_query()
            .order_by(OrderDB.order_id)
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(statement)

        return [
            self._to_response(row)
            for row in result.all()
        ]

    async def _insert_entity_if_missing(
        self,
        model,
        values: dict,
        key: str,
    ) -> None:
        statement = (
            pg_insert(model)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[key])
        )

        await self.session.execute(statement)

    async def create(
        self,
        record: RecordResponse,
    ) -> RecordResponse:
        if record.storage_location not in ("POSTGRESQL", "BOTH"):
            raise ValueError(
                "PostgreSQL cannot create a record stored only in MongoDB."
            )

        if record.order.order_id != record.transaction.order_id:
            raise ValueError(
                "Order ID and transaction Order ID must match."
            )

        existing = await self.session.scalar(
            select(OrderDB.order_id).where(
                OrderDB.order_id == record.order.order_id
            )
        )

        if existing is not None:
            raise ValueError(
                f"Order '{record.order.order_id}' already exists."
            )

        await self._insert_entity_if_missing(
            CustomerDB,
            record.customer.model_dump(),
            "customer_id",
        )

        await self._insert_entity_if_missing(
            StoreDB,
            record.store.model_dump(),
            "store_id",
        )

        await self._insert_entity_if_missing(
            SalesRepresentativeDB,
            record.sales_representative.model_dump(),
            "sales_representative_id",
        )

        await self._insert_entity_if_missing(
            ProductDB,
            record.product.model_dump(),
            "product_id",
        )

        if record.promotion is not None:
            await self._insert_entity_if_missing(
                PromotionDB,
                record.promotion.model_dump(),
                "promotion_code",
            )

        await self.session.execute(
            pg_insert(OrderDB).values(
                **record.order.model_dump()
            )
        )

        await self.session.execute(
            pg_insert(TransactionDB).values(
                **record.transaction.model_dump()
            )
        )

        if record.return_record is not None:
            await self.session.execute(
                pg_insert(ReturnDB).values(
                    **record.return_record.model_dump()
                )
            )

        await self.session.execute(
            pg_insert(RecordLocationDB).values(
                order_id=record.order.order_id,
                storage_location=record.storage_location,
                version=record.version,
            )
        )

        return record

    async def _update_entity(
        self,
        model,
        values: dict,
        key: str,
    ) -> None:
        statement = (
            update(model)
            .where(getattr(model, key) == values[key])
            .values(**values)
        )

        result = await self.session.execute(statement)

        if result.rowcount != 1:
            raise ValueError(
                f"Related entity '{values[key]}' was not found."
            )

    async def update(
        self,
        record: RecordResponse,
    ) -> RecordResponse:
        if record.storage_location not in ("POSTGRESQL", "BOTH"):
            raise ValueError(
                "PostgreSQL cannot update a record stored only in MongoDB."
            )

        if record.order.order_id != record.transaction.order_id:
            raise ValueError(
                "Order ID and transaction Order ID must match."
            )

        if record.return_record is not None:
            if record.return_record.order_id != record.order.order_id:
                raise ValueError(
                    "Return Order ID must match the Order ID."
                )

        existing = await self.get_by_order_id(
            record.order.order_id
        )

        if existing is None:
            raise ValueError(
                f"Order '{record.order.order_id}' does not exist."
            )

        if existing.storage_location != record.storage_location:
            raise ValueError(
                "Storage location cannot be changed by this repository."
            )

        if existing.order.customer_id != record.order.customer_id:
            raise ValueError("Customer ID cannot be changed.")

        if existing.order.store_id != record.order.store_id:
            raise ValueError("Store ID cannot be changed.")

        if (
            existing.order.sales_representative_id
            != record.order.sales_representative_id
        ):
            raise ValueError(
                "Sales representative ID cannot be changed."
            )

        if existing.order.promotion_code != record.order.promotion_code:
            raise ValueError("Promotion code cannot be changed.")

        if (
            existing.transaction.transaction_id
            != record.transaction.transaction_id
        ):
            raise ValueError("Transaction ID cannot be changed.")

        if existing.transaction.product_id != record.transaction.product_id:
            raise ValueError("Product ID cannot be changed.")

        if record.version != existing.version:
            raise ValueError(
                "Version conflict: the record has been modified."
            )

        await self._update_entity(
            CustomerDB,
            record.customer.model_dump(),
            "customer_id",
        )

        await self._update_entity(
            StoreDB,
            record.store.model_dump(),
            "store_id",
        )

        await self._update_entity(
            SalesRepresentativeDB,
            record.sales_representative.model_dump(),
            "sales_representative_id",
        )

        await self._update_entity(
            ProductDB,
            record.product.model_dump(),
            "product_id",
        )

        if record.promotion is not None:
            await self._update_entity(
                PromotionDB,
                record.promotion.model_dump(),
                "promotion_code",
            )

        await self._update_entity(
            OrderDB,
            record.order.model_dump(),
            "order_id",
        )

        await self._update_entity(
            TransactionDB,
            record.transaction.model_dump(),
            "transaction_id",
        )

        if record.return_record is None:
            await self.session.execute(
                delete(ReturnDB).where(
                    ReturnDB.order_id == record.order.order_id
                )
            )
        elif existing.return_record is None:
            await self.session.execute(
                pg_insert(ReturnDB).values(
                    **record.return_record.model_dump()
                )
            )
        else:
            await self._update_entity(
                ReturnDB,
                record.return_record.model_dump(),
                "order_id",
            )

        version_statement = (
            update(RecordLocationDB)
            .where(
                RecordLocationDB.order_id == record.order.order_id,
                RecordLocationDB.version == record.version,
            )
            .values(version=RecordLocationDB.version + 1)
        )

        version_result = await self.session.execute(
            version_statement
        )

        if version_result.rowcount != 1:
            raise ValueError(
                "Version conflict: the record has been modified."
            )

        return record.model_copy(
            update={"version": record.version + 1}
        )

    async def delete(
        self,
        order_id: str,
        expected_version: int,
    ) -> bool:
        location = await self.session.scalar(
            select(RecordLocationDB).where(
                RecordLocationDB.order_id == order_id
            )
        )

        if location is None:
            raise ValueError(
                f"Order '{order_id}' does not exist in PostgreSQL."
            )

        if location.storage_location not in ("POSTGRESQL", "BOTH"):
            raise ValueError(
                "This record is not stored in PostgreSQL."
            )

        if location.version != expected_version:
            raise ValueError(
                "Version conflict: the record has been modified."
            )

        await self.session.execute(
            delete(TransactionDB).where(
                TransactionDB.order_id == order_id
            )
        )

        await self.session.execute(
            delete(ReturnDB).where(
                ReturnDB.order_id == order_id
            )
        )

        order_result = await self.session.execute(
            delete(OrderDB).where(
                OrderDB.order_id == order_id
            )
        )

        if order_result.rowcount != 1:
            raise ValueError(
                f"Order '{order_id}' could not be deleted."
            )

        await self.session.execute(
            delete(RecordLocationDB).where(
                RecordLocationDB.order_id == order_id
            )
        )

        return True

    async def get_storage_location(
        self,
        order_id: str,
    ) -> RecordLocationDB | None:
        statement = select(RecordLocationDB).where(
            RecordLocationDB.order_id == order_id
        )

        return await self.session.scalar(statement)

    async def get_all_storage_locations(
        self,
    ) -> list[RecordLocationDB]:
        statement = (
            select(RecordLocationDB)
            .order_by(RecordLocationDB.order_id)
        )

        result = await self.session.scalars(statement)

        return list(result.all())
