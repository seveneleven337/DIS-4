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
from app.schemas.filters import RecordFilters
from app.schemas.record import RecordResponse, RecordUpdate


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

    def _apply_filters(self, statement, filters: RecordFilters):
        exact_filters = {
            "order_id": OrderDB.order_id,
            "customer_id": CustomerDB.customer_id,
            "product_id": ProductDB.product_id,
            "store_id": StoreDB.store_id,
            "sales_representative_id": (
                OrderDB.sales_representative_id
            ),
            "promotion_code": OrderDB.promotion_code,
            "order_status": OrderDB.order_status,
            "sales_channel": OrderDB.sales_channel,
            "payment_method": OrderDB.payment_method,
            "shipping_method": OrderDB.shipping_method,
        }

        for field, column in exact_filters.items():
            value = getattr(filters, field)

            if value is not None:
                statement = statement.where(column == value)

        text_filters = {
            "customer_name": CustomerDB.customer_name,
            "customer_segment": CustomerDB.customer_segment,
            "product_name": ProductDB.product_name,
            "product_category": ProductDB.product_category,
            "country": StoreDB.country,
            "region": StoreDB.region,
            "city": StoreDB.city,
        }

        for field, column in text_filters.items():
            value = getattr(filters, field)

            if value is not None:
                statement = statement.where(
                    column.ilike(f"%{value}%")
                )

        if filters.order_date_from is not None:
            statement = statement.where(
                OrderDB.order_date >= filters.order_date_from
            )

        if filters.order_date_to is not None:
            statement = statement.where(
                OrderDB.order_date <= filters.order_date_to
            )

        if filters.has_return is True:
            statement = statement.where(
                ReturnDB.order_id.is_not(None)
            )
        elif filters.has_return is False:
            statement = statement.where(
                ReturnDB.order_id.is_(None)
            )

        return statement

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
        filters: RecordFilters | None = None,
    ) -> list[RecordResponse]:
        statement = self._build_query()

        if filters is not None:
            statement = self._apply_filters(statement, filters)

        statement = (
            statement
            .order_by(OrderDB.order_id)
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(statement)

        return [
            self._to_response(row)
            for row in result.all()
        ]

    async def get_affected_order_ids(
        self,
        order_id: str,
        customer_id: str | None = None,
        store_id: str | None = None,
        sales_representative_id: int | None = None,
        product_id: str | None = None,
    ) -> list[str]:
        from sqlalchemy import or_

        conditions = [
            OrderDB.order_id == order_id,
        ]

        if customer_id is not None:
            conditions.append(
                OrderDB.customer_id == customer_id
            )

        if store_id is not None:
            conditions.append(
                OrderDB.store_id == store_id
            )

        if sales_representative_id is not None:
            conditions.append(
                OrderDB.sales_representative_id
                == sales_representative_id
            )

        if product_id is not None:
            conditions.append(
                TransactionDB.product_id == product_id
            )

        statement = (
            select(OrderDB.order_id)
            .select_from(OrderDB)
            .join(
                RecordLocationDB,
                OrderDB.order_id == RecordLocationDB.order_id,
            )
            .join(
                TransactionDB,
                OrderDB.order_id == TransactionDB.order_id,
            )
            .where(
                RecordLocationDB.storage_location.in_(
                    ["POSTGRESQL", "BOTH"]
                ),
                or_(*conditions),
            )
            .distinct()
            .order_by(OrderDB.order_id)
        )

        result = await self.session.scalars(statement)

        return list(result.all())

    async def lock_storage_locations(
        self,
        order_ids: list[str],
    ) -> list[RecordLocationDB]:
        ordered_ids = sorted(set(order_ids))

        if not ordered_ids:
            return []

        statement = (
            select(RecordLocationDB)
            .where(
                RecordLocationDB.order_id.in_(ordered_ids)
            )
            .order_by(RecordLocationDB.order_id)
            .with_for_update()
        )

        result = await self.session.scalars(statement)
        locations = list(result.all())

        found_ids = {
            location.order_id
            for location in locations
        }

        missing_ids = sorted(set(ordered_ids) - found_ids)

        if missing_ids:
            raise ValueError(
                "Storage metadata not found for orders: "
                + ", ".join(missing_ids)
            )

        return locations

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
        entity_id = values[key]

        statement = (
            update(model)
            .where(getattr(model, key) == entity_id)
            .values(**values)
        )

        result = await self.session.execute(statement)

        if result.rowcount != 1:
            raise ValueError(
                f"Related entity '{entity_id}' was not found."
            )

    async def update_shared_entities(
        self,
        record: RecordUpdate,
        existing: RecordResponse,
    ) -> None:
        entities = (
            (
                CustomerDB,
                record.customer,
                existing.customer,
                "customer_id",
            ),
            (
                StoreDB,
                record.store,
                existing.store,
                "store_id",
            ),
            (
                SalesRepresentativeDB,
                record.sales_representative,
                existing.sales_representative,
                "sales_representative_id",
            ),
            (
                ProductDB,
                record.product,
                existing.product,
                "product_id",
            ),
        )

        for model, new_entity, old_entity, key in entities:
            if new_entity == old_entity:
                continue

            entity_id = getattr(new_entity, key)
            existing_entity = await self.session.get(
                model,
                entity_id,
            )

            if existing_entity is None:
                continue

            await self._update_entity(
                model,
                new_entity.model_dump(),
                key,
            )

    async def update_order_data(
        self,
        record: RecordUpdate,
    ) -> None:
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

        existing_return = await self.session.scalar(
            select(ReturnDB.order_id).where(
                ReturnDB.order_id == record.order.order_id
            )
        )

        if record.return_record is None:
            if existing_return is not None:
                await self.session.execute(
                    delete(ReturnDB).where(
                        ReturnDB.order_id == record.order.order_id
                    )
                )

        elif existing_return is None:
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

    async def increment_storage_versions(
        self,
        expected_versions: dict[str, int],
    ) -> dict[str, int]:
        if not expected_versions:
            return {}

        new_versions = {}

        for order_id in sorted(expected_versions):
            expected_version = expected_versions[order_id]

            if (
                isinstance(expected_version, bool)
                or not isinstance(expected_version, int)
                or expected_version < 1
            ):
                raise ValueError(
                    f"Invalid expected version for order '{order_id}'."
                )

            statement = (
                update(RecordLocationDB)
                .where(
                    RecordLocationDB.order_id == order_id,
                    RecordLocationDB.version == expected_version,
                )
                .values(
                    version=RecordLocationDB.version + 1
                )
            )

            result = await self.session.execute(statement)

            if result.rowcount != 1:
                raise ValueError(
                    f"Version conflict for order '{order_id}'."
                )

            new_versions[order_id] = expected_version + 1

        return new_versions

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

    async def create_storage_location(
        self,
        order_id: str,
        storage_location: str,
        version: int = 1,
    ) -> None:
        if storage_location != "MONGODB":
            raise ValueError(
                "Metadata-only creation is reserved for MONGODB records."
            )

        if version < 1:
            raise ValueError(
                "Version must be greater than or equal to 1."
            )

        existing = await self.get_storage_location(order_id)

        if existing is not None:
            raise ValueError(
                f"Metadata for order '{order_id}' already exists."
            )

        await self.session.execute(
            pg_insert(RecordLocationDB).values(
                order_id=order_id,
                storage_location=storage_location,
                version=version,
            )
        )

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

    async def lock_storage_location(
        self,
        order_id: str,
    ) -> RecordLocationDB | None:
        statement = (
            select(RecordLocationDB)
            .where(RecordLocationDB.order_id == order_id)
            .with_for_update()
        )

        return await self.session.scalar(statement)

    async def delete_storage_location(
        self,
        order_id: str,
        expected_version: int,
    ) -> bool:
        result = await self.session.execute(
            delete(RecordLocationDB).where(
                RecordLocationDB.order_id == order_id,
                RecordLocationDB.storage_location == "MONGODB",
                RecordLocationDB.version == expected_version,
            )
        )

        if result.rowcount != 1:
            raise ValueError(
                f"Could not delete metadata for order '{order_id}'."
            )

        return True
