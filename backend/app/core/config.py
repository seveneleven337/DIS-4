
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = Field(validation_alias="POSTGRES_DB")
    postgres_user: str = Field(validation_alias="POSTGRES_USER")
    postgres_password: SecretStr = Field(
        validation_alias="POSTGRES_PASSWORD"
    )

    mongo_host: str = "mongodb"
    mongo_port: int = 27017
    mongo_db: str = Field(
        validation_alias="MONGO_INITDB_DATABASE"
    )
    mongo_username: str = Field(
        validation_alias="MONGO_INITDB_ROOT_USERNAME"
    )
    mongo_password: SecretStr = Field(
        validation_alias="MONGO_INITDB_ROOT_PASSWORD"
    )


settings = Settings()
