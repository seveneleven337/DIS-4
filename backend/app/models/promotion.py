from pydantic import Field

from app.models.base import LogicalModel


class Promotion(LogicalModel):
    promotion_code: str = Field(min_length=1, max_length=100)