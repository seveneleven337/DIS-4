from pydantic import BaseModel, ConfigDict


class LogicalModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )
