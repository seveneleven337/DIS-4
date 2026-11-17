from pydantic import Field

from app.models.base import LogicalModel


class Product(LogicalModel):
    product_id: str = Field(min_length=1, max_length=50)
    product_name: str = Field(min_length=1, max_length=255)
    product_category: str = Field(min_length=1, max_length=100)
    product_subcategory: str | None = Field(
        default=None,
        max_length=100,
    )