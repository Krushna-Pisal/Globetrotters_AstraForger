"""FastAPI application. Monitoring only: no route writes commands to equipment or source systems (invariant 12)."""

from fastapi import FastAPI

from app.api import auth, health

app = FastAPI(title="PS4 Performance Assurance Platform", version="0.1.0")
app.include_router(health.router)
app.include_router(auth.router)
