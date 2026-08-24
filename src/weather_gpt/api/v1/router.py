from fastapi import APIRouter
from weather_gpt.api.v1.auth import router as auth_router
from weather_gpt.api.v1.locations import router as locations_router
from weather_gpt.api.v1.weather import router as weather_router
from weather_gpt.api.v1.alerts import router as alerts_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(locations_router)
api_router.include_router(weather_router)
api_router.include_router(alerts_router)

