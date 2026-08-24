from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any

class ActiveAlert(BaseModel):
    event: str = "weather_alert"
    alert_id: str
    district: str
    severity: str
    title: str
    message: str
    action: str
    valid_until: datetime

class CurrentWeatherResponse(BaseModel):
    location: str
    latitude: float
    longitude: float
    temperature: float  # °C
    feels_like: float   # °C
    humidity: float     # %
    pressure: float     # hPa
    wind_speed: float   # km/h
    wind_direction: str
    weather_condition: str
    description: str
    active_alerts: List[ActiveAlert] = []
    source: str = "IMD"
    cached: bool = False
    timestamp: datetime

class ForecastDay(BaseModel):
    date: str
    max_temp: float
    min_temp: float
    rainfall_probability: float
    condition: str
    warning: Optional[str] = None

class ForecastResponse(BaseModel):
    location: str
    latitude: float
    longitude: float
    forecast: List[ForecastDay]
    active_alerts: List[ActiveAlert] = []
    source: str = "IMD"
    cached: bool = False

class HistoricalWeatherResponse(BaseModel):
    id: int
    location_id: int
    record_timestamp: datetime
    temperature: float
    humidity: Optional[float] = None
    rainfall: float
    pressure: Optional[float] = None
    wind_speed: Optional[float] = None
    weather_condition: str
    source: str
    raw_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

