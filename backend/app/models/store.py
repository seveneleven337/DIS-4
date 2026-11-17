from pydantic import Field

from app.models.base import LogicalModel


class Store(LogicalModel):
    store_id: str = Field(min_length=1, max_length=50)
    store_name: str = Field(min_length=1, max_length=255)
    country: str = Field(min_length=1, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)