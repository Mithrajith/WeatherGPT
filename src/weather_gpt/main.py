import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from weather_gpt.config import settings
from weather_gpt.db.session import init_db
from weather_gpt.api.v1.router import api_router

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("weather_gpt")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing WeatherGPT Backend Service...")
    await init_db()
    logger.info("Database schemas initialized successfully.")
    yield
    logger.info("Shutting down WeatherGPT Backend Service...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Conversational AI Backend for Weather Forecasting, Extreme Alerts, and IMD Meteorological Integration.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Welcome to WeatherGPT API Service",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("weather_gpt.main:app", host="0.0.0.0", port=8000, reload=True)
