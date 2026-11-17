from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
    )

    postgres_host: str = "postgres"
    postgres_port: int = Field(
        default=5432,
        validation_alias="POSTGRES_INTERNAL_PORT",
    )
    postgres_db: str = Field(validation_alias="POSTGRES_DB")
    postgres_user: str = Field(validation_alias="POSTGRES_USER")
    postgres_password: SecretStr = Field(
        validation_alias="POSTGRES_PASSWORD"
    )


settings = Settings()
