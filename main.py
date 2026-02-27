from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from database.session import engine
from database.models import Base
from api import router as api_router, limiter
import os

# Create Database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener API")

# Rate limiter setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include separated API routes
app.include_router(api_router)

# Mount static files (this serves index.html at / and stats.html at /stats.html)
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
