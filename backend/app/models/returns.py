from pydantic import Field

from app.models.base import LogicalModel


class Return(LogicalModel):
    order_id: str = Field(min_length=1, max_length=50)
    return_reason: str | None = None