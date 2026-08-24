from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from weather_gpt.db.session import get_db
from weather_gpt.models.historical_weather import HistoricalWeather
from weather_gpt.schemas.weather import CurrentWeatherResponse, ForecastResponse, HistoricalWeatherResponse
from weather_gpt.services.imd_service import imd_client

router = APIRouter(prefix="/weather", tags=["Weather Intelligence"])

@router.get("/current", response_model=CurrentWeatherResponse)
async def get_current_weather(
    city: str = Query("New Delhi", description="Name of the city or district in India"),
    lat: float = Query(28.6139, description="Latitude"),
    lon: float = Query(77.2090, description="Longitude")
):
    """Retrieve current weather data using the cached IMD wrapper service."""
    return await imd_client.get_current_weather(location_name=city, lat=lat, lon=lon)

@router.get("/forecast", response_model=ForecastResponse)
async def get_weather_forecast(
    city: str = Query("New Delhi", description="Name of the city or district in India"),
    lat: float = Query(28.6139, description="Latitude"),
    lon: float = Query(77.2090, description="Longitude"),
    days: int = Query(5, ge=1, le=10, description="Forecast horizon in days")
):
    """Retrieve multi-day forecast using the cached IMD wrapper service."""
    return await imd_client.get_forecast(location_name=city, lat=lat, lon=lon, days=days)

@router.get("/historical", response_model=List[HistoricalWeatherResponse])
async def get_historical_records(
    location_id: Optional[int] = Query(None, description="Location ID to filter historical logs"),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Query historical weather database records for climate analysis."""
    stmt = select(HistoricalWeather)
    if location_id:
        stmt = stmt.where(HistoricalWeather.location_id == location_id)
    stmt = stmt.order_by(HistoricalWeather.record_timestamp.desc()).limit(limit)
    
    result = await db.execute(stmt)
    return result.scalars().all()
