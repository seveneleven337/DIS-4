from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pymongo.errors import PyMongoError
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.mongodb.database import (
    check_mongodb_connection,
    close_mongodb_connection,
)
from app.adapters.mongodb.schema import create_mongodb_schema
from app.adapters.mongodb.seeds import seed_mongodb_records
from app.adapters.postgresql.database import (
    check_postgresql_connection,
    close_postgresql_connection,
)
from app.adapters.postgresql.schema import create_database_schema
from app.api.routes.records import router as records_router
from app.loaders.postgresql_seed import seed_postgresql


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Initialize database schemas.
        await create_database_schema()
        await create_mongodb_schema()

        # Insert initial data without overwriting existing records.
        await seed_postgresql()
        await seed_mongodb_records()

        yield
    finally:
        try:
            await close_mongodb_connection()
        finally:
            await close_postgresql_connection()


app = FastAPI(
    title="Distributed Database Project API",
    description="Backend API for a distributed SQL and NoSQL database system.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(
    records_router,
    prefix="/api",
)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "distributed-database-project-api",
    }


@app.get("/health/postgresql", tags=["Health"])
async def postgresql_health_check():
    try:
        await check_postgresql_connection()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL is unavailable",
        ) from exc

    return {
        "status": "healthy",
        "database": "postgresql",
    }


@app.get("/health/mongodb", tags=["Health"])
async def mongodb_health_check():
    try:
        await check_mongodb_connection()
    except PyMongoError as exc:
        raise HTTPException(
            status_code=503,
            detail="MongoDB is unavailable",
        ) from exc

    return {
        "status": "healthy",
        "database": "mongodb",
    }
