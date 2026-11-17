from fastapi import FastAPI


app = FastAPI(
    title="Distributed Database Project API",
    description="Backend API for a distributed SQL and NoSQL database system.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "distributed-database-project-api",
    }
