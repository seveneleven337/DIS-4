from pydantic import Field

from app.models.base import LogicalModel


class Customer(LogicalModel):
    customer_id: str = Field(min_length=1, max_length=50)
    customer_name: str = Field(min_length=1, max_length=255)
    customer_gender: str | None = Field(default=None, max_length=50)
    customer_segment: str | None = Field(default=None, max_length=100)