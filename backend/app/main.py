
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.postgresql.database import (
    check_postgresql_connection,
    close_postgresql_connection,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_postgresql_connection()


app = FastAPI(
    title="Distributed Database Project API",
    description="Backend API for a distributed SQL and NoSQL database system.",
    version="0.1.0",
    lifespan=lifespan,
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
