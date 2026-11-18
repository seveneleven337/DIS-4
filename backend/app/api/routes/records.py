from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.mongodb.database import database
from app.api.dependencies import get_postgresql_session
from app.schemas.filters import RecordFilters
from app.schemas.record import (
    RecordCreate,
    RecordResponse,
    RecordUpdate,
)
from app.services.distributed import DistributedRecordService


router = APIRouter(
    prefix="/records",
    tags=["Records"],
)


@router.post(
    "",
    response_model=RecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_record(
    record: RecordCreate,
    session: AsyncSession = Depends(get_postgresql_session),
):
    service = DistributedRecordService(
        session=session,
        mongodb_database=database,
    )

    try:
        return await service.create(record)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.put(
    "/{order_id}",
    response_model=RecordResponse,
)
async def update_record(
    order_id: str,
    record: RecordUpdate,
    session: AsyncSession = Depends(get_postgresql_session),
):
    service = DistributedRecordService(
        session=session,
        mongodb_database=database,
    )

    try:
        return await service.update(
            order_id=order_id,
            record=record,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[RecordResponse],
)
async def get_records(
    source: Literal["ALL", "POSTGRESQL", "MONGODB"] = Query(
        default="ALL"
    ),
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    order_id: str | None = None,
    customer_id: str | None = None,
    customer_name: str | None = None,
    customer_segment: str | None = None,
    product_id: str | None = None,
    product_name: str | None = None,
    product_category: str | None = None,
    store_id: str | None = None,
    country: str | None = None,
    region: str | None = None,
    city: str | None = None,
    sales_representative_id: int | None = None,
    promotion_code: str | None = None,
    order_status: str | None = None,
    sales_channel: str | None = None,
    payment_method: str | None = None,
    shipping_method: str | None = None,
    order_date_from: date | None = None,
    order_date_to: date | None = None,
    has_return: bool | None = None,
    session: AsyncSession = Depends(get_postgresql_session),
):
    try:
        filters = RecordFilters(
            order_id=order_id,
            customer_id=customer_id,
            customer_name=customer_name,
            customer_segment=customer_segment,
            product_id=product_id,
            product_name=product_name,
            product_category=product_category,
            store_id=store_id,
            country=country,
            region=region,
            city=city,
            sales_representative_id=sales_representative_id,
            promotion_code=promotion_code,
            order_status=order_status,
            sales_channel=sales_channel,
            payment_method=payment_method,
            shipping_method=shipping_method,
            order_date_from=order_date_from,
            order_date_to=order_date_to,
            has_return=has_return,
        )

        service = DistributedRecordService(
            session=session,
            mongodb_database=database,
        )

        return await service.get_all(
            source=source,
            limit=limit,
            offset=offset,
            filters=filters,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "/{order_id}",
    response_model=RecordResponse,
)
async def get_record_by_order_id(
    order_id: str,
    session: AsyncSession = Depends(get_postgresql_session),
):
    service = DistributedRecordService(
        session=session,
        mongodb_database=database,
    )

    record = await service.get_by_order_id(order_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record {order_id} not found",
        )

    return record


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_record(
    order_id: str,
    expected_version: Annotated[int, Query(gt=0)],
    session: AsyncSession = Depends(get_postgresql_session),
):
    service = DistributedRecordService(
        session=session,
        mongodb_database=database,
    )

    try:
        await service.delete(
            order_id=order_id,
            expected_version=expected_version,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
