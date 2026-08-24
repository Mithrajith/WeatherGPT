from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from weather_gpt.db.base import Base
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from weather_gpt.models.location import Location

class HistoricalWeather(Base):
    __tablename__ = "historical_weather"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True)
    record_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    temperature: Mapped[float] = mapped_column(Float, nullable=False)  # in Celsius
    humidity: Mapped[float] = mapped_column(Float, nullable=True)     # percentage %
    rainfall: Mapped[float] = mapped_column(Float, default=0.0, nullable=False) # mm
    pressure: Mapped[float] = mapped_column(Float, nullable=True)     # hPa
    wind_speed: Mapped[float] = mapped_column(Float, nullable=True)   # km/h
    weather_condition: Mapped[str] = mapped_column(String(100), default="Clear", nullable=False)
    
    source: Mapped[str] = mapped_column(String(50), default="IMD", nullable=False)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    location: Mapped["Location"] = relationship("Location", back_populates="historical_records")

    def __repr__(self) -> str:
        return f"<HistoricalWeather(id={self.id}, location_id={self.location_id}, temp={self.temperature}°C)>"
