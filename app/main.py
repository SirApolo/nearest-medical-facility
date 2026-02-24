from fastapi import FastAPI
from app.api import endpoints
from app.db.database import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Healthcare Spatial Intelligence API - Brazil",
    description="API for healthcare units in Brazil using PostGIS",
    version="1.0.0"
)

app.include_router(endpoints.router)

@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Welcome to Healthcare Spatial Intelligence API - Brazil"}
