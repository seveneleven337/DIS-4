from pydantic import Field

from app.models.base import LogicalModel


class SalesRepresentative(LogicalModel):
    sales_representative_id: int | None = Field(default=None, gt=0)
    sales_representative_name: str = Field(
        min_length=1,
        max_length=255,
    )